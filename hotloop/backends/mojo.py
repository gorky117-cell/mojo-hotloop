# Copyright 2026 Gaurav Kumar Singh
# SPDX-License-Identifier: Apache-2.0
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from typing import Optional, Tuple

from .base import BaseBackend
from ..ast_transpiler import transpile_python_to_mojo, ASTTranspileError

TRANSPILER_VERSION = "0.2.0-ast"


def _atomic_write_text(target_path: str, content: str) -> None:
    dir_name = os.path.dirname(os.path.abspath(target_path))
    os.makedirs(dir_name, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(dir=dir_name, prefix=".tmp_", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(content)
        os.replace(tmp_path, target_path)
    except Exception:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise


class MojoBackend(BaseBackend):
    def __init__(self, mojo_bin: Optional[str] = None):
        self.mojo_bin = mojo_bin or self._find_mojo()
        self._compiler_version: Optional[str] = None

    def _get_subprocess_env(self) -> dict:
        env = os.environ.copy()
        venv_dir = os.path.dirname(os.path.dirname(os.path.abspath(sys.executable)))
        if os.path.isfile(os.path.join(venv_dir, "pyvenv.cfg")):
            env["VIRTUAL_ENV"] = venv_dir
        # Sanitize PYTHONEXECUTABLE: Mojo C-runtime initialization can set PYTHONEXECUTABLE
        # to system python (e.g. /usr/bin/python3), which breaks virtualenv Python scripts like .venv/bin/mojo.
        if "PYTHONEXECUTABLE" in env and env["PYTHONEXECUTABLE"] != sys.executable:
            env["PYTHONEXECUTABLE"] = sys.executable
        return env

    def get_compiler_version(self) -> str:
        if self._compiler_version is None:
            try:
                proc = subprocess.run([self.mojo_bin, "--version"], capture_output=True, text=True, env=self._get_subprocess_env())
                self._compiler_version = proc.stdout.strip() or "mojo unknown"
            except Exception:
                self._compiler_version = "mojo unknown"
        return self._compiler_version

    def _write_build_metadata(self, file_path: str, mod_name: str, so_path: str) -> None:
        dir_name = os.path.dirname(os.path.abspath(file_path))
        with open(file_path, "rb") as f:
            source_bytes = f.read()
        source_hash = hashlib.sha256(source_bytes).hexdigest()

        with open(so_path, "rb") as f:
            so_hash = hashlib.sha256(f.read()).hexdigest()

        manifest_path = os.path.join(dir_name, f"{mod_name}.hotloop_manifest.json")
        manifest_data = {
            "source_file": os.path.basename(file_path),
            "source_sha256": source_hash,
            "so_sha256": so_hash,
            "compiler_version": self.get_compiler_version(),
            "transpiler_version": TRANSPILER_VERSION,
            "build_timestamp": time.time(),
        }
        _atomic_write_text(manifest_path, json.dumps(manifest_data, indent=2))

        # Content-addressed cache directory (atomic copy + replace)
        cache_dir = os.path.join(dir_name, "__mojocache__")
        os.makedirs(cache_dir, exist_ok=True)
        cached_so_path = os.path.join(cache_dir, f"{mod_name}_{source_hash[:16]}.so")
        fd, tmp_cache = tempfile.mkstemp(dir=cache_dir, prefix=f".{mod_name}_", suffix=".so.tmp")
        os.close(fd)
        try:
            shutil.copy2(so_path, tmp_cache)
            os.replace(tmp_cache, cached_so_path)
        except OSError:
            try:
                os.unlink(tmp_cache)
            except OSError:
                pass

    def _find_mojo(self) -> str:
        # 1. Explicit MOJO_BIN override
        env_mojo = os.environ.get("MOJO_BIN", "").strip()
        if env_mojo and os.path.isfile(env_mojo) and os.access(env_mojo, os.X_OK):
            return env_mojo

        # 2. Same environment/venv bin directory as active Python interpreter
        py_bin_mojo = os.path.join(os.path.dirname(os.path.abspath(sys.executable)), "mojo")
        if os.path.isfile(py_bin_mojo) and os.access(py_bin_mojo, os.X_OK):
            return py_bin_mojo

        # 3. Standard PATH lookup
        which_mojo = shutil.which("mojo")
        if which_mojo:
            return which_mojo

        # 4. Standard Modular install location
        modular_mojo = os.path.expanduser("~/.modular/bin/mojo")
        if os.path.isfile(modular_mojo) and os.access(modular_mojo, os.X_OK):
            return modular_mojo

        return "mojo"

    def compile_mojo(self, mojo_path: str, so_path: str) -> Tuple[bool, str]:
        dir_name = os.path.dirname(os.path.abspath(so_path))
        os.makedirs(dir_name, exist_ok=True)
        fd, tmp_so = tempfile.mkstemp(dir=dir_name, prefix=".build_", suffix=".so")
        os.close(fd)
        cmd = [self.mojo_bin, "build", "-O3", mojo_path, "--emit", "shared-lib", "-o", tmp_so]
        try:
            proc = subprocess.run(cmd, capture_output=True, text=True, env=self._get_subprocess_env())
            if proc.returncode == 0:
                os.replace(tmp_so, so_path)
                return True, proc.stdout
            try:
                os.unlink(tmp_so)
            except OSError:
                pass
            return False, proc.stderr
        except Exception as e:
            try:
                os.unlink(tmp_so)
            except OSError:
                pass
            return False, f"Failed to execute '{self.mojo_bin}': {e}"

    def build_ast(self, file_path: str, mod_name: str = "fast") -> Tuple[bool, str, Optional[str]]:
        with open(file_path, "r", encoding="utf-8") as f:
            source = f.read()

        try:
            mojo_code = transpile_python_to_mojo(source, mod_name)
        except ASTTranspileError as e:
            return False, f"AST Transpiler rejected code: {e}", None
        except Exception as e:
            return False, f"AST Parsing error: {e}", None

        dir_name = os.path.dirname(os.path.abspath(file_path))
        mojo_path = os.path.join(dir_name, f"{mod_name}.mojo")
        so_path = os.path.join(dir_name, f"{mod_name}.so")

        _atomic_write_text(mojo_path, mojo_code)

        ok, err = self.compile_mojo(mojo_path, so_path)
        if ok:
            self._write_build_metadata(file_path, mod_name, so_path)
            return True, f"Successfully transpiled and built {so_path} via AST engine.", so_path
        else:
            return False, f"Mojo compilation failed:\n{err}", None

    def build(self, file_path: str, engine: str = "ast") -> Tuple[bool, str, Optional[str]]:
        if engine in ("ast", "auto"):
            ok, msg, so_path = self.build_ast(file_path)
            if ok:
                return True, f"[Engine: AST] {msg}", so_path
            return False, f"[Engine: AST] {msg}", None
        elif engine == "gemini":
            return False, "The 'gemini' engine is not supported in v0.1.0; mojo-hotloop compiles strictly offline using engine='ast'.", None
        else:
            return False, f"Unknown engine '{engine}'. Choose 'ast'.", None

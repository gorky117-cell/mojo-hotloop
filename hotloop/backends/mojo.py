# Copyright 2026 Gaurav Kumar Singh
# SPDX-License-Identifier: Apache-2.0

import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
from typing import Optional, Tuple

from .base import BaseBackend
from ..ast_transpiler import transpile_python_to_mojo, ASTTranspileError
from .._native_cache import (
    BUILD_FLAGS, binary_path, build_context, build_environment, build_identity,
    checked_binary, verify_cache_directory, file_hash, find_mojo, manifest_path, read_manifest,
)

TRANSPILER_VERSION = "0.2.1-ast"


def _atomic_publish(target: Path, data: bytes) -> None:
    fd, temporary = tempfile.mkstemp(dir=target.parent, prefix=".hotloop-")
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(data)
        os.replace(temporary, target)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


class MojoBackend(BaseBackend):
    def __init__(self, mojo_bin: Optional[str] = None):
        self.mojo_bin = (shutil.which(mojo_bin) or mojo_bin) if mojo_bin else find_mojo()

    def _get_subprocess_env(self) -> dict:
        return build_environment()

    def get_compiler_version(self) -> str:
        if self.mojo_bin:
            try:
                return build_context(self.mojo_bin, self._get_subprocess_env())["compiler_version"]
            except (OSError, ValueError):
                pass
        return "mojo unknown"

    def compile_mojo(self, mojo_path: str, so_path: str, *, env=None) -> Tuple[bool, str]:
        if not self.mojo_bin:
            return False, "Mojo compiler not found"
        cmd = [self.mojo_bin, *BUILD_FLAGS, mojo_path, "-o", so_path]
        try:
            proc = subprocess.run(cmd, capture_output=True, text=True, env=env if env is not None else self._get_subprocess_env())
        except OSError as exc:
            return False, f"Failed to execute '{self.mojo_bin}': {exc}"
        return proc.returncode == 0, proc.stdout if proc.returncode == 0 else proc.stderr

    def build_ast(self, file_path: str, mod_name: str = "fast") -> Tuple[bool, str, Optional[str]]:
        source_path = Path(file_path).absolute()
        if not mod_name.isascii() or not mod_name.isidentifier():
            return False, "Native module name must be an ASCII identifier", None
        try:
            source = source_path.read_bytes()
            mojo_code = transpile_python_to_mojo(source.decode("utf-8"), mod_name).encode("utf-8")
        except ASTTranspileError as exc:
            return False, f"AST Transpiler rejected code: {exc}", None
        except (OSError, SyntaxError, UnicodeError) as exc:
            return False, f"AST Parsing error: {exc}", None

        # Keep generated source available for diagnostics even on Mojo failures.
        try:
            verify_cache_directory(source_path.parent)
            _atomic_publish(source_path.with_name(f"{mod_name}.mojo"), mojo_code)
            if not self.mojo_bin:
                return False, "Mojo compiler not found", None
            return self._build_verified(source_path, source, mod_name, mojo_code)
        except (OSError, ValueError) as exc:
            return False, f"Native build failed: {exc}", None

    def _build_verified(self, source_path, source, mod_name, mojo_code):
        env = self._get_subprocess_env()
        context = build_context(self.mojo_bin, env)
        source_hash = hashlib.sha256(source).hexdigest()
        identity = build_identity(source_path, source_hash, mod_name, context)
        generated_hash = hashlib.sha256(mojo_code).hexdigest()
        cache_dir = source_path.parent / "__mojocache__"
        cache_dir.mkdir(mode=0o700, exist_ok=True)
        verify_cache_directory(cache_dir)
        manifest = manifest_path(cache_dir, identity, generated_hash)

        try:
            data = read_manifest(manifest)
            cached = checked_binary(manifest, data, identity)
        except (OSError, ValueError):
            cached = None

        cache_hit = cached is not None
        if not cache_hit:
            with tempfile.TemporaryDirectory(dir=source_path.parent, prefix=".hotloop-build-") as work:
                generated = Path(work) / f"{mod_name}.mojo"
                generated.write_bytes(mojo_code)
                built = Path(work) / f"{mod_name}.so"
                ok, diagnostic = self.compile_mojo(str(generated), str(built), env=env)
                if not ok:
                    # Expose the stable generated filename in compiler diagnostics.
                    return False, f"Mojo compilation failed:\n{diagnostic.replace(str(generated), str(source_path.with_name(generated.name)))}", None
                if build_context(self.mojo_bin, self._get_subprocess_env()) != context:
                    return False, "Mojo toolchain or build settings changed during compilation", None
                binary = built.read_bytes()
            if not binary.startswith(b"\x7fELF"):
                return False, "Mojo did not produce an ELF shared library", None
            data = {
                **identity,
                "compiler_version": context["compiler_version"],
                "transpiler_version": TRANSPILER_VERSION,
                "generated_sha256": generated_hash,
                "so_sha256": hashlib.sha256(binary).hexdigest(),
            }
            cached = binary_path(cache_dir, identity, data["so_sha256"])
        else:
            binary = cached.read_bytes()
            if hashlib.sha256(binary).hexdigest() != data["so_sha256"]:
                return False, "Cached native binary changed during build", None

        if file_hash(source_path) != source_hash:
            return False, "Python source changed during native compilation; build again", None

        metadata = json.dumps(data, indent=2, sort_keys=True).encode() + b"\n"
        if not cache_hit:
            if file_hash(cached) != data["so_sha256"]:
                _atomic_publish(cached, binary)
            _atomic_publish(manifest, metadata)

        # Preserve the public build artifact. Runtime dispatch reads only the
        # verified immutable cache entry, so concurrent alias updates are safe.
        so_path = source_path.with_name(f"{mod_name}.so")
        _atomic_publish(so_path, binary)
        _atomic_publish(source_path.with_name(f"{mod_name}.hotloop_manifest.json"), metadata)
        message = "Reused verified AST build" if cache_hit else "Successfully transpiled and built"
        note = next((line[2:] for line in mojo_code.decode().splitlines()
                     if line.startswith("# Python-only entries:") and line.split(":", 1)[1].strip()), "")
        return True, f"{message} {so_path} via AST engine. {note}".rstrip(), str(so_path)

    def build(self, file_path: str, engine: str = "ast") -> Tuple[bool, str, Optional[str]]:
        if engine in ("ast", "auto"):
            ok, msg, so_path = self.build_ast(file_path)
            return ok, f"[Engine: AST] {msg}", so_path
        if engine == "gemini":
            return False, "The 'gemini' engine is not supported; mojo-hotloop compiles strictly offline using engine='ast'.", None
        return False, f"Unknown engine '{engine}'. Choose 'ast'.", None

import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
from typing import Optional, Tuple
from dotenv import load_dotenv

from .base import BaseBackend
from ..ast_transpiler import transpile_python_to_mojo, ASTTranspileError

TRANSPILER_VERSION = "1.2.0-phaseC"

class MojoBackend(BaseBackend):
    def __init__(self, mojo_bin: Optional[str] = None):
        self.mojo_bin = mojo_bin or self._find_mojo()
        self._compiler_version: Optional[str] = None

    def get_compiler_version(self) -> str:
        if self._compiler_version is None:
            try:
                proc = subprocess.run([self.mojo_bin, "--version"], capture_output=True, text=True)
                self._compiler_version = proc.stdout.strip() or "mojo unknown"
            except Exception:
                self._compiler_version = "mojo unknown"
        return self._compiler_version

    def _write_build_metadata(self, file_path: str, mod_name: str, so_path: str) -> None:
        dir_name = os.path.dirname(os.path.abspath(file_path))
        with open(file_path, "rb") as f:
            source_bytes = f.read()
        source_hash = hashlib.sha256(source_bytes).hexdigest()

        manifest_path = os.path.join(dir_name, f"{mod_name}.hotloop_manifest.json")
        manifest_data = {
            "source_file": os.path.basename(file_path),
            "source_sha256": source_hash,
            "compiler_version": self.get_compiler_version(),
            "transpiler_version": TRANSPILER_VERSION,
            "build_timestamp": time.time(),
        }
        with open(manifest_path, "w", encoding="utf-8") as f:
            json.dump(manifest_data, f, indent=2)

        # Content-addressed cache directory
        cache_dir = os.path.join(dir_name, "__mojocache__")
        os.makedirs(cache_dir, exist_ok=True)
        cached_so_path = os.path.join(cache_dir, f"{mod_name}_{source_hash[:16]}.so")
        try:
            shutil.copy2(so_path, cached_so_path)
        except OSError:
            pass

    def _find_mojo(self) -> str:
        # Check venv first, then PATH
        venv_bin = os.path.expanduser("~/mojo-hotloop/.venv/bin/mojo")
        if os.path.isfile(venv_bin) and os.access(venv_bin, os.X_OK):
            return venv_bin
        return "mojo"

    def compile_mojo(self, mojo_path: str, so_path: str) -> Tuple[bool, str]:
        cmd = [self.mojo_bin, "build", mojo_path, "--emit", "shared-lib", "-o", so_path]
        proc = subprocess.run(cmd, capture_output=True, text=True)
        if proc.returncode == 0:
            return True, proc.stdout
        return False, proc.stderr

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

        with open(mojo_path, "w", encoding="utf-8") as f:
            f.write(mojo_code)

        ok, err = self.compile_mojo(mojo_path, so_path)
        if ok:
            self._write_build_metadata(file_path, mod_name, so_path)
            return True, f"Successfully transpiled and built {so_path} via AST engine.", so_path
        else:
            return False, f"Mojo compilation failed:\n{err}", None

    def build_gemini(self, file_path: str, mod_name: str = "fast") -> Tuple[bool, str, Optional[str]]:
        # Load .env
        env_path = os.path.expanduser("~/mojo-hotloop/.env")
        load_dotenv(env_path)
        api_key = os.getenv("GEMINI_API_KEY", "").strip()
        model_name = os.getenv("HOTLOOP_MODEL", "").strip()

        if not api_key or not model_name:
            return False, "STOP: .env is missing GEMINI_API_KEY or HOTLOOP_MODEL. Please configure .env to use Gemini engine.", None

        try:
            from google import genai
            from google.genai import types
        except ImportError:
            return False, "google-genai package not found. Run 'uv pip install google-genai'.", None

        # Read rules
        rules_path = os.path.expanduser("~/mojo-hotloop/MOJO_RULES.md")
        rules_text = ""
        if os.path.isfile(rules_path):
            with open(rules_path, "r", encoding="utf-8") as f:
                rules_text = f.read()

        with open(file_path, "r", encoding="utf-8") as f:
            py_source = f.read()

        dir_name = os.path.dirname(os.path.abspath(file_path))
        mojo_path = os.path.join(dir_name, f"{mod_name}.mojo")
        so_path = os.path.join(dir_name, f"{mod_name}.so")

        client = genai.Client(api_key=api_key)

        prompt = f"""You are the principal Mojo compiler engineer.
Translate this Python function into a high-performance Mojo 1.2.0 module named '{mod_name}'.
Build target: shared library (.so) for Python C-ABI.

CRITICAL RULES:
1. Module Init:
   from std.python import PythonObject
   from std.python.bindings import PythonModuleBuilder
   from std.os import abort
   
   @export
   def PyInit_{mod_name}() abi("C") -> PythonObject:
       try:
           var m = PythonModuleBuilder("{mod_name}")
           m.def_function[<fn_name>]("<fn_name>")
           return m.finalize()
       except e:
           abort(String("error creating Python Mojo module: ", e))

2. Argument Unboxing:
   def <fn_name>(arg0: PythonObject, ...) raises -> PythonObject:
       # Convert PythonObjects once upfront:
       # var a = Int(py=arg0)
       # var f = Float64(py=arg1)
       # var s = String(py=arg2)
       # Call native Mojo function that does all heavy work with 0 PythonObject operations inside loops
       # return PythonObject(result)

3. Mojo 1.2.0 Syntax:
   - Use `def` and `var`. NEVER use `let`, `@value`, `DynamicVector`, or `from python import ...`.
   - Use standard library modules with `std.` prefix.
   - Do NOT include a `main()` function.

4. Reference Guidelines:
{rules_text}

PYTHON SOURCE:
```python
{py_source}
```

Return ONLY valid Mojo source code inside a single ```mojo code block without extra markdown explanation.
"""
        max_attempts = 5
        attempt = 0
        last_error = ""

        while attempt < max_attempts:
            attempt += 1
            print(f"  [Gemini Engine] Attempt {attempt}/{max_attempts} generating Mojo code...")
            try:
                response = client.models.generate_content(
                    model=model_name,
                    contents=prompt if attempt == 1 else f"Compilation failed with error:\n{last_error}\nPlease fix the Mojo code to resolve this compiler error. Return only the full corrected Mojo source code in a ```mojo block."
                )
                text = response.text or ""
            except Exception as e:
                return False, f"Gemini API call failed: {e}", None

            # Extract code block
            mojo_code = text
            if "```mojo" in text:
                mojo_code = text.split("```mojo", 1)[1].split("```", 1)[0].strip()
            elif "```" in text:
                mojo_code = text.split("```", 1)[1].split("```", 1)[0].strip()

            with open(mojo_path, "w", encoding="utf-8") as f:
                f.write(mojo_code)

            ok, err = self.compile_mojo(mojo_path, so_path)
            if ok:
                # Check if verify.py exists
                verify_path = os.path.join(dir_name, "verify.py")
                if os.path.isfile(verify_path):
                    print("  [Gemini Engine] Compiled successfully, running isolated verification...")
                    v_proc = subprocess.run([sys.executable, verify_path], capture_output=True, text=True, timeout=30)
                    if v_proc.returncode == 0:
                        self._write_build_metadata(file_path, mod_name, so_path)
                        return True, f"Successfully built and verified {so_path} via Gemini engine on attempt {attempt}.", so_path
                    else:
                        print(f"  [Gemini Engine] Verification failed on attempt {attempt}.")
                        # Truncate counterexample to <= 256 chars (ACM/IEEE privacy guardrail)
                        clean_err = (v_proc.stdout + "\n" + v_proc.stderr).strip()[:256]
                        last_error = f"Verification failed:\n{clean_err}"
                        continue
                self._write_build_metadata(file_path, mod_name, so_path)
                return True, f"Successfully compiled {so_path} via Gemini engine on attempt {attempt}.", so_path
            else:
                print(f"  [Gemini Engine] Mojo build error on attempt {attempt}: {err.strip()[:100]}...")
                last_error = err

        if os.path.isfile(so_path):
            try:
                os.remove(so_path)
            except OSError:
                pass
        return False, f"Gemini engine failed after {max_attempts} attempts. Last error:\n{last_error}", None

    def build(self, file_path: str, engine: str = "auto") -> Tuple[bool, str, Optional[str]]:
        if engine == "ast":
            return self.build_ast(file_path)
        elif engine == "gemini":
            return self.build_gemini(file_path)
        elif engine == "auto":
            # Try AST first
            ok, msg, so_path = self.build_ast(file_path)
            if ok:
                return True, f"[Engine: AST] {msg}", so_path
            print(f"AST engine skipped/declined: {msg}. Falling back to Gemini engine...")
            ok_g, msg_g, so_g = self.build_gemini(file_path)
            if ok_g:
                return True, f"[Engine: Gemini] {msg_g}", so_g
            return False, f"Both engines failed.\nAST: {msg}\nGemini: {msg_g}", None
        else:
            return False, f"Unknown engine '{engine}'. Choose 'ast', 'gemini', or 'auto'.", None

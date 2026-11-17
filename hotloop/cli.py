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

import argparse
import os
import sys
import subprocess

from . import __version__
from .backends.mojo import MojoBackend

def main():
    parser = argparse.ArgumentParser(
        prog="hotloop",
        description="mojo-hotloop: Accelerate Python hot loops with compiled Mojo shared libraries"
    )
    parser.add_argument(
        "-v", "--version",
        action="version",
        version=f"%(prog)s {__version__}",
        help="Show program's version number and exit"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # hotloop build <file.py>
    build_parser = subparsers.add_parser("build", help="Transpile and build a hot loop shared library")
    build_parser.add_argument("file", help="Python source file containing the @hotloop function")
    build_parser.add_argument(
        "--engine",
        choices=["ast", "auto"],
        default="ast",
        help="Transpilation engine: 'ast' (deterministic offline Python AST-to-Mojo compiler, default; 'auto' aliases 'ast')"
    )
    build_parser.add_argument(
        "--backend",
        choices=["mojo"],
        default="mojo",
        help="Target compilation backend (default: mojo)"
    )
    build_parser.add_argument(
        "--no-verify",
        action="store_true",
        help="Skip automatic verification after build"
    )
    build_parser.add_argument(
        "--check-syntax", "--dry-run",
        dest="check_syntax",
        action="store_true",
        help="Perform offline AST transpilation and syntax check without invoking Mojo"
    )

    # hotloop check <file.py>
    check_parser = subparsers.add_parser("check", help="Offline syntax validation for @hotloop functions without invoking Mojo")
    check_parser.add_argument("file", help="Python source file containing the @hotloop function")

    args = parser.parse_args()

    if args.command == "check" or (args.command == "build" and getattr(args, "check_syntax", False)):
        target_file = os.path.abspath(args.file)
        if not os.path.isfile(target_file):
            print(f"Error: File '{target_file}' not found.")
            sys.exit(1)

        print(f"[*] mojo-hotloop checking syntax for '{target_file}' (offline AST engine)")
        try:
            with open(target_file, "r", encoding="utf-8") as f:
                source = f.read()
            from .ast_transpiler import transpile_python_to_mojo, ASTTranspileError
            transpile_python_to_mojo(source, mod_name="check_target")
            print("[+] Syntax check PASSED: All @hotloop functions are compatible")
            sys.exit(0)
        except ASTTranspileError as e:
            print(f"[-] Syntax check FAILED:\nASTTranspileError: {e}")
            sys.exit(1)
        except SyntaxError as e:
            print(f"[-] Syntax check FAILED:\nSyntaxError at line {e.lineno}: {e.msg}")
            sys.exit(1)
        except Exception as e:
            print(f"[-] Syntax check FAILED:\n{type(e).__name__}: {e}")
            sys.exit(1)

    if args.command == "build":
        target_file = os.path.abspath(args.file)
        if not os.path.isfile(target_file):
            print(f"Error: File '{target_file}' not found.")
            sys.exit(1)

        print(f"[*] mojo-hotloop building '{target_file}' using engine='{args.engine}', backend='{args.backend}'")

        if args.backend == "mojo":
            backend = MojoBackend()
        else:
            print(f"Error: Unsupported backend '{args.backend}'")
            sys.exit(1)

        ok, msg, so_path = backend.build(target_file, engine=args.engine)
        if not ok:
            print(f"[-] Build FAILED:\n{msg}")
            sys.exit(1)

        print(f"[+] Build SUCCESS: {msg}")
        if so_path:
            print(f"    Artifact: {so_path}")

        # Verification step if verify.py is present
        if not args.no_verify:
            target_dir = os.path.dirname(target_file)
            verify_script = os.path.join(target_dir, "verify.py")
            if os.path.isfile(verify_script):
                print(f"[*] Running isolated verification suite: {verify_script}")
                v_proc = subprocess.run([sys.executable, verify_script], capture_output=False)
                if v_proc.returncode != 0:
                    print(f"[-] Verification FAILED (exit code {v_proc.returncode})")
                    sys.exit(v_proc.returncode)
                else:
                    print("[+] Verification PASSED (0 mismatches)")

        print("[✓] Done.")

if __name__ == "__main__":
    main()

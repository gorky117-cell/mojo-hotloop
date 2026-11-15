import argparse
import os
import sys
import subprocess

from .backends.mojo import MojoBackend

def main():
    parser = argparse.ArgumentParser(
        prog="hotloop",
        description="mojo-hotloop: Accelerate Python hot loops with compiled Mojo shared libraries"
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

    args = parser.parse_args()

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

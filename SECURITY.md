# Security Policy

## Supported Versions

| Version | Supported |
|---------|-----------|
| 0.2.x (Developer Preview) | ✅ Active security support |
| 0.1.x (Developer Preview) | ⚠️ Maintenance only |

## Reporting a Vulnerability

**Do not open a public GitHub issue for security vulnerabilities.**

To report a security issue privately:

1. Go to the GitHub repository Security tab
2. Click **"Report a vulnerability"** to open a private GitHub Security Advisory
3. Describe the vulnerability, affected versions, and reproduction steps

The maintainers will acknowledge your report within **72 hours** and aim to
provide a fix or mitigation within **14 days** for critical issues.

## Scope

Security issues we care about:

- **Credential exposure**: API keys or secrets leaked via source code, git history, or build artifacts
- **Shell injection**: User-controlled input reaching `subprocess` without sanitization
- **Arbitrary file read/write**: The build CLI writing or reading files outside the project directory
- **Cache poisoning**: Maliciously crafted `.hotloop_manifest.json` files causing incorrect binary loading
- **Native memory safety**: Crashes or memory corruption in the Mojo shared library dispatch path
- **Denial of service**: Transpiler or decorator causing unbounded memory or CPU consumption on adversarial inputs

## Out of Scope

- Vulnerabilities in the Mojo compiler itself (report to [Modular](https://www.modular.com/security))
- Vulnerabilities in Python itself
- Issues requiring physical access to the machine

## Security Design Notes

- Offline-by-design: The compiler builds and runs completely offline with zero network calls or AI API keys; `.gitignore` excludes local `.env` files
- All `subprocess` calls use list-form arguments, never `shell=True`
- No `eval()` or `exec()` on user inputs; AST transpiler uses Python's `ast.parse()` on source text
- The `mojo` compiler binary path (`MOJO_BIN` / venv / `PATH`) is validated to exist before invocation
- v0.2.1 validates cache ownership, build context, and the binary digest before loading through a pinned Linux file descriptor. Trust the source directory, installed package, compiler and running user account.
- Buffer exporters and NumPy objects use Python. Native list kernels operate on private copies of validated built-in elements.
- Compilation writes `.mojo`, `.so`, and manifests atomically via temp files + `os.replace`
- Thread-safe module cache (`threading.Lock`) guards shared module loading and fallback warnings

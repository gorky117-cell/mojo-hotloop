---
name: Compiler Bug Report
about: Report incorrect transpiler output, failed code generation, or semantic divergence from Python
labels: compiler correctness, bug
---

## Compiler Bug Report

### Summary
<!-- A clear, concise 1-sentence summary of the incorrect compiler behavior -->

### Environment
- **mojo-hotloop version**: <!-- git rev-parse HEAD or pip show mojo-hotloop -->
- **Python version**: <!-- python3 --version (e.g., 3.12.16) -->
- **Mojo version**: <!-- mojo --version (e.g., 1.2.0) -->
- **Operating System**: <!-- e.g., Ubuntu 24.04 LTS native / WSL2 -->

### Minimal Python Reproducer
<!-- Provide the smallest reproducible Python code snippet decorated with @hotloop -->
```python
from hotloop import hotloop

@hotloop
def repro(x: int) -> int:
    # Minimal code triggering the issue
    return x
```

### Expected Behavior
<!-- What Python produces, or what the transpiled Mojo code should have done -->

### Actual Behavior
<!-- Error traceback, compiler rejection message, or incorrect numeric output -->
```text
<!-- Paste traceback or output here -->
```

### Transpilation Stage
Does the error happen during AST transpilation, native Mojo compilation, or runtime execution?
- [ ] Fails during AST transpilation (offline in `transpile_python_to_mojo`)
- [ ] AST succeeds, but `mojo build` fails on the generated `.mojo` file
- [ ] Both compile, but native C-ABI execution produces incorrect output
- [ ] Unexpected Python fallback occurred without warning

import functools
import importlib
import importlib.machinery
import importlib.util
import os
import sys

def hotloop(fn):
    """
    Decorator that transparently routes calls to a compiled Mojo .so shared library
    if present in the same directory, falling back cleanly to the original Python
    function if the .so is not found or fails to load.
    """
    fn_name = fn.__name__
    mod_file = sys.modules[fn.__module__].__file__ if fn.__module__ in sys.modules else None
    compiled_fn = None
    loaded_mod = None

    if mod_file:
        mod_dir = os.path.dirname(os.path.abspath(mod_file))
        base_name = os.path.splitext(os.path.basename(mod_file))[0]
        # Search for <base_name>.so, fast.so, or any matching .so in mod_dir
        candidates = [base_name, f"{base_name}_mojo", "fast"]
        for c in candidates:
            so_path = os.path.join(mod_dir, f"{c}.so")
            if os.path.isfile(so_path):
                try:
                    loader = importlib.machinery.ExtensionFileLoader(f"{c}_{fn_name}", so_path)
                    spec = importlib.util.spec_from_loader(f"{c}_{fn_name}", loader)
                    if spec and spec.loader:
                        mod = importlib.util.module_from_spec(spec)
                        spec.loader.exec_module(mod)
                        if hasattr(mod, fn_name):
                            compiled_fn = getattr(mod, fn_name)
                            loaded_mod = mod
                            break
                except Exception:
                    continue

    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        if compiled_fn is not None:
            return compiled_fn(*args, **kwargs)
        return fn(*args, **kwargs)

    wrapper._original = fn
    wrapper._compiled = compiled_fn
    wrapper._module = loaded_mod
    return wrapper

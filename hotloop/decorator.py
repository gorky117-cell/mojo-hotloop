import functools
import importlib.machinery
import importlib.util
import os
import sys
import types
import warnings
from typing import Callable, Dict, Optional, Set, Tuple

class HotloopError(Exception):
    """Base exception for all hotloop runtime errors."""
    pass

class HotloopNativeExecutionError(HotloopError):
    """Raised when native execution fails or is unavailable in strict mode."""
    pass

class HotloopFallbackWarning(UserWarning):
    """Warning issued when execution falls back to the original Python implementation."""
    pass

# Global cache of loaded native modules keyed by canonical absolute .so path
_LOADED_MODULES: Dict[str, types.ModuleType] = {}

# Set of (function_qualname, reason_key) to prevent warning spam
_WARNED_FALLBACKS: Set[Tuple[str, str]] = set()

def _load_native_module(so_path: str) -> Tuple[Optional[types.ModuleType], Optional[str]]:
    """
    Dynamically loads a compiled shared library with proper C-ABI namespacing.
    In Python, ExtensionFileLoader('<namespace>.<stem>', so_path) looks for
    PyInit_<stem>() in the shared library, avoiding symbol mismatches while
    ensuring module isolation in sys.modules.
    """
    real_path = os.path.realpath(so_path)
    if real_path in _LOADED_MODULES:
        return _LOADED_MODULES[real_path], None

    if not os.path.isfile(real_path):
        return None, f"File does not exist: {real_path}"

    stem = os.path.splitext(os.path.basename(real_path))[0]
    # Hierarchical module name: Python looks for PyInit_<last_part>
    unique_mod_name = f"_hotloop_mod_{len(_LOADED_MODULES)}_{stem}.{stem}"

    try:
        loader = importlib.machinery.ExtensionFileLoader(unique_mod_name, real_path)
        spec = importlib.util.spec_from_loader(unique_mod_name, loader)
        if spec is None or spec.loader is None:
            return None, f"Failed to create module spec for {real_path}"

        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        _LOADED_MODULES[real_path] = mod
        return mod, None
    except Exception as e:
        return None, f"Dynamic load error ({type(e).__name__}): {e}"

def _find_and_load_native_fn(fn: Callable) -> Tuple[Optional[Callable], Optional[types.ModuleType], Optional[str]]:
    """
    Searches for a compiled .so in the directory containing the defining Python file.
    Returns (compiled_fn, loaded_mod, failure_reason).
    """
    fn_name = fn.__name__
    mod_name = getattr(fn, "__module__", None)
    mod_file = sys.modules[mod_name].__file__ if mod_name in sys.modules else None

    if not mod_file:
        return None, None, f"Cannot determine defining source file for function '{fn_name}'"

    mod_dir = os.path.dirname(os.path.abspath(mod_file))
    base_name = os.path.splitext(os.path.basename(mod_file))[0]

    # Search candidates: <base_name>.so, <base_name>_mojo.so, fast.so
    candidates = [base_name, f"{base_name}_mojo", "fast"]
    attempted_paths = []

    for c in candidates:
        so_path = os.path.join(mod_dir, f"{c}.so")
        attempted_paths.append(so_path)
        if os.path.isfile(so_path):
            mod, load_err = _load_native_module(so_path)
            if mod is not None:
                if hasattr(mod, fn_name):
                    compiled_fn = getattr(mod, fn_name)
                    return compiled_fn, mod, None
                else:
                    return None, mod, f"Module '{c}' found at {so_path} but does not export function '{fn_name}'"
            else:
                return None, None, f"Found candidate {so_path} but failed to load: {load_err}"

    return None, None, f"No native binary found. Checked candidates: {', '.join(attempted_paths)}"

def _create_hotloop_wrapper(fn: Callable, strict: bool = False) -> Callable:
    compiled_fn, loaded_mod, init_error = _find_and_load_native_fn(fn)

    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        # Allow runtime override of strict mode via environment variable
        is_strict = strict or (os.environ.get("HOTLOOP_STRICT", "").strip().lower() in ("1", "true", "yes"))

        if wrapper._compiled is not None:
            wrapper._last_backend = "native"
            wrapper._call_count_native += 1
            return wrapper._compiled(*args, **kwargs)

        # Fallback path
        reason = wrapper._fallback_reason or "Compiled native implementation not available"
        if is_strict:
            raise HotloopNativeExecutionError(
                f"Strict native mode enabled: failed to execute native Mojo backend for '{fn.__name__}'. "
                f"Reason: {reason}"
            )

        wrapper._last_backend = "python_fallback"
        wrapper._call_count_fallback += 1

        # Non-repetitive warning emission
        warn_key = (f"{fn.__module__}.{fn.__qualname__}", reason)
        if warn_key not in _WARNED_FALLBACKS:
            _WARNED_FALLBACKS.add(warn_key)
            warnings.warn(
                f"[mojo-hotloop] Falling back to Python implementation for '{fn.__name__}': {reason}",
                HotloopFallbackWarning,
                stacklevel=2
            )

        return wrapper._original(*args, **kwargs)

    # Attach diagnostic and inspectable attributes
    wrapper._original = fn
    wrapper._compiled = compiled_fn
    wrapper._module = loaded_mod
    wrapper._fallback_reason = init_error
    wrapper._is_strict = strict
    wrapper._last_backend = None
    wrapper._call_count_native = 0
    wrapper._call_count_fallback = 0

    return wrapper

def hotloop(fn: Optional[Callable] = None, *, strict: bool = False):
    """
    Decorator that transparently routes calls to a compiled Mojo .so shared library
    if present in the same directory, falling back cleanly to Python or raising
    HotloopNativeExecutionError in strict mode.
    Supports both @hotloop and @hotloop(strict=True).
    """
    if fn is None:
        return lambda f: _create_hotloop_wrapper(f, strict=strict)
    return _create_hotloop_wrapper(fn, strict=strict)

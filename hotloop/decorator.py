import functools
import hashlib
import importlib.machinery
import importlib.util
import json
import os
import sys
import time
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

def _load_native_module(so_path: str, export_symbol: Optional[str] = None) -> Tuple[Optional[types.ModuleType], Optional[str]]:
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
    sym = export_symbol or stem
    if export_symbol is None and "_" in stem and len(stem.rsplit("_", 1)[-1]) == 16:
        sym = stem.rsplit("_", 1)[0]

    # Hierarchical module name: Python looks for PyInit_<last_part>
    unique_mod_name = f"_hotloop_mod_{len(_LOADED_MODULES)}_{stem}.{sym}"

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

def _compute_file_hash(path: str) -> Optional[str]:
    try:
        with open(path, "rb") as f:
            return hashlib.sha256(f.read()).hexdigest()
    except OSError:
        return None

def _is_binary_stale(so_path: str, mod_file: str, current_hash: Optional[str]) -> Tuple[bool, Optional[str]]:
    """
    Checks if a candidate .so is stale compared to mod_file.
    Returns (is_stale, reason).
    """
    stem = os.path.splitext(os.path.basename(so_path))[0]
    manifest_path = os.path.join(os.path.dirname(so_path), f"{stem}.hotloop_manifest.json")
    if os.path.isfile(manifest_path):
        try:
            with open(manifest_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            expected_hash = data.get("source_sha256")
            if current_hash and expected_hash and current_hash != expected_hash:
                return True, f"Source SHA256 mismatch (source modified after '{stem}.so' was built)"
            if current_hash and expected_hash and current_hash == expected_hash:
                return False, None
        except Exception:
            pass

    # Fallback to mtime check
    try:
        so_mtime = os.path.getmtime(so_path)
        py_mtime = os.path.getmtime(mod_file)
        if so_mtime < py_mtime:
            return True, f"Binary mtime ({so_mtime:.1f}) is older than source file mtime ({py_mtime:.1f})"
    except OSError:
        pass

    return False, None

def _find_and_load_native_fn(fn: Callable) -> Tuple[Optional[Callable], Optional[types.ModuleType], Optional[str], Optional[str], Optional[str], float]:
    """
    Searches for a compiled .so in the directory containing the defining Python file.
    Returns (compiled_fn, loaded_mod, failure_reason, mod_file, source_hash, loaded_mtime).
    """
    fn_name = fn.__name__
    mod_name = getattr(fn, "__module__", None)
    mod_file = sys.modules[mod_name].__file__ if mod_name in sys.modules else None

    if not mod_file:
        return None, None, f"Cannot determine defining source file for function '{fn_name}'", None, None, 0.0

    mod_dir = os.path.dirname(os.path.abspath(mod_file))
    base_name = os.path.splitext(os.path.basename(mod_file))[0]
    current_hash = _compute_file_hash(mod_file)
    try:
        loaded_mtime = os.path.getmtime(mod_file)
    except OSError:
        loaded_mtime = 0.0

    # 1. Content-addressed lookup in __mojocache__
    if current_hash:
        cache_dir = os.path.join(mod_dir, "__mojocache__")
        for stem in [base_name, f"{base_name}_mojo", "fast"]:
            cached_so = os.path.join(cache_dir, f"{stem}_{current_hash[:16]}.so")
            if os.path.isfile(cached_so):
                mod, load_err = _load_native_module(cached_so, export_symbol=stem)
                if mod and hasattr(mod, fn_name):
                    return getattr(mod, fn_name), mod, None, mod_file, current_hash, loaded_mtime

    # 2. Co-located candidate search with staleness checks
    candidates = [base_name, f"{base_name}_mojo", "fast"]
    attempted_paths = []
    stale_reasons = []

    for c in candidates:
        so_path = os.path.join(mod_dir, f"{c}.so")
        attempted_paths.append(so_path)
        if os.path.isfile(so_path):
            mod, load_err = _load_native_module(so_path)
            if mod is None:
                return None, None, f"Found candidate {so_path} but failed to load: {load_err}", mod_file, current_hash, loaded_mtime

            if not hasattr(mod, fn_name):
                return None, mod, f"Module '{c}' found at {so_path} but does not export function '{fn_name}'", mod_file, current_hash, loaded_mtime

            is_stale, stale_reason = _is_binary_stale(so_path, mod_file, current_hash)
            if is_stale:
                stale_reasons.append(f"{c}.so: {stale_reason}")
                continue

            return getattr(mod, fn_name), mod, None, mod_file, current_hash, loaded_mtime

    if stale_reasons:
        return None, None, f"Stale native binary detected: {'; '.join(stale_reasons)}", mod_file, current_hash, loaded_mtime

    return None, None, f"No native binary found. Checked candidates: {', '.join(attempted_paths)}", mod_file, current_hash, loaded_mtime

def _is_strict_active(explicit_strict: bool) -> bool:
    if explicit_strict:
        return True
    val = os.environ.get("HOTLOOP_STRICT", "").strip().lower()
    return val in ("1", "true", "yes")

def _create_hotloop_wrapper(fn: Callable, strict: bool = False, cache_check: Optional[str] = None) -> Callable:
    compiled_fn, loaded_mod, init_error, mod_file, source_hash, loaded_mtime = _find_and_load_native_fn(fn)

    # Determine cache check policy:
    # "import": check cache only at decoration/import time (zero runtime filesystem overhead)
    # "runtime" or "interval": throttled check (at most once every check_interval seconds)
    # "always": check on every single call
    env_cache_mode = os.environ.get("HOTLOOP_CACHE_CHECK", "").strip().lower()
    mode = (cache_check or env_cache_mode or "runtime").lower()
    if mode in ("import", "none", "off"):
        check_interval: Optional[float] = None
    elif mode == "always":
        check_interval = 0.0
    else:
        # Default runtime mode: throttled to 20ms
        check_interval = 0.02

    last_check_time = 0.0

    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        # Check for runtime modification of the source file (if runtime checking is active)
        nonlocal last_check_time
        if check_interval is not None and wrapper._compiled is not None and wrapper._mod_file:
            now = time.monotonic() if check_interval > 0.0 else 0.0
            if check_interval == 0.0 or (now - last_check_time) >= check_interval:
                last_check_time = now
                try:
                    curr_mtime = os.path.getmtime(wrapper._mod_file)
                    if curr_mtime > wrapper._loaded_mtime:
                        curr_hash = _compute_file_hash(wrapper._mod_file)
                        if curr_hash != wrapper._source_hash:
                            wrapper._compiled = None
                            wrapper._fallback_reason = "Stale native binary detected: Source file modified during runtime"
                except OSError:
                    pass

        if wrapper._compiled is not None:
            wrapper._last_backend = "native"
            wrapper._call_count_native += 1
            try:
                return wrapper._compiled(*args, **kwargs)
            except Exception as e:
                is_strict = _is_strict_active(strict)
                err_str = str(e)
                # Check for integer overflow (either at C-ABI conversion or inside intermediate calculations)
                if ("HOTLOOP_INTEGER_OVERFLOW" in err_str or
                    "Python int too large to convert to C ssize_t" in err_str):
                    if is_strict:
                        wrapper._last_backend = "native_error"
                        raise HotloopNativeExecutionError(
                            f"Strict native mode enabled: native Mojo 64-bit integer overflow occurred: {err_str}"
                        ) from e

                    # Pure scalar function fallback: safe to re-execute in arbitrary-precision Python
                    wrapper._last_backend = "python_fallback_overflow"
                    wrapper._call_count_fallback += 1
                    warn_key = (f"{fn.__module__}.{fn.__qualname__}", "integer_overflow")
                    if warn_key not in _WARNED_FALLBACKS:
                        _WARNED_FALLBACKS.add(warn_key)
                        warnings.warn(
                            f"[mojo-hotloop] Integer overflow in native execution for '{fn.__name__}'; "
                            f"falling back to arbitrary-precision Python: {err_str}",
                            HotloopFallbackWarning,
                            stacklevel=2
                        )
                    return wrapper._original(*args, **kwargs)

                elif "HOTLOOP_ZERO_DIVISION_ERROR" in err_str:
                    # Restore exact Python ZeroDivisionError
                    msg = err_str.split("HOTLOOP_ZERO_DIVISION_ERROR: ", 1)[-1]
                    raise ZeroDivisionError(msg) from None

                elif "HOTLOOP_VALUE_ERROR" in err_str:
                    msg = err_str.split("HOTLOOP_VALUE_ERROR: ", 1)[-1]
                    raise ValueError(msg) from None

                # Re-raise any other native exception
                raise

        # Fallback path when native binary is missing, stale, or failed to load
        is_strict = _is_strict_active(strict)
        reason = wrapper._fallback_reason or "Compiled native implementation not available"
        is_stale = "Stale native binary" in reason or "stale cache" in reason

        if is_strict:
            raise HotloopNativeExecutionError(
                f"Strict native mode enabled: failed to execute native Mojo backend for '{fn.__name__}'. "
                f"Reason: {reason}"
            )

        wrapper._last_backend = "python_fallback_stale_cache" if is_stale else "python_fallback"
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
    wrapper._cache_check = mode
    wrapper._last_backend = "native" if compiled_fn is not None else ("python_fallback_stale_cache" if ("Stale" in (init_error or "")) else "python_fallback")
    wrapper._call_count_native = 0
    wrapper._call_count_fallback = 0
    wrapper._mod_file = mod_file
    wrapper._source_hash = source_hash
    wrapper._loaded_mtime = loaded_mtime

    return wrapper

def hotloop(fn: Optional[Callable] = None, *, strict: bool = False, cache_check: Optional[str] = None):
    """
    Decorator that transparently routes calls to a compiled Mojo .so shared library
    if present in the same directory, falling back cleanly to Python or raising
    HotloopNativeExecutionError in strict mode.
    Supports both @hotloop and @hotloop(strict=True).
    """
    if fn is None:
        return lambda f: _create_hotloop_wrapper(f, strict=strict, cache_check=cache_check)
    return _create_hotloop_wrapper(fn, strict=strict, cache_check=cache_check)

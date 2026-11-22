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

import functools
import hashlib
import importlib.machinery
import importlib.util
import inspect
import os
import sys
import threading
import time
import types
import warnings
from typing import Any, Callable, Dict, Optional, Set, Tuple

from pathlib import Path

from ._native_cache import (
    build_context, build_environment, build_identity, checked_binary,
    file_hash as _compute_file_hash, file_stamp, verify_cache_directory, find_mojo, read_manifest,
)

class HotloopError(Exception):
    """Base exception for all hotloop runtime errors."""
    pass

class HotloopNativeExecutionError(HotloopError):
    """Raised when native execution fails or is unavailable in strict mode."""
    pass

class HotloopFallbackWarning(UserWarning):
    """Warning issued when execution falls back to the original Python implementation."""
    pass

_STATE_LOCK = threading.Lock()

# Global cache of loaded native modules keyed by canonical absolute .so path
_LOADED_MODULES: Dict[Tuple[str, str], types.ModuleType] = {}
_PINNED_MODULE_FDS: list[int] = []

# Set of (function_qualname, reason_key) to prevent warning spam
_WARNED_FALLBACKS: Set[Tuple[str, str]] = set()

# Cache of dispatch qualification decisions keyed by (function_qualname, tuple(arg_types))
_DISPATCH_QUALIFIER_CACHE: Dict[Tuple[str, Tuple[type, ...]], Tuple[str, str]] = {}


def _warn_once(warn_key: Tuple[str, str], message: str) -> None:
    with _STATE_LOCK:
        if warn_key in _WARNED_FALLBACKS:
            return
        _WARNED_FALLBACKS.add(warn_key)
    warnings.warn(message, HotloopFallbackWarning, stacklevel=3)


def _load_native_module(so_path: str, export_symbol: str, digest: str):
    """Pin the verified inode through dlopen; never resolve its filename a second time."""
    key = (so_path, digest)
    with _STATE_LOCK:
        if key in _LOADED_MODULES:
            return _LOADED_MODULES[key], None
        try:
            fd = os.open(so_path, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC)
            with os.fdopen(fd, "rb") as binary:
                if binary.read(4) != b"\x7fELF":
                    return None, "Native artifact is not ELF"
                binary.seek(0)
                if hashlib.file_digest(binary, "sha256").hexdigest() != digest:
                    return None, "Native artifact changed before import"
                # Keep a distinct descriptor path alive for each resident extension.
                # CPython and the dynamic linker can cache an extension by this path.
                pinned = os.dup(binary.fileno())
            name = f"_hotloop_mod_{len(_LOADED_MODULES)}.{export_symbol}"
            path = f"/proc/self/fd/{pinned}"
            original_env = {k: os.environ.get(k) for k in ("PYTHONEXECUTABLE", "PYTHONPATH", "MOJO_PYTHON_LIBRARY")}
            try:
                loader = importlib.machinery.ExtensionFileLoader(name, path)
                spec = importlib.util.spec_from_loader(name, loader)
                mod = importlib.util.module_from_spec(spec)
                loader.exec_module(mod)
                _LOADED_MODULES[key] = mod
                _PINNED_MODULE_FDS.append(pinned)
                return mod, None
            finally:
                if key not in _LOADED_MODULES:
                    os.close(pinned)
                for k, value in original_env.items():
                    if value is None:
                        os.environ.pop(k, None)
                        # Mojo can set libc environ without updating os.environ.
                        os.unsetenv(k)
                    else:
                        os.environ[k] = value
        except Exception as exc:
            return None, f"Dynamic load error ({type(exc).__name__}): {exc}"


def _is_binary_stale(so_path: str, mod_file: str, current_hash: Optional[str]) -> Tuple[bool, Optional[str]]:
    """Use the adjacent export manifest for stale-source diagnostics."""
    path = Path(so_path).with_suffix(".hotloop_manifest.json")
    try:
        data = read_manifest(path)
    except (OSError, ValueError):
        return False, None
    if data.get("source_sha256") != current_hash or data.get("source_file") != Path(mod_file).name:
        return True, f"Source SHA256 mismatch (source modified after '{Path(so_path).name}' was built)"
    return False, None


def _find_and_load_native_fn(fn: Callable):
    """Load a validated immutable artifact for the defining Python source."""
    fn_name = fn.__name__
    module = sys.modules.get(fn.__module__)
    mod_file = getattr(module, "__file__", None)
    if not mod_file:
        return None, None, f"Cannot determine defining source file for function '{fn_name}'", None, None, None

    source = Path(mod_file).absolute()
    source_stamp = file_stamp(source)
    source_hash = _compute_file_hash(source)
    stems = tuple(dict.fromkeys((source.stem, f"{source.stem}_mojo", "fast")))
    cache_dir = source.parent / "__mojocache__"
    if cache_dir.exists() or cache_dir.is_symlink():
        try:
            verify_cache_directory(cache_dir)
        except (OSError, ValueError) as exc:
            return None, None, str(exc), mod_file, source_hash, source_stamp
    errors = []
    stale = []
    contexts = {}
    selected = find_mojo() if cache_dir.is_dir() else None
    env = build_environment()
    for stem in stems:
        for manifest in sorted(cache_dir.glob(f"{stem}_{source_hash}_*.json")):
            try:
                data = read_manifest(manifest)
                recorded = data.get("context")
                if not isinstance(recorded, dict):
                    raise ValueError("Invalid native build context")
                if not selected:
                    raise ValueError("Cannot independently identify a local Mojo toolchain")
                if selected not in contexts:
                    contexts[selected] = build_context(selected, env)
                identity = build_identity(source, source_hash, stem, contexts[selected])
                if recorded != identity["context"] or data.get("schema") != identity["schema"]:
                    stale.append("Compiler revision, toolchain, runtime ABI or build settings changed")
                    continue
                binary = checked_binary(manifest, data, identity)
            except (OSError, ValueError) as exc:
                errors.append(str(exc))
                continue

            if source_stamp != file_stamp(source):
                stale.append("Source file changed while checking the native build")
                break
            native_module, load_error = _load_native_module(str(binary), stem, data["so_sha256"])
            if native_module is not None and hasattr(native_module, fn_name):
                return getattr(native_module, fn_name), native_module, None, mod_file, source_hash, source_stamp
            errors.append(load_error or f"Native module has no qualified entry for '{fn_name}' (Python list identity, mutation or control flow may require Python)")

        alias = source.with_name(f"{stem}.so")
        if alias.is_file():
            is_stale, reason = _is_binary_stale(str(alias), mod_file, source_hash)
            if is_stale:
                stale.append(reason)
            else:
                errors.append(f"No verified cache entry for {alias.name}; rebuild with hotloop build")

    if stale:
        reason = "Stale native binary detected: " + stale[0]
    elif errors:
        reason = errors[0]
    else:
        reason = f"No native binary found for {source.name}"
    return None, None, reason, mod_file, source_hash, source_stamp


def _is_strict_active(explicit_strict: bool) -> bool:
    if explicit_strict:
        return True
    val = os.environ.get("HOTLOOP_STRICT", "").strip().lower()
    return val in ("1", "true", "yes")

def _is_force_native(explicit_force: bool, explicit_strict: bool) -> bool:
    if explicit_force or explicit_strict:
        return True
    val = os.environ.get("HOTLOOP_FORCE_NATIVE", "").strip().lower()
    return val in ("1", "true", "yes")

def _is_slower_workload(args: Tuple, kwargs: Dict, fn: Optional[Callable] = None) -> bool:
    """
    Checks if any input argument is a standard Python collection (list/set),
    or if the function returns a list of strings (list[str]),
    which incurs per-element PythonObject FFI conversion overhead that makes
    native Mojo execution slower than pure Python loops.
    """
    if fn is not None:
        try:
            ret_type = getattr(fn, "__annotations__", {}).get("return")
            if ret_type in (list[str], "list[str]"):
                return True
        except Exception:
            pass

    for a in args:
        if isinstance(a, (list, set)):
            return True
    for v in kwargs.values():
        if isinstance(v, (list, set)):
            return True
    return False

def _has_unsupported_surrogates(args: Tuple, kwargs: Dict) -> bool:
    """
    Checks if any string input argument contains lone surrogates (U+D800 - U+DFFF),
    which are invalid in UTF-8 and cannot be converted across C-ABI boundary.
    """
    for a in args:
        if isinstance(a, str) and not a.isascii():
            try:
                a.encode("utf-8")
            except UnicodeEncodeError:
                return True
    for v in kwargs.values():
        if isinstance(v, str) and not v.isascii():
            try:
                v.encode("utf-8")
            except UnicodeEncodeError:
                return True
    return False

def _create_hotloop_wrapper(fn: Callable, strict: bool = False, force_native: bool = False, cache_check: Optional[str] = None) -> Callable:
    compiled_fn, loaded_mod, init_error, mod_file, source_hash, source_stamp = _find_and_load_native_fn(fn)

    provenance_entry = None
    if compiled_fn is not None:
        try:
            from ._provenance import bind
            compiled_fn = provenance_entry = bind(fn,compiled_fn,loaded_mod)
        except Exception as exc:
            compiled_fn = None
            init_error = f"Unproven return context: {exc}"

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

    try:
        _sig = inspect.signature(fn)
        _params = list(_sig.parameters.values())
        _can_bind_sig = not any(
            p.kind in (inspect.Parameter.VAR_POSITIONAL, inspect.Parameter.VAR_KEYWORD)
            for p in _params
        )
        _param_count = len(_params)
    except (ValueError, TypeError):
        _sig = None
        _can_bind_sig = False
        _param_count = -1

    last_check_time = 0.0

    def python_semantics(args, kwargs, reason):
        if _is_strict_active(strict):
            wrapper._last_backend = "native_error"
            raise HotloopNativeExecutionError(f"Strict native mode: {reason}")
        wrapper._last_backend = "python_fallback_semantics"
        wrapper._call_count_fallback += 1
        _warn_once((fn.__qualname__, "python_semantics"), f"[mojo-hotloop] {fn.__name__}: {reason}")
        return wrapper._original(*args, **kwargs)

    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        if wrapper._compiled is not None and provenance_entry is not None and not provenance_entry.root_valid():
            return python_semantics(args,kwargs,"callable code/default ownership changed")
        if _can_bind_sig and (kwargs or len(args) != _param_count):
            try:
                bound = _sig.bind(*args, **kwargs)
                bound.apply_defaults()
                call_args = bound.args
                call_kwargs: Dict = {}
            except TypeError:
                return wrapper._original(*args, **kwargs)
        else:
            call_args = args
            call_kwargs = kwargs

        if wrapper._compiled is not None:
            for value in call_args:
                kind = type(value)
                if all(kind is not allowed for allowed in (int, float, str, bool, list)):
                    return python_semantics(args, kwargs, "input requires Python object semantics")

        # Performance-aware qualification check:
        # Standard Python lists/sets have high FFI boxing/unboxing overhead that is slower
        # than pure Python. Fall back to Python unless explicitly forced by user.
        is_forced = _is_force_native(wrapper._force_native, _is_strict_active(strict))
        if wrapper._compiled is not None and not is_forced and _is_slower_workload(call_args, call_kwargs, fn):
            strict_perf = os.environ.get("HOTLOOP_STRICT_PERF", "").strip().lower() in ("1", "true", "yes")
            if strict_perf:
                wrapper._last_backend = "performance_not_qualified"
                raise HotloopNativeExecutionError(
                    f"Strict performance mode enabled: native Mojo backend for '{fn.__name__}' is not "
                    f"qualified as faster than pure Python for standard collection inputs."
                )

            wrapper._last_backend = "python_fallback_slower"
            wrapper._call_count_fallback += 1
            cache_sig = (f"{fn.__module__}.{fn.__qualname__}", tuple(type(a) for a in call_args))
            _DISPATCH_QUALIFIER_CACHE[cache_sig] = ("fallback", "python_fallback_slower")
            _warn_once(
                (f"{fn.__module__}.{fn.__qualname__}", "slower_than_python"),
                f"[mojo-hotloop] Python collection input/output detected for '{fn.__name__}'; "
                f"per-element FFI conversion overhead makes native execution slower than pure Python. "
                f"Safely executing pure Python implementation. "
                f"(force_native=True may enable a qualified read-only list kernel.)"
            )
            return wrapper._original(*args, **kwargs)

        # Check for runtime modification of the source file (if runtime checking is active)
        nonlocal last_check_time
        if check_interval is not None and wrapper._compiled is not None and wrapper._mod_file:
            now = time.monotonic() if check_interval > 0.0 else 0.0
            if check_interval == 0.0 or (now - last_check_time) >= check_interval:
                last_check_time = now
                current_stamp = file_stamp(wrapper._mod_file)
                if current_stamp != wrapper._source_stamp:
                    curr_hash = _compute_file_hash(wrapper._mod_file)
                    if curr_hash != wrapper._source_hash:
                        wrapper._compiled = None
                        wrapper._fallback_reason = "Stale native binary detected: Source file modified during runtime"
                    else:
                        wrapper._source_stamp = current_stamp

        # Check for lone surrogate codepoints which cannot cross UTF-8 C-ABI boundary safely
        if wrapper._compiled is not None and _has_unsupported_surrogates(call_args, call_kwargs):
            is_strict = _is_strict_active(strict)
            if is_strict:
                wrapper._last_backend = "native_error"
                raise HotloopNativeExecutionError(
                    f"Strict native mode enabled: input contains lone surrogate codepoints (U+D800 - U+DFFF) "
                    f"which cannot be converted across UTF-8 C-ABI boundary."
                )
            wrapper._last_backend = "python_fallback_surrogate"
            wrapper._call_count_fallback += 1
            cache_sig = (f"{fn.__module__}.{fn.__qualname__}", tuple(type(a) for a in call_args))
            _DISPATCH_QUALIFIER_CACHE[cache_sig] = ("fallback", "python_fallback_surrogate")
            _warn_once(
                (f"{fn.__module__}.{fn.__qualname__}", "surrogate_fallback"),
                f"[mojo-hotloop] Input contains lone surrogate codepoints for '{fn.__name__}'; "
                f"UTF-8 C-ABI boundary cannot represent surrogates. Safely executing pure Python implementation."
            )
            return wrapper._original(*args, **kwargs)

        if wrapper._compiled is not None:
            wrapper._last_backend = "native"
            cache_sig = (f"{fn.__module__}.{fn.__qualname__}", tuple(type(a) for a in call_args))
            _DISPATCH_QUALIFIER_CACHE[cache_sig] = ("native", "qualified_faster")
            try:
                res = wrapper._compiled(*call_args, **call_kwargs)
                wrapper._call_count_native += 1
                return res
            except Exception as e:
                is_strict = _is_strict_active(strict)
                err_str = str(e)
                if "HOTLOOP_PYTHON_SEMANTICS" in err_str:
                    return python_semantics(args, kwargs, "native conversion cannot preserve Python semantics")
                # Check for integer overflow (either at C-ABI conversion or intermediate calculations)
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
                    cache_sig = (f"{fn.__module__}.{fn.__qualname__}", tuple(type(a) for a in call_args))
                    _DISPATCH_QUALIFIER_CACHE[cache_sig] = ("fallback", "python_fallback_overflow")
                    _warn_once(
                        (f"{fn.__module__}.{fn.__qualname__}", "integer_overflow"),
                        f"[mojo-hotloop] Integer overflow in native execution for '{fn.__name__}'; "
                        f"falling back to arbitrary-precision Python: {err_str}"
                    )
                    return wrapper._original(*args, **kwargs)

                elif "HOTLOOP_ZERO_DIVISION_ERROR" in err_str:
                    wrapper._call_count_native += 1
                    msg = err_str.split("HOTLOOP_ZERO_DIVISION_ERROR: ", 1)[-1]
                    raise ZeroDivisionError(msg) from None

                elif "HOTLOOP_VALUE_ERROR" in err_str:
                    wrapper._call_count_native += 1
                    msg = err_str.split("HOTLOOP_VALUE_ERROR: ", 1)[-1]
                    raise ValueError(msg) from None

                elif "HOTLOOP_INDEX_ERROR" in err_str:
                    wrapper._call_count_native += 1
                    msg = err_str.split("HOTLOOP_INDEX_ERROR: ", 1)[-1]
                    raise IndexError(msg) from None

                # Re-raise any other native exception
                wrapper._call_count_native += 1
                raise

        # Fallback path when native binary is missing, stale, or failed to load
        is_strict = _is_strict_active(strict)
        reason = wrapper._fallback_reason or "Compiled native implementation not available"
        is_stale = "Stale native binary" in reason or "stale cache" in reason

        if is_strict:
            wrapper._last_backend = "native_error"
            raise HotloopNativeExecutionError(
                f"Strict native mode enabled: failed to execute native Mojo backend for '{fn.__name__}'. "
                f"Reason: {reason}"
            )

        wrapper._last_backend = "python_fallback_stale_cache" if is_stale else "python_fallback"
        wrapper._call_count_fallback += 1
        cache_sig = (f"{fn.__module__}.{fn.__qualname__}", tuple(type(a) for a in call_args))
        _DISPATCH_QUALIFIER_CACHE[cache_sig] = ("fallback", wrapper._last_backend)

        _warn_once(
            (f"{fn.__module__}.{fn.__qualname__}", reason),
            f"[mojo-hotloop] Falling back to Python implementation for '{fn.__name__}': {reason}"
        )

        return wrapper._original(*args, **kwargs)

    # Attach diagnostic and inspectable attributes
    wrapper._original = fn
    wrapper._compiled = compiled_fn
    wrapper._module = loaded_mod
    wrapper._fallback_reason = init_error
    wrapper._is_strict = strict
    wrapper._force_native = force_native
    wrapper._cache_check = mode
    wrapper._last_backend = "native" if compiled_fn is not None else ("python_fallback_stale_cache" if ("Stale" in (init_error or "")) else "python_fallback")
    wrapper._call_count_native = 0
    wrapper._call_count_fallback = 0
    wrapper._mod_file = mod_file
    wrapper._source_hash = source_hash
    wrapper._source_stamp = source_stamp

    return wrapper

def hotloop(fn: Optional[Callable] = None, *, strict: bool = False, force_native: bool = False, cache_check: Optional[str] = None):
    """
    Route qualified calls to a verified locally compiled Mojo extension,
    falling back to Python or raising
    HotloopNativeExecutionError in strict mode.
    Supports @hotloop, @hotloop(strict=True), @hotloop(force_native=True), and @hotloop(cache_check="import").
    """
    if fn is None:
        return lambda f: _create_hotloop_wrapper(f, strict=strict, force_native=force_native, cache_check=cache_check)
    return _create_hotloop_wrapper(fn, strict=strict, force_native=force_native, cache_check=cache_check)


def inspect_dispatch(fn: Callable) -> Dict[str, Any]:
    """
    Inspect the runtime dispatch state and configuration of a @hotloop-decorated function.
    Returns a dictionary detailing:
    - is_hotloop: bool (whether fn is a hotloop wrapper)
    - backend_available: bool (whether compiled native shared library is available)
    - last_backend: str (last backend used: 'native', 'python_fallback', 'python_fallback_slower', etc.)
    - call_count_native: int (number of native invocations)
    - call_count_fallback: int (number of Python fallback invocations)
    - fallback_reason: Optional[str] (reason native compilation/loading failed or fell back)
    - strict: bool (whether strict native execution is enforced)
    - force_native: bool (whether native execution is forced)
    - cache_check: Optional[str] (cache check mode: None, 'call', 'import')
    - binary_path: Optional[str] (path to loaded shared object, if any)
    - source_hash: Optional[str] (source code hash used for cache invalidation)
    - module_loaded: bool (whether the Mojo shared object module is currently loaded)
    """
    if not hasattr(fn, "_original") or not hasattr(fn, "_compiled"):
        return {
            "is_hotloop": False,
            "backend_available": False,
            "last_backend": "none",
            "call_count_native": 0,
            "call_count_fallback": 0,
            "fallback_reason": "Not a hotloop-decorated function",
            "strict": False,
            "force_native": False,
            "cache_check": None,
            "binary_path": None,
            "source_hash": None,
            "module_loaded": False,
        }

    return {
        "is_hotloop": True,
        "backend_available": getattr(fn, "_compiled", None) is not None,
        "last_backend": getattr(fn, "_last_backend", "none"),
        "call_count_native": getattr(fn, "_call_count_native", 0),
        "call_count_fallback": getattr(fn, "_call_count_fallback", 0),
        "fallback_reason": getattr(fn, "_fallback_reason", None),
        "strict": getattr(fn, "_is_strict", False),
        "force_native": getattr(fn, "_force_native", False),
        "cache_check": getattr(fn, "_cache_check", None),
        "binary_path": getattr(fn, "_mod_file", None),
        "source_hash": getattr(fn, "_source_hash", None),
        "module_loaded": getattr(fn, "_module", None) is not None,
    }


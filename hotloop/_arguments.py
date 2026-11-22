"""Validate boxed arguments before conversion by a generated extension."""
import sys

_TYPES = {"int": int, "float": float, "str": str, "bool": bool}


def _check_scalar(value, expected):
    if type(value) is not expected:
        raise TypeError("HOTLOOP_PYTHON_SEMANTICS: input type requires Python")
    if expected is int and not -sys.maxsize - 1 <= value <= sys.maxsize:
        raise OverflowError("HOTLOOP_INTEGER_OVERFLOW: integer exceeds native range")
    if expected is str and not value.isascii():
        try:
            value.encode("utf-8")
        except UnicodeEncodeError:
            raise ValueError("HOTLOOP_PYTHON_SEMANTICS: string requires Python") from None


def checked_argument(value, kind):
    if kind.startswith("list["):
        if type(value) is not list:
            raise TypeError("HOTLOOP_PYTHON_SEMANTICS: native collection entry requires an exact list")
        # Snapshot while holding the GIL. Validation and unboxing see the same
        # immutable sequence, independently of future writes to the caller's list.
        snapshot = tuple(value)
        element = _TYPES[kind[5:-1]]
        for item in snapshot:
            _check_scalar(item, element)
        return snapshot
    _check_scalar(value, _TYPES[kind])
    return value

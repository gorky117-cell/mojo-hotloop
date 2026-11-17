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

"""
Offline AST and Live Native Mojo verification for str.startswith() and str.endswith().
Verifies AST transpilation, compilation, and exact parity with CPython across ASCII and Unicode.
"""

import os
import shutil
import sys
import tempfile
import pytest

from hotloop import hotloop
from hotloop.ast_transpiler import transpile_python_to_mojo, ASTTranspileError
from hotloop.backends.mojo import MojoBackend


def test_offline_ast_startswith_endswith():
    """Verify offline AST transpilation produces valid Mojo for all prefix/suffix variants."""
    source = """
from hotloop import hotloop

@hotloop
def check_prefix_suffix(s: str, p: str, suf: str) -> bool:
    b1: bool = s.startswith(p)
    b2: bool = s.endswith(suf)
    b3: bool = s.startswith("http://")
    b4: bool = s.endswith(".json")
    b5: bool = s.startswith(("a", "b", "c"))
    return b1 and b2 and b3 and b4 and b5
"""
    code = transpile_python_to_mojo(source, "prefix_ast_mod")
    assert "s.startswith(p)" in code
    assert "s.endswith(suf)" in code
    assert "s.startswith(" in code
    assert "s.endswith(" in code


def test_offline_ast_pystr_startswith_endswith():
    """Verify subscripted string (_PyStr) transpiles startswith and endswith correctly."""
    source = """
from hotloop import hotloop

@hotloop
def check_subscript_prefix(s: str) -> bool:
    first_char: str = s[0]
    return s.startswith("foo") and s.endswith("bar")
"""
    code = transpile_python_to_mojo(source, "pystr_prefix_ast_mod")
    assert "s.startswith(" in code
    assert "s.endswith(" in code


def test_offline_ast_startswith_invalid_args():
    """Verify startswith with no args or >3 args raises ASTTranspileError."""
    source_no_args = """
from hotloop import hotloop

@hotloop
def bad_fn(s: str) -> bool:
    return s.startswith()
"""
    with pytest.raises(ASTTranspileError, match="expects 1 to 3 arguments"):
        transpile_python_to_mojo(source_no_args, "bad_mod")

    source_too_many = """
from hotloop import hotloop

@hotloop
def bad_fn2(s: str) -> bool:
    return s.startswith("a", 1, 2, 3)
"""
    with pytest.raises(ASTTranspileError, match="expects 1 to 3 arguments"):
        transpile_python_to_mojo(source_too_many, "bad_mod2")


def test_native_runtime_startswith_endswith():
    """
    Mandatory Native Mojo Runtime Verification (Issue #2):
    Compile shared library with Mojo 1.2.0 and verify 100% numerical boolean parity
    against CPython 3.12 across varied ASCII, Unicode, emoji, and boundary strings.
    """
    app_source = """
from hotloop import hotloop

@hotloop
def check_prefix(line: str, prefix: str) -> bool:
    return line.startswith(prefix)

@hotloop
def check_suffix(line: str, suffix: str) -> bool:
    return line.endswith(suffix)

@hotloop
def check_prefix_tuple(line: str) -> bool:
    return line.startswith(("https://", "http://", "ftp://"))
"""
    tmp_dir = tempfile.mkdtemp(prefix="hotloop_native_str_")
    try:
        app_file = os.path.join(tmp_dir, "app.py")
        with open(app_file, "w", encoding="utf-8") as f:
            f.write(app_source)

        backend = MojoBackend()
        ok, msg, so_path = backend.build(app_file, engine="ast")
        assert ok, f"Native compilation failed: {msg}"
        assert so_path and os.path.isfile(so_path), "Shared library artifact missing"

        # Load compiled module in isolated namespace
        sys.path.insert(0, tmp_dir)
        import app
        import importlib
        importlib.reload(app)

        # Test cases for startswith and endswith
        test_strings = [
            ("hello world", "hello", "world"),
            ("hello world", "he", "ld"),
            ("hello world", "hello world", "hello world"),
            ("hello world", "world", "hello"),
            ("hello world", "xyz", "abc"),
            ("hello world", "", ""),
            ("", "", ""),
            ("", "a", "a"),
            ("a", "a", "a"),
            ("a", "b", "b"),
            ("foo_bar_baz.json", "foo_", ".json"),
            ("foo_bar_baz.json", "bar", ".csv"),
            # Unicode / Devanagari
            ("नमस्ते दुनिया!", "नमस्ते", "दुनिया!"),
            ("नमस्ते दुनिया!", "दुनिया", "नमस्ते"),
            ("नमस्ते दुनिया!", "न", "!"),
            # Accented & Emoji
            ("crème brûlée 🍰", "crème", "🍰"),
            ("crème brûlée 🍰", "creme", "cake"),
            ("🚀 blastoff 🌟", "🚀", "🌟"),
            ("🚀 blastoff 🌟", "🌟", "🚀"),
        ]

        for s, p, suf in test_strings:
            # Check startswith
            py_res = s.startswith(p)
            native_res = app.check_prefix(s, p)
            assert native_res == py_res, (
                f"check_prefix mismatch for s={s!r}, p={p!r}: "
                f"native={native_res}, python={py_res}"
            )
            assert app.check_prefix._last_backend == "native"

            # Check endswith
            py_suf = s.endswith(suf)
            native_suf = app.check_suffix(s, suf)
            assert native_suf == py_suf, (
                f"check_suffix mismatch for s={s!r}, suf={suf!r}: "
                f"native={native_suf}, python={py_suf}"
            )
            assert app.check_suffix._last_backend == "native"

        # Check tuple prefixes
        urls = [
            ("https://example.com", True),
            ("http://localhost:8080", True),
            ("ftp://files.archive.org", True),
            ("ssh://git@github.com", False),
            ("file:///home/user", False),
            ("", False),
        ]
        for url, expected in urls:
            nat_url = app.check_prefix_tuple(url)
            assert nat_url == expected, (
                f"check_prefix_tuple mismatch for url={url!r}: "
                f"native={nat_url}, expected={expected}"
            )
            assert app.check_prefix_tuple._last_backend == "native"

    finally:
        if tmp_dir in sys.path:
            sys.path.remove(tmp_dir)
        shutil.rmtree(tmp_dir, ignore_errors=True)

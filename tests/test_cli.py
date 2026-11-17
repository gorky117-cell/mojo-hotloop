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

"""Unit tests for hotloop CLI flags including --check-syntax, --dry-run, and check."""

import os
import subprocess
import sys
import tempfile
import pytest

from hotloop import __version__


def run_cli(*args):
    cmd = [sys.executable, "-m", "hotloop.cli", *args]
    return subprocess.run(cmd, capture_output=True, text=True)


def test_cli_version():
    res = run_cli("-v")
    assert res.returncode == 0
    assert __version__ in res.stdout or __version__ in res.stderr


def test_check_syntax_valid():
    with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False) as f:
        f.write(
            "from hotloop import hotloop\n\n"
            "@hotloop\n"
            "def add_numbers(a: int, b: int) -> int:\n"
            "    return a + b\n"
        )
        tmp_path = f.name

    try:
        # Test --check-syntax
        res1 = run_cli("build", tmp_path, "--check-syntax")
        assert res1.returncode == 0
        assert "[+] Syntax check PASSED" in res1.stdout

        # Test --dry-run alias
        res2 = run_cli("build", tmp_path, "--dry-run")
        assert res2.returncode == 0
        assert "[+] Syntax check PASSED" in res2.stdout

        # Test check subcommand
        res3 = run_cli("check", tmp_path)
        assert res3.returncode == 0
        assert "[+] Syntax check PASSED" in res3.stdout
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


def test_check_syntax_unsupported_ast():
    with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False) as f:
        f.write(
            "from hotloop import hotloop\n\n"
            "@hotloop\n"
            "def generator_func(x: int) -> int:\n"
            "    yield x\n"
        )
        tmp_path = f.name

    try:
        res = run_cli("build", tmp_path, "--check-syntax")
        assert res.returncode == 1
        assert "[-] Syntax check FAILED" in res.stdout
        assert "ASTTranspileError" in res.stdout
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


def test_check_syntax_missing_file():
    res = run_cli("check", "/tmp/non_existent_hotloop_test_file.py")
    assert res.returncode == 1
    assert "not found" in res.stdout or "not found" in res.stderr


def test_check_syntax_parse_error():
    with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False) as f:
        f.write("def broken(:\n    pass\n")
        tmp_path = f.name

    try:
        res = run_cli("check", tmp_path)
        assert res.returncode == 1
        assert "[-] Syntax check FAILED" in res.stdout
        assert "SyntaxError" in res.stdout
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)

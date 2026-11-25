# Copyright 2026 Gaurav Kumar Singh
# SPDX-License-Identifier: Apache-2.0

import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

import pytest

import hotloop._native_cache as cache
import hotloop.decorator as runtime
from hotloop import HotloopFallbackWarning, inspect_dispatch
from hotloop.backends.mojo import MojoBackend


SOURCE = """from hotloop import hotloop

@hotloop
def calculate(x: int) -> int:
    return x * 3
"""


@pytest.fixture(scope="module")
def native_fixture(tmp_path_factory):
    root = tmp_path_factory.mktemp("verified-native")
    path = root / "subject.py"
    path.write_text(SOURCE)
    ok, msg, _ = MojoBackend().build_ast(path)
    assert ok, msg
    return root


@pytest.fixture
def artifact(native_fixture, tmp_path):
    path = tmp_path / "artifact"
    shutil.copytree(native_fixture, path)
    return path


def load(path, monkeypatch):
    spec = importlib.util.spec_from_file_location("verified_subject", path / "subject.py")
    mod = importlib.util.module_from_spec(spec)
    monkeypatch.setitem(sys.modules, spec.name, mod)
    spec.loader.exec_module(mod)
    return mod.calculate


def reject_loader(*args, **kwargs):
    pytest.fail("An unverified artifact reached the native loader")


@pytest.mark.parametrize("component", ["implementation", "ABI", "toolchain", "version", "settings"])
def test_rejects_changed_build_identity(artifact, monkeypatch, component):
    if component == "implementation":
        monkeypatch.setattr(cache, "implementation_revision", lambda: "changed")
    elif component == "ABI":
        monkeypatch.setattr(cache, "host_abi", lambda: "changed")
    elif component == "toolchain":
        monkeypatch.setattr(cache, "toolchain_fingerprint", lambda *args: "changed")
    elif component == "version":
        monkeypatch.setattr(cache, "_version", lambda *args: "different Mojo version")
    else:
        monkeypatch.setenv("MOJO_CACHE_TEST_SETTING", "different")
    monkeypatch.setattr(runtime, "_load_native_module", reject_loader)
    kernel = load(artifact, monkeypatch)
    assert kernel._compiled is None
    assert "Stale native binary" in inspect_dispatch(kernel)["fallback_reason"]


@pytest.mark.parametrize("damage", ["binary", "manifest", "generated_sha256", "legacy"])
def test_rejects_corruption_before_native_loader(artifact, monkeypatch, damage):
    directory = artifact / "__mojocache__"
    manifest, = directory.glob("*.json")
    binary, = directory.glob("*.so")
    if damage == "binary":
        with binary.open("ab") as stream:
            stream.write(b"accidentally appended bytes")
    elif damage == "manifest":
        manifest.write_text("{")
    elif damage == "generated_sha256":
        data = json.loads(manifest.read_text())
        data[damage] = "3" * 64
        manifest.write_text(json.dumps(data))
    else:
        manifest.unlink()
        binary.unlink()
    monkeypatch.setattr(runtime, "_load_native_module", reject_loader)
    kernel = load(artifact, monkeypatch)
    assert kernel._compiled is None
    assert kernel(7) == 21


def test_verified_build_hit_uses_existing_binary(artifact, monkeypatch):
    backend = MojoBackend()
    monkeypatch.setattr(backend, "compile_mojo", reject_loader)
    ok, msg, _ = backend.build_ast(artifact / "subject.py")
    assert ok and "Reused verified" in msg
    kernel = load(artifact, monkeypatch)
    assert kernel(4) == 12
    assert inspect_dispatch(kernel)["call_count_native"] == 1


def test_source_change_with_restored_mtime(artifact, monkeypatch):
    monkeypatch.setenv("HOTLOOP_CACHE_CHECK", "always")
    kernel = load(artifact, monkeypatch)
    assert kernel(4) == 12
    source = artifact / "subject.py"
    stat = source.stat()
    source.write_text(SOURCE.replace("x * 3", "x * 5"))
    os.utime(source, ns=(stat.st_atime_ns, stat.st_mtime_ns))
    with pytest.warns(HotloopFallbackWarning, match="modified during runtime"):
        assert kernel(4) == 12  # The already-imported Python body remains the reference.
    assert inspect_dispatch(kernel)["last_backend"] == "python_fallback_stale_cache"


def test_compile_rechecks_captured_source(tmp_path, monkeypatch):
    source = tmp_path / "edited.py"
    source.write_text(SOURCE)
    backend = MojoBackend()

    def changing_source(_mojo, _out, *, env):
        source.write_text(SOURCE.replace("x * 3", "x * 5"))
        Path(_out).write_bytes(b"\x7fELF")
        return True, ""

    monkeypatch.setattr(backend, "compile_mojo", changing_source)
    ok, msg, path = backend.build_ast(source)
    assert not ok and "source changed" in msg
    assert path is None
    assert not list((tmp_path / "__mojocache__").glob("*.json"))


def test_optimizer_mode_has_distinct_abi(artifact):
    result = subprocess.run(
        [sys.executable, "-O", "-c",
         "from subject import calculate; print(calculate(-2), calculate._last_backend)"],
        cwd=artifact, check=True, capture_output=True, text=True,
    )
    assert "-6 python_fallback_stale_cache" in result.stdout


@pytest.mark.parametrize("target", ["directory", "manifest", "binary"])
def test_shared_cache_rejected_before_loading(artifact, monkeypatch, target):
    directory = artifact / "__mojocache__"
    item = directory if target == "directory" else next(directory.glob("*.json" if target == "manifest" else "*.so"))
    item.chmod(item.stat().st_mode | 0o020)
    monkeypatch.setattr(runtime, "_load_native_module", reject_loader)
    fn = load(artifact, monkeypatch)
    assert fn._compiled is None
    assert fn(7) == 21

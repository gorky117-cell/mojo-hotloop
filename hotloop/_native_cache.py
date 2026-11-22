# Copyright 2026 Gaurav Kumar Singh
# SPDX-License-Identifier: Apache-2.0
"""Shared identity and validation for locally built native artifacts."""

from functools import cache, lru_cache
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import stat
import struct
import subprocess
import sys
import sysconfig

CACHE_SCHEMA = 4
BUILD_FLAGS = ("build", "-O3", "--fp-mode", "contract=off", "--emit", "shared-lib")
_BUILD_ENV = frozenset({
    "CC", "CXX", "LD", "CFLAGS", "CPPFLAGS", "LDFLAGS", "CPATH",
    "C_INCLUDE_PATH", "CPLUS_INCLUDE_PATH", "LIBRARY_PATH", "LD_LIBRARY_PATH",
    "LD_PRELOAD", "SDKROOT",
})
_PACKAGE = Path(__file__).resolve().parent


def verify_cache_directory(directory):
    """Reject symlinks and directories under another user's write control."""
    uid = os.geteuid()
    for path in (directory, *directory.parents):
        entry = path.lstat()
        if not stat.S_ISDIR(entry.st_mode) or entry.st_uid not in (0, uid):
            raise ValueError("Untrusted native cache directory")
        if entry.st_mode & 0o022:
            # A root-owned sticky ancestor such as /tmp protects the owned child.
            if path == directory or entry.st_uid != 0 or not entry.st_mode & stat.S_ISVTX:
                raise ValueError("Writable shared native cache directory")


def verify_cache_file(path):
    entry = path.lstat()
    if (not stat.S_ISREG(entry.st_mode) or entry.st_uid not in (0, os.geteuid())
            or entry.st_mode & 0o022):
        raise ValueError("Untrusted native cache file")


def file_stamp(path):
    try:
        stat = os.stat(path)
    except OSError:
        return None
    return (stat.st_dev, stat.st_ino, stat.st_size, stat.st_mtime_ns, stat.st_ctime_ns)


def file_hash(path):
    try:
        with open(path, "rb") as stream:
            return hashlib.file_digest(stream, "sha256").hexdigest()
    except OSError:
        return None


def _json_hash(value):
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


@cache
def implementation_revision():
    # Installed wheels and editable checkouts use the same bytes. The imported
    # implementation is fixed for the lifetime of a Python process.
    return _json_hash({
        path.relative_to(_PACKAGE).as_posix(): file_hash(path)
        for path in sorted(_PACKAGE.rglob("*.py"))
    })


@cache
def host_abi():
    cpu = {}
    try:
        for line in Path("/proc/cpuinfo").read_text().splitlines():
            if not line.strip() and cpu:
                break
            name, _, value = line.partition(":")
            if name.strip() in {"vendor_id", "cpu family", "model", "stepping", "flags"}:
                cpu[name.strip()] = value.strip()
    except OSError:
        pass
    return _json_hash([
        sys.platform, platform.machine(), sys.byteorder, struct.calcsize("P"),
        sys.implementation.cache_tag, sysconfig.get_config_var("SOABI"),
        sysconfig.get_config_var("Py_DEBUG"), sys.flags.optimize, platform.libc_ver(), cpu,
    ])


def build_environment():
    env = os.environ.copy()
    venv = Path(sys.executable).absolute().parent.parent
    if (venv / "pyvenv.cfg").is_file():
        env["VIRTUAL_ENV"] = str(venv)
    if "PYTHONEXECUTABLE" in env:
        env["PYTHONEXECUTABLE"] = sys.executable
    return env


def find_mojo():
    candidates = (
        os.environ.get("MOJO_BIN", "").strip(),
        Path(sys.executable).absolute().with_name("mojo"),
        shutil.which("mojo"),
        Path.home() / ".modular/bin/mojo",
    )
    for path in candidates:
        if path and os.path.isfile(path) and os.access(path, os.X_OK):
            return str(Path(path).absolute())
    return None


def _sdk_files(root):
    lib = root / "lib"
    return {
        root / "bin/mojo", root / "bin/lld",
        lib / "libKGENCompilerRTShared.so", lib / "mojo/std.mojoc",
    }


def _toolchain_files(launcher, env):
    # Support the SDK executable and its wheel launcher. Other executables are
    # fingerprinted themselves together with explicitly selected SDK assets.
    path = Path(launcher)
    real_path = path.resolve()
    files = {real_path}
    for root in {path.parent.parent, real_path.parent.parent}:
        files.update(file for file in _sdk_files(root) if file.is_file())
        for site in root.glob("lib/python*/site-packages"):
            files.update(file for file in _sdk_files(site / "modular") if file.is_file())
            files.update(
                file for file in (site / "mojo").glob("*.py") if file.is_file()
            )
            for distribution in ("mojo", "mojo_compiler", "mojo_runtime"):
                files.update(site.glob(f"{distribution}-*.dist-info/METADATA"))
    for key in ("MODULAR_MAX_PACKAGE_ROOT", "MODULAR_MOJO_MAX_PACKAGE_ROOT", "MODULAR_HOME"):
        if location := env.get(key):
            files.update(file for file in _sdk_files(Path(location)) if file.is_file())
    for key in ("MODULAR_MOJO_MAX_DRIVER_PATH", "MODULAR_MOJO_MAX_LLD_PATH"):
        if location := env.get(key):
            files.add(Path(location))
    for location in env.get("MODULAR_MOJO_MAX_IMPORT_PATH", "").split(os.pathsep):
        if location:
            files.update(Path(location).glob("*.mojoc"))
    return sorted({str(file.resolve()) for file in files})


@lru_cache(maxsize=256)
def _stamped_hash(path, stamp):
    digest = file_hash(path) if stamp is not None else None
    return digest if file_stamp(path) == stamp else None


def toolchain_fingerprint(launcher, env):
    files = _toolchain_files(launcher, env)
    contents = {path: _stamped_hash(path, file_stamp(path)) for path in files}
    if any(digest is None for digest in contents.values()):
        raise ValueError("Could not verify the selected Mojo toolchain files")
    return _json_hash(contents)


def compilation_settings(env):
    return _json_hash([
        BUILD_FLAGS,
        {
            name: value for name, value in env.items()
            if name in _BUILD_ENV
            or (
                name != "MOJO_BIN"
                and name.startswith(("MODULAR_", "MOJO_"))
            )
        },
    ])


@lru_cache(maxsize=16)
def _version(launcher, fingerprint, settings, env):
    try:
        probe = subprocess.run(
            [launcher, "--version"], check=True, capture_output=True, text=True,
            env=dict(env), timeout=10,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    return probe.stdout.strip() or None


def build_context(launcher, env):
    launcher = str(Path(launcher).absolute())
    settings = compilation_settings(env)
    fingerprint = toolchain_fingerprint(launcher, env)
    version = _version(
        launcher, fingerprint, settings,
        tuple(sorted((key, value) for key, value in env.items() if key != "PWD")),
    )
    if not version:
        raise ValueError("Could not identify the selected Mojo toolchain version")
    return {
        "implementation": implementation_revision(),
        "abi": host_abi(),
        "settings": settings,
        "toolchain": fingerprint,
        "launcher": launcher,
        "compiler_version": version,
    }


def build_identity(source, source_hash, module, context):
    return {
        "schema": CACHE_SCHEMA,
        "source_file": source.name,
        "source_sha256": source_hash,
        "module": module,
        "context": context,
    }


def manifest_path(directory, identity, generated):
    key = _json_hash([identity, generated])
    name = f"{identity['module']}_{identity['source_sha256']}_{key}.json"
    return directory / name


def binary_path(directory, identity, digest):
    return directory / f"{identity['module']}_{_json_hash(identity)}_{digest}.so"


def read_manifest(path):
    verify_cache_file(path)
    with path.open(encoding="utf-8") as stream:
        data = json.load(stream)
    if not isinstance(data, dict):
        raise ValueError("Invalid native build manifest")
    return data


def checked_binary(manifest, data, identity):
    if any(data.get(key) != value for key, value in identity.items()):
        raise ValueError("Native build identity mismatch")
    digest = data.get("so_sha256")
    generated = data.get("generated_sha256")
    if not all(
        isinstance(value, str) and len(value) == 64
        and all(digit in "0123456789abcdef" for digit in value)
        for value in (digest, generated)
    ):
        raise ValueError("Invalid native build checksum")
    if manifest != manifest_path(manifest.parent, identity, generated):
        raise ValueError("Native build manifest filename mismatch")
    path = binary_path(manifest.parent, identity, digest)
    verify_cache_file(path)
    if file_hash(path) != digest:
        raise ValueError("Native binary is missing or failed SHA256 verification")
    return path

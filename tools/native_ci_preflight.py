"""Fail before test selection on an unqualified hosted native environment."""
import argparse
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import shutil
import struct
import subprocess
import sys
import sysconfig
import hotloop
from hotloop._native_cache import build_context,build_environment

p=argparse.ArgumentParser();p.add_argument("--output",type=Path,required=True);args=p.parse_args()
mojo=shutil.which("mojo")
assert mojo,"Mojo compiler missing"
version=subprocess.check_output([mojo,"--version"],text=True).strip()
assert "1.2.0 (2016d0cd)" in version,version
assert sys.implementation.name=="cpython" and sys.version_info[:3]==(3,12,16)
assert sys.platform=="linux" and platform.machine()=="x86_64" and struct.calcsize("P")==8
assert sys.byteorder=="little" and sys.int_info.bits_per_digit==30
assert not sysconfig.get_config_var("Py_GIL_DISABLED")
assert getattr(sys,"_is_gil_enabled",lambda:True)()
assert importlib.metadata.version("mojo-hotloop")=="0.2.1"
for name in ("mojo", "mojo-compiler", "mojo-lldb-libs"):
    assert importlib.metadata.version(name)=="1.2.0", name
assert not Path(hotloop.__file__).resolve().is_relative_to(Path(__file__).resolve().parents[1]/"hotloop"),"source checkout shadows installation"
record=dict(python=sys.version,abi=sysconfig.get_config_var("SOABI"),machine=platform.machine(),platform=platform.platform(),
 mojo=version,mojo_launcher_sha256=hashlib.sha256(Path(mojo).read_bytes()).hexdigest(),build_context=build_context(mojo,build_environment()),package=hotloop.__file__,
 runner_image=os.environ.get("ImageVersion"),runner_os_image=os.environ.get("ImageOS"),run_id=os.environ.get("GITHUB_RUN_ID"),git_sha=os.environ.get("GITHUB_SHA"))
args.output.write_text(json.dumps(record,indent=2)+"\n")
print(json.dumps(record))

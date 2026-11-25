"""Check packaged content against an exact local Git revision (no network access)."""
import argparse
import base64
import csv
from email.parser import BytesParser
import hashlib
from io import StringIO
from pathlib import Path
import subprocess
import tarfile
import zipfile


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("dist", type=Path)
    parser.add_argument("revision")
    args = parser.parse_args()

    def source(path):
        return subprocess.check_output(["git", "show", f"{args.revision}:{path}"])

    wheel, = args.dist.glob("*.whl")
    sdist, = args.dist.glob("*.tar.gz")
    with zipfile.ZipFile(wheel) as z, tarfile.open(sdist) as t:
        data = {i.filename: z.read(i) for i in z.infolist() if not i.is_dir()}
        tar = {m.name.partition("/")[2]: t.extractfile(m).read() for m in t if m.isfile()}
    runtime = subprocess.check_output(["git", "ls-tree", "-r", "--name-only", args.revision, "hotloop"]).decode().splitlines()
    assert set(runtime) == {p for p in data if p.startswith("hotloop/")} == {p for p in tar if p.startswith("hotloop/")}
    for p in runtime:
        assert data[p] == tar[p] == source(p), p
    for p in ("LICENSE", "NOTICE"):
        key, = (k for k in data if k.endswith("/licenses/" + p))
        assert data[key] == tar[p] == source(p), p
    record, = (p for p in data if p.endswith("/RECORD"))
    listed = set()
    for path, digest, size in csv.reader(StringIO(data[record].decode())):
        listed.add(path)
        if path == record:
            assert not digest and not size
        else:
            actual = base64.urlsafe_b64encode(hashlib.sha256(data[path]).digest()).decode().rstrip("=")
            assert digest == "sha256=" + actual and int(size) == len(data[path]), path
    assert listed == set(data)
    meta, = (raw for p, raw in data.items() if p.endswith("/METADATA"))
    for raw in (meta, tar["PKG-INFO"]):
        m = BytesParser().parsebytes(raw)
        assert (m["Name"], m["Version"], m["License-Expression"], m["Requires-Python"]) == ("mojo-hotloop","0.2.1","Apache-2.0",">=3.12")
        assert set(m.get_all("License-File")) == {"LICENSE","NOTICE"}
        assert set(m.get_all("Requires-Dist", [])) == {'numpy>=1.24; extra == "numpy"', 'numpy>=1.24; extra == "dev"'}
    assert not any(p.endswith((".so",".dll",".dylib")) for p in (*data,*tar))
    for p in (wheel, sdist):
        print(hashlib.sha256(p.read_bytes()).hexdigest(), p.name)
    print(f"Verified {len(runtime)} package files, {len(data)} wheel members, {len(tar)} sdist members.")


if __name__ == "__main__":
    main()

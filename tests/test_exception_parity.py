"""Exercise list bounds and exception order through the real public interface."""
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def test_list_exception_parity_and_non_list_exception_isolation(tmp_path):
    env = os.environ.copy()
    for key in ("HOTLOOP_STRICT", "HOTLOOP_FORCE_NATIVE", "HOTLOOP_STRICT_PERF"):
        env.pop(key, None)
    output = tmp_path / "observations"
    process = subprocess.run(
        [sys.executable, str(ROOT / "audit/exception_parity/gate.py"), "--output", str(output)],
        env=env, capture_output=True, text=True, timeout=180,
    )
    assert process.returncode == 0, process.stdout + process.stderr
    report = json.loads((output / "observations.json").read_text())
    assert len(report["rows"]) == 390
    assert report["counts"] == dict(A=236, B=125, C=29, D=0)
    assert not report["failures"]
    geographic = [row for row in report["rows"]
                  if row["function"] == "geographic" and row["expected"].get("exception") == "IndexError"]
    assert len(geographic) == 3
    assert all(row["actual"]["message"] == "list index out of range" for row in geographic)
    assert [row["backend"] for row in geographic] == ["python_fallback_slower", "native", "native"]
    explicit = [row for row in report["rows"] if row["function"].startswith("explicit_")]
    assert len(explicit) == 24
    assert all(row["classification"] == ("C" if row["mode"] == "strict" else "B") for row in explicit)

"""Retain the old gates unchanged and exercise the two-blocker input contract."""
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def test_numeric_operand_admission_and_predicate_native_routes(tmp_path):
    env = os.environ.copy()
    for key in ("HOTLOOP_STRICT", "HOTLOOP_FORCE_NATIVE", "HOTLOOP_STRICT_PERF"):
        env.pop(key, None)
    output = tmp_path / "observations"
    process = subprocess.run(
        [sys.executable, str(ROOT / "audit/two_blocker/gate.py"), "--output", str(output)],
        env=env, capture_output=True, text=True, timeout=180,
    )
    assert process.returncode == 0, process.stdout + process.stderr
    report = json.loads((output / "observations.json").read_text())
    assert not report["failures"] and report["counts"]["D"] == 0
    assert report["counts"]["A"] > 0 and report["counts"]["B"] > 0 and report["counts"]["C"] > 0
    predicates = [r for r in report["rows"]
                  if r["function"] in ("isnan_float", "isinf_float", "isnan_int", "isinf_int",
                                       "isnan_bool", "isinf_bool")]
    assert predicates and all(r["classification"] == "A" for r in predicates)

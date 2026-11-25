"""Permanent public-call math gates. The operand-type failure remains blocking."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]
GATE=ROOT/"audit/math_correctness"

def run_gate(script,tmp_path):
    env=os.environ.copy()
    for key in ("HOTLOOP_STRICT","HOTLOOP_FORCE_NATIVE","HOTLOOP_STRICT_PERF"):
        env.pop(key,None)
    destination=tmp_path/"observations"
    process=subprocess.run([sys.executable,str(GATE/script),"--output",str(destination)],
                           env=env,capture_output=True,text=True,timeout=180)
    report=json.loads((destination/"observations.json").read_text())
    return process,report

def test_original_fifteen_math_checks_unchanged(tmp_path):
    raw=(GATE/"original_gate.py").read_bytes()
    assert hashlib.sha256(raw).hexdigest()=="23d1a795a11dc26ca4ae170b64aaf4d940c256e855ad0518bc983e08d9f7067b"
    process,report=run_gate("original_gate.py",tmp_path)
    assert process.returncode==0,process.stdout+process.stderr
    assert report["denominator"]==15 and report["failures"]==[]
    assert all(x["backend"]=="native" and x["native_calls"]==1 and x["fallback_calls"]==0 for x in report["rows"])

def test_focused_native_math_bits_and_exceptions(tmp_path):
    process,report=run_gate("run_focused.py",tmp_path)
    assert process.returncode==0,process.stdout+process.stderr
    assert len(report["rows"])==342
    assert report["counts"]=={"A":342,"B":0,"C":0,"D":0}

def test_adjacent_math_admission_side_effects_and_aliases(tmp_path):
    process,report=run_gate("run_adjacent.py",tmp_path)
    # Not xfailed: string operands must never become numerical values
    # merely because Mojo can parse them.
    assert process.returncode==0,report["failures"]
    assert len(report["rows"])==111 and report["counts"]["D"]==0
    assert all(x["correct"] for x in report["rows"])

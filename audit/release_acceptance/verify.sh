#!/usr/bin/env bash
# Offline, installed-artifact verification. V is the provisioned toolchain venv.
# bash audit/release_acceptance/verify.sh NEW_OUTPUT_DIR COMMIT
set -euo pipefail
root=$(git rev-parse --show-toplevel)
dest=$1
revision=$2
expected_tests=${HOTLOOP_EXPECTED_PYTEST_COUNT:-324}
[[ "$expected_tests" =~ ^[0-9]+$ ]] || exit 2
mkdir "$dest"
dest=$(cd "$dest" && pwd)
mkdir -p "$dest"/{src,dist,rebuilt,bare,sdist-smoke,suite/benchmarks,parity,identity}
export PATH="$V/bin:$PATH" MOJO_BIN="$V/bin/mojo" PIP_NO_INDEX=1 PIP_DISABLE_PIP_VERSION_CHECK=1
export PYTHONDONTWRITEBYTECODE=1 OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1
unset PYTHONPATH HOTLOOP_STRICT HOTLOOP_FORCE_NATIVE HOTLOOP_STRICT_PERF
git archive "$revision" | tar -x -C "$dest/src"
git rev-parse "$revision" > "$dest/src/.artifact_revision"
export SOURCE_DATE_EPOCH=$(git show -s --format=%ct "$revision")
(cd "$dest/src"; "$V/bin/python" -c 'import sys,setuptools.build_meta as b; out=sys.argv[1]; b.build_sdist(out); b.build_wheel(out)' "$dest/dist") > "$dest/build.log" 2>&1
"$V/bin/python" "$root/audit/verify_patch_artifacts.py" "$dest/dist" "$revision" > "$dest/artifacts.log"
"$V/bin/python" -m venv "$dest/venv"
py="$dest/venv/bin/python"
"$py" -m pip install --no-deps --no-index "$dest/dist/"*.whl > "$dest/install.log"
(cd "$dest/bare"; "$py" "$root/audit/remediation/offline_probe.py"; "$py" -m pip check) > "$dest/bare.log"
"$V/bin/python" -m pip wheel --no-index --no-cache-dir --no-deps --no-build-isolation "$dest/dist/"*.tar.gz -w "$dest/rebuilt" > "$dest/rebuild.log"
cmp "$dest/dist/"*.whl "$dest/rebuilt/"*.whl
"$V/bin/python" -m venv "$dest/from-sdist"
"$dest/from-sdist/bin/pip" install --no-index "$dest/rebuilt/"*.whl > "$dest/sdist-install.log"
(cd "$dest/sdist-smoke"; "$dest/from-sdist/bin/python" "$root/audit/remediation/offline_probe.py"; "$dest/from-sdist/bin/pip" check) > "$dest/sdist.log"
dep=$("$V/bin/python" -c 'import sysconfig;print(sysconfig.get_path("purelib"))')
own=$("$py" -c 'import sysconfig;print(sysconfig.get_path("purelib"))')
printf '%s\n' "$dep" > "$own/test-dependencies.pth"
cp -r "$dest/src/"{tests,audit,examples} "$dest/suite/"
status=0
(cd "$dest/suite"; export PYTHONPATH="$PWD:$PWD/audit"; "$py" -m pytest -q tests) > "$dest/pytest.log" 2>&1 || status=$?
echo "$status" > "$dest/pytest-exit"
(cd "$dest/suite"; export PYTHONPATH="$PWD:$PWD/audit"; "$py" tests/test_compiler_adversarial.py) > "$dest/adversarial.log" 2>&1
(cd "$dest/suite"; export PYTHONPATH="$PWD:$PWD/audit"; "$py" audit/test_cache_invalidation.py) > "$dest/cache.log" 2>&1
(cd "$dest/parity"; "$py" "$root/audit/remediation/parity_probe.py") > "$dest/parity.json" 2> "$dest/parity.stderr"
(cd "$dest/identity"; "$py" "$root/audit/remediation/identity_probe.py" "$dest/src/tests/test_unfamiliar_functions.py") > "$dest/identity.json" 2> "$dest/identity.stderr"
for app in quant_backtest ar_spatial geo_distance ocr_matcher pii_scrubber pdf_cleaner rag_chunker; do
    (cd "$dest/suite"; export PYTHONPATH="$PWD:$PWD/audit"; "$py" -m hotloop.cli build "examples/$app/original.py" --no-verify && "$py" "$root/audit/return_provenance/application_probe.py" "$app" "$dest/dispatch-$app.json") > "$dest/verify-$app.log" 2>&1
done
for pair in 'v0.2.0 published' 'c2aebd78 remediation'; do
    read -r tag suite <<< "$pair"
    mkdir -p "$dest/$suite-tests/benchmarks"
    git archive "$tag" tests | tar -x -C "$dest/$suite-tests"
    status=0
    (cd "$dest/$suite-tests"; export PYTHONPATH="$PWD"; "$py" -m pytest -q tests) > "$dest/$suite-tests/result.log" 2>&1 || status=$?
    echo "$status" > "$dest/$suite-tests/exit"
done
"$V/bin/python" - "$dest" "$root" "$expected_tests" <<'PY'
import json
import sys
from pathlib import Path
dest, root = map(Path, sys.argv[1:3])
expected_tests = int(sys.argv[3])
baseline = json.loads((root / "docs/evidence/v0_2_1_remediation.json").read_text())
expected = set(baseline["historical_suites"]["v0.2.0"]["candidate_failures"])
def failures(path):
    return {line.removeprefix("FAILED ").split(" - ")[0] for line in path.read_text().splitlines()
            if line.startswith("FAILED ")}
assert failures(dest / "published-tests/result.log") == expected
assert "11 failed, 75 passed" in (dest / "published-tests/result.log").read_text()
assert not failures(dest / "remediation-tests/result.log")
assert "129 passed" in (dest / "remediation-tests/result.log").read_text()
cases = json.loads((dest / "parity.json").read_text())["cases"]
assert len(cases) == 15 and all(case["equal"] for case in cases.values())
identity = json.loads((dest / "identity.json").read_text())
assert identity["forced"]["returned_input"] and identity["strict"]["route"] == "native_error"
assert not failures(dest / "pytest.log")
assert f"{expected_tests} passed" in (dest / "pytest.log").read_text()
print("Installed artifact, original nine constant tests and complete regressions verified.")
PY

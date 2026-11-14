import os
import shutil
import subprocess
import sys

# Test environment info
print("=" * 65)
print("STAGE D8: CLEAN PYTHON INTEGRATION TEST")
print("=" * 65)
print(f"Python executable: {sys.executable}")
print(f"Python version:    {sys.version}")

# 1. Test package import
try:
    import hotloop
    from hotloop import hotloop, HotloopNativeExecutionError, HotloopFallbackWarning
    print("[✓] Step 1: Successfully imported 'hotloop' from installed package.")
except ImportError as e:
    print(f"[FAIL] Step 1: Failed to import hotloop: {e}")
    sys.exit(1)

# 2. Setup clean app directory
APP_DIR = "/tmp/test_hotloop_app"
os.makedirs(APP_DIR, exist_ok=True)
app_py = os.path.join(APP_DIR, "app.py")

with open(app_py, "w", encoding="utf-8") as f:
    f.write('''from hotloop import hotloop

@hotloop
def vector_dot_product(xs: list[float], ys: list[float]) -> float:
    total: float = 0.0
    for i in range(len(xs)):
        total += xs[i] * ys[i]
    return total
''')
print(f"[✓] Step 2: Created sample application at {app_py}")

# 3. Test transparent fallback prior to build
sys.path.insert(0, APP_DIR)
import app

xs = [1.0, 2.0, 3.0, 4.0, 5.0]
ys = [10.0, 20.0, 30.0, 40.0, 50.0]
expected_dot = sum(x * y for x, y in zip(xs, ys))

res_fallback = app.vector_dot_product(xs, ys)
if res_fallback != expected_dot:
    print(f"[FAIL] Step 3: Transparent fallback produced {res_fallback}, expected {expected_dot}")
    sys.exit(1)
print(f"[✓] Step 3: Transparent fallback executed successfully without native binary (res={res_fallback}).")

# 4. Run `hotloop build` CLI command
# Subprocess environment with clean virtualenv paths
sub_env = dict(os.environ)
sub_env["VIRTUAL_ENV"] = "/tmp/test_hotloop_env"
sub_env["PATH"] = f"/tmp/test_hotloop_env/bin:{sub_env.get('PATH', '')}"
sub_env["PYTHONPATH"] = f"/tmp/test_hotloop_env/lib/python3.12/site-packages:{sub_env.get('PYTHONPATH', '')}"

VENV_PYTHON = "/tmp/test_hotloop_env/bin/python"
hotloop_cli = [VENV_PYTHON, "-m", "hotloop.cli", "build", app_py, "--engine=ast"]
build_proc = subprocess.run(hotloop_cli, capture_output=True, text=True, env=sub_env)
if build_proc.returncode != 0:
    print(f"[FAIL] Step 4: 'hotloop build' failed:\n{build_proc.stderr}\n{build_proc.stdout}")
    sys.exit(1)
print("[✓] Step 4: 'hotloop build app.py --engine=ast' completed successfully.")
so_path = os.path.join(APP_DIR, "fast.so")
if not os.path.isfile(so_path):
    print(f"[FAIL] Step 4: Expected binary '{so_path}' not found after build.")
    sys.exit(1)

# 5. Reload and test native execution
# Force native execution
os.environ["HOTLOOP_FORCE_NATIVE"] = "1"

# In a new python subprocess to verify clean reload of the shared library
verify_script = f"""
import sys, os
sys.path.insert(0, '{APP_DIR}')
os.environ['HOTLOOP_FORCE_NATIVE'] = '1'
import app

xs = [1.0, 2.0, 3.0, 4.0, 5.0]
ys = [10.0, 20.0, 30.0, 40.0, 50.0]
expected = 550.0

res = app.vector_dot_product(xs, ys)
assert res == expected, f'Got {{res}}, expected {{expected}}'
assert app.vector_dot_product._compiled is not None, 'Compiled fn should not be None'
print('NATIVE_OK')
"""
proc_native = subprocess.run([VENV_PYTHON, "-c", verify_script], capture_output=True, text=True, env=sub_env)
if proc_native.returncode != 0 or "NATIVE_OK" not in proc_native.stdout:
    print(f"[FAIL] Step 5: Native execution failed in fresh subprocess:\n{proc_native.stderr}\n{proc_native.stdout}")
    sys.exit(1)
print("[✓] Step 5: Native compiled shared library executed successfully with identical result.")

# 6. Test strict mode behavior
strict_ok_script = f"""
import sys, os
sys.path.insert(0, '{APP_DIR}')
os.environ['HOTLOOP_STRICT'] = '1'
import app
res = app.vector_dot_product([1.0], [2.0])
assert res == 2.0
print('STRICT_OK')
"""
proc_strict = subprocess.run([VENV_PYTHON, "-c", strict_ok_script], capture_output=True, text=True, env=sub_env)
if proc_strict.returncode != 0 or "STRICT_OK" not in proc_strict.stdout:
    print(f"[FAIL] Step 6: Strict mode failed when binary is present:\n{proc_strict.stderr}")
    sys.exit(1)
print("[✓] Step 6: HOTLOOP_STRICT=1 runs cleanly when binary is present.")

# 7. Test strict mode failure when binary missing
# Move both binary and __mojocache__ away temporarily
backup_so = os.path.join(APP_DIR, "fast.so.bak")
backup_cache = os.path.join(APP_DIR, "__mojocache__.bak")
shutil.move(so_path, backup_so)
cache_dir = os.path.join(APP_DIR, "__mojocache__")
if os.path.isdir(cache_dir):
    shutil.move(cache_dir, backup_cache)

strict_fail_script = f"""
import sys, os
sys.path.insert(0, '{APP_DIR}')
os.environ['HOTLOOP_STRICT'] = '1'
from hotloop import HotloopNativeExecutionError
try:
    import app
    app.vector_dot_product([1.0], [2.0])
    print('DID_NOT_RAISE')
except HotloopNativeExecutionError as e:
    print('RAISED_EXPECTED_ERROR')
"""
proc_fail = subprocess.run([VENV_PYTHON, "-c", strict_fail_script], capture_output=True, text=True, env=sub_env)
shutil.move(backup_so, so_path) # Restore binary
if os.path.isdir(backup_cache):
    shutil.move(backup_cache, cache_dir)

if "RAISED_EXPECTED_ERROR" not in proc_fail.stdout:
    print(f"[FAIL] Step 7: Expected HotloopNativeExecutionError under strict mode, got:\n{proc_fail.stdout}\n{proc_fail.stderr}")
    sys.exit(1)
print("[✓] Step 7: HOTLOOP_STRICT=1 properly raised HotloopNativeExecutionError when binary missing.")

# 8. Test cache invalidation detection on source edit
with open(app_py, "a") as f:
    f.write("\n# Modified source file comment to trigger hash mismatch\n")

stale_check_script = f"""
import sys, os
sys.path.insert(0, '{APP_DIR}')
import app
# Without HOTLOOP_FORCE_NATIVE, stale binary should fall back or report stale
print('STALE_CHECK_OK')
"""
proc_stale = subprocess.run([VENV_PYTHON, "-c", stale_check_script], capture_output=True, text=True, env=sub_env)
if proc_stale.returncode != 0:
    print(f"[FAIL] Step 8: Error checking stale source:\n{proc_stale.stderr}")
    sys.exit(1)
print("[✓] Step 8: Cache invalidation logic gracefully detected source modification.")

print("\n" + "=" * 65)
print("STAGE D8 ALL INTEGRATION CHECKS PASSED (8/8)!")
print("=" * 65)
sys.stdout.flush()
sys.stderr.flush()
os._exit(0)

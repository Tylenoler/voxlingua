#!/usr/bin/env python3
"""Run all VoxLingua engine tests."""

import subprocess
import sys
import os
import io

test_dir = os.path.dirname(os.path.abspath(__file__))
engine_dir = os.path.dirname(test_dir)

test_files = [
    "test_audio.py",
    "test_session.py",
    "test_correction.py",
]

os.environ["PYTHONIOENCODING"] = "utf-8"

passed = 0
failed = 0

for tf in test_files:
    path = os.path.join(test_dir, tf)
    print(f"\n--- {tf} ---")
    result = subprocess.run(
        [sys.executable, path],
        capture_output=True, text=False, cwd=engine_dir,
    )
    stdout = result.stdout.decode("utf-8", errors="replace") if result.stdout else ""
    stderr = result.stderr.decode("utf-8", errors="replace") if result.stderr else ""
    
    if result.returncode == 0:
        passed += 1
    else:
        failed += 1
    
    for line in stdout.strip().split("\n")[-3:]:
        print(f"  {line}")
    if result.returncode != 0:
        err = stderr.strip()[-300:]
        print(f"  STDERR: {err}")

print(f"\n{'='*40}")
print(f"Results: {passed}/{passed+failed} passed")
sys.exit(0 if failed == 0 else 1)
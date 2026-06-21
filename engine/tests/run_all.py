#!/usr/bin/env python3
"""Run all VoxLingua engine tests."""

import subprocess
import sys
import os

test_dir = os.path.dirname(os.path.abspath(__file__))
engine_dir = os.path.dirname(test_dir)

test_files = [
    "test_audio.py",
    "test_session.py",
    "test_correction.py",
    "test_e2e_speech.py",
]

os.environ["PYTHONIOENCODING"] = "utf-8"

passed = 0
failed = 0

for tf in test_files:
    path = os.path.join(test_dir, tf)
    print(f"--- {tf} ---")
    result = subprocess.run(
        [sys.executable, path],
        capture_output=True, text=False, cwd=engine_dir,
    )
    stdout = result.stdout.decode("utf-8", errors="replace") if result.stdout else ""
    
    if result.returncode == 0:
        passed += 1
        for line in stdout.strip().split("\n")[-2:]:
            if line.strip():
                print(f"  {line}")
    else:
        failed += 1
        stderr = result.stderr.decode("utf-8", errors="replace") if result.stderr else ""
        print(f"  FAILED. STDERR: {stderr.strip()[-200:]}")
    print()

print(f"Results: {passed}/{passed+failed} passed")
sys.exit(0 if failed == 0 else 1)
"""
Simple backend runner - starts and keeps running
"""
import subprocess
import sys

print("=" * 50)
print("DrumTracKAI Backend Starter")
print("=" * 50)
print()
print("Starting backend...")
print("Press Ctrl+C to stop")
print()

python_exe = r"f:\DrumTracKAI_v1.1.11\drumtrackai_env\Scripts\python.exe"
backend_script = r"f:\DrumTracKAI_v1.1.16_Clean\dcsm_backend.py"

try:
    # Run backend and wait for it
    result = subprocess.run([python_exe, backend_script], cwd=r"f:\DrumTracKAI_v1.1.16_Clean")
    print()
    print("=" * 50)
    print(f"Backend exited with code: {result.returncode}")
    print("=" * 50)
except KeyboardInterrupt:
    print()
    print("Backend stopped by user")
except Exception as e:
    print()
    print(f"Error: {e}")

print()
input("Press Enter to close...")

@echo off
cd /d "f:\DrumTracKAI_v1.1.16_Clean"
set PYTHONPATH=%CD%
set USE_RUST=0
set HOST=0.0.0.0
set API_PORT=8000

echo Starting DrumTracKAI Backend Server...
f:\DrumTracKAI_v1.1.11\drumtrackai_env\Scripts\python.exe dcsm_backend.py
pause

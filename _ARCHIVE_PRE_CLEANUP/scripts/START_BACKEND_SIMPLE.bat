@echo off
cd /d f:\DrumTracKAI_v1.1.16_Clean
start "DrumTracKAI Backend" f:\DrumTracKAI_v1.1.11\drumtrackai_env\Scripts\python.exe run_backend.py
timeout /t 8 /nobreak
echo Backend starting in new window...
pause

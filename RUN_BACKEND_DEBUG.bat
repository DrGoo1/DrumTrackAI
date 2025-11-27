@echo off
echo ========================================
echo Running Backend in DEBUG mode
echo ========================================
echo.

cd /d f:\DrumTracKAI_v1.1.16_Clean

echo Using Python from: f:\DrumTracKAI_v1.1.11\drumtrackai_env\Scripts\python.exe
echo.
echo Starting backend...
echo Press Ctrl+C to stop
echo.

f:\DrumTracKAI_v1.1.11\drumtrackai_env\Scripts\python.exe dcsm_backend.py

echo.
echo ========================================
echo Backend stopped!
echo.
pause

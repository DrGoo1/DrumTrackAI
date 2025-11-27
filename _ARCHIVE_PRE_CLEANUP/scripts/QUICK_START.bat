@echo off
echo ========================================
echo DrumTracKAI v1.1.16 Quick Start
echo ========================================

REM Kill existing processes on our ports
taskkill /f /im python.exe 2>nul
taskkill /f /im node.exe 2>nul

echo Starting Backend Server (port 8000)...
start "Backend" cmd /k "cd /d f:\DrumTracKAI_v1.1.16_Clean && set PYTHONPATH=%CD% && set USE_RUST=0 && f:\DrumTracKAI_v1.1.11\drumtrackai_env\Scripts\python.exe dcsm_backend.py"

timeout /t 3 /nobreak >nul

echo Starting Frontend Server (port 3000)...
start "Frontend" cmd /k "cd /d f:\DrumTracKAI_v1.1.16_Clean\frontend && npm start"

echo.
echo Services starting...
echo - Backend: http://localhost:8000
echo - Frontend: http://localhost:3000  
echo - Files: http://localhost:8001
echo.
echo Wait 10-15 seconds then check the services.
pause

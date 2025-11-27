@echo off
echo ========================================
echo DrumTracKAI v1.1.16 Complete Startup
echo ========================================
echo.

echo Starting Backend Server...
start "Backend" cmd /c "cd /d %~dp0 && drumtrackai_env\Scripts\python.exe dcsm_backend.py"
timeout /t 3 >nul

echo Starting Main DCSM Frontend...
start "DCSM Frontend" cmd /c "cd /d %~dp0\frontend && npm start"
timeout /t 3 >nul

echo Starting Landing Page...
start "Landing Page" cmd /c "cd /d %~dp0\web-frontend-landing-v117 && set PORT=3004 && npm start"

echo.
echo ========================================
echo All services starting...
echo ========================================
echo Backend:       http://localhost:8000
echo DCSM Studio:   http://localhost:3000
echo Landing Page:  http://localhost:3004
echo ========================================
echo.
pause

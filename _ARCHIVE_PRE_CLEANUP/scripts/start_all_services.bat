@echo off
echo ========================================
echo DrumTracKAI v1.1.16 - Starting All Services
echo ========================================
echo.

echo Services to start:
echo   1. Backend API (port 8000)
echo   2. DCSM Studio (port 3000)
echo   3. Landing Page (port 3004)
echo.

REM Start Backend in new window
echo Starting Backend API...
start "DrumTracKAI Backend" cmd /k "cd /d f:\DrumTracKAI_v1.1.16_Clean && f:\DrumTracKAI_v1.1.11\drumtrackai_env\Scripts\python.exe dcsm_backend.py"

timeout /t 3 /nobreak >nul

REM Start DCSM Studio in new window
echo Starting DCSM Studio...
start "DCSM Studio" cmd /k "cd /d f:\DrumTracKAI_v1.1.16_Clean\frontend && npm start"

timeout /t 3 /nobreak >nul

REM Start Landing Page in new window
echo Starting Landing Page...
start "Landing Page" cmd /k "cd /d f:\DrumTracKAI_v1.1.16_Clean\web-frontend-landing-v117 && set PORT=3004 && npm start"

echo.
echo ========================================
echo All services starting...
echo ========================================
echo.
echo Wait 30 seconds for all services to be ready, then access:
echo.
echo   Landing Page:  http://localhost:3004  (Main Entry)
echo   DCSM Studio:   http://localhost:3000  (Drum Composer)
echo   Backend API:   http://localhost:8000  (AI System)
echo.
echo Press any key to open landing page in browser...
pause >nul

start http://localhost:3004

echo.
echo All services running!
echo Close this window when done.
echo.

@echo off
echo ========================================
echo DrumTracKAI v1.1.16 - Starting All Services
echo ========================================
echo.
echo This will start:
echo   1. Backend API (port 8000)
echo   2. DCSM Studio (port 3000)
echo   3. Landing Page (port 3004)
echo.
echo Each service will open in a new window.
echo.
pause

REM Start Backend
echo Starting Backend...
start "DrumTracKAI Backend" cmd /k "f:\DrumTracKAI_v1.1.16_Clean\1_START_BACKEND.bat"
timeout /t 3 /nobreak >nul

REM Start DCSM
echo Starting DCSM Studio...
start "DCSM Studio" cmd /k "f:\DrumTracKAI_v1.1.16_Clean\2_START_DCSM.bat"
timeout /t 3 /nobreak >nul

REM Start Landing Page
echo Starting Landing Page...
start "Landing Page" cmd /k "f:\DrumTracKAI_v1.1.16_Clean\3_START_LANDING_PAGE.bat"

echo.
echo ========================================
echo All services are starting...
echo ========================================
echo.
echo Wait 30-60 seconds, then access:
echo.
echo   Landing Page:  http://localhost:3004
echo   DCSM Studio:   http://localhost:3000
echo   Backend API:   http://localhost:8000
echo.
echo Opening landing page in browser...
timeout /t 15 /nobreak >nul
start http://localhost:3004

echo.
echo All services running!
echo To stop: run STOP_ALL.bat
echo.
pause

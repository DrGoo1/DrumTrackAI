@echo off
echo ========================================
echo Starting Complete DrumTracKAI System
echo ========================================
echo.

echo Step 1: Stopping any existing Node processes...
taskkill /F /IM node.exe 2>nul
timeout /t 2 /nobreak >nul

echo.
echo Step 2: Starting DCSM Frontend (port 3000)...
cd /d f:\DrumTracKAI_v1.1.16_Clean\frontend
start "DCSM Frontend - Port 3000" cmd /k "npm start"

echo.
echo Step 3: Waiting 20 seconds for DCSM to initialize...
timeout /t 20 /nobreak

echo.
echo Step 4: Starting Landing Page (port 3004)...
cd /d f:\DrumTracKAI_v1.1.16_Clean\web-frontend-landing-v117
start "Landing Page - Port 3004" cmd /k "set PORT=3004 && npm start"

echo.
echo Step 5: Waiting 30 seconds for Landing Page to initialize...
timeout /t 30 /nobreak

echo.
echo ========================================
echo ✅ System Started!
echo ========================================
echo.
echo DCSM Frontend: http://localhost:3000
echo Landing Page:  http://localhost:3004
echo.
echo Opening Landing Page (Professional Tier)...
start http://localhost:3004/?page=professional

echo.
echo ========================================
echo Both services are running in separate windows.
echo Close those windows to stop the services.
echo ========================================
pause

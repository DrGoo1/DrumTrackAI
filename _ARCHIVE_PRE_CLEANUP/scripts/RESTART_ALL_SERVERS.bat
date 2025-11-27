@echo off
echo ========================================
echo Restarting All DrumTracKAI Servers
echo ========================================
echo.

echo Step 1: Killing all Node.js processes...
taskkill /F /IM node.exe 2>nul
timeout /t 2 /nobreak >nul

echo.
echo Step 2: Starting Backend Server (port 8000)...
cd /d f:\DrumTracKAI_v1.1.16_Clean
start "Backend Server - Port 8000" cmd /k "f:\DrumTracKAI_v1.1.11\drumtrackai_env\Scripts\python.exe dcsm_backend.py"
timeout /t 5 /nobreak

echo.
echo Step 3: Starting DCSM Frontend (port 3000)...
cd /d f:\DrumTracKAI_v1.1.16_Clean\frontend
start "DCSM Frontend - Port 3000" cmd /k "npm start"
timeout /t 15 /nobreak

echo.
echo Step 4: Starting Landing Page (port 3004)...
cd /d f:\DrumTracKAI_v1.1.16_Clean\web-frontend-landing-v117
start "Landing Page - Port 3004" cmd /k "set PORT=3004 && npm start"
timeout /t 15 /nobreak

echo.
echo ========================================
echo All Servers Started!
echo ========================================
echo.
echo Backend:      http://localhost:8000
echo DCSM:         http://localhost:3000
echo Landing Page: http://localhost:3004
echo.
echo Opening Landing Page in 5 seconds...
timeout /t 5 /nobreak >nul
start http://localhost:3004

echo.
pause

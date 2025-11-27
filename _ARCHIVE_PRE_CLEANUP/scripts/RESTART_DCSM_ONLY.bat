@echo off
echo ========================================
echo Restarting DCSM Frontend Only
echo ========================================
echo.

echo Killing DCSM frontend on port 3000...
for /f "tokens=5" %%a in ('netstat -aon ^| findstr :3000') do taskkill /F /PID %%a 2>nul
timeout /t 2 /nobreak >nul

echo.
echo Starting DCSM Frontend (port 3000)...
cd /d f:\DrumTracKAI_v1.1.16_Clean\frontend
start "DCSM Frontend - Port 3000" cmd /k "npm start"

echo.
echo Waiting 25 seconds for frontend to compile...
timeout /t 25 /nobreak

echo.
echo ========================================
echo DCSM Frontend Restarted!
echo ========================================
echo Access: http://localhost:3000
echo.
pause

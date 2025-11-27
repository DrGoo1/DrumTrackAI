@echo off
echo ========================================
echo Restarting Landing Page Only
echo ========================================
echo.

echo Killing existing Node processes...
for /f "tokens=5" %%a in ('netstat -aon ^| findstr :3004') do taskkill /F /PID %%a 2>nul
timeout /t 2 /nobreak >nul

echo.
echo Starting Landing Page (port 3004)...
cd /d f:\DrumTracKAI_v1.1.16_Clean\web-frontend-landing-v117
start "Landing Page - Port 3004" cmd /k "set PORT=3004 && npm start"

echo.
echo Waiting 30 seconds for page to compile...
timeout /t 30 /nobreak

echo.
echo Opening Professional Tier page...
start http://localhost:3004/?page=professional

echo.
echo ========================================
echo Landing Page Restarted!
echo ========================================
echo Access: http://localhost:3004
pause

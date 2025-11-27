@echo off
echo ========================================
echo Restarting Landing Page
echo ========================================
echo.

echo Stopping any existing Node processes...
taskkill /F /IM node.exe 2>nul

echo.
echo Waiting 3 seconds...
timeout /t 3 /nobreak >nul

echo.
echo Starting Landing Page on port 3004...
cd /d f:\DrumTracKAI_v1.1.16_Clean\web-frontend-landing-v117
set PORT=3004
start "Landing Page" npm start

echo.
echo Landing page is starting...
echo Wait 30 seconds, then it will open in browser.
echo.
timeout /t 30 /nobreak

echo Opening in browser...
start http://localhost:3004

echo.
echo If you see a black screen:
echo   1. Wait another 30 seconds
echo   2. Refresh the page (F5)
echo   3. Check the "Landing Page" window for errors
echo.
pause

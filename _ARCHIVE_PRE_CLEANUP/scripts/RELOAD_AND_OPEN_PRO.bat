@echo off
echo ========================================
echo Reloading Landing Page and Opening Pro Tier
echo ========================================
echo.

echo Step 1: Stopping any existing Node processes...
taskkill /F /IM node.exe 2>nul
echo Done.

echo.
echo Step 2: Waiting 3 seconds...
timeout /t 3 /nobreak >nul

echo.
echo Step 3: Starting Landing Page...
cd /d f:\DrumTracKAI_v1.1.16_Clean\web-frontend-landing-v117
start "Landing Page" cmd /k "set PORT=3004 && npm start"

echo.
echo Step 4: Waiting 45 seconds for service to start...
timeout /t 45 /nobreak

echo.
echo Step 5: Opening Professional Tier page...
start http://localhost:3004/?page=professional

echo.
echo ========================================
echo Professional Tier page should be opening!
echo ========================================
echo.
echo If you see errors, wait 15 more seconds and refresh.
echo.
pause

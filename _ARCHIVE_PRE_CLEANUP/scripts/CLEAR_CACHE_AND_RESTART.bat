@echo off
echo ========================================
echo Clearing Browser Cache and Restarting
echo ========================================
echo.

echo Step 1: Stopping Landing Page server...
taskkill /F /IM node.exe /FI "WINDOWTITLE eq Landing Page*" 2>nul
timeout /t 2 /nobreak >nul

echo.
echo Step 2: Clearing npm cache...
cd /d f:\DrumTracKAI_v1.1.16_Clean\web-frontend-landing-v117
call npm cache clean --force

echo.
echo Step 3: Deleting build folder...
if exist build rmdir /s /q build

echo.
echo Step 4: Restarting Landing Page...
start "Landing Page - Port 3004" cmd /k "set PORT=3004 && npm start"

echo.
echo Step 5: Waiting 30 seconds for server to start...
timeout /t 30 /nobreak

echo.
echo ========================================
echo ✅ Done! Now:
echo ========================================
echo.
echo 1. Close ALL browser windows/tabs
echo 2. Reopen browser
echo 3. Go to: http://localhost:3004
echo 4. Press Ctrl+Shift+Delete
echo 5. Clear "Cached images and files"
echo 6. Click Professional tab
echo.
echo This should load the NEW page!
echo.
pause

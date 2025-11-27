@echo off
echo ========================================
echo Force Refresh Landing Page
echo ========================================
echo.

echo Step 1: Killing Landing Page server...
for /f "tokens=5" %%a in ('netstat -aon ^| findstr :3004') do taskkill /F /PID %%a 2>nul
timeout /t 2 /nobreak >nul

echo.
echo Step 2: Deleting old build cache...
cd /d f:\DrumTracKAI_v1.1.16_Clean\web-frontend-landing-v117
if exist build rmdir /s /q build
if exist .cache rmdir /s /q .cache

echo.
echo Step 3: Restarting server on port 3004...
start "Landing Page - Port 3004" cmd /k "set PORT=3004 && npm start"

echo.
echo Waiting 35 seconds for server to compile...
timeout /t 35 /nobreak

echo.
echo ========================================
echo Server Restarted!
echo ========================================
echo.
echo CORRECT URL: http://localhost:3004
echo.
echo INSTRUCTIONS:
echo 1. Close ALL browser windows/tabs
echo 2. Open a NEW browser window
echo 3. Go to: http://localhost:3004
echo 4. Click on "Professional" in the navigation
echo 5. You should see the NEW page with:
echo    - Upload Audio File
echo    - Professional Drummer Analysis
echo    - Classic Beats Library
echo    - Sing In a Beat
echo.
echo Opening in 5 seconds...
timeout /t 5 /nobreak >nul
start http://localhost:3004

pause

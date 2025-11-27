@echo off
echo ========================================
echo Checking and Starting DCSM
echo ========================================
echo.

echo Checking if DCSM is running on port 3000...
netstat -ano | findstr ":3000" >nul 2>&1

if %ERRORLEVEL% EQU 0 (
    echo ✅ DCSM is already running on port 3000
    echo Opening DCSM in browser...
    start http://localhost:3000
) else (
    echo ⚠️ DCSM is not running. Starting it now...
    echo.
    cd /d f:\DrumTracKAI_v1.1.16_Clean\frontend
    start "DCSM Frontend" npm start
    
    echo.
    echo Waiting 30 seconds for DCSM to start...
    timeout /t 30 /nobreak
    
    echo Opening DCSM in browser...
    start http://localhost:3000
)

echo.
echo ========================================
echo DCSM should be accessible at:
echo http://localhost:3000
echo ========================================
pause

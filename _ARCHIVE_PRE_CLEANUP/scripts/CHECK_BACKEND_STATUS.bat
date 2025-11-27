@echo off
echo ========================================
echo Checking Backend Status
echo ========================================
echo.

echo Checking if backend is running on port 8000...
netstat -ano | findstr ":8000"

if %ERRORLEVEL% EQU 0 (
    echo.
    echo ✅ Backend is running on port 8000
) else (
    echo.
    echo ❌ Backend is NOT running on port 8000
    echo.
    echo Starting backend now...
    cd /d f:\DrumTracKAI_v1.1.16_Clean
    start "Backend Server - Port 8000" cmd /k "python dcsm_backend.py"
    
    echo.
    echo Waiting 10 seconds for backend to start...
    timeout /t 10 /nobreak
)

echo.
echo Testing backend connection...
curl -f http://localhost:8000/healthz

echo.
echo.
pause

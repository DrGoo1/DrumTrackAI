@echo off
echo ========================================
echo Checking What's Killing the Backend
echo ========================================
echo.

echo 1. Checking if backend is running...
netstat -ano | findstr ":8000"

if %ERRORLEVEL% EQU 0 (
    echo Backend IS running
) else (
    echo Backend is NOT running - it crashed!
)

echo.
echo 2. Checking Python processes...
tasklist | findstr python

echo.
echo 3. Testing backend connection...
powershell -Command "try { Invoke-WebRequest -Uri 'http://localhost:8000/healthz' -UseBasicParsing | Select-Object -ExpandProperty Content } catch { Write-Host 'Backend not responding' -ForegroundColor Red }"

echo.
echo ========================================
echo.
echo IMPORTANT: Look at the backend console window
echo to see the actual Python error that's killing it!
echo.
pause

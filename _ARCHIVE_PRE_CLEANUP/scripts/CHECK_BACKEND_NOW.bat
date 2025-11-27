@echo off
echo ========================================
echo Checking Backend Status
echo ========================================
echo.

echo 1. Checking if port 8000 is open...
netstat -ano | findstr ":8000"

echo.
echo 2. Trying to connect...
powershell -Command "try { $r = Invoke-WebRequest -Uri 'http://localhost:8000/healthz' -UseBasicParsing; Write-Host 'SUCCESS:' $r.Content -ForegroundColor Green } catch { Write-Host 'FAILED:' $_.Exception.Message -ForegroundColor Red }"

echo.
echo 3. Checking Python processes...
tasklist | findstr python

echo.
pause

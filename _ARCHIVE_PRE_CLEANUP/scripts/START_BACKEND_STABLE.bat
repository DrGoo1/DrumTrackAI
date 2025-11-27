@echo off
echo ========================================
echo Starting Backend (Stable Version)
echo ========================================

echo Killing existing processes on port 8000...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :8000') do taskkill /F /PID %%a 2>nul
timeout /t 2 /nobreak >nul

cd /d f:\DrumTracKAI_v1.1.16_Clean

echo.
echo Starting backend...
start "DrumTracKAI Backend - Port 8000" cmd /c "f:\DrumTracKAI_v1.1.11\drumtrackai_env\Scripts\python.exe dcsm_backend.py || (echo Backend crashed! & pause)"

timeout /t 8 /nobreak

echo.
echo Testing connection...
powershell -Command "try { (Invoke-WebRequest -Uri 'http://localhost:8000/healthz' -UseBasicParsing).Content } catch { Write-Host 'Failed' -ForegroundColor Red }"

echo.
echo Backend should be running now.
echo DO NOT CLOSE the backend window!
echo.
pause

@echo off
echo Testing backend...
echo.

cd /d f:\DrumTracKAI_v1.1.16_Clean

echo Using Python from v1.1.11 environment...
f:\DrumTracKAI_v1.1.11\drumtrackai_env\Scripts\python.exe -c "print('Python OK')"

echo.
echo Starting backend with correct Python...
start "Backend - Port 8000" cmd /k "f:\DrumTracKAI_v1.1.11\drumtrackai_env\Scripts\python.exe dcsm_backend.py"

echo.
echo Waiting 10 seconds for backend to start...
timeout /t 10 /nobreak

echo.
echo Testing connection...
powershell -Command "try { (Invoke-WebRequest -Uri 'http://localhost:8000/healthz').Content } catch { Write-Host 'Failed to connect' -ForegroundColor Red }"

pause

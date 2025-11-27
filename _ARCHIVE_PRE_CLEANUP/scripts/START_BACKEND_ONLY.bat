@echo off
echo ========================================
echo Starting Backend Server ONLY
echo ========================================
echo.

echo Killing any existing Python processes on port 8000...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :8000') do taskkill /F /PID %%a 2>nul
timeout /t 2 /nobreak >nul

echo.
echo Starting Backend with correct Python environment...
cd /d f:\DrumTracKAI_v1.1.16_Clean

echo.
echo Backend will start in a new window.
echo Starting backend with correct Python...
start "Backend Server - Port 8000 - KEEP THIS OPEN" cmd /k "f:\DrumTracKAI_v1.1.11\drumtrackai_env\Scripts\python.exe dcsm_backend.py & echo. & echo Backend exited unexpectedly! & echo Press any key to close... & pause"

echo.
echo Waiting 8 seconds for backend to start...
timeout /t 8 /nobreak

echo.
echo Testing backend connection...
powershell -Command "$ProgressPreference = 'SilentlyContinue'; try { $r = Invoke-WebRequest -Uri 'http://localhost:8000/healthz' -UseBasicParsing; Write-Host 'SUCCESS! Backend is running!' -ForegroundColor Green; Write-Host $r.Content } catch { Write-Host 'FAILED! Backend did not start!' -ForegroundColor Red; Write-Host $_.Exception.Message }"

echo.
echo ========================================
echo.
echo If you see SUCCESS above, backend is ready!
echo If you see FAILED, check the backend window for errors.
echo.
pause

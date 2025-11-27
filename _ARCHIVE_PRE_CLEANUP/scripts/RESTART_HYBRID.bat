@echo off
echo ================================================
echo Restarting DrumTracKAI v1.1.16 with Hybrid FFI
echo ================================================
echo.

:: Kill existing processes
echo Stopping existing services...
taskkill /f /im python.exe >nul 2>&1
taskkill /f /im node.exe >nul 2>&1
for /f "tokens=5" %%a in ('netstat -aon ^| findstr :8000') do taskkill /f /pid %%a >nul 2>&1
for /f "tokens=5" %%a in ('netstat -aon ^| findstr :3000') do taskkill /f /pid %%a >nul 2>&1

timeout /t 2 /nobreak >nul

:: Set environment variables for hybrid mode
set USE_RUST=0
set USE_TRACKTION_FFI=1
set TRACKTION_FFI_LIB=%CD%\tracktion-hybrid\rust\audio-core-ffi\target\release\audio_core_ffi.dll
set PYTHONPATH=%CD%\drumtrackai_env\Lib\site-packages

echo Starting backend with Tracktion FFI integration...
start "DrumTracKAI Backend" cmd /k "drumtrackai_env\Scripts\python.exe dcsm_backend.py"

timeout /t 3 /nobreak >nul

echo Starting frontend...
cd frontend
start "DrumTracKAI Frontend" cmd /k "npm start"
cd ..

echo.
echo ================================================
echo DrumTracKAI v1.1.16 Hybrid System Starting...
echo ================================================
echo.
echo Backend (with FFI): http://localhost:8000
echo Frontend:           http://localhost:3000
echo.
echo FFI Library: %TRACKTION_FFI_LIB%
echo.
echo Wait 10-15 seconds for services to fully start...
echo.
pause

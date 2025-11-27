@echo off
echo ================================================
echo DrumTracKAI v1.1.16 Hybrid System - Simple Deploy
echo ================================================
echo.

:: Kill existing processes
taskkill /f /im python.exe >nul 2>&1
taskkill /f /im node.exe >nul 2>&1

:: Wait for cleanup
timeout /t 2 /nobreak >nul

echo Starting backend server with FFI integration...
start "Backend" cmd /k "cd /d %~dp0 && set USE_TRACKTION_FFI=1 && set TRACKTION_FFI_LIB=%~dp0tracktion-hybrid\rust\audio-core-ffi\target\release\audio_core_ffi.dll && drumtrackai_env\Scripts\python.exe dcsm_backend.py"

echo Waiting for backend to start...
timeout /t 5 /nobreak >nul

echo Starting frontend server...
start "Frontend" cmd /k "cd /d %~dp0frontend && npm start"

echo.
echo ================================================
echo Services Starting...
echo ================================================
echo.
echo Backend (FFI): http://localhost:8000
echo Frontend:      http://localhost:3000
echo.
echo Wait 15-20 seconds for services to fully initialize
echo Then open: http://localhost:3000
echo.
pause

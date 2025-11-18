@echo off
echo ========================================
echo DrumTracKAI v1.1.16 Native Launch Script
echo ========================================
echo.

REM Set environment variables
set PYTHONPATH=%CD%
set USE_RUST=1
set AUDIO_CORE_BIN=%CD%\audio-core\target\release\audio-core.exe
set TRACKTION_FFI_LIB=%CD%\tracktion-hybrid\rust\audio-core-ffi\target\release\audio_core_ffi.dll

echo Starting DrumTracKAI v1.1.16 with Tracktion Hybrid...
echo.

REM Check if Python environment exists
if not exist "f:\DrumTracKAI_v1.1.11\drumtrackai_env\Scripts\python.exe" (
    echo ERROR: Python environment not found at f:\DrumTracKAI_v1.1.11\drumtrackai_env\
    echo Please run the environment setup first.
    pause
    exit /b 1
)

REM Start backend server in new window
echo [1/3] Starting DCSM Backend Server (port 8000)...
start "DrumTracKAI Backend v1.1.16" cmd /k "f:\DrumTracKAI_v1.1.11\drumtrackai_env\Scripts\python.exe dcsm_backend.py"

REM Wait a moment for backend to start
timeout /t 3 /nobreak >nul

REM Start frontend server in new window
echo [2/3] Starting React Frontend (port 3000)...
cd frontend
if not exist node_modules (
    echo Installing frontend dependencies...
    call npm install
)
start "DrumTracKAI Frontend v1.1.16" cmd /k "npm start"
cd ..

REM Wait a moment for frontend to start
timeout /t 3 /nobreak >nul

REM Build and start Tracktion Hybrid if available
echo [3/3] Building Tracktion Hybrid FFI Library...
if exist tracktion-hybrid\rust\audio-core-ffi (
    cd tracktion-hybrid\rust\audio-core-ffi
    echo Building Rust FFI library...
    cargo build --release
    if %ERRORLEVEL% EQU 0 (
        echo Tracktion Hybrid FFI library built successfully!
        echo Location: %CD%\target\release\audio_core_ffi.dll
    ) else (
        echo WARNING: Failed to build Tracktion Hybrid FFI library
    )
    cd ..\..\..
) else (
    echo WARNING: Tracktion Hybrid components not found
)

echo.
echo ========================================
echo DrumTracKAI v1.1.16 Launch Complete!
echo ========================================
echo.
echo Access Points:
echo - DCSM Studio:    http://localhost:3000
echo - Backend API:    http://localhost:8000
echo - Benchmarks:     http://localhost:3000/bench
echo.
echo Environment Variables Set:
echo - PYTHONPATH=%PYTHONPATH%
echo - USE_RUST=%USE_RUST%
echo - AUDIO_CORE_BIN=%AUDIO_CORE_BIN%
echo - TRACKTION_FFI_LIB=%TRACKTION_FFI_LIB%
echo.
echo Press any key to open DCSM Studio in browser...
pause >nul
start "" "http://localhost:3000"

echo.
echo All services are running. Close this window to keep services active.
echo To stop services, close the individual command windows.
pause

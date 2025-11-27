@echo off
echo ================================================
echo DrumTracKAI v1.1.16 Hybrid - Manual Start
echo ================================================
echo.

:: Kill any existing processes
taskkill /f /im python.exe >nul 2>&1
taskkill /f /im node.exe >nul 2>&1
timeout /t 2 /nobreak >nul

:: Check Python installation
echo Checking Python installation...
python --version
if %errorlevel% neq 0 (
    echo ERROR: Python not found in PATH
    echo Please install Python 3.11+ and add to PATH
    pause
    exit /b 1
)

:: Check if virtual environment exists
if not exist "drumtrackai_env\Scripts\python.exe" (
    echo Creating Python virtual environment...
    python -m venv drumtrackai_env
    echo Installing requirements...
    drumtrackai_env\Scripts\pip install -r requirements.txt
)

:: Set environment variables
set USE_TRACKTION_FFI=1
set TRACKTION_FFI_LIB=%CD%\tracktion-hybrid\rust\audio-core-ffi\target\release\audio_core_ffi.dll

echo.
echo Starting backend server...
echo Environment: USE_TRACKTION_FFI=%USE_TRACKTION_FFI%
echo FFI Library: %TRACKTION_FFI_LIB%
echo.

:: Start backend in new window
start "DrumTracKAI Backend" cmd /k "cd /d %CD% && set USE_TRACKTION_FFI=1 && set TRACKTION_FFI_LIB=%TRACKTION_FFI_LIB% && drumtrackai_env\Scripts\python.exe dcsm_backend.py"

echo Waiting 8 seconds for backend to start...
timeout /t 8 /nobreak

:: Check if Node.js is available
where npm >nul 2>&1
if %errorlevel% neq 0 (
    echo WARNING: npm not found. Please install Node.js
    echo You can still access the backend at http://localhost:8000
    pause
    exit /b 0
)

echo Starting frontend server...
start "DrumTracKAI Frontend" cmd /k "cd /d %CD%\frontend && npm start"

echo.
echo ================================================
echo DrumTracKAI v1.1.16 Hybrid System Started
echo ================================================
echo.
echo Backend API:  http://localhost:8000
echo Frontend App: http://localhost:3000
echo.
echo Wait 15-20 seconds for frontend to compile
echo Then open: http://localhost:3000
echo.
echo Press any key to open the application...
pause >nul
start http://localhost:3000

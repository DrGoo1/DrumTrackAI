@echo off
echo ================================================
echo DrumTracKAI v1.1.16 Hybrid - Working Launch
echo ================================================
echo.

:: Kill any existing processes
taskkill /f /im python.exe >nul 2>&1
taskkill /f /im node.exe >nul 2>&1
timeout /t 2 /nobreak >nul

:: Check if Python environment exists
if not exist "drumtrackai_env\Scripts\python.exe" (
    echo Creating Python virtual environment...
    python -m venv drumtrackai_env
    if %errorlevel% neq 0 (
        echo ERROR: Failed to create virtual environment
        echo Make sure Python is installed and in PATH
        pause
        exit /b 1
    )
    
    echo Installing Python dependencies...
    drumtrackai_env\Scripts\pip install -r requirements.txt
    if %errorlevel% neq 0 (
        echo ERROR: Failed to install dependencies
        pause
        exit /b 1
    )
)

:: Start backend server
echo Starting backend server with FFI integration...
set USE_TRACKTION_FFI=1
set TRACKTION_FFI_LIB=%CD%\tracktion-hybrid\rust\audio-core-ffi\target\release\audio_core_ffi.dll

start "DrumTracKAI Backend" cmd /k "cd /d %CD% && set USE_TRACKTION_FFI=1 && set TRACKTION_FFI_LIB=%TRACKTION_FFI_LIB% && echo Starting backend... && drumtrackai_env\Scripts\python.exe dcsm_backend.py"

echo Waiting for backend to initialize...
timeout /t 8 /nobreak

:: Check if frontend directory exists
if not exist "frontend\package.json" (
    echo ERROR: Frontend directory not found
    echo Make sure you're in the correct DrumTracKAI directory
    pause
    exit /b 1
)

:: Check if Node.js is available
where npm >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: npm not found
    echo Please install Node.js from https://nodejs.org/
    pause
    exit /b 1
)

:: Install frontend dependencies if needed
if not exist "frontend\node_modules" (
    echo Installing frontend dependencies...
    cd frontend
    npm install
    cd ..
)

:: Start frontend server
echo Starting frontend server...
start "DrumTracKAI Frontend" cmd /k "cd /d %CD%\frontend && echo Starting frontend... && npm start"

echo.
echo ================================================
echo Services Starting...
echo ================================================
echo.
echo Backend:  http://localhost:8000
echo Frontend: http://localhost:3000
echo.
echo Wait 20-30 seconds for services to fully start
echo Then the browser should automatically open
echo.
echo If browser doesn't open automatically:
echo 1. Open your browser
echo 2. Go to: http://localhost:3000
echo.
timeout /t 25 /nobreak
start http://localhost:3000

@echo off
echo ================================================
echo DrumTracKAI v1.1.16 Complete Deployment Script
echo ================================================
echo.

:: Set working directory
cd /d "f:\DrumTracKAI_v1.1.16_Clean"

:: Check if Python 3.13 is available
C:\Python313\python.exe --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Python 3.13 not found at C:\Python313\
    echo Please install Python 3.13 or update the path
    pause
    exit /b 1
)

echo Python 3.13.7 found
echo.

:: Install Python dependencies with timeout handling
echo Installing Python dependencies...
timeout /t 1 /nobreak >nul
C:\Python313\python.exe -m pip install --user --no-cache-dir aiohttp==3.9.1 aiohttp-cors==0.7.0 numpy==1.24.3 librosa==0.10.1 scipy==1.10.1 soundfile==0.12.1 fastapi==0.104.1 uvicorn==0.24.0
if %errorlevel% neq 0 (
    echo WARNING: Some Python packages may have failed to install
    echo Continuing with available packages...
)
echo.

:: Check if Node.js is installed
where node >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Node.js not found. Please install Node.js 18+ LTS
    echo Download from: https://nodejs.org/
    pause
    exit /b 1
)

echo Node.js version:
node --version
echo.

:: Install frontend dependencies if needed
if not exist "frontend\node_modules" (
    echo Installing frontend dependencies...
    cd frontend
    npm install --legacy-peer-deps
    if %errorlevel% neq 0 (
        echo ERROR: Frontend dependencies installation failed
        cd ..
        pause
        exit /b 1
    )
    cd ..
    echo Frontend dependencies installed successfully
    echo.
)

:: Set environment variables
set USE_RUST=1
set AUDIO_CORE_MODE=auto
set REACT_APP_API_BASE=http://localhost:8000

:: Start backend server
echo Starting DCSM Backend v1.1.16...
start "DCSM Backend v1.1.16" cmd /k "C:\Python313\python.exe dcsm_backend.py"

:: Wait for backend to start
echo Waiting for backend to initialize...
timeout /t 8 /nobreak >nul

:: Start frontend server
echo Starting DCSM Frontend v1.1.16...
cd frontend
start "DCSM Frontend v1.1.16" cmd /k "npm start"
cd ..

:: Wait for frontend to start
echo Waiting for frontend to initialize...
timeout /t 10 /nobreak >nul

:: Open application
echo Opening DrumTracKAI v1.1.16 DCSM Studio...
start http://localhost:3000

echo.
echo ================================================
echo DrumTracKAI v1.1.16 Deployment Complete!
echo ================================================
echo.
echo Access Points:
echo - DCSM Studio: http://localhost:3000
echo - Backend API: http://localhost:8000
echo - Benchmarks: http://localhost:3000/bench
echo - Landing Page: landing_page.html
echo.
echo Features Available:
echo - Advanced Groove Engine with swing presets
echo - Multi-bar Fill Library with style-aware patterns
echo - Smart Sectionization with downbeat detection
echo - Type-1 Multi-track MIDI Export
echo - Performance Benchmarking Suite
echo - Professional mixer and piano roll
echo.
echo Press any key to exit this deployment script...
pause >nul

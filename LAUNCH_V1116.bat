@echo off
echo ================================================
echo DrumTracKAI v1.1.16 Enhanced DCSM Launch Script
echo ================================================
echo.

:: Set working directory
cd /d "f:\DrumTracKAI_v1.1.16_Clean"

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

:: Check if Python is available
where python >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Python not found. Using v1.1.11 environment...
    set PYTHON_EXE=f:\DrumTracKAI_v1.1.11\drumtrackai_env\Scripts\python.exe
) else (
    set PYTHON_EXE=python
)

:: Install frontend dependencies if needed
if not exist "frontend\node_modules" (
    echo Installing frontend dependencies...
    cd frontend
    npm install
    cd ..
    echo.
)

:: Start the backend server
echo Starting DCSM Backend v1.1.16...
start "DCSM Backend v1.1.16" cmd /k "%PYTHON_EXE% dcsm_backend.py"

:: Wait for backend to start
timeout /t 5 /nobreak >nul

:: Start the enhanced DCSM frontend
echo Starting Enhanced DCSM Frontend v1.1.16...
echo Frontend will be available at: http://localhost:3000
echo.
echo Features included:
echo - Advanced Groove Engine with swing presets
echo - Multi-bar Fill Library with style-aware patterns
echo - Smart Sectionization with downbeat detection
echo - Type-1 Multi-track MIDI Export
echo - Performance Benchmarking Suite
echo - Professional mixer and piano roll
echo.

start "DCSM Frontend v1.1.16" cmd /k "cd /d f:\DrumTracKAI_v1.1.16_Clean\frontend && npm start"

:: Wait a moment for frontend to start
timeout /t 3 /nobreak >nul

:: Open landing page
echo Opening DrumTracKAI v1.1.16 Landing Page...
start "" "f:\DrumTracKAI_v1.1.16_Clean\landing_page.html"

echo.
echo ================================================
echo DrumTracKAI v1.1.16 Enhanced DCSM is starting...
echo ================================================
echo.
echo Access points:
echo - DCSM Studio: http://localhost:3000
echo - Backend API: http://localhost:8000
echo - Benchmarks: http://localhost:3000/bench
echo - Landing Page: landing_page.html
echo.
echo Press any key to exit this launcher...
pause >nul

@echo off
echo 🎯 DrumTracKAI v1.1.16 DCSM - Clean Build
echo ==========================================

:: Check Python environment - use original environment
if not exist "f:\DrumTracKAI_v1.1.11\drumtrackai_env\Scripts\python.exe" (
    echo ❌ Python environment not found!
    echo Please ensure f:\DrumTracKAI_v1.1.11\drumtrackai_env exists
    pause
    exit /b 1
)

:: Set environment variables for DCSM
set USE_RUST=1
set AUDIO_CORE_MODE=auto
set AUDIO_CORE_BIN=%CD%\audio-core\target\release\audio-core.exe
set REACT_APP_API_BASE=http://localhost:8000

:: Build Rust audio-core if needed
if not exist "audio-core\target\release\audio-core.exe" (
    echo 🔧 Building Rust audio-core...
    cd audio-core
    cargo build --release
    if errorlevel 1 (
        echo ❌ Rust build failed!
        cd ..
        pause
        exit /b 1
    )
    cd ..
    echo ✅ Rust audio-core built successfully
)

:: Start DCSM Backend
echo 🚀 Starting DCSM Backend Server...
start "DCSM Backend" cmd /k "f:\DrumTracKAI_v1.1.11\drumtrackai_env\Scripts\python.exe dcsm_backend.py"

:: Wait for backend to initialize
echo ⏳ Waiting for backend to start...
timeout /t 5 /nobreak >nul

:: Start DCSM Frontend
echo 🌐 Starting DCSM Frontend...
cd frontend
if not exist "node_modules" (
    echo 📦 Installing frontend dependencies...
    npm install
)
start "DCSM Frontend" cmd /k "npm start"
cd ..

echo.
echo ✅ DrumTracKAI v1.1.16 DCSM Started Successfully!
echo ==========================================
echo 🎵 DCSM Studio: http://localhost:3000
echo 🔧 Backend API: http://localhost:8000
echo 📊 Benchmarks: http://localhost:3000/bench
echo 📄 Landing Page: file:///%CD%/landing_page.html
echo.
echo Press any key to open DCSM Studio...
pause >nul
start http://localhost:3000
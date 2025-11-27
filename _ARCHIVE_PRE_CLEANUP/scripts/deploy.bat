@echo off
echo 🚀 Deploying DrumTracKAI DCSM v1.1.16 Locally
echo ================================================

:: Set environment variables for production
set NODE_ENV=production
set REACT_APP_API_BASE=http://localhost:8000
set USE_RUST=1
set AUDIO_CORE_MODE=auto

:: Build Rust audio-core if not already built
echo Building Rust audio-core...
cd audio-core
if not exist "target\release\audio-core.exe" (
    cargo build --release
    if errorlevel 1 (
        echo ❌ Rust build failed
        pause
        exit /b 1
    )
)
cd ..

:: Set Rust binary path
set AUDIO_CORE_BIN=%CD%\audio-core\target\release\audio-core.exe

:: Build React frontend
echo Building React frontend...
cd web-frontend
call npm install
if errorlevel 1 (
    echo ❌ npm install failed
    pause
    exit /b 1
)

call npm run build
if errorlevel 1 (
    echo ❌ React build failed
    pause
    exit /b 1
)
cd ..

:: Start backend server
echo Starting backend server...
start "DrumTracKAI Backend" cmd /k "drumtrackai_env\Scripts\python.exe drumtrackai_api_server_clean.py"

:: Wait for backend to start
timeout /t 3 /nobreak >nul

:: Start frontend server (production build)
echo Starting frontend server...
cd web-frontend
start "DrumTracKAI Frontend" cmd /k "npx serve -s build -l 3000"

echo.
echo ✅ DCSM Deployment Complete!
echo ================================
echo 🌐 Frontend: http://localhost:3000
echo 🔧 Backend:  http://localhost:8000
echo 📊 Benchmarks: http://localhost:3000/bench
echo.
echo Features Available:
echo • Advanced Groove Presets (swing, velocity profiles)
echo • Multi-bar Fill Library (style-aware)
echo • Smart Sectionization (downbeat-aware)
echo • Type-1 Multi-track MIDI Export
echo • Performance Benchmarking Suite
echo • PyO3 Rust Integration
echo.
echo Press any key to open the application...
pause >nul
start http://localhost:3000

@echo off
echo 🔧 DrumTracKAI v1.1.16 DCSM Setup
echo =================================

:: Install Python dependencies
echo 📦 Installing Python dependencies...
pip install -r requirements.txt
if errorlevel 1 (
    echo ❌ Python dependencies installation failed!
    pause
    exit /b 1
)

:: Install frontend dependencies
echo 📦 Installing frontend dependencies...
cd frontend
npm install
if errorlevel 1 (
    echo ❌ Frontend dependencies installation failed!
    cd ..
    pause
    exit /b 1
)
cd ..

:: Build Rust audio-core
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

echo.
echo ✅ DrumTracKAI v1.1.16 DCSM Setup Complete!
echo ===========================================
echo.
echo Next steps:
echo 1. Run: start_dcsm.bat
echo 2. Access DCSM Studio at http://localhost:3000
echo.
pause

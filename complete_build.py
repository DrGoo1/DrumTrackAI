#!/usr/bin/env python3
"""
Complete the DrumTracKAI v1.1.16 Clean Build
"""

import os
import shutil
from pathlib import Path

def complete_build():
    """Complete the clean build by copying remaining components"""
    
    source_dir = Path("f:\\DrumTracKAI_v1.1.11")
    target_dir = Path("f:\\DrumTracKAI_v1.1.16_Clean")
    
    print("🔧 Completing DrumTracKAI v1.1.16 Clean Build")
    print("=" * 50)
    
    # Copy remaining essential components
    remaining_items = [
        ("web-frontend/src/components", "frontend/src/components"),
        ("web-frontend/src/services", "frontend/src/services"),
        ("web-frontend/src/audio", "frontend/src/audio"),
        ("web-frontend/src/rust", "frontend/src/rust"),
        ("web-frontend/src/pages", "frontend/src/pages"),
        ("web-frontend/src/index.tsx", "frontend/src/index.tsx"),
        ("web-frontend/public", "frontend/public"),
        ("admin/main.py", "admin/main.py"),
        ("admin/core", "admin/core"),
        ("admin/ui", "admin/ui"),
        ("LandingPage_v1.1.11_COMPLETE.html", "landing_page.html"),
        ("LandingPage_v1.1.11_COMPLETE.js", "landing_page.js"),
    ]
    
    for source_item, target_item in remaining_items:
        source_path = source_dir / source_item
        target_path = target_dir / target_item
        
        if source_path.exists():
            try:
                if source_path.is_dir():
                    print(f"📁 Copying: {source_item}")
                    if target_path.exists():
                        shutil.rmtree(target_path)
                    shutil.copytree(source_path, target_path, ignore=shutil.ignore_patterns(
                        '*.pyc', '__pycache__', 'node_modules', '.git'
                    ))
                else:
                    print(f"📄 Copying: {source_item}")
                    target_path.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(source_path, target_path)
            except Exception as e:
                print(f"⚠️  Failed to copy {source_item}: {e}")
        else:
            print(f"⚠️  Not found: {source_item}")
    
    # Create clean DCSM startup script
    startup_content = """@echo off
echo 🎯 DrumTracKAI v1.1.16 DCSM - Clean Build
echo ==========================================

:: Check Python environment
if not exist "drumtrackai_env\\Scripts\\python.exe" (
    echo ❌ Python environment not found!
    echo Please run: pip install -r requirements.txt
    pause
    exit /b 1
)

:: Set environment variables for DCSM
set USE_RUST=1
set AUDIO_CORE_MODE=auto
set AUDIO_CORE_BIN=%CD%\\audio-core\\target\\release\\audio-core.exe
set REACT_APP_API_BASE=http://localhost:8000

:: Build Rust audio-core if needed
if not exist "audio-core\\target\\release\\audio-core.exe" (
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
start "DCSM Backend" cmd /k "drumtrackai_env\\Scripts\\python.exe dcsm_backend.py"

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
"""
    
    with open(target_dir / "start_dcsm.bat", 'w') as f:
        f.write(startup_content)
    
    # Create setup script
    setup_content = """@echo off
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
"""
    
    with open(target_dir / "setup.bat", 'w') as f:
        f.write(setup_content)
    
    print("\n✅ Clean build completion finished!")
    print(f"📁 Location: {target_dir}")
    
    return True

if __name__ == "__main__":
    complete_build()

@echo off
REM DrumTracKAI v1.1.16 Complete Deployment Script
REM Handles Docker and Native deployment with full environment setup

setlocal enabledelayedexpansion

echo ====================================
echo DrumTracKAI v1.1.16 Complete Deploy
echo ====================================
echo.

cd /d "%~dp0"

REM Check if all components are present
echo Checking migration status...
if not exist "admin" (
    echo [ERROR] Admin module missing - run F:\MIGRATE_V1116.bat first
    pause
    exit /b 1
)

if not exist "frontend" (
    echo [ERROR] Frontend missing - run F:\MIGRATE_V1116.bat first
    pause
    exit /b 1
)

if not exist "tracktion-hybrid" (
    echo [ERROR] Tracktion Hybrid missing - run F:\MIGRATE_V1116.bat first
    pause
    exit /b 1
)

echo [OK] All components present
echo.

REM Display deployment options
echo ====================================
echo Deployment Options:
echo ====================================
echo.
echo 1. Docker Deployment (Recommended)
echo    - Complete containerization
echo    - Automatic dependency management
echo    - Production-ready isolation
echo.
echo 2. Native Windows Deployment
echo    - Direct host execution
echo    - Manual dependency setup
echo    - Development-friendly
echo.
echo 3. Build Rust FFI Only
echo    - Just build audio_core_ffi.dll
echo    - For manual integration
echo.
echo 4. Setup Python Environment Only
echo    - Create virtual environment
echo    - Install dependencies
echo.
echo 5. Install Frontend Dependencies Only
echo    - npm install in frontend/
echo.

set /p DEPLOY_CHOICE="Select deployment option (1-5): "

if "%DEPLOY_CHOICE%"=="1" goto docker_deploy
if "%DEPLOY_CHOICE%"=="2" goto native_deploy
if "%DEPLOY_CHOICE%"=="3" goto build_rust
if "%DEPLOY_CHOICE%"=="4" goto setup_python
if "%DEPLOY_CHOICE%"=="5" goto setup_frontend

echo Invalid choice. Exiting.
pause
exit /b 1

REM ========================================
REM Docker Deployment
REM ========================================
:docker_deploy
echo.
echo ====================================
echo Docker Deployment
echo ====================================
echo.

REM Check if Docker is available
docker --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Docker is not installed or not in PATH
    echo.
    echo Please install Docker Desktop from:
    echo https://www.docker.com/products/docker-desktop
    echo.
    pause
    exit /b 1
)

echo [OK] Docker is available
echo.

echo Checking Docker daemon...
docker ps >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Docker daemon is not running
    echo.
    echo Please start Docker Desktop and try again.
    echo.
    pause
    exit /b 1
)

echo [OK] Docker daemon is running
echo.

echo Building and deploying all services...
echo This may take 10-15 minutes for the first build.
echo.

docker-compose down -v 2>nul
docker-compose up -d --build

if errorlevel 1 (
    echo.
    echo [ERROR] Docker deployment failed
    echo.
    echo Checking logs...
    docker-compose logs --tail=50
    pause
    exit /b 1
)

echo.
echo ====================================
echo Docker Deployment Complete!
echo ====================================
echo.
echo Services running:
docker-compose ps
echo.
echo Access Points:
echo   Frontend:  http://localhost:3000
echo   Backend:   http://localhost:8000
echo   Tracktion: http://localhost:8080
echo.
echo View logs: docker-compose logs -f
echo Stop:      docker-compose down
echo.
pause
exit /b 0

REM ========================================
REM Native Windows Deployment
REM ========================================
:native_deploy
echo.
echo ====================================
echo Native Windows Deployment
echo ====================================
echo.

REM Step 1: Build Rust FFI
echo Step 1/4: Building Rust FFI Library...
call :build_rust_ffi
if errorlevel 1 (
    echo [ERROR] Rust FFI build failed
    pause
    exit /b 1
)

REM Step 2: Setup Python Environment
echo.
echo Step 2/4: Setting up Python Environment...
call :setup_python_env
if errorlevel 1 (
    echo [ERROR] Python environment setup failed
    pause
    exit /b 1
)

REM Step 3: Install Frontend Dependencies
echo.
echo Step 3/4: Installing Frontend Dependencies...
call :setup_frontend_deps
if errorlevel 1 (
    echo [ERROR] Frontend dependency installation failed
    pause
    exit /b 1
)

REM Step 4: Start Services
echo.
echo Step 4/4: Starting Services...
echo.

echo Starting Backend Server...
start "DrumTracKAI Backend" cmd /k "drumtrackai_env\Scripts\activate && set USE_TRACKTION_FFI=1 && set TRACKTION_FFI_LIB=%CD%\tracktion-hybrid\rust\audio-core-ffi\target\release\audio_core_ffi.dll && python dcsm_backend.py"

timeout /t 5 /nobreak >nul

echo Starting Frontend Server...
start "DrumTracKAI Frontend" cmd /k "cd frontend && npm start"

echo.
echo ====================================
echo Native Deployment Started!
echo ====================================
echo.
echo Backend:  http://localhost:8000 (starting...)
echo Frontend: http://localhost:3000 (starting...)
echo.
echo Admin App: python admin/main.py
echo.
echo Check the opened windows for logs.
echo.
pause
exit /b 0

REM ========================================
REM Build Rust FFI Only
REM ========================================
:build_rust
echo.
echo ====================================
echo Building Rust FFI Library
echo ====================================
echo.
call :build_rust_ffi
pause
exit /b 0

REM ========================================
REM Setup Python Only
REM ========================================
:setup_python
echo.
echo ====================================
echo Setting Up Python Environment
echo ====================================
echo.
call :setup_python_env
pause
exit /b 0

REM ========================================
REM Setup Frontend Only
REM ========================================
:setup_frontend
echo.
echo ====================================
echo Installing Frontend Dependencies
echo ====================================
echo.
call :setup_frontend_deps
pause
exit /b 0

REM ========================================
REM Helper Functions
REM ========================================

:build_rust_ffi
echo Checking Rust installation...
cargo --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Rust is not installed
    echo.
    echo Please install Rust from: https://rustup.rs/
    echo Or run: rustup-init.exe
    exit /b 1
)

echo [OK] Rust is installed
echo.

if exist "tracktion-hybrid\rust\audio-core-ffi\target\release\audio_core_ffi.dll" (
    echo [INFO] FFI library already exists
    set /p REBUILD="Rebuild FFI library? (Y/N): "
    if /i not "!REBUILD!"=="Y" (
        echo Skipping build
        exit /b 0
    )
)

echo Building FFI library (this may take 5-10 minutes)...
cd tracktion-hybrid\rust\audio-core-ffi
cargo build --release

if errorlevel 1 (
    echo [ERROR] Rust build failed
    cd ..\..\..
    exit /b 1
)

cd ..\..\..
echo [OK] FFI library built successfully
dir /b tracktion-hybrid\rust\audio-core-ffi\target\release\audio_core_ffi.dll
exit /b 0

:setup_python_env
echo Checking Python installation...
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python is not installed or not in PATH
    exit /b 1
)

python --version
echo.

if exist "drumtrackai_env" (
    echo [INFO] Virtual environment already exists
    set /p RECREATE="Recreate environment? (Y/N): "
    if /i "!RECREATE!"=="Y" (
        echo Removing old environment...
        rmdir /s /q drumtrackai_env
    ) else (
        echo Using existing environment
        exit /b 0
    )
)

echo Creating virtual environment...
python -m venv drumtrackai_env

if errorlevel 1 (
    echo [ERROR] Failed to create virtual environment
    exit /b 1
)

echo [OK] Virtual environment created
echo.

echo Installing dependencies...
call drumtrackai_env\Scripts\activate.bat
pip install --upgrade pip
pip install -r requirements.txt

if errorlevel 1 (
    echo [ERROR] Failed to install dependencies
    exit /b 1
)

echo [OK] Python environment ready
exit /b 0

:setup_frontend_deps
echo Checking Node.js installation...
node --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Node.js is not installed or not in PATH
    exit /b 1
)

node --version
npm --version
echo.

if exist "frontend\node_modules" (
    echo [INFO] node_modules already exists
    set /p REINSTALL="Reinstall dependencies? (Y/N): "
    if /i not "!REINSTALL!"=="Y" (
        echo Using existing dependencies
        exit /b 0
    )
)

echo Installing frontend dependencies...
cd frontend
call npm install

if errorlevel 1 (
    echo [ERROR] Failed to install frontend dependencies
    cd ..
    exit /b 1
)

cd ..
echo [OK] Frontend dependencies installed
exit /b 0

@echo off
echo ========================================
echo DrumTracKAI v1.1.16 Simple Deployment
echo ========================================
echo.

REM Kill any existing processes on our ports
echo Stopping any existing services...
for /f "tokens=5" %%a in ('netstat -aon ^| findstr :8000') do taskkill /f /pid %%a 2>nul
for /f "tokens=5" %%a in ('netstat -aon ^| findstr :3000') do taskkill /f /pid %%a 2>nul
for /f "tokens=5" %%a in ('netstat -aon ^| findstr :8001') do taskkill /f /pid %%a 2>nul

echo.
echo Starting DrumTracKAI v1.1.16 services...

REM Set environment variables
set PYTHONPATH=%CD%
set USE_RUST=0
set HOST=0.0.0.0
set API_PORT=8000

REM Start backend server
echo [1/3] Starting Backend Server (port 8000)...
start "DrumTracKAI Backend" cmd /k "f:\DrumTracKAI_v1.1.11\drumtrackai_env\Scripts\python.exe dcsm_backend.py"

REM Wait for backend to start
timeout /t 5 /nobreak >nul

REM Start frontend build server
echo [2/3] Starting Frontend Build Server (port 3000)...
cd frontend
if not exist node_modules (
    echo Installing frontend dependencies...
    call npm install
)
start "DrumTracKAI Frontend" cmd /k "npm start"
cd ..

REM Start static file server as backup
echo [3/3] Starting Static File Server (port 8001)...
start "DrumTracKAI Static" cmd /k "f:\DrumTracKAI_v1.1.11\drumtrackai_env\Scripts\python.exe -m http.server 8001"

echo.
echo Waiting for services to initialize...
timeout /t 10 /nobreak >nul

echo.
echo ========================================
echo DrumTracKAI v1.1.16 Deployment Complete!
echo ========================================
echo.
echo Access Points:
echo - Backend API:     http://localhost:8000
echo - Frontend App:    http://localhost:3000  
echo - Static Files:    http://localhost:8001
echo - Landing Page:    http://localhost:8001/landing_page.html
echo.

REM Test backend connectivity
echo Testing backend connectivity...
curl -s http://localhost:8000/healthz >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    echo ✓ Backend server is responding
) else (
    echo ✗ Backend server not responding - check backend window
)

REM Test frontend connectivity  
curl -s http://localhost:3000 >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    echo ✓ Frontend server is responding
) else (
    echo ✗ Frontend server not responding - using static fallback
)

echo.
echo Opening DCSM Studio in browser...
timeout /t 2 /nobreak >nul
start "" "http://localhost:3000"

echo.
echo All services started. Keep this window open.
echo To stop services, close the individual service windows.
echo.
pause

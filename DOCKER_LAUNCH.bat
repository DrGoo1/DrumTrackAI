@echo off
echo ================================================
echo DrumTracKAI v1.1.16 Hybrid - Docker Launch
echo ================================================
echo.

:: Add Docker to PATH
set PATH=%PATH%;C:\Program Files\Docker\Docker\resources\bin

:: Kill any existing containers
echo Stopping existing containers...
docker-compose down -v 2>nul

:: Build and start containers
echo Building and starting Docker containers...
docker-compose up -d --build

:: Wait for containers to start
echo Waiting for containers to initialize...
timeout /t 30 /nobreak

:: Show container status
echo.
echo Container Status:
docker ps

echo.
echo ================================================
echo Services should be available at:
echo ================================================
echo Backend:  http://localhost:8000
echo Frontend: http://localhost:3000
echo Tracktion: http://localhost:8080
echo.
echo Opening frontend in browser...
timeout /t 5 /nobreak
start http://localhost:3000

@echo off
echo ========================================
echo Stopping All DrumTracKAI Services
echo ========================================
echo.

set NO_PAUSE=0
if /I "%~1"=="/NOPAUSE" set NO_PAUSE=1

set SCRIPT_DIR=%~dp0scripts

if not exist "%SCRIPT_DIR%\free_port.ps1" (
    echo ERROR: scripts\free_port.ps1 not found at %SCRIPT_DIR%\free_port.ps1
    echo Please run from the DrumTracKAI project root.
    echo.
    pause
    exit /b 1
)

echo Freeing Backend port 8000...
powershell -NoProfile -ExecutionPolicy Bypass -File "%SCRIPT_DIR%\free_port.ps1" -Port 8000 -Force

echo.
echo Freeing Frontend port 3000...
powershell -NoProfile -ExecutionPolicy Bypass -File "%SCRIPT_DIR%\free_port.ps1" -Port 3000 -Force

echo.
echo Freeing LLM port 9000...
powershell -NoProfile -ExecutionPolicy Bypass -File "%SCRIPT_DIR%\free_port.ps1" -Port 9000 -Force

echo.
echo Freeing Landing port 3004 (if used)...
powershell -NoProfile -ExecutionPolicy Bypass -File "%SCRIPT_DIR%\free_port.ps1" -Port 3004 -Force

echo.
echo ========================================
echo All services stopped!
echo ========================================
echo.
if %NO_PAUSE%==0 pause

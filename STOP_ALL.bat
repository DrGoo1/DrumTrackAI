@echo off
echo ========================================
echo Stopping All DrumTracKAI Services
echo ========================================
echo.

echo Stopping Node processes (Frontend)...
taskkill /F /IM node.exe 2>nul
if %errorlevel%==0 (
    echo   Node processes stopped
) else (
    echo   No Node processes running
)

echo.
echo Stopping Python processes (Backend)...
taskkill /F /IM python.exe 2>nul
if %errorlevel%==0 (
    echo   Python processes stopped
) else (
    echo   No Python processes running
)

echo.
echo ========================================
echo All services stopped!
echo ========================================
echo.
pause

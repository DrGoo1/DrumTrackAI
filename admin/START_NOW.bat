@echo off
REM Quick Start - Foundation Learning
REM Launches the foundation learning system with GUI monitoring

echo ================================================================
echo DrumTracKAI - Foundation Learning Quick Start
echo ================================================================
echo.
echo This will start autonomous YouTube foundation learning:
echo   - 50+ drumming techniques
echo   - ~110 educational videos
echo   - Beginner, Intermediate, Advanced levels
echo   - Estimated time: 2-3 hours
echo.
echo The system will search and download automatically!
echo.
pause

echo.
echo Launching Foundation Learning Monitor...
echo.

cd /d "%~dp0"
START_FOUNDATION_LEARNING.bat

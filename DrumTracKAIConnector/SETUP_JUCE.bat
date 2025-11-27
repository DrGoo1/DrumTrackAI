@echo off
REM Download and setup JUCE Framework

echo ================================================================================
echo DrumTracKAI Connector - JUCE Setup
echo ================================================================================

cd /d "%~dp0\.."

REM Check if deps folder exists
if not exist "deps" mkdir deps
cd deps

REM Check if JUCE already exists
if exist "JUCE\CMakeLists.txt" (
    echo JUCE already installed!
    echo Location: %CD%\JUCE
    echo.
    pause
    exit /b 0
)

echo Checking for git...
git --version >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Git not found!
    echo.
    echo Please install Git from: https://git-scm.com/download/win
    echo Or manually download JUCE from: https://github.com/juce-framework/JUCE
    pause
    exit /b 1
)

echo.
echo Downloading JUCE Framework 7.0.9...
echo This will take a few minutes...
echo.

git clone --depth=1 --branch=7.0.9 https://github.com/juce-framework/JUCE.git

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo ERROR: Failed to download JUCE!
    echo.
    echo You can manually download from:
    echo https://github.com/juce-framework/JUCE/releases/tag/7.0.9
    echo.
    echo Extract to: %CD%\JUCE
    pause
    exit /b 1
)

echo.
echo ================================================================================
echo JUCE SETUP COMPLETE!
echo ================================================================================
echo.
echo JUCE installed to: %CD%\JUCE
echo.
echo Next step: Run BUILD_PLUGIN.bat
echo.

pause

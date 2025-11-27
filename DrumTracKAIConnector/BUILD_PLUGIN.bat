@echo off
REM Build DrumTracKAI Connector Plugin (Windows VST3)

echo ================================================================================
echo Building DrumTracKAI Connector Plugin
echo ================================================================================

cd /d "%~dp0"

REM Check for JUCE
if not exist "..\deps\JUCE\CMakeLists.txt" (
    echo ERROR: JUCE not found!
    echo Please run SETUP_JUCE.bat first
    exit /b 1
)

REM Create build directory
if not exist "build" mkdir build
cd build

echo.
echo Configuring CMake...
cmake .. -G "Visual Studio 17 2022" -A x64

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo ERROR: CMake configuration failed!
    echo.
    echo Make sure you have Visual Studio 2022 installed
    echo Or try: cmake .. -G "Visual Studio 16 2019" -A x64
    pause
    exit /b 1
)

echo.
echo Building plugin...
cmake --build . --config Release

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo ERROR: Build failed!
    pause
    exit /b 1
)

echo.
echo ================================================================================
echo BUILD COMPLETE!
echo ================================================================================
echo.
echo Plugin installed to:
echo   VST3: C:\Program Files\Common Files\VST3\DrumTracKAI Connector.vst3
echo   Standalone: build\DrumTracKAIConnector_artefacts\Release\Standalone\
echo.
echo Next steps:
echo   1. Start DrumTracKAI backend: python ..\drumtrackai_api_server_clean.py
echo   2. Open your DAW and scan for new plugins
echo   3. Load "DrumTracKAI Connector" as a MIDI effect
echo.

pause

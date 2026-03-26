@echo off
REM ========================================================================
REM Jamstix/Reaper Training System - Activation Script
REM ========================================================================

echo.
echo ╔════════════════════════════════════════════════════════════════════╗
echo ║       Jamstix/Reaper Training System - Activation                  ║
echo ╚════════════════════════════════════════════════════════════════════╝
echo.

REM Check if REAPER is installed
echo [1/5] Checking for REAPER installation...
if exist "C:\Program Files\REAPER\reaper.exe" (
    echo ✅ REAPER found at: C:\Program Files\REAPER\reaper.exe
) else if exist "C:\Program Files (x86)\REAPER\reaper.exe" (
    echo ✅ REAPER found at: C:\Program Files (x86)\REAPER\reaper.exe
) else (
    echo ⚠️  REAPER not found in standard locations
    echo    Please install REAPER from: https://www.reaper.fm/download.php
    echo.
    pause
    exit /b 1
)
echo.

REM Check for template directory
echo [2/5] Checking template directory...
if not exist "C:\Users\dagol\ReaperTemplates" (
    echo Creating template directory...
    mkdir "C:\Users\dagol\ReaperTemplates"
    echo ✅ Created: C:\Users\dagol\ReaperTemplates
) else (
    echo ✅ Template directory exists
)
echo.

REM Check for output directory
echo [3/5] Checking output directory...
if not exist "F:\DrumTrackAI_Jamstix_Dataset" (
    echo Creating output directory...
    mkdir "F:\DrumTrackAI_Jamstix_Dataset"
    echo ✅ Created: F:\DrumTrackAI_Jamstix_Dataset
) else (
    echo ✅ Output directory exists
)
echo.

REM Check Python dependencies
echo [4/5] Checking Python dependencies...
python -c "import mido" 2>nul
if %errorlevel% equ 0 (
    echo ✅ mido library installed
) else (
    echo Installing mido library...
    pip install mido
    if %errorlevel% equ 0 (
        echo ✅ mido installed successfully
    ) else (
        echo ❌ Failed to install mido
        pause
        exit /b 1
    )
)
echo.

REM Check for Reaper template
echo [5/5] Checking for Jamstix template...
if exist "C:\Users\dagol\ReaperTemplates\JamstixTemplate.rpp" (
    echo ✅ Template found: JamstixTemplate.rpp
    echo.
    echo ╔════════════════════════════════════════════════════════════════╗
    echo ║                 ✅ SYSTEM READY!                               ║
    echo ╚════════════════════════════════════════════════════════════════╝
    echo.
    echo You can now:
    echo   1. Open REAPER
    echo   2. Load template: File → Project Templates → JamstixTemplate
    echo   3. Run script: Actions → Load → JamstixBatchGenerator_COMPLETE.lua
    echo.
) else (
    echo ⚠️  Template not found
    echo.
    echo ╔════════════════════════════════════════════════════════════════╗
    echo ║         TEMPLATE SETUP REQUIRED                                ║
    echo ╚════════════════════════════════════════════════════════════════╝
    echo.
    echo Next steps:
    echo   1. Open REAPER
    echo   2. Create new project
    echo   3. Add Track 1: "Jamstix Drums" with Jamstix plugin
    echo   4. Add Track 2: "MIDI Capture" (record from Track 1)
    echo   5. Save as: C:\Users\dagol\ReaperTemplates\JamstixTemplate.rpp
    echo.
    echo Then run this script again.
    echo.
    echo Opening setup guide...
    start "" "%~dp0JAMSTIX_COMPLETE_SETUP.md"
)

echo.
echo ════════════════════════════════════════════════════════════════════
echo Directories:
echo   Template: C:\Users\dagol\ReaperTemplates\
echo   Output:   F:\DrumTrackAI_Jamstix_Dataset\
echo   Script:   %~dp0phase1_data_generation\reaper_automation\
echo ════════════════════════════════════════════════════════════════════
echo.

pause

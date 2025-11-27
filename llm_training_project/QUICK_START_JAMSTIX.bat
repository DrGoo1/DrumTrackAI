@echo off
REM Quick launcher for Jamstix/Reaper system

echo.
echo ╔════════════════════════════════════════════════════════════════╗
echo ║          Jamstix/Reaper Training System - Quick Start          ║
echo ╚════════════════════════════════════════════════════════════════╝
echo.
echo What would you like to do?
echo.
echo [1] Check system status (what do I need?)
echo [2] Open setup guide (how to create template)
echo [3] Open usage guide (how to generate data)
echo [4] Convert existing MIDI to training data
echo [5] Test Jamstix brain integration
echo.
set /p choice="Enter choice (1-5): "

if "%choice%"=="1" (
    echo.
    echo Running system check...
    python activate_jamstix_system.py
    pause
    exit
)

if "%choice%"=="2" (
    echo.
    echo Opening setup guide...
    start "" "HOW_TO_USE_JAMSTIX_REAPER.md"
    echo See: STEP 1 - Create the REAPER Template
    pause
    exit
)

if "%choice%"=="3" (
    echo.
    echo Opening usage guide...
    start "" "HOW_TO_USE_JAMSTIX_REAPER.md"
    echo See: STEP 2 - Run the Automation Script
    pause
    exit
)

if "%choice%"=="4" (
    echo.
    echo Converting Jamstix MIDI to training data...
    cd phase1_data_generation\corpus_builders
    python jamstix_dataset_builder.py
    pause
    exit
)

if "%choice%"=="5" (
    echo.
    echo Testing Jamstix brain integration...
    cd ..\..
    python test_jamstix_backend_integration.py
    pause
    exit
)

echo Invalid choice!
pause

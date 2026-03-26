@echo off
echo ========================================
echo REAPER ReaScript Diagnostic Tool
echo ========================================
echo.
echo This tool will help diagnose and enable ReaScript in REAPER.
echo.
echo STEP 1: Check REAPER Installation
echo ================================
echo Looking for REAPER installation...

if exist "C:\Program Files\REAPER\reaper.exe" (
    echo ✓ Found REAPER at: C:\Program Files\REAPER\
    set REAPER_PATH=C:\Program Files\REAPER
) else if exist "C:\Program Files (x86)\REAPER\reaper.exe" (
    echo ✓ Found REAPER at: C:\Program Files (x86)\REAPER\
    set REAPER_PATH=C:\Program Files (x86)\REAPER
) else (
    echo ⚠ REAPER not found in standard locations
    echo Please locate your REAPER installation manually
    set REAPER_PATH=UNKNOWN
)

echo.
echo STEP 2: Check ReaScript Files
echo =============================
if "%REAPER_PATH%" NEQ "UNKNOWN" (
    if exist "%REAPER_PATH%\Scripts" (
        echo ✓ Scripts folder exists
        dir "%REAPER_PATH%\Scripts" /b | findstr /i "lua" >nul
        if %errorlevel% equ 0 (
            echo ✓ Lua scripts found in Scripts folder
        ) else (
            echo ⚠ No Lua scripts found in Scripts folder
        )
    ) else (
        echo ⚠ Scripts folder not found
    )
)

echo.
echo STEP 3: Check User Scripts Folder
echo =================================
set USER_SCRIPTS=%APPDATA%\REAPER\Scripts
if exist "%USER_SCRIPTS%" (
    echo ✓ User Scripts folder exists: %USER_SCRIPTS%
) else (
    echo Creating user Scripts folder...
    mkdir "%USER_SCRIPTS%" 2>nul
    if exist "%USER_SCRIPTS%" (
        echo ✓ Created user Scripts folder: %USER_SCRIPTS%
    ) else (
        echo ⚠ Could not create user Scripts folder
    )
)

echo.
echo STEP 4: Copy Our Test Script
echo ============================
if exist "%USER_SCRIPTS%" (
    copy "D:\DrumTracKAI_v1.1.7\admin\batch_test_3files.lua" "%USER_SCRIPTS%\" >nul 2>&1
    if exist "%USER_SCRIPTS%\batch_test_3files.lua" (
        echo ✓ Copied test script to user Scripts folder
        echo   Location: %USER_SCRIPTS%\batch_test_3files.lua
    ) else (
        echo ⚠ Could not copy test script
    )
)

echo.
echo STEP 5: Instructions
echo ====================
echo Now try these methods in REAPER:
echo.
echo METHOD A: Actions Window
echo 1. Open Actions window (? key)
echo 2. Search for "batch_test_3files"
echo 3. If found, double-click to run
echo.
echo METHOD B: Browse for Scripts
echo 1. In Actions window, look for "Browse..." or "Load..." button
echo 2. Navigate to: %USER_SCRIPTS%
echo 3. Select: batch_test_3files.lua
echo.
echo METHOD C: Check Preferences
echo 1. Options → Preferences
echo 2. Look for "ReaScript" or "Scripting"
echo 3. Enable if disabled
echo.
echo METHOD D: Manual Menu Search
echo Look for these menus in REAPER:
echo - Extensions → ReaScript
echo - Tools → Scripts
echo - Actions → Load ReaScript
echo - Scripts (top-level menu)
echo.
pause

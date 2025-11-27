@echo off
REM ============================================================================
REM Drum Builder v2.0 - Frontend Testing Script
REM ============================================================================

echo.
echo ========================================
echo   Drum Builder v2.0 - Frontend Tests
echo ========================================
echo.

cd web-frontend

REM Check if node_modules exists
if not exist "node_modules" (
    echo [1/4] node_modules not found, installing dependencies...
    call npm install
    if %ERRORLEVEL% NEQ 0 (
        echo [ERROR] npm install failed
        pause
        exit /b 1
    )
    echo [OK] Dependencies installed
) else (
    echo [1/4] Dependencies already installed
)

echo.
echo [2/4] Checking TypeScript compilation...
call npm run build > build_output.txt 2>&1
if %ERRORLEVEL% EQU 0 (
    echo [OK] TypeScript compilation successful
) else (
    echo [ERROR] TypeScript compilation failed
    echo.
    echo Showing errors:
    type build_output.txt
    echo.
    echo Full output saved to: web-frontend\build_output.txt
    pause
    exit /b 1
)

echo.
echo [3/4] Checking for new v2.0 files...
set FILES_OK=1

if exist "src\types\drumTrack.ts" (
    echo [OK] drumTrack.ts exists
) else (
    echo [ERROR] drumTrack.ts missing
    set FILES_OK=0
)

if exist "src\utils\drumTrackUtils.ts" (
    echo [OK] drumTrackUtils.ts exists
) else (
    echo [ERROR] drumTrackUtils.ts missing
    set FILES_OK=0
)

if exist "src\utils\rehumanize.ts" (
    echo [OK] rehumanize.ts exists
) else (
    echo [ERROR] rehumanize.ts missing
    set FILES_OK=0
)

if exist "src\components\DrumBuilderPanelV2.tsx" (
    echo [OK] DrumBuilderPanelV2.tsx exists
) else (
    echo [ERROR] DrumBuilderPanelV2.tsx missing
    set FILES_OK=0
)

if exist "src\components\SectionTimelineStrip.tsx" (
    echo [OK] SectionTimelineStrip.tsx exists
) else (
    echo [ERROR] SectionTimelineStrip.tsx missing
    set FILES_OK=0
)

if exist "src\components\RehumanizePanel.tsx" (
    echo [OK] RehumanizePanel.tsx exists
) else (
    echo [ERROR] RehumanizePanel.tsx missing
    set FILES_OK=0
)

if %FILES_OK% EQU 0 (
    echo.
    echo [ERROR] Some v2.0 files are missing!
    pause
    exit /b 1
)

echo.
echo [4/4] Checking file sizes...
for %%F in (
    "src\types\drumTrack.ts"
    "src\utils\drumTrackUtils.ts"
    "src\utils\rehumanize.ts"
    "src\components\DrumBuilderPanelV2.tsx"
    "src\components\SectionTimelineStrip.tsx"
    "src\components\RehumanizePanel.tsx"
) do (
    if exist %%F (
        for %%A in (%%F) do echo   %%~nxA: %%~zA bytes
    )
)

echo.
echo ========================================
echo   Frontend Tests Complete!
echo ========================================
echo.
echo Next steps:
echo   1. Start dev server: npm start
echo   2. Open http://localhost:3000
echo   3. Test components manually
echo.

cd ..
pause

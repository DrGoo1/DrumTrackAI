@echo off
REM ============================================================================
REM Drum Builder v2.0 - Quick Start Testing
REM ============================================================================

echo.
echo ╔════════════════════════════════════════════════════════════════╗
echo ║                                                                ║
echo ║         🥁 Drum Builder v2.0 - Testing Quick Start 🥁         ║
echo ║                                                                ║
echo ╚════════════════════════════════════════════════════════════════╝
echo.

REM Check if we're in the right directory
if not exist "dcsm_backend.py" (
    echo [ERROR] Not in the correct directory!
    echo Please run this from f:\DrumTracKAI_v1.1.16_Clean\
    pause
    exit /b 1
)

echo ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
echo  Step 1: Verify File Structure
echo ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
echo.

set FILES_OK=1

echo Checking backend files...
if exist "backend\drum_generation\drum_generation_config.py" (
    echo   [✓] drum_generation_config.py
) else (
    echo   [✗] drum_generation_config.py MISSING
    set FILES_OK=0
)

if exist "backend\drum_generation\llm_performance_spec.py" (
    echo   [✓] llm_performance_spec.py
) else (
    echo   [✗] llm_performance_spec.py MISSING
    set FILES_OK=0
)

if exist "backend\dcsmpiano\drumtrack_schema.py" (
    echo   [✓] drumtrack_schema.py
) else (
    echo   [✗] drumtrack_schema.py MISSING
    set FILES_OK=0
)

if exist "drum_generation_api.py" (
    echo   [✓] drum_generation_api.py
) else (
    echo   [✗] drum_generation_api.py MISSING
    set FILES_OK=0
)

echo.
echo Checking frontend files...
if exist "frontend\src\types\drumTrack.ts" (
    echo   [✓] types\drumTrack.ts
) else (
    echo   [✗] types\drumTrack.ts MISSING
    set FILES_OK=0
)

if exist "frontend\src\utils\drumTrackUtils.ts" (
    echo   [✓] utils\drumTrackUtils.ts
) else (
    echo   [✗] utils\drumTrackUtils.ts MISSING
    set FILES_OK=0
)

if exist "frontend\src\utils\rehumanize.ts" (
    echo   [✓] utils\rehumanize.ts
) else (
    echo   [✗] utils\rehumanize.ts MISSING
    set FILES_OK=0
)

if exist "frontend\src\components\DrumBuilderPanelV2.tsx" (
    echo   [✓] components\DrumBuilderPanelV2.tsx
) else (
    echo   [✗] components\DrumBuilderPanelV2.tsx MISSING
    set FILES_OK=0
)

if exist "frontend\src\components\SectionTimelineStrip.tsx" (
    echo   [✓] components\SectionTimelineStrip.tsx
) else (
    echo   [✗] components\SectionTimelineStrip.tsx MISSING
    set FILES_OK=0
)

if exist "frontend\src\components\RehumanizePanel.tsx" (
    echo   [✓] components\RehumanizePanel.tsx
) else (
    echo   [✗] components\RehumanizePanel.tsx MISSING
    set FILES_OK=0
)

if %FILES_OK% EQU 0 (
    echo.
    echo [ERROR] Some required files are missing!
    echo Please ensure all v2.0 files have been created.
    pause
    exit /b 1
)

echo.
echo [✓] All required files present!

echo.
echo ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
echo  Step 2: Check Python Environment
echo ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
echo.

REM Check for v1.1.16 environment
if exist "drumtrackai_v1116_env" (
    echo [✓] Found v1.1.16 environment
    set PYTHON_ENV=drumtrackai_v1116_env\Scripts\python.exe
) else if exist "..\DrumTracKAI_v1.1.11\drumtrackai_env" (
    echo [✓] Found v1.1.11 environment (using shared)
    set PYTHON_ENV=..\DrumTracKAI_v1.1.11\drumtrackai_env\Scripts\python.exe
) else (
    echo [⚠] No Python environment found
    echo You'll need to set up a virtual environment first.
    set PYTHON_ENV=python
)

echo Python: %PYTHON_ENV%
echo.

echo ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
echo  Step 3: Testing Options
echo ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
echo.
echo What would you like to test?
echo.
echo   [1] Backend API Tests (automated)
echo   [2] Frontend TypeScript Compilation
echo   [3] Start Backend Server
echo   [4] Start Frontend Dev Server
echo   [5] Full Manual Testing Guide
echo   [6] View Documentation
echo   [0] Exit
echo.

set /p CHOICE="Enter your choice (0-6): "

if "%CHOICE%"=="1" goto backend_test
if "%CHOICE%"=="2" goto frontend_test
if "%CHOICE%"=="3" goto start_backend
if "%CHOICE%"=="4" goto start_frontend
if "%CHOICE%"=="5" goto manual_guide
if "%CHOICE%"=="6" goto view_docs
if "%CHOICE%"=="0" goto end

echo Invalid choice!
pause
exit /b 1

:backend_test
echo.
echo ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
echo  Running Backend Tests
echo ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
echo.
call TEST_BACKEND.bat
goto end

:frontend_test
echo.
echo ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
echo  Testing Frontend TypeScript
echo ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
echo.
call TEST_FRONTEND.bat
goto end

:start_backend
echo.
echo ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
echo  Starting Backend Server
echo ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
echo.
echo Starting backend on port 8000...
echo.
echo Press Ctrl+C to stop the server
echo.
%PYTHON_ENV% dcsm_backend.py
goto end

:start_frontend
echo.
echo ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
echo  Starting Frontend Dev Server
echo ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
echo.
cd frontend
echo Installing dependencies (if needed)...
call npm install
echo.
echo Starting dev server on port 3000...
echo.
echo Press Ctrl+C to stop the server
echo.
call npm start
cd ..
goto end

:manual_guide
echo.
echo ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
echo  Opening Manual Testing Guide
echo ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
echo.
start MANUAL_TESTING_GUIDE.md
echo Guide opened in your default markdown viewer
pause
goto end

:view_docs
echo.
echo ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
echo  Available Documentation
echo ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
echo.
echo Main Documentation:
echo   - START_HERE_DRUM_BUILDER_V2.md
echo   - DRUM_BUILDER_V2_IMPLEMENTATION_COMPLETE.md
echo   - PHASES_3_4_5_COMPLETE.md
echo.
echo Testing:
echo   - TESTING_PLAN_V2.md
echo   - MANUAL_TESTING_GUIDE.md
echo.
echo Phase Documentation:
echo   - PHASE_1_COMPLETE_SUMMARY.md
echo   - PHASE_2_COMPLETE_API_INTEGRATION.md
echo.
echo Opening main documentation...
start START_HERE_DRUM_BUILDER_V2.md
pause
goto end

:end
echo.
echo ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
echo  Testing Tools Ready!
echo ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
echo.
echo Next Steps:
echo   1. Start backend: START_TESTING.bat → Option 3
echo   2. Start frontend: START_TESTING.bat → Option 4
echo   3. Run tests: TEST_BACKEND.bat
echo   4. Manual testing: MANUAL_TESTING_GUIDE.md
echo.
pause

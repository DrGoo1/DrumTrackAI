@echo off
REM Phase 1 Workflow Test Runner
REM Activates virtual environment and runs complete test suite

echo ===================================================================
echo   Phase 1: DCSM Studio Workflow Test
echo ===================================================================
echo.

REM Check if virtual environment exists
if not exist "drumtrackai_env\Scripts\activate.bat" (
    echo ERROR: Virtual environment not found!
    echo Please create it first: python -m venv drumtrackai_env
    echo Then install dependencies: pip install -r requirements.txt
    pause
    exit /b 1
)

REM Activate virtual environment
echo Activating virtual environment...
call drumtrackai_env\Scripts\activate.bat

REM Check if aiohttp is installed
python -c "import aiohttp" 2>nul
if errorlevel 1 (
    echo.
    echo ERROR: Required packages not installed!
    echo Installing dependencies...
    pip install aiohttp librosa numpy scipy soundfile
    echo.
)

REM Run test
echo.
echo Running Phase 1 tests...
echo.

if "%~1"=="" (
    echo Running basic test (no audio file)...
    python test_phase1_complete_workflow.py
) else (
    echo Running full test with audio file: %~1
    python test_phase1_complete_workflow.py "%~1"
)

echo.
echo ===================================================================
pause

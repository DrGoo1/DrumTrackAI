@echo off
REM Complete E-GMD Pipeline: Extract → Train
REM ==========================================
echo.
echo ================================================================
echo DrumTracKAI - Complete E-GMD Training Pipeline
echo ================================================================
echo.
echo This will:
echo   1. Extract all 91,074 E-GMD MIDI files (~90 min)
echo   2. Build training datasets
echo   3. Train style classifier model
echo   4. Train humanization model
echo.
echo Total time: ~2 hours
echo.
pause

cd /d "%~dp0"

python extract_and_train_pipeline.py

echo.
echo ================================================================
echo Pipeline Complete!
echo ================================================================
echo.
pause

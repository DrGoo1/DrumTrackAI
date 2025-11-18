@echo off
echo.
echo ================================================================================
echo  DRUMTRACKAI AI TRAINING - QUICK STATUS CHECK
echo ================================================================================
echo.

REM Check data preparation progress
echo [DATA PREPARATION]
if exist "E:\DrumTracKAI_Master\03_Training_Data\preprocessed\train_features.npy" (
    echo   Status: COMPLETE
    echo   Training data ready!
) else (
    echo   Status: IN PROGRESS
    echo   Processing 91,074 MIDI patterns...
    echo   Check terminal window for detailed progress
)

echo.
echo [MODEL TRAINING]
if exist "E:\DrumTracKAI_Master\04_Models\current\training_history.json" (
    echo   Status: TRAINING
    powershell -Command "Get-Content 'E:\DrumTracKAI_Master\04_Models\current\training_history.json' | ConvertFrom-Json | Select -ExpandProperty epochs | Select -Last 1 | ForEach-Object { Write-Host '   Current Epoch:' $_ }"
) else (
    echo   Status: WAITING
    echo   Will start automatically after data prep
)

echo.
echo [MODEL CHECKPOINTS]
if exist "E:\DrumTracKAI_Master\04_Models\current\groove_vae_best.pth" (
    echo   Best model: SAVED
    dir "E:\DrumTracKAI_Master\04_Models\current\*.pth" /B 2>nul | find /c ".pth" > temp_count.txt
    set /p CKPT_COUNT=<temp_count.txt
    del temp_count.txt
    echo   Total checkpoints: %CKPT_COUNT%
) else (
    echo   No checkpoints yet
)

echo.
echo ================================================================================
echo  MONITORING OPTIONS:
echo ================================================================================
echo   1. Terminal Monitor:  python monitor_training.py
echo   2. Quick Check:       check_progress.bat  (this file)
echo   3. Web Dashboard:     Open training_dashboard.html in browser
echo ================================================================================
echo.

pause

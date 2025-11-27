@echo off
REM DrumTracKAI Training System Setup
REM Installs all dependencies and tests the system

echo ========================================
echo DrumTracKAI Training System Setup
echo ========================================
echo.

REM Activate environment
echo [1/5] Activating Python environment...
call ..\DrumTracKAI_v1.1.11\drumtrackai_env\Scripts\activate.bat
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Could not activate environment
    echo Make sure DrumTracKAI_v1.1.11 environment exists
    pause
    exit /b 1
)

echo.
echo [2/5] Installing training dependencies...
echo This may take 5-10 minutes...
echo.

REM Install PyTorch (check if CUDA available)
python -c "import torch; print('PyTorch already installed:', torch.__version__)" 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo Installing PyTorch...
    pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
    if %ERRORLEVEL% NEQ 0 (
        echo WARNING: CUDA PyTorch failed, installing CPU version...
        pip install torch torchvision torchaudio
    )
) else (
    echo PyTorch already installed
)

echo.
echo [3/5] Installing other dependencies...
pip install scikit-learn
pip install librosa soundfile

echo.
echo [4/5] Testing training modules...
python admin\training\data_extraction.py
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Data extraction test failed
    pause
    exit /b 1
)

python admin\training\dataset_builder.py
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Dataset builder test failed
    pause
    exit /b 1
)

python admin\training\model_trainer.py
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Model trainer test failed
    pause
    exit /b 1
)

echo.
echo [5/5] Checking GPU availability...
python -c "import torch; print('CUDA Available:', torch.cuda.is_available()); print('Device:', torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'CPU')"

echo.
echo ========================================
echo Setup Complete!
echo ========================================
echo.
echo Next Steps:
echo 1. Run: python admin\main.py
echo 2. Go to "AI Training" tab
echo 3. Start extracting training data
echo 4. Train your first model!
echo.
echo Press any key to launch admin app...
pause >nul

python admin\main.py

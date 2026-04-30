@echo off
REM Start Foundation Learning Monitor
REM Quick launcher for YouTube foundation learning with progress monitoring

echo ================================================================
echo Starting Foundation Learning Monitor
echo ================================================================
echo.

REM Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python not found in PATH
    echo Please install Python 3.11+ or activate your environment
    pause
    exit /b 1
)

echo Python found: OK
echo.

REM Launch the foundation learning widget
echo Launching Foundation Learning Monitor UI...
echo.
echo This will open a window where you can:
echo   - Start autonomous foundation learning
echo   - Monitor progress in real-time
echo   - See which techniques are being learned
echo   - Track download progress
echo.

cd /d "%~dp0"
python -c "from ui.foundation_learning_widget import FoundationLearningWidget; from PySide6.QtWidgets import QApplication; import sys; app = QApplication(sys.argv); widget = FoundationLearningWidget(); widget.setWindowTitle('DrumTracKAI - Foundation Learning Monitor'); widget.resize(1000, 800); widget.show(); sys.exit(app.exec())"

if errorlevel 1 (
    echo.
    echo ERROR: Failed to launch UI
    echo.
    echo Possible issues:
    echo   1. PySide6 not installed: pip install PySide6
    echo   2. Missing dependencies: pip install yt-dlp
    echo.
    pause
)

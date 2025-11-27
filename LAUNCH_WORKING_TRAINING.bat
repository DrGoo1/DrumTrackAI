@echo off
REM Launch Working Training Widget
echo ================================================================
echo DrumTracKAI - WORKING Training Widget Launcher
echo ================================================================
echo.

cd /d "%~dp0"

python -c "from PySide6.QtWidgets import QApplication; from admin.ui.working_training_widget import WorkingTrainingWidget; import sys; app = QApplication(sys.argv); widget = WorkingTrainingWidget(); widget.setWindowTitle('DrumTracKAI - Working Training'); widget.resize(800, 700); widget.show(); sys.exit(app.exec())"

if errorlevel 1 (
    echo.
    echo ERROR: Failed to launch
    echo.
    echo Make sure PySide6 is installed:
    echo   pip install PySide6
    echo.
    pause
)

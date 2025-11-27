@echo off
REM Launch WORKING Comprehensive Training Widget
echo ================================================================
echo DrumTracKAI - WORKING Comprehensive Training Widget
echo ================================================================
echo.

cd /d "%~dp0"

python -c "from PySide6.QtWidgets import QApplication; from admin.ui.working_comprehensive_training_widget import WorkingComprehensiveTrainingWidget; import sys; app = QApplication(sys.argv); widget = WorkingComprehensiveTrainingWidget(); widget.setWindowTitle('DrumTracKAI - Comprehensive Training (WORKING)'); widget.resize(900, 750); widget.show(); sys.exit(app.exec())"

if errorlevel 1 (
    echo.
    echo ERROR: Failed to launch
    echo.
    pause
)

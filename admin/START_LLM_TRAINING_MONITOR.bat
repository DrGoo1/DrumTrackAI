@echo off
REM Start LLM Training Monitor
REM Track LLM training progress and expertise development

echo ================================================================
echo Starting LLM Training & Expertise Monitor
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

REM Launch the enhanced LLM training monitor
echo Launching LLM Training Monitor UI...
echo.
echo This window provides:
echo   - Track A (General Expertise) monitoring
echo   - Track B (Drummer Profiles) monitoring
echo   - Real-time training progress
echo   - Evaluation tools
echo   - Historical tracking
echo.

cd /d "%~dp0"
python -c "from ui.enhanced_llm_training_widget import EnhancedLLMTrainingWidget; from PySide6.QtWidgets import QApplication; import sys; app = QApplication(sys.argv); widget = EnhancedLLMTrainingWidget(); widget.setWindowTitle('DrumTracKAI - LLM Training Monitor'); widget.resize(1000, 700); widget.show(); sys.exit(app.exec())"

if errorlevel 1 (
    echo.
    echo ERROR: Failed to launch UI
    echo.
    echo Possible issues:
    echo   1. PySide6 not installed: pip install PySide6
    echo   2. Missing dependencies
    echo.
    pause
)

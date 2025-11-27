@echo off
REM Launch E-GMD Feature Extractor
echo ================================================================
echo DrumTracKAI - E-GMD MIDI Feature Extractor
echo ================================================================
echo.

cd /d "%~dp0"

echo Installing required dependency: mido
pip install mido

echo.
echo Launching E-GMD Extractor...
python -c "from PySide6.QtWidgets import QApplication; from admin.ui.egmd_extraction_widget import EGMDExtractionWidget; import sys; app = QApplication(sys.argv); widget = EGMDExtractionWidget(); widget.setWindowTitle('E-GMD Feature Extraction'); widget.resize(900, 750); widget.show(); sys.exit(app.exec())"

if errorlevel 1 (
    echo.
    echo ERROR: Failed to launch
    echo.
    pause
)

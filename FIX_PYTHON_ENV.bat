@echo off
echo Fixing v1.1.16 Python Environment...
echo.

REM Activate environment
call drumtrackai_env\Scripts\activate.bat

REM Reinstall broken pydantic modules
pip install --force-reinstall --no-cache-dir pydantic-core
pip install --force-reinstall --no-cache-dir pydantic

echo.
echo Python environment fixed!
echo Now run: 1_START_BACKEND.bat
pause

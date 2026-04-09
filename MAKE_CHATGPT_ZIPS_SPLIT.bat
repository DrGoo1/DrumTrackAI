@echo off
setlocal

set SCRIPT_DIR=%~dp0
echo Running: %SCRIPT_DIR%MAKE_CHATGPT_ZIPS_SPLIT.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File "%SCRIPT_DIR%MAKE_CHATGPT_ZIPS_SPLIT.ps1"
echo.
echo If you saw errors above, copy/paste them into chat.
pause

endlocal

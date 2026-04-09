@echo off
setlocal

REM Run from repo root: f:\DrumTracKAI_v1.1.17
set SCRIPT_DIR=%~dp0

echo Running: %SCRIPT_DIR%MAKE_CHATGPT_ZIPS.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File "%SCRIPT_DIR%MAKE_CHATGPT_ZIPS.ps1"
echo.
echo If you saw errors above, copy/paste them into chat.
pause

endlocal

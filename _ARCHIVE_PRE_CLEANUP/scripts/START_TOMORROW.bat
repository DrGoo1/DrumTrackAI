@echo off
echo ========================================
echo DrumTracKAI v1.1.16 - Morning Startup
echo ========================================
echo.
echo TODAY'S GOALS:
echo 1. Fix audio playback (CORS issue)
echo 2. Clean up debug logging
echo 3. Test everything
echo 4. Create backup
echo.
echo ========================================
echo READ THESE FIRST:
echo ========================================
echo 1. ACTION_PLAN_TOMORROW.md  ^<-- START HERE
echo 2. SYSTEM_MAP_COMPLETE.md   ^<-- Reference
echo 3. SESSION_SUMMARY_NOV_18.md ^<-- Yesterday
echo.
pause
echo.
echo ========================================
echo Starting Backend...
echo ========================================
start "Backend" cmd /c "cd /d %~dp0 && f:\DrumTracKAI_v1.1.11\drumtrackai_env\Scripts\python.exe dcsm_backend.py"
echo Backend starting on port 8000...
timeout /t 5 >nul

echo.
echo ========================================
echo Starting Frontend...
echo ========================================  
start "Frontend" cmd /c "cd /d %~dp0\frontend && npm start"
echo Frontend starting on port 3000...
timeout /t 3 >nul

echo.
echo ========================================
echo SYSTEM STARTING...
echo ========================================
echo Backend:  http://localhost:8000
echo DCSM:     http://localhost:3000
echo Pro:      http://localhost:3000/pro
echo ========================================
echo.
echo Wait 30 seconds for compile...
echo Then open: http://localhost:3000/pro
echo.
echo REMEMBER: Follow ACTION_PLAN_TOMORROW.md
echo ========================================
pause

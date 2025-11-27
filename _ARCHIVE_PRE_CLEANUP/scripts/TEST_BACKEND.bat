@echo off
echo ========================================
echo Testing Backend API
echo ========================================
echo.

echo Testing AI Status endpoint...
curl http://localhost:8000/api/ai/status
echo.
echo.

echo ========================================
echo Test complete!
echo ========================================
pause

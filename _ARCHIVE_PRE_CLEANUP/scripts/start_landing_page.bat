@echo off
echo Starting DrumTracKAI v1.1.7 Comprehensive React Landing Page...
echo Port: 3004
echo.

cd /d f:\DrumTracKAI_v1.1.16_Clean\web-frontend-landing-v117

REM Set port to 3004 to avoid conflict with DCSM on port 3000
set PORT=3004

npm start

pause

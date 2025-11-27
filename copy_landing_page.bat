@echo off
echo Copying v1.1.7 Comprehensive React Landing Page to v1.1.16...
echo.

REM Copy the entire web-frontend folder
xcopy "F:\DrumTracKAI_Archives\legacy_versions\DrumTracKAI_v1.1.7\web-frontend" "f:\DrumTracKAI_v1.1.16_Clean\web-frontend-landing-v117\" /E /I /H /Y

echo.
echo Copy complete!
echo.
echo Landing page copied to: f:\DrumTracKAI_v1.1.16_Clean\web-frontend-landing-v117
echo.
echo Next steps:
echo   1. cd web-frontend-landing-v117
echo   2. npm install
echo   3. npm start
echo.
echo The comprehensive React landing page will run on http://localhost:3000
echo.
pause

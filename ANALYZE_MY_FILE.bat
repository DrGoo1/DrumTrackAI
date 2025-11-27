@echo off
echo Copying your audio file to uploads...

set SOURCE="C:\Users\dagol\OneDrive\Documents\Sound Recordings\Recording (2).m4a"
set TIMESTAMP=%date:~10,4%%date:~4,2%%date:~7,2%_%time:~0,2%%time:~3,2%%time:~6,2%
set TIMESTAMP=%TIMESTAMP: =0%
set DEST=uploads\%TIMESTAMP%-Recording_2.m4a

copy %SOURCE% %DEST%

if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Failed to copy file. Check if the source file exists.
    pause
    exit /b 1
)

echo File copied successfully to: %DEST%
echo.
echo Now analyzing with backend...
echo.

REM Get just the filename
for %%F in (%DEST%) do set FILENAME=%%~nxF

REM Call the backend API to get waveform
curl -X GET "http://localhost:8000/waveform?key=%FILENAME%"

echo.
echo.
echo File key: %FILENAME%
echo.
echo You can now load this file in the React app using this key!
echo.
pause

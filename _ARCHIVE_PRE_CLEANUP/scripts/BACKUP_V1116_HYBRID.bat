@echo off
echo ================================================
echo DrumTracKAI v1.1.16 Hybrid System Backup
echo ================================================
echo.

set BACKUP_DIR=f:\DrumTracKAI_v1.1.16_Hybrid_Backup_%DATE:~-4,4%%DATE:~-10,2%%DATE:~-7,2%_%TIME:~0,2%%TIME:~3,2%%TIME:~6,2%
set BACKUP_DIR=%BACKUP_DIR: =0%

echo Creating backup directory: %BACKUP_DIR%
mkdir "%BACKUP_DIR%"

echo.
echo Backing up complete hybrid system...

:: Copy entire project
xcopy /E /I /H /Y "%CD%" "%BACKUP_DIR%\DrumTracKAI_v1.1.16_Clean"

:: Create backup manifest
echo DrumTracKAI v1.1.16 Hybrid System Backup > "%BACKUP_DIR%\BACKUP_MANIFEST.txt"
echo Backup Date: %DATE% %TIME% >> "%BACKUP_DIR%\BACKUP_MANIFEST.txt"
echo. >> "%BACKUP_DIR%\BACKUP_MANIFEST.txt"
echo COMPONENTS INCLUDED: >> "%BACKUP_DIR%\BACKUP_MANIFEST.txt"
echo - Complete DCSM v1.1.16 web application >> "%BACKUP_DIR%\BACKUP_MANIFEST.txt"
echo - Tracktion Hybrid FFI integration >> "%BACKUP_DIR%\BACKUP_MANIFEST.txt"
echo - Built Rust audio-core FFI library >> "%BACKUP_DIR%\BACKUP_MANIFEST.txt"
echo - Docker orchestration configuration >> "%BACKUP_DIR%\BACKUP_MANIFEST.txt"
echo - C++ JUCE Tracktion application source >> "%BACKUP_DIR%\BACKUP_MANIFEST.txt"
echo - Python backend with FFI integration >> "%BACKUP_DIR%\BACKUP_MANIFEST.txt"
echo - React TypeScript frontend >> "%BACKUP_DIR%\BACKUP_MANIFEST.txt"
echo - Complete build and deployment scripts >> "%BACKUP_DIR%\BACKUP_MANIFEST.txt"

echo.
echo ================================================
echo Backup Complete!
echo ================================================
echo.
echo Backup Location: %BACKUP_DIR%
echo.
dir "%BACKUP_DIR%" /s | find "File(s)"
echo.
pause

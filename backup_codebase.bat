@echo off
REM Backup Codebase - DrumTracKAI v1.1.16
REM Creates timestamped backup of entire codebase

echo ========================================
echo BACKUP CODEBASE - DrumTracKAI v1.1.16
echo ========================================
echo.

REM Get timestamp
for /f "tokens=2 delims==" %%I in ('wmic os get localdatetime /value') do set datetime=%%I
set TIMESTAMP=%datetime:~0,8%_%datetime:~8,6%
set BACKUP_NAME=DrumTracKAI_v1.1.16_Backup_%TIMESTAMP%

REM Backup directory
set BACKUP_DIR=F:\Backups\DrumTracKAI
set BACKUP_PATH=%BACKUP_DIR%\%BACKUP_NAME%

echo Creating backup...
echo Timestamp: %TIMESTAMP%
echo Backup location: %BACKUP_PATH%
echo.

REM Create backup directory
if not exist "%BACKUP_DIR%" mkdir "%BACKUP_DIR%"

REM Copy entire directory
echo Copying files...
xcopy /E /I /H /Y "f:\DrumTracKAI_v1.1.16_Clean" "%BACKUP_PATH%"

echo.
echo ========================================
echo Backup complete!
echo ========================================
echo.
echo Backup saved to:
echo %BACKUP_PATH%
echo.
echo Files backed up:
dir "%BACKUP_PATH%" /s /-c | find "File(s)"
echo.

REM Create backup info file
echo DrumTracKAI v1.1.16 Backup > "%BACKUP_PATH%\BACKUP_INFO.txt"
echo ============================= >> "%BACKUP_PATH%\BACKUP_INFO.txt"
echo. >> "%BACKUP_PATH%\BACKUP_INFO.txt"
echo Backup Date: %date% %time% >> "%BACKUP_PATH%\BACKUP_INFO.txt"
echo Timestamp: %TIMESTAMP% >> "%BACKUP_PATH%\BACKUP_INFO.txt"
echo Source: f:\DrumTracKAI_v1.1.16_Clean >> "%BACKUP_PATH%\BACKUP_INFO.txt"
echo. >> "%BACKUP_PATH%\BACKUP_INFO.txt"
echo FEATURES: >> "%BACKUP_PATH%\BACKUP_INFO.txt"
echo - AI Pattern Generator (91,074 patterns) >> "%BACKUP_PATH%\BACKUP_INFO.txt"
echo - Category Drummer System (7 categories, 12 drummers) >> "%BACKUP_PATH%\BACKUP_INFO.txt"
echo - Profile Maturity Tracking >> "%BACKUP_PATH%\BACKUP_INFO.txt"
echo - Automated Profile Builder >> "%BACKUP_PATH%\BACKUP_INFO.txt"
echo - 8 AI API Endpoints >> "%BACKUP_PATH%\BACKUP_INFO.txt"
echo - Complete Documentation >> "%BACKUP_PATH%\BACKUP_INFO.txt"
echo. >> "%BACKUP_PATH%\BACKUP_INFO.txt"
echo STATUS: Production-ready >> "%BACKUP_PATH%\BACKUP_INFO.txt"

echo Backup info saved to: %BACKUP_PATH%\BACKUP_INFO.txt
echo.

REM Optional: Create compressed archive
set COMPRESS=N
set /p COMPRESS="Create compressed archive (7z)? (Y/N): "
if /i "%COMPRESS%"=="Y" (
    echo.
    echo Creating compressed archive...
    if exist "C:\Program Files\7-Zip\7z.exe" (
        "C:\Program Files\7-Zip\7z.exe" a -t7z "%BACKUP_DIR%\%BACKUP_NAME%.7z" "%BACKUP_PATH%\*" -mx=9
        echo.
        echo Compressed archive created: %BACKUP_DIR%\%BACKUP_NAME%.7z
    ) else (
        echo 7-Zip not found at C:\Program Files\7-Zip\7z.exe
        echo Install 7-Zip or manually compress: %BACKUP_PATH%
    )
)

echo.
echo ========================================
echo All done!
echo ========================================
pause

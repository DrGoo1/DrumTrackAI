@echo off
REM ============================================================================
REM DrumTracKAI v1.1.16 Complete Backup Script
REM With Guide Track Feature Implementation
REM ============================================================================

echo.
echo ================================================================================
echo DrumTracKAI v1.1.16 - Complete System Backup
echo With Guide Track Feature
echo ================================================================================
echo.

set TIMESTAMP=%date:~-4%%date:~-10,2%%date:~-7,2%_%time:~0,2%%time:~3,2%
set TIMESTAMP=%TIMESTAMP: =0%
set BACKUP_NAME=DrumTracKAI_v1.1.16_GuideTrack_%TIMESTAMP%
set BACKUP_DIR=F:\Backups\%BACKUP_NAME%

echo Creating backup: %BACKUP_NAME%
echo Destination: %BACKUP_DIR%
echo.

REM Create backup directory
if not exist "F:\Backups" mkdir "F:\Backups"
mkdir "%BACKUP_DIR%"

echo [1/8] Backing up Plugin Source Code...
xcopy /E /I /Y "DrumTracKAIConnector" "%BACKUP_DIR%\DrumTracKAIConnector\" > nul
echo      ✓ Plugin source copied

echo [2/8] Backing up Backend Python Code...
xcopy /Y "*.py" "%BACKUP_DIR%\" > nul
echo      ✓ Backend scripts copied

echo [3/8] Backing up Configuration Files...
xcopy /Y "*.json" "%BACKUP_DIR%\" > nul 2>nul
xcopy /Y "*.toml" "%BACKUP_DIR%\" > nul 2>nul
xcopy /Y "*.yml" "%BACKUP_DIR%\" > nul 2>nul
xcopy /Y ".env*" "%BACKUP_DIR%\" > nul 2>nul
echo      ✓ Configuration files copied

echo [4/8] Backing up Documentation...
xcopy /Y "*.md" "%BACKUP_DIR%\" > nul
xcopy /Y "*.txt" "%BACKUP_DIR%\" > nul 2>nul
echo      ✓ Documentation copied

echo [5/8] Backing up Build Scripts...
xcopy /Y "*.bat" "%BACKUP_DIR%\" > nul
xcopy /Y "*.sh" "%BACKUP_DIR%\" > nul 2>nul
echo      ✓ Build scripts copied

echo [6/8] Backing up Rust Source Code...
if exist "audio-core" xcopy /E /I /Y "audio-core" "%BACKUP_DIR%\audio-core\" > nul
if exist "rust-core" xcopy /E /I /Y "rust-core" "%BACKUP_DIR%\rust-core\" > nul
if exist "rust-audio" xcopy /E /I /Y "rust-audio" "%BACKUP_DIR%\rust-audio\" > nul
if exist "Cargo.toml" xcopy /Y "Cargo.toml" "%BACKUP_DIR%\" > nul
if exist "Cargo.lock" xcopy /Y "Cargo.lock" "%BACKUP_DIR%\" > nul
echo      ✓ Rust source copied

echo [7/8] Backing up Web Frontend...
if exist "web-frontend" (
    xcopy /E /I /Y "web-frontend\src" "%BACKUP_DIR%\web-frontend\src\" > nul
    xcopy /E /I /Y "web-frontend\public" "%BACKUP_DIR%\web-frontend\public\" > nul
    xcopy /Y "web-frontend\package*.json" "%BACKUP_DIR%\web-frontend\" > nul 2>nul
    xcopy /Y "web-frontend\*.ts*" "%BACKUP_DIR%\web-frontend\" > nul 2>nul
    echo      ✓ Web frontend copied
) else (
    echo      ! Web frontend not found - skipped
)

echo [8/8] Creating backup manifest...
(
    echo DrumTracKAI v1.1.16 - Complete System Backup
    echo ============================================
    echo.
    echo Backup Date: %date% %time%
    echo Backup Name: %BACKUP_NAME%
    echo.
    echo FEATURES INCLUDED:
    echo - Complete VST3/AU Plugin with Guide Track Feature
    echo - Python Backend with Guide Track API
    echo - Rust Audio Core Integration
    echo - Web Frontend DCSM Interface
    echo - All Documentation and Build Scripts
    echo.
    echo NEW IN THIS BACKUP:
    echo - ✓ Guide Track Toggle in Plugin UI
    echo - ✓ Instrument Selector ^(Mix/Bass/Guitar/Keys/Vocal/Other^)
    echo - ✓ Backend API Extended for Guide Metadata
    echo - ✓ Persistent State Management
    echo - ✓ Complete Documentation
    echo.
    echo PLUGIN CHANGES:
    echo - NetworkClient: Added guide fields to Request struct
    echo - PluginProcessor: State management for guide settings
    echo - PluginEditor: New UI controls ^(toggle + combo box^)
    echo - Total: ~71 lines of C++ code
    echo.
    echo BACKEND CHANGES:
    echo - plugin_endpoint.py: Extended API handler
    echo - Guide-aware analysis pipeline
    echo - Total: ~45 lines of Python code
    echo.
    echo FILES STRUCTURE:
    echo - DrumTracKAIConnector/    : Complete JUCE plugin source
    echo - *.py                      : Backend Python modules
    echo - audio-core/              : Rust audio processing
    echo - web-frontend/            : React TypeScript UI
    echo - *.md                      : Documentation
    echo - *.bat                     : Build and deployment scripts
    echo.
    echo RESTORE INSTRUCTIONS:
    echo 1. Copy all files from this backup to working directory
    echo 2. Run SETUP_JUCE.bat to download JUCE framework
    echo 3. Run BUILD_PLUGIN.bat to compile plugin
    echo 4. Start backend: python plugin_endpoint.py
    echo 5. Load plugin in DAW
    echo.
    echo For detailed guide track documentation see:
    echo - GUIDE_TRACK_IMPLEMENTATION.md
    echo - GUIDE_TRACK_PATCH_SUMMARY.md
    echo.
) > "%BACKUP_DIR%\BACKUP_MANIFEST.txt"
echo      ✓ Manifest created

echo.
echo ================================================================================
echo BACKUP COMPLETE!
echo ================================================================================
echo.
echo Backup Location: %BACKUP_DIR%
echo.
echo Contents:
dir /B "%BACKUP_DIR%"
echo.
echo Backup Size:
for /f "tokens=3" %%a in ('dir "%BACKUP_DIR%" ^| find "File(s)"') do echo %%a bytes
echo.
echo To restore this backup:
echo 1. Copy contents to DrumTracKAI_v1.1.16_Clean folder
echo 2. Run build scripts as needed
echo.
pause

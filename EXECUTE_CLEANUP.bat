@echo off
REM ============================================================================
REM DrumTracKAI v1.1.16.1 - Codebase Cleanup Script
REM Archives unused/legacy files while preserving active components
REM ============================================================================

echo.
echo ================================================================================
echo DrumTracKAI v1.1.16.1 - Codebase Cleanup
echo ================================================================================
echo.
echo This script will archive ~300 legacy files to keep only active v1.1.16.1 code
echo.
echo SAFETY: All files will be MOVED (not deleted) to _ARCHIVE_PRE_CLEANUP\
echo You can restore them if needed.
echo.
pause

set ARCHIVE_ROOT=_ARCHIVE_PRE_CLEANUP
set TIMESTAMP=%date:~-4%%date:~-10,2%%date:~-7,2%_%time:~0,2%%time:~3,2%
set TIMESTAMP=%TIMESTAMP: =0%

echo.
echo Creating archive directory structure...
mkdir "%ARCHIVE_ROOT%" 2>nul
mkdir "%ARCHIVE_ROOT%\documentation" 2>nul
mkdir "%ARCHIVE_ROOT%\scripts" 2>nul
mkdir "%ARCHIVE_ROOT%\old_frontends" 2>nul
mkdir "%ARCHIVE_ROOT%\test_files" 2>nul
mkdir "%ARCHIVE_ROOT%\training" 2>nul
mkdir "%ARCHIVE_ROOT%\legacy_backend" 2>nul
mkdir "%ARCHIVE_ROOT%\temp_files" 2>nul
echo ✓ Archive structure created

REM ============================================================================
REM 1. Archive Legacy Documentation (100+ .md files)
REM ============================================================================
echo.
echo [1/9] Archiving legacy documentation...

REM Keep only these essential docs
set KEEP_DOCS=README.md GUIDE_TRACK_IMPLEMENTATION.md COMPLETE_PLUGIN_INTEGRATION_GUIDE.md README_START_HERE.md CLEANUP_PLAN.md

REM Move all other .md files
for %%F in (*.md) do (
    set "KEEP_FILE="
    for %%K in (%KEEP_DOCS%) do (
        if /I "%%F"=="%%K" set "KEEP_FILE=1"
    )
    if not defined KEEP_FILE (
        move "%%F" "%ARCHIVE_ROOT%\documentation\" >nul 2>&1
    )
)
echo      ✓ Legacy documentation archived

REM ============================================================================
REM 2. Archive Deprecated Scripts
REM ============================================================================
echo [2/9] Archiving deprecated scripts...

REM Keep only these essential scripts
set KEEP_SCRIPTS=LAUNCH_V1116.bat BACKUP_v1.1.16_with_guide_track.bat STOP_ALL.bat EXECUTE_CLEANUP.bat

REM Move START_*, TEST_*, CHECK_*, DEPLOY_*, RESTART_*, OPEN_* variants
for %%F in (START_*.bat TEST_*.bat CHECK_*.bat DEPLOY_*.bat RESTART_*.bat OPEN_*.bat CLEAR_*.bat FORCE_*.bat RELOAD_*.bat REMOVE_*.bat SETUP_*.bat SIMPLE_*.bat) do (
    set "KEEP_FILE="
    for %%K in (%KEEP_SCRIPTS%) do (
        if /I "%%F"=="%%K" set "KEEP_FILE=1"
    )
    if not defined KEEP_FILE (
        move "%%F" "%ARCHIVE_ROOT%\scripts\" >nul 2>&1
    )
)

REM Move numbered startup scripts
move "1_START_BACKEND.bat" "%ARCHIVE_ROOT%\scripts\" >nul 2>&1
move "2_START_DCSM.bat" "%ARCHIVE_ROOT%\scripts\" >nul 2>&1
move "3_START_LANDING_PAGE.bat" "%ARCHIVE_ROOT%\scripts\" >nul 2>&1

REM Move PowerShell scripts
move "*.ps1" "%ARCHIVE_ROOT%\scripts\" >nul 2>&1

REM Move old build/deploy scripts
move "setup.bat" "%ARCHIVE_ROOT%\scripts\" >nul 2>&1
move "deploy.bat" "%ARCHIVE_ROOT%\scripts\" >nul 2>&1
move "deploy_v1116.bat" "%ARCHIVE_ROOT%\scripts\" >nul 2>&1
move "backup_codebase.bat" "%ARCHIVE_ROOT%\scripts\" >nul 2>&1
move "backup_git.bat" "%ARCHIVE_ROOT%\scripts\" >nul 2>&1
move "git_save_progress.bat" "%ARCHIVE_ROOT%\scripts\" >nul 2>&1
move "copy_landing_page.bat" "%ARCHIVE_ROOT%\scripts\" >nul 2>&1
move "rebuild_rust_core.bat" "%ARCHIVE_ROOT%\scripts\" >nul 2>&1
move "build_rust_python.bat" "%ARCHIVE_ROOT%\scripts\" >nul 2>&1

echo      ✓ Deprecated scripts archived

REM ============================================================================
REM 3. Archive Old Frontend Versions
REM ============================================================================
echo [3/9] Archiving old frontend versions...

if exist "frontend\" move "frontend" "%ARCHIVE_ROOT%\old_frontends\" >nul 2>&1
if exist "web-frontend-landing-v117\" move "web-frontend-landing-v117" "%ARCHIVE_ROOT%\old_frontends\" >nul 2>&1
move "*.OLD" "%ARCHIVE_ROOT%\old_frontends\" >nul 2>&1
move "landing_page.html.OLD" "%ARCHIVE_ROOT%\old_frontends\" >nul 2>&1
move "landing_page.js.OLD" "%ARCHIVE_ROOT%\old_frontends\" >nul 2>&1
move "LandingPage.html.OLD" "%ARCHIVE_ROOT%\old_frontends\" >nul 2>&1
move "LandingPage.js.OLD" "%ARCHIVE_ROOT%\old_frontends\" >nul 2>&1
move "temp_main.js" "%ARCHIVE_ROOT%\old_frontends\" >nul 2>&1
move "test_frontend.html" "%ARCHIVE_ROOT%\old_frontends\" >nul 2>&1
move "test_upload.html" "%ARCHIVE_ROOT%\old_frontends\" >nul 2>&1
move "training_dashboard.html" "%ARCHIVE_ROOT%\old_frontends\" >nul 2>&1

echo      ✓ Old frontends archived

REM ============================================================================
REM 4. Archive Test Files & Analysis Results
REM ============================================================================
echo [4/9] Archiving test files and analysis results...

REM Move test Python scripts
move "test_*.py" "%ARCHIVE_ROOT%\test_files\" >nul 2>&1
move "analyze_*.py" "%ARCHIVE_ROOT%\test_files\" >nul 2>&1
move "scan_*.py" "%ARCHIVE_ROOT%\test_files\" >nul 2>&1
move "check_*.py" "%ARCHIVE_ROOT%\test_files\" >nul 2>&1

REM Move test output files
move "test_output.json" "%ARCHIVE_ROOT%\test_files\" >nul 2>&1
move "test_pattern.json" "%ARCHIVE_ROOT%\test_files\" >nul 2>&1
move "sectionalization_test_results.json" "%ARCHIVE_ROOT%\test_files\" >nul 2>&1
move "sectionalization_refined.json" "%ARCHIVE_ROOT%\test_files\" >nul 2>&1
move "songmap_test.json" "%ARCHIVE_ROOT%\test_files\" >nul 2>&1
move "validation_report.json" "%ARCHIVE_ROOT%\test_files\" >nul 2>&1
move "rust_output.json" "%ARCHIVE_ROOT%\test_files\" >nul 2>&1

REM Move large analysis files
move "e_drive_analysis_report.json" "%ARCHIVE_ROOT%\test_files\" >nul 2>&1
move "database_scan_results.txt" "%ARCHIVE_ROOT%\test_files\" >nul 2>&1
move "midi_migration_log_*.json" "%ARCHIVE_ROOT%\test_files\" >nul 2>&1

echo      ✓ Test files archived

REM ============================================================================
REM 5. Archive Training Scripts
REM ============================================================================
echo [5/9] Archiving training scripts...

move "train_*.py" "%ARCHIVE_ROOT%\training\" >nul 2>&1
move "prepare_training_data.py" "%ARCHIVE_ROOT%\training\" >nul 2>&1
move "bootstrap_training.py" "%ARCHIVE_ROOT%\training\" >nul 2>&1
move "auto_train_complete.py" "%ARCHIVE_ROOT%\training\" >nul 2>&1
move "validate_groove_vae.py" "%ARCHIVE_ROOT%\training\" >nul 2>&1
move "monitor_training.py" "%ARCHIVE_ROOT%\training\" >nul 2>&1
move "groove_vae_model.py" "%ARCHIVE_ROOT%\training\" >nul 2>&1
move "extract_and_train.py" "%ARCHIVE_ROOT%\training\" >nul 2>&1
move "quick_*.py" "%ARCHIVE_ROOT%\training\" >nul 2>&1
move "training_documentation.db" "%ARCHIVE_ROOT%\training\" >nul 2>&1

echo      ✓ Training scripts archived

REM ============================================================================
REM 6. Archive Legacy Backend Components
REM ============================================================================
echo [6/9] Archiving legacy backend components...

move "simple_backend.py" "%ARCHIVE_ROOT%\legacy_backend\" >nul 2>&1
move "minimal_backend.py" "%ARCHIVE_ROOT%\legacy_backend\" >nul 2>&1
move "run_backend.py" "%ARCHIVE_ROOT%\legacy_backend\" >nul 2>&1
move "*.backup" "%ARCHIVE_ROOT%\legacy_backend\" >nul 2>&1
move "dcsm_backend.py.backup" "%ARCHIVE_ROOT%\legacy_backend\" >nul 2>&1

REM Archive admin folder if it exists and not actively used
REM Uncomment if you want to archive it:
REM if exist "admin\" move "admin" "%ARCHIVE_ROOT%\legacy_backend\" >nul 2>&1

REM Archive tracktion-hybrid if focusing on plugin
REM Uncomment if you want to archive it:
REM if exist "tracktion-hybrid\" move "tracktion-hybrid" "%ARCHIVE_ROOT%\legacy_backend\" >nul 2>&1

echo      ✓ Legacy backend archived

REM ============================================================================
REM 7. Archive Temporary/Generated Files
REM ============================================================================
echo [7/9] Archiving temporary and generated files...

move "ai_generated_test.mid" "%ARCHIVE_ROOT%\temp_files\" >nul 2>&1
move "generated_peg_drums.mid" "%ARCHIVE_ROOT%\temp_files\" >nul 2>&1
move "commit_message.txt" "%ARCHIVE_ROOT%\temp_files\" >nul 2>&1
move "Saves" "%ARCHIVE_ROOT%\temp_files\" >nul 2>&1
move "DB" "%ARCHIVE_ROOT%\temp_files\" >nul 2>&1

REM Move miscellaneous Python scripts not in core system
move "automated_drummer_profile_builder.py" "%ARCHIVE_ROOT%\temp_files\" >nul 2>&1
move "backend_ai_endpoints.py" "%ARCHIVE_ROOT%\temp_files\" >nul 2>&1
move "complete_build.py" "%ARCHIVE_ROOT%\temp_files\" >nul 2>&1
move "complete_migration_plan.py" "%ARCHIVE_ROOT%\temp_files\" >nul 2>&1
move "create_clean_build.py" "%ARCHIVE_ROOT%\temp_files\" >nul 2>&1
move "create_optimal_structure.py" "%ARCHIVE_ROOT%\temp_files\" >nul 2>&1
move "dataset_scanner.py" "%ARCHIVE_ROOT%\temp_files\" >nul 2>&1
move "drum_generation_api.py" "%ARCHIVE_ROOT%\temp_files\" >nul 2>&1
move "drummer_*.py" "%ARCHIVE_ROOT%\temp_files\" >nul 2>&1
move "export_midi_test.py" "%ARCHIVE_ROOT%\temp_files\" >nul 2>&1
move "initialize_database.py" "%ARCHIVE_ROOT%\temp_files\" >nul 2>&1
move "integrate_ai_backend.py" "%ARCHIVE_ROOT%\temp_files\" >nul 2>&1
move "migrate_midi_priority.py" "%ARCHIVE_ROOT%\temp_files\" >nul 2>&1
move "native_deployment_agent.py" "%ARCHIVE_ROOT%\temp_files\" >nul 2>&1
move "refine_sectionalization.py" "%ARCHIVE_ROOT%\temp_files\" >nul 2>&1
move "section_analyzer.py" "%ARCHIVE_ROOT%\temp_files\" >nul 2>&1
move "song_lookup_service.py" "%ARCHIVE_ROOT%\temp_files\" >nul 2>&1
move "swarm_orchestrator.py" "%ARCHIVE_ROOT%\temp_files\" >nul 2>&1
move "ultimate_scanner.py" "%ARCHIVE_ROOT%\temp_files\" >nul 2>&1
move "ai_pattern_generator.py" "%ARCHIVE_ROOT%\temp_files\" >nul 2>&1
move "analyze_pattern.py" "%ARCHIVE_ROOT%\temp_files\" >nul 2>&1
move "unified_database_schema.sql" "%ARCHIVE_ROOT%\temp_files\" >nul 2>&1

echo      ✓ Temporary files archived

REM ============================================================================
REM 8. Archive Docker files if not used
REM ============================================================================
echo [8/9] Archiving Docker files (if not actively using Docker)...

REM Uncomment these if you're NOT using Docker:
REM move "Dockerfile.*" "%ARCHIVE_ROOT%\temp_files\" >nul 2>&1
REM move "docker-compose.*.yml" "%ARCHIVE_ROOT%\temp_files\" >nul 2>&1
REM move "DOCKER_*.bat" "%ARCHIVE_ROOT%\scripts\" >nul 2>&1

echo      ✓ Docker files handled

REM ============================================================================
REM 9. Clean Up Empty Directories
REM ============================================================================
echo [9/9] Removing empty directories...

REM Remove validation_samples if empty
if exist "validation_samples\" rmdir "validation_samples" 2>nul

echo      ✓ Empty directories removed

REM ============================================================================
REM Create Cleanup Log
REM ============================================================================
echo.
echo Creating cleanup log...

(
    echo DrumTracKAI v1.1.16.1 - Cleanup Log
    echo ====================================
    echo.
    echo Date: %date% %time%
    echo Archive Location: %ARCHIVE_ROOT%\
    echo.
    echo Files Archived:
    dir /B /S "%ARCHIVE_ROOT%" 2>nul
    echo.
    echo Remaining Active Files:
    dir /B /A-D 2>nul
) > "%ARCHIVE_ROOT%\CLEANUP_LOG_%TIMESTAMP%.txt"

echo ✓ Log created

echo.
echo ================================================================================
echo CLEANUP COMPLETE!
echo ================================================================================
echo.
echo Archive Location: %ARCHIVE_ROOT%\
echo.
echo Active files remaining in root:
dir /B /A-D | find /C /V ""
echo.
echo You can now verify the system still works:
echo 1. Test the plugin build: cd DrumTracKAIConnector ^&^& BUILD_PLUGIN.bat
echo 2. Test the backend: python plugin_endpoint.py
echo.
echo If anything is missing, restore from: %ARCHIVE_ROOT%\
echo.
pause

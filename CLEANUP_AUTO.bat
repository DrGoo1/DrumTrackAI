@echo off
REM ============================================================================
REM DrumTracKAI v1.1.16.1 - Automatic Codebase Cleanup
REM Archives unused/legacy files while preserving active components
REM ============================================================================

echo ================================================================================
echo DrumTracKAI v1.1.16.1 - Codebase Cleanup (AUTO)
echo ================================================================================
echo Archiving legacy files to _ARCHIVE_PRE_CLEANUP\

set ARCHIVE_ROOT=_ARCHIVE_PRE_CLEANUP
set TIMESTAMP=%date:~-4%%date:~-10,2%%date:~-7,2%_%time:~0,2%%time:~3,2%
set TIMESTAMP=%TIMESTAMP: =0%

echo Creating archive directories...
mkdir "%ARCHIVE_ROOT%" 2>nul
mkdir "%ARCHIVE_ROOT%\documentation" 2>nul
mkdir "%ARCHIVE_ROOT%\scripts" 2>nul
mkdir "%ARCHIVE_ROOT%\old_frontends" 2>nul
mkdir "%ARCHIVE_ROOT%\test_files" 2>nul
mkdir "%ARCHIVE_ROOT%\training" 2>nul
mkdir "%ARCHIVE_ROOT%\legacy_backend" 2>nul
mkdir "%ARCHIVE_ROOT%\temp_files" 2>nul

REM Archive Legacy Documentation
echo [1/9] Archiving legacy documentation...
for %%F in (*.md) do (
    if /I not "%%F"=="README.md" (
        if /I not "%%F"=="GUIDE_TRACK_IMPLEMENTATION.md" (
            if /I not "%%F"=="COMPLETE_PLUGIN_INTEGRATION_GUIDE.md" (
                if /I not "%%F"=="README_START_HERE.md" (
                    if /I not "%%F"=="CLEANUP_PLAN.md" (
                        move "%%F" "%ARCHIVE_ROOT%\documentation\" >nul 2>&1
                    )
                )
            )
        )
    )
)

REM Archive Deprecated Scripts
echo [2/9] Archiving deprecated scripts...
for %%F in (START_*.bat TEST_*.bat CHECK_*.bat DEPLOY_*.bat RESTART_*.bat OPEN_*.bat CLEAR_*.bat FORCE_*.bat RELOAD_*.bat REMOVE_*.bat SETUP_*.bat SIMPLE_*.bat) do (
    if /I not "%%F"=="STOP_ALL.bat" (
        move "%%F" "%ARCHIVE_ROOT%\scripts\" >nul 2>&1
    )
)

move "1_START_BACKEND.bat" "%ARCHIVE_ROOT%\scripts\" >nul 2>&1
move "2_START_DCSM.bat" "%ARCHIVE_ROOT%\scripts\" >nul 2>&1
move "3_START_LANDING_PAGE.bat" "%ARCHIVE_ROOT%\scripts\" >nul 2>&1
move "*.ps1" "%ARCHIVE_ROOT%\scripts\" >nul 2>&1
move "setup.bat" "%ARCHIVE_ROOT%\scripts\" >nul 2>&1
move "deploy.bat" "%ARCHIVE_ROOT%\scripts\" >nul 2>&1
move "deploy_v1116.bat" "%ARCHIVE_ROOT%\scripts\" >nul 2>&1
move "backup_codebase.bat" "%ARCHIVE_ROOT%\scripts\" >nul 2>&1
move "backup_git.bat" "%ARCHIVE_ROOT%\scripts\" >nul 2>&1
move "git_save_progress.bat" "%ARCHIVE_ROOT%\scripts\" >nul 2>&1
move "BACKUP_V1116_HYBRID.bat" "%ARCHIVE_ROOT%\scripts\" >nul 2>&1
move "QUICK_START.bat" "%ARCHIVE_ROOT%\scripts\" >nul 2>&1

REM Archive Old Frontends
echo [3/9] Archiving old frontend versions...
if exist "frontend\" move "frontend" "%ARCHIVE_ROOT%\old_frontends\" >nul 2>&1
if exist "web-frontend-landing-v117\" move "web-frontend-landing-v117" "%ARCHIVE_ROOT%\old_frontends\" >nul 2>&1
move "*.OLD" "%ARCHIVE_ROOT%\old_frontends\" >nul 2>&1
move "temp_main.js" "%ARCHIVE_ROOT%\old_frontends\" >nul 2>&1
move "test_frontend.html" "%ARCHIVE_ROOT%\old_frontends\" >nul 2>&1
move "test_upload.html" "%ARCHIVE_ROOT%\old_frontends\" >nul 2>&1
move "training_dashboard.html" "%ARCHIVE_ROOT%\old_frontends\" >nul 2>&1

REM Archive Test Files
echo [4/9] Archiving test files...
move "test_*.py" "%ARCHIVE_ROOT%\test_files\" >nul 2>&1
move "analyze_*.py" "%ARCHIVE_ROOT%\test_files\" >nul 2>&1
move "scan_*.py" "%ARCHIVE_ROOT%\test_files\" >nul 2>&1
move "check_*.py" "%ARCHIVE_ROOT%\test_files\" >nul 2>&1
move "test_*.json" "%ARCHIVE_ROOT%\test_files\" >nul 2>&1
move "sectionalization_*.json" "%ARCHIVE_ROOT%\test_files\" >nul 2>&1
move "validation_report.json" "%ARCHIVE_ROOT%\test_files\" >nul 2>&1
move "rust_output.json" "%ARCHIVE_ROOT%\test_files\" >nul 2>&1
move "e_drive_analysis_report.json" "%ARCHIVE_ROOT%\test_files\" >nul 2>&1
move "database_scan_results.txt" "%ARCHIVE_ROOT%\test_files\" >nul 2>&1
move "midi_migration_log_*.json" "%ARCHIVE_ROOT%\test_files\" >nul 2>&1

REM Archive Training Scripts
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

REM Archive Legacy Backend
echo [6/9] Archiving legacy backend...
move "simple_backend.py" "%ARCHIVE_ROOT%\legacy_backend\" >nul 2>&1
move "minimal_backend.py" "%ARCHIVE_ROOT%\legacy_backend\" >nul 2>&1
move "run_backend.py" "%ARCHIVE_ROOT%\legacy_backend\" >nul 2>&1
move "*.backup" "%ARCHIVE_ROOT%\legacy_backend\" >nul 2>&1
if exist "admin\" move "admin" "%ARCHIVE_ROOT%\legacy_backend\" >nul 2>&1
if exist "tracktion-hybrid\" move "tracktion-hybrid" "%ARCHIVE_ROOT%\legacy_backend\" >nul 2>&1

REM Archive Temp Files
echo [7/9] Archiving temporary files...
move "ai_generated_test.mid" "%ARCHIVE_ROOT%\temp_files\" >nul 2>&1
move "generated_peg_drums.mid" "%ARCHIVE_ROOT%\temp_files\" >nul 2>&1
move "commit_message.txt" "%ARCHIVE_ROOT%\temp_files\" >nul 2>&1
move "Saves" "%ARCHIVE_ROOT%\temp_files\" >nul 2>&1
move "DB" "%ARCHIVE_ROOT%\temp_files\" >nul 2>&1
move "automated_drummer_profile_builder.py" "%ARCHIVE_ROOT%\temp_files\" >nul 2>&1
move "backend_ai_endpoints.py" "%ARCHIVE_ROOT%\temp_files\" >nul 2>&1
move "complete_*.py" "%ARCHIVE_ROOT%\temp_files\" >nul 2>&1
move "create_*.py" "%ARCHIVE_ROOT%\temp_files\" >nul 2>&1
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
move "songmap_test.json" "%ARCHIVE_ROOT%\temp_files\" >nul 2>&1

REM Archive Docker files
echo [8/9] Archiving Docker files...
move "Dockerfile.backend" "%ARCHIVE_ROOT%\temp_files\" >nul 2>&1
move "Dockerfile.tracktion" "%ARCHIVE_ROOT%\temp_files\" >nul 2>&1
move "docker-compose.override.yml" "%ARCHIVE_ROOT%\temp_files\" >nul 2>&1

REM Clean empty directories
echo [9/9] Cleaning up...
if exist "validation_samples\" rmdir "validation_samples" 2>nul

REM Count remaining files
echo.
echo ================================================================================
echo CLEANUP COMPLETE!
echo ================================================================================
echo.
for /f %%A in ('dir /B /A-D ^| find /C /V ""') do echo Active files in root: %%A
echo Archive location: %ARCHIVE_ROOT%\
echo.
echo Cleanup finished successfully!

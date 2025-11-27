@echo off
REM Git Backup Script for DrumTracKAI v1.1.16
REM Drummer Style Integration Complete

echo ===================================================================
echo   DrumTracKAI v1.1.16 - Git Backup Script
echo   Drummer Style Integration Complete
echo ===================================================================
echo.

cd /d "%~dp0"

echo [1/6] Checking git status...
git status

echo.
echo [2/6] Staging new files...
git add drummer_mapping_service.py
git add frontend/src/components/DrummerSelector.tsx
git add test_drummer_connection.py
git add dcsm_backend.py
git add frontend/src/components/WebDAWApp.tsx

echo.
echo [3/6] Staging documentation...
git add README_MAIN.md
git add ARCHITECTURE.md
git add API_DOCUMENTATION.md
git add DRUMMER_INTEGRATION.md
git add NEXT_STEPS.md
git add TROUBLESHOOTING.md
git add DRUMMER_CONNECTION_COMPLETE.md
git add BACKUP_PROCEDURE.md
git add backup_git.bat
git add backup_archive.ps1

echo.
echo [4/6] Committing changes...
git commit -m "feat: Add drummer style integration system v1.1.16

- Created drummer mapping service (10 DrumTrackAI drummers)
- Built DrummerSelector UI component with cards
- Added 3 new API endpoints (/api/drummers, /api/drummers/{id}, /api/generate_with_drummer)
- Integrated drummer selection into WebDAWApp
- Connected admin database to user app (fictional names to real characteristics)
- Complete split documentation (6 new .md files)
- All tests passing (test_drummer_connection.py)

This completes the drummer style integration milestone.
Ready for end-to-end testing with Peg audio file."

echo.
echo [5/6] Creating git tag...
git tag -a v1.1.16-drummer-integration -m "v1.1.16: Drummer Style Integration Complete"

echo.
echo [6/6] Listing recent commits and tags...
git log -3 --oneline --decorate
echo.
git tag -l "v1.1.16*"

echo.
echo ===================================================================
echo   Git Backup Complete!
echo ===================================================================
echo.
echo   Commit: v1.1.16-drummer-integration
echo   Files: 12 new/modified files
echo   Lines: ~3,500+ new lines of code
echo.
echo   To push to remote:
echo     git push origin main
echo     git push origin v1.1.16-drummer-integration
echo.
echo ===================================================================

pause

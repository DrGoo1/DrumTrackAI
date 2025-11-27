@echo off
REM ============================================================================
REM Drum Builder v2.0 - Backend Testing Script
REM ============================================================================

echo.
echo ========================================
echo   Drum Builder v2.0 - Backend Tests
echo ========================================
echo.

REM Check if backend is running
echo [1/5] Checking if backend is running...
curl -s http://localhost:8000/ > nul 2>&1
if %ERRORLEVEL% EQU 0 (
    echo [OK] Backend is running on port 8000
) else (
    echo [ERROR] Backend is not running!
    echo.
    echo Please start the backend first:
    echo   python dcsm_backend.py
    echo.
    pause
    exit /b 1
)

echo.
echo [2/5] Testing health endpoint...
curl -s http://localhost:8000/ > test_health.json
if exist test_health.json (
    echo [OK] Health endpoint responded
    type test_health.json
    echo.
) else (
    echo [ERROR] No response from health endpoint
)

echo.
echo [3/5] Testing drum generation endpoint (template mode)...
curl -X POST http://localhost:8000/api/generate-drums ^
  -H "Content-Type: application/json" ^
  -d "{\"style\":\"rock\",\"drummer\":\"jeff_porcaro\",\"intensity\":0.7,\"variation\":0.8,\"humanize\":true,\"humanizeAmount\":0.7,\"ghostNoteAmount\":0.6,\"swingAmount\":0.2,\"generationMode\":\"template\",\"sectionId\":\"test\",\"startMeasure\":0,\"endMeasure\":4,\"tempos\":[120,120,120,120],\"timeSignature\":[4,4],\"fillLocations\":[3],\"fillType\":\"auto\",\"buildScope\":\"selected_section\"}" ^
  -o test_generation.json

if exist test_generation.json (
    echo [OK] Generation endpoint responded
    echo.
    echo Response saved to: test_generation.json
    echo Checking response structure...
    
    REM Use PowerShell to parse JSON and check key fields
    powershell -Command "$json = Get-Content test_generation.json | ConvertFrom-Json; Write-Host 'OK: ' $json.ok; Write-Host 'Has drum_track: ' ($json.drum_track -ne $null); if ($json.drum_track) { Write-Host 'Resolution PPQ: ' $json.drum_track.resolution_ppq; Write-Host 'Note count: ' $json.drum_track.notes.Count; Write-Host 'Has performance_spec: ' ($json.drum_track.performance_spec -ne $null) }; if ($json.metadata) { Write-Host 'Builder version: ' $json.metadata.builder_version }"
    
    echo.
) else (
    echo [ERROR] No response from generation endpoint
)

echo.
echo [4/5] Testing with v2.0 controls (high humanization)...
curl -X POST http://localhost:8000/api/generate-drums ^
  -H "Content-Type: application/json" ^
  -d "{\"style\":\"funk\",\"drummer\":\"bernard_purdie\",\"intensity\":0.8,\"variation\":0.9,\"humanize\":true,\"humanizeAmount\":0.9,\"ghostNoteAmount\":0.8,\"swingAmount\":0.5,\"generationMode\":\"ai_variation\",\"sectionId\":\"test2\",\"startMeasure\":0,\"endMeasure\":8,\"tempos\":[100,100,100,100,100,100,100,100],\"timeSignature\":[4,4],\"fillLocations\":[7],\"fillType\":\"tom_run\",\"buildScope\":\"selected_section\"}" ^
  -o test_generation_v2.json

if exist test_generation_v2.json (
    echo [OK] v2.0 controls test responded
    echo Response saved to: test_generation_v2.json
    echo.
) else (
    echo [ERROR] v2.0 controls test failed
)

echo.
echo [5/5] Checking for v2.0 features in response...
if exist test_generation.json (
    powershell -Command "$json = Get-Content test_generation.json | ConvertFrom-Json; if ($json.drum_track) { $note = $json.drum_track.notes[0]; Write-Host 'Sample note analysis:'; Write-Host '  - Has microTimingMs: ' ($note.microTimingMs -ne $null); Write-Host '  - Has instrumentId: ' ($note.instrumentId -ne $null); Write-Host '  - Has velocity: ' $note.velocity; Write-Host '  - Has barIndex: ' $note.barIndex; Write-Host '  - Has tickInBar: ' $note.tickInBar }"
    echo.
)

echo.
echo ========================================
echo   Backend Tests Complete!
echo ========================================
echo.
echo Test results saved:
echo   - test_health.json
echo   - test_generation.json
echo   - test_generation_v2.json
echo.
echo Review the JSON files to verify:
echo   1. resolution_ppq = 960
echo   2. notes have microTimingMs
echo   3. performance_spec present
echo   4. metadata.builder_version = "v2.0"
echo.

pause

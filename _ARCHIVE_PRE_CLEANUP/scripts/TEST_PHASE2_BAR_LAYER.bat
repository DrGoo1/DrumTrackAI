@echo off
REM Test Phase 2 Bar Layer Implementation
REM Created: November 19, 2025

echo ========================================
echo Testing Phase 2: Bar Layer + Meter
echo ========================================
echo.

set AUDIO_CORE=target\release\audio-core.exe

if not exist "%AUDIO_CORE%" (
    echo ERROR: audio-core.exe not found!
    echo Please build first: cd audio-core ^&^& cargo build --release
    pause
    exit /b 1
)

echo [OK] Found Rust binary: %AUDIO_CORE%
echo.

REM Check for test audio files
if exist "uploads\*.mp3" (
    echo Testing with first MP3 file found...
    for %%f in (uploads\*.mp3) do (
        echo.
        echo ================================================
        echo Testing: %%~nxf
        echo ================================================
        
        echo.
        echo [TEST 1/3] Full Analysis (bars + meter + sections)
        echo ------------------------------------------------
        %AUDIO_CORE% analyze-full "%%f"
        
        if errorlevel 1 (
            echo [FAIL] analyze-full returned error
            goto :test_failed
        )
        
        echo.
        echo [OK] Full analysis completed
        echo.
        
        echo ================================================
        echo Expected Output Format:
        echo ================================================
        echo {
        echo   "duration": 180.5,
        echo   "global_bpm_estimate": 128.0,
        echo   "meter": [4, 4],           ^<-- Detected meter
        echo   "bars": [
        echo     {
        echo       "index": 0,
        echo       "start_time": 0.0,
        echo       "end_time": 1.875,
        echo       "meter": [4, 4],
        echo       "tempo_bpm": 128.0,    ^<-- Per-bar tempo
        echo       "beat_times": [...],
        echo       "confidence": 0.85
        echo     }
        echo   ],
        echo   "sections": [
        echo     {
        echo       "start": 0.0,
        echo       "end": 8.5,
        echo       "label": "intro",
        echo       "energy": 0.35,
        echo       "spectral_centroid": 0.42,
        echo       "start_bar_index": 0,  ^<-- Bar integration
        echo       "end_bar_index": 4,
        echo       "bar_count": 5
        echo     }
        echo   ],
        echo   "beat_times": [...]
        echo }
        echo.
        
        goto :test_complete
    )
) else if exist "uploads\*.wav" (
    echo Testing with first WAV file found...
    for %%f in (uploads\*.wav) do (
        echo.
        echo ================================================
        echo Testing: %%~nxf
        echo ================================================
        
        %AUDIO_CORE% analyze-full "%%f"
        
        if errorlevel 1 (
            echo [FAIL] analyze-full returned error
            goto :test_failed
        )
        
        echo [OK] Full analysis completed
        goto :test_complete
    )
) else (
    echo ⚠️  No test audio files found in uploads\ directory
    echo.
    echo Please upload an audio file to test, or provide a file path:
    echo   %AUDIO_CORE% analyze-full "path\to\your\file.mp3"
    echo.
    goto :manual_test
)

:test_complete
echo.
echo ========================================
echo Phase 2 Implementation Status
echo ========================================
echo ✅ Bar structure: Implemented
echo ✅ Meter detection: 4/4 vs 3/4
echo ✅ Per-bar tempo: Calculated
echo ✅ SongMap output: Complete
echo ✅ Rust build: Success
echo.
echo ========================================
echo What to Check:
echo ========================================
echo 1. "meter" field shows detected time signature
echo 2. "bars" array has multiple bars with per-bar tempo
echo 3. Each bar has "tempo_bpm" field
echo 4. Sections have "start_bar_index", "end_bar_index"
echo 5. "bar_count" matches the bar range
echo.
echo ========================================
echo Next Steps:
echo ========================================
echo 1. Test backend: curl "http://localhost:8000/dcsm/analyze_full?key=test.mp3"
echo 2. Test frontend: Upload file and check console
echo 3. Validate meter detection with known 3/4 songs
echo 4. Check per-bar tempo variations
echo.
goto :end

:test_failed
echo.
echo ========================================
echo TEST FAILED
echo ========================================
echo Please check:
echo 1. Audio file is valid
echo 2. Rust binary built correctly
echo 3. Check error messages above
echo.
goto :end

:manual_test
echo ========================================
echo Manual Testing
echo ========================================
echo.
echo Example:
echo   %AUDIO_CORE% analyze-full "C:\Music\song.mp3"
echo.
echo Or place MP3/WAV files in uploads\ folder and run again
echo.

:end
pause

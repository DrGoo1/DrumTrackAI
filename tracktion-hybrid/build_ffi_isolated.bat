@echo off
echo ================================================
echo Building Rust FFI Library in Isolation
echo ================================================
echo.

:: Navigate to FFI directory
cd /d "f:\DrumTracKAI_v1.1.11\tracktion-hybrid\rust\audio-core-ffi"

:: Set environment to avoid workspace conflicts
set CARGO_WORKSPACE_DIR=
set CARGO_TARGET_DIR=target

echo Building audio-core-ffi library...
echo Working directory: %CD%
echo.

:: Build with explicit target directory to avoid workspace
cargo build --release --target-dir target

if %errorlevel% equ 0 (
    echo.
    echo ✅ Build successful!
    echo Library location: %CD%\target\release\audio_core_ffi.dll
    
    if exist "target\release\audio_core_ffi.dll" (
        echo File size:
        dir target\release\audio_core_ffi.dll | findstr audio_core_ffi.dll
        echo.
        echo Testing the library...
        cd ..\..
        python quick_test_ffi.py
    ) else (
        echo ❌ Expected DLL not found
        echo Checking target directory...
        dir target\release\
    )
) else (
    echo.
    echo ❌ Build failed
    echo This might be due to workspace conflicts or missing dependencies
    echo.
    echo Troubleshooting steps:
    echo 1. Ensure you're in the correct directory
    echo 2. Check that Rust is properly installed
    echo 3. Try: cargo clean && cargo build --release
)

echo.
pause

@echo off
echo ========================================
echo Rebuilding Rust Audio Core
echo ========================================
echo.

echo Building audio-core with new parameters...
cd /d f:\DrumTracKAI_v1.1.16_Clean\audio-core

echo.
echo Running cargo build --release...
cargo build --release

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo ❌ Build failed! Check errors above.
    pause
    exit /b 1
)

echo.
echo ✅ Build successful!
echo.
echo Binary location:
echo f:\DrumTracKAI_v1.1.16_Clean\audio-core\target\release\audio-core.exe
echo.

echo Running tests...
cargo test

echo.
echo ========================================
echo Rust core rebuilt successfully!
echo ========================================
pause

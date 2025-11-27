@echo off
echo ================================================
echo DrumTracKAI Tracktion Hybrid Build Script v1.2
echo ================================================
echo.

:: Set working directory
cd /d "f:\DrumTracKAI_v1.1.11\tracktion-hybrid"

:: Check if Rust is installed
where cargo >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Rust/Cargo not found. Please install Rust from https://rustup.rs/
    pause
    exit /b 1
)

echo Building Rust FFI library...
cd rust\audio-core-ffi
cargo build --release
if %errorlevel% neq 0 (
    echo ERROR: Rust FFI build failed
    cd ..\..
    pause
    exit /b 1
)

echo Rust FFI library built successfully
cd ..\..

:: Check if CMake is available
where cmake >nul 2>&1
if %errorlevel% neq 0 (
    echo WARNING: CMake not found. Please install CMake for C++ build
    echo You can still use the Rust FFI library with existing JUCE/Tracktion projects
    echo.
    echo Rust FFI library location:
    echo %CD%\rust\audio-core-ffi\target\release\audio_core_ffi.dll
    pause
    exit /b 0
)

:: Create build directory
if not exist "build" mkdir build
cd build

echo Configuring CMake build...
cmake .. -G "Visual Studio 17 2022" -A x64
if %errorlevel% neq 0 (
    echo WARNING: CMake configuration failed
    echo This might be due to missing JUCE or Tracktion Engine dependencies
    echo You can still use the Rust FFI library manually
    cd ..
    pause
    exit /b 0
)

echo Building C++ application...
cmake --build . --config Release
if %errorlevel% neq 0 (
    echo WARNING: C++ build failed
    echo The Rust FFI library is still available for manual integration
    cd ..
    pause
    exit /b 0
)

cd ..

echo.
echo ================================================
echo Build Complete!
echo ================================================
echo.
echo Rust FFI Library: rust\audio-core-ffi\target\release\audio_core_ffi.dll
echo C++ Application: build\Release\TracktionHybrid.exe (if successful)
echo.
echo Integration Instructions:
echo 1. Copy audio_core_ffi.dll next to your Tracktion application
echo 2. Include the C++ headers from cpp\ directory
echo 3. Use DCSMOrchestrator to process audio files
echo.
echo Example usage:
echo   DCSMOrchestrator orch("MyApp");
echo   orch.loadRust(File("audio_core_ffi.dll"));
echo   orch.processFile(File("audio.wav"), "rock");
echo.
pause

@echo off
echo ================================================
echo Rust Installation Script for Tracktion Hybrid
echo ================================================
echo.

:: Check if Rust is already installed
where cargo >nul 2>&1
if %errorlevel% equ 0 (
    echo Rust is already installed!
    cargo --version
    rustc --version
    echo.
    echo Proceeding to build FFI library...
    goto :build_ffi
)

echo Rust not found. Installing Rust via rustup...
echo.

:: Download and run rustup installer
echo Downloading rustup-init.exe...
powershell -Command "Invoke-WebRequest -Uri 'https://win.rustup.rs/x86_64' -OutFile 'rustup-init.exe'"

if not exist "rustup-init.exe" (
    echo ERROR: Failed to download rustup installer
    echo Please manually download from: https://rustup.rs/
    pause
    exit /b 1
)

echo Running rustup installer...
echo Please follow the prompts and accept the default installation.
rustup-init.exe

:: Clean up installer
del rustup-init.exe

:: Refresh environment variables
echo Refreshing environment variables...
call refreshenv.cmd >nul 2>&1

:: Check if installation was successful
where cargo >nul 2>&1
if %errorlevel% neq 0 (
    echo.
    echo Installation may have completed, but cargo is not in PATH.
    echo Please restart your command prompt and run this script again.
    echo Or manually add Rust to your PATH:
    echo   %USERPROFILE%\.cargo\bin
    pause
    exit /b 1
)

echo.
echo Rust installation successful!
cargo --version
rustc --version

:build_ffi
echo.
echo ================================================
echo Building Rust FFI Library
echo ================================================
echo.

cd rust\audio-core-ffi

echo Building audio-core-ffi in release mode...
cargo build --release

if %errorlevel% neq 0 (
    echo.
    echo ERROR: FFI library build failed
    echo This might be due to missing Visual Studio Build Tools
    echo Please install Visual Studio 2022 with C++ workload
    pause
    exit /b 1
)

echo.
echo ================================================
echo Build Complete!
echo ================================================
echo.

if exist "target\release\audio_core_ffi.dll" (
    echo FFI Library: %CD%\target\release\audio_core_ffi.dll
    echo File size: 
    dir target\release\audio_core_ffi.dll | findstr audio_core_ffi.dll
    echo.
    echo The Rust FFI library is ready for integration!
    echo Copy audio_core_ffi.dll next to your JUCE/Tracktion application.
) else (
    echo WARNING: Expected DLL not found at target\release\audio_core_ffi.dll
    echo Check the build output above for errors.
)

echo.
echo Next steps:
echo 1. Copy the DLL to your application directory
echo 2. Include the C++ headers from cpp\ directory  
echo 3. Use DCSMOrchestrator to process audio files
echo.
echo Example integration:
echo   DCSMOrchestrator orch("MyApp");
echo   orch.loadRust(File("audio_core_ffi.dll"));
echo   orch.processFile(File("audio.wav"), "rock");
echo.
pause

@echo off
echo ================================================
echo DrumTracKAI Complete Environment Setup
echo Installing Rust + Visual Studio Build Tools
echo ================================================
echo.

:: Check if running as administrator
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo This script requires administrator privileges for some installations.
    echo Please run as administrator or install manually.
    echo.
)

:: Step 1: Install Chocolatey (package manager)
echo Installing Chocolatey package manager...
powershell -NoProfile -InputFormat None -ExecutionPolicy Bypass -Command "iex ((New-Object System.Net.WebClient).DownloadString('https://chocolatey.org/install.ps1'))"

:: Refresh environment
call refreshenv.cmd >nul 2>&1

:: Step 2: Install Rust via Chocolatey
echo.
echo Installing Rust toolchain...
choco install rust -y

:: Step 3: Install Visual Studio Build Tools
echo.
echo Installing Visual Studio Build Tools 2022...
choco install visualstudio2022buildtools --package-parameters "--add Microsoft.VisualStudio.Workload.VCTools --includeRecommended" -y

:: Step 4: Install CMake
echo.
echo Installing CMake...
choco install cmake -y

:: Step 5: Install Git (if needed)
echo.
echo Installing Git...
choco install git -y

:: Refresh environment variables
echo.
echo Refreshing environment variables...
call refreshenv.cmd >nul 2>&1

:: Verify installations
echo.
echo ================================================
echo Verifying Installations
echo ================================================

echo Checking Rust...
rustc --version
cargo --version

echo.
echo Checking CMake...
cmake --version

echo.
echo Checking Visual Studio Build Tools...
where cl.exe >nul 2>&1
if %errorlevel% equ 0 (
    echo Visual Studio Build Tools: Found
) else (
    echo Visual Studio Build Tools: Not found in PATH
    echo You may need to run from Developer Command Prompt
)

echo.
echo ================================================
echo Building Rust FFI Library
echo ================================================

cd rust\audio-core-ffi
echo Building audio-core-ffi...
cargo build --release

if %errorlevel% equ 0 (
    echo.
    echo ✅ Rust FFI library built successfully!
    echo Location: %CD%\target\release\audio_core_ffi.dll
    
    :: Test the library
    echo.
    echo Testing FFI library...
    cd ..\..
    python quick_test_ffi.py
    
) else (
    echo.
    echo ❌ Rust FFI build failed
    echo This might require manual Visual Studio setup
)

echo.
echo ================================================
echo Setup Complete
echo ================================================
echo.
echo Next steps:
echo 1. Restart your command prompt to ensure all PATH changes take effect
echo 2. Run: python quick_test_ffi.py (to test FFI library)
echo 3. Run: build_hybrid.bat (to build complete C++ application)
echo.
echo If builds fail, you may need to:
echo - Run from "Developer Command Prompt for VS 2022"
echo - Manually install Visual Studio 2022 Community with C++ workload
echo.
pause

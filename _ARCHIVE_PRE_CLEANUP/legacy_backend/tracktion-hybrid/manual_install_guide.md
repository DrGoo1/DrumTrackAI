# Manual Installation Guide - DrumTracKAI Tracktion Hybrid

Since automated installation may require administrator privileges, here's a manual step-by-step guide:

## Step 1: Install Rust (Required)

### Option A: Direct Download
1. Go to: https://rustup.rs/
2. Download `rustup-init.exe`
3. Run the installer
4. Choose default installation (press Enter)
5. Restart your command prompt

### Option B: Using Package Manager
```cmd
# If you have Chocolatey:
choco install rust

# If you have Scoop:
scoop install rust
```

## Step 2: Verify Rust Installation
```cmd
rustc --version
cargo --version
```

## Step 3: Build the FFI Library
```cmd
cd f:\DrumTracKAI_v1.1.11\tracktion-hybrid\rust\audio-core-ffi
cargo build --release
```

This creates: `target\release\audio_core_ffi.dll`

## Step 4: Test the FFI Library
```cmd
cd f:\DrumTracKAI_v1.1.11\tracktion-hybrid
python quick_test_ffi.py
```

## Step 5: Install C++ Build Tools (Optional)

For the complete JUCE application:

### Option A: Visual Studio Community 2022
1. Download from: https://visualstudio.microsoft.com/downloads/
2. Install with "Desktop development with C++" workload
3. Include CMake tools

### Option B: Build Tools Only
1. Download "Build Tools for Visual Studio 2022"
2. Install with C++ build tools
3. Install CMake separately

## Step 6: Build Complete Application (Optional)
```cmd
cd f:\DrumTracKAI_v1.1.11\tracktion-hybrid
mkdir build
cd build
cmake .. -G "Visual Studio 17 2022" -A x64
cmake --build . --config Release
```

## Minimum Requirements

**For FFI Library Only:**
- Rust toolchain (rustc + cargo)
- Windows 10/11

**For Complete Application:**
- Above + Visual Studio Build Tools
- CMake 3.22+
- JUCE framework (if not using provided)

## Troubleshooting

### "cargo: command not found"
- Restart command prompt after Rust installation
- Check PATH includes: `%USERPROFILE%\.cargo\bin`

### "MSVC linker not found"
- Install Visual Studio Build Tools with C++ workload
- Or run from "Developer Command Prompt for VS 2022"

### CMake errors
- Ensure CMake is in PATH
- Install Visual Studio with CMake tools
- Or download CMake separately from cmake.org

## Quick Verification

After Rust installation:
```cmd
cd f:\DrumTracKAI_v1.1.11\tracktion-hybrid\rust\audio-core-ffi
cargo build --release
cd ..\..
python quick_test_ffi.py
```

If this works, you have a functional FFI library ready for integration!

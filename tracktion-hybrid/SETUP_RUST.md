# Rust Setup for Tracktion Hybrid

The Tracktion Hybrid DCSM Adapter requires Rust to build the FFI library. Here's how to install and configure Rust on Windows:

## Install Rust

### Option 1: Using rustup (Recommended)
1. Download rustup from: https://rustup.rs/
2. Run the installer and follow the prompts
3. Restart your terminal/command prompt
4. Verify installation:
   ```cmd
   rustc --version
   cargo --version
   ```

### Option 2: Using Chocolatey
```cmd
choco install rust
```

### Option 3: Using Scoop
```cmd
scoop install rust
```

## Build the FFI Library

Once Rust is installed:

```cmd
cd f:\DrumTracKAI_v1.1.11\tracktion-hybrid\rust\audio-core-ffi
cargo build --release
```

This will create:
- `target/release/audio_core_ffi.dll` (Windows)
- `target/release/libaudio_core_ffi.dylib` (macOS)
- `target/release/libaudio_core_ffi.so` (Linux)

## Troubleshooting

### "cargo: command not found"
- Ensure Rust is in your PATH
- Restart your terminal
- Check installation: `where cargo`

### Build Errors
- Update Rust: `rustup update`
- Clean build: `cargo clean && cargo build --release`
- Check dependencies in Cargo.toml

### Missing Visual Studio Build Tools (Windows)
If you get linker errors, install:
- Visual Studio 2022 with C++ build tools
- Or Visual Studio Build Tools 2022

## Next Steps

After successful build:
1. Copy the FFI library next to your JUCE/Tracktion application
2. Use the C++ components from the `cpp/` directory
3. Follow the integration examples in README.md

## Performance Notes

The Rust FFI library provides:
- 5-7x faster audio processing than Python
- Native multi-threading with rayon
- Memory-safe audio decoding with symphonia
- Professional-grade spectral analysis

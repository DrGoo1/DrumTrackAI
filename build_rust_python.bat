@echo off
echo Building Rust audio-core with PyO3 Python bindings...

cd audio-core
if errorlevel 1 (
    echo Error: Could not change to audio-core directory
    exit /b 1
)

echo Installing maturin for Python extension building...
pip install maturin

echo Building Python extension with maturin...
maturin develop --features python
if errorlevel 1 (
    echo Error: maturin build failed
    cd ..
    exit /b 1
)

cd ..
echo.
echo PyO3 audio-core Python extension built successfully!
echo You can now use AUDIO_CORE_MODE=pyo3 for in-process Rust calls.
echo.
echo Testing PyO3 integration...
python -c "try: import audio_core; print('✓ PyO3 audio_core module imported successfully'); except Exception as e: print('✗ Import failed:', e)"

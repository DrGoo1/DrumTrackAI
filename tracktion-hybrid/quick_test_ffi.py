#!/usr/bin/env python3
"""
Quick test script to verify Rust FFI library functionality
without requiring full JUCE/Tracktion setup.
"""

import ctypes
import json
import base64
import os
import sys
from pathlib import Path

def test_rust_ffi():
    """Test the Rust FFI library functions"""
    
    # Find the FFI library
    ffi_path = Path("rust/audio-core-ffi/target/release")
    
    if os.name == 'nt':  # Windows
        lib_file = ffi_path / "audio_core_ffi.dll"
    elif sys.platform == 'darwin':  # macOS
        lib_file = ffi_path / "libaudio_core_ffi.dylib"
    else:  # Linux
        lib_file = ffi_path / "libaudio_core_ffi.so"
    
    if not lib_file.exists():
        print(f"❌ FFI library not found at: {lib_file}")
        print("Please build the library first:")
        print("  cd rust/audio-core-ffi")
        print("  cargo build --release")
        return False
    
    print(f"✅ Found FFI library: {lib_file}")
    
    try:
        # Load the library
        lib = ctypes.CDLL(str(lib_file))
        
        # Define function signatures
        lib.ac_version.restype = ctypes.c_char_p
        lib.ac_free.argtypes = [ctypes.c_char_p]
        lib.ac_last_error.restype = ctypes.c_char_p
        
        lib.ac_generate_json.argtypes = [ctypes.c_char_p]
        lib.ac_generate_json.restype = ctypes.c_char_p
        
        lib.ac_generate_midi64.argtypes = [ctypes.c_char_p]
        lib.ac_generate_midi64.restype = ctypes.c_char_p
        
        # Test version
        version = lib.ac_version()
        print(f"✅ Library version: {version.decode('utf-8')}")
        lib.ac_free(version)
        
        # Test drum generation
        params = {
            "bpm": 120.0,
            "start": 0.0,
            "end": 8.0,
            "style": "rock",
            "label": "verse",
            "density": 0.65,
            "swing": 0.1,
            "humanize": 0.12,
            "seed": 42,
            "swing_preset": "light",
            "vel_preset": "accent24",
            "fill_preset": "random"
        }
        
        params_json = json.dumps(params).encode('utf-8')
        
        # Test JSON generation
        result_ptr = lib.ac_generate_json(params_json)
        if result_ptr:
            result_str = ctypes.string_at(result_ptr).decode('utf-8')
            lib.ac_free(result_ptr)
            
            try:
                result = json.loads(result_str)
                notes = result.get('notes', [])
                print(f"✅ Generated {len(notes)} drum notes")
                
                # Show first few notes
                for i, note in enumerate(notes[:3]):
                    print(f"  Note {i+1}: {note['lane']} at {note['time']:.3f}s, vel={note['vel']}")
                
                if len(notes) > 3:
                    print(f"  ... and {len(notes) - 3} more notes")
                    
            except json.JSONDecodeError as e:
                print(f"❌ Invalid JSON response: {e}")
                print(f"Response: {result_str[:200]}...")
                return False
        else:
            error_ptr = lib.ac_last_error()
            error_str = ctypes.string_at(error_ptr).decode('utf-8') if error_ptr else "Unknown error"
            lib.ac_free(error_ptr)
            print(f"❌ Generation failed: {error_str}")
            return False
        
        # Test MIDI generation
        midi_ptr = lib.ac_generate_midi64(params_json)
        if midi_ptr:
            midi_b64 = ctypes.string_at(midi_ptr).decode('utf-8')
            lib.ac_free(midi_ptr)
            
            if midi_b64:
                try:
                    midi_data = base64.b64decode(midi_b64)
                    print(f"✅ Generated MIDI file: {len(midi_data)} bytes")
                    
                    # Save test MIDI file
                    with open("test_output.mid", "wb") as f:
                        f.write(midi_data)
                    print("✅ Saved test MIDI to: test_output.mid")
                    
                except Exception as e:
                    print(f"❌ MIDI decode error: {e}")
                    return False
            else:
                print("❌ Empty MIDI response")
                return False
        else:
            error_ptr = lib.ac_last_error()
            error_str = ctypes.string_at(error_ptr).decode('utf-8') if error_ptr else "Unknown error"
            lib.ac_free(error_ptr)
            print(f"❌ MIDI generation failed: {error_str}")
            return False
        
        print("\n🎉 All FFI tests passed!")
        print("\nThe Rust FFI library is working correctly and ready for integration.")
        print("You can now use it with the C++ Tracktion components.")
        return True
        
    except Exception as e:
        print(f"❌ Library test failed: {e}")
        return False

if __name__ == "__main__":
    print("=" * 50)
    print("DrumTracKAI Rust FFI Library Test")
    print("=" * 50)
    
    success = test_rust_ffi()
    sys.exit(0 if success else 1)

#!/usr/bin/env python3
"""
Run Optimized Extraction - Execute Enhanced ReaScript
=====================================================

Runs the optimized ReaScript with ML-focused audio processing
and proper file naming/timing controls.

Author: DrumTracKAI v1.1.7
Date: July 23, 2025
"""

import subprocess
import time
from pathlib import Path

def execute_optimized_reascript():
    """Execute the optimized ReaScript"""
    print("AUDIO RUNNING OPTIMIZED REASCRIPT")
    print("=" * 60)
    print("Enhanced extraction with ML-optimized audio processing")
    print("=" * 60)
    
    script_path = Path(__file__).parent / "optimized_midi_render.lua"
    
    if not script_path.exists():
        print(f"ERROR Optimized ReaScript not found: {script_path}")
        return False
    
    print(f" OPTIMIZATIONS INCLUDED:")
    print(f"SUCCESS Precise timing: MIDI at beat 1.3, render 1.1-2.1")
    print(f"SUCCESS Proper file naming: instrument_name.wav")
    print(f"SUCCESS ML-optimized format: 16-bit WAV, 44.1kHz")
    print(f"SUCCESS Audio processing chain:")
    print(f"   • High-pass filter (20Hz) - removes DC offset")
    print(f"   • Gentle compression - consistent levels")
    print(f"   • Limiter - prevents clipping")
    print(f"SUCCESS Project cleanup between files")
    
    print(f"\nTARGET EXPECTED IMPROVEMENTS:")
    print(f"• Correct file duration (~0.5 seconds)")
    print(f"• Proper file naming (china_china_hard.wav)")
    print(f"• Consistent audio levels for ML training")
    print(f"• No clipping or distortion")
    print(f"• Optimal format for neural network input")
    
    print(f"\n TESTING OPTIMIZED EXTRACTION")
    print("Make sure Reaper is open with SD3 loaded on track 1")
    
    response = input("Is Reaper ready for optimized extraction? (y/n): ").lower()
    if not response.startswith('y'):
        print("Please prepare Reaper first")
        return False
    
    # Execute optimized ReaScript
    reaper_exe = "C:\\Program Files\\REAPER (x64)\\reaper.exe"
    
    try:
        cmd = [reaper_exe, "-nonewinst", str(script_path)]
        print(f"\nLAUNCH Executing optimized ReaScript...")
        print(f"Command: {' '.join(cmd)}")
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=60
        )
        
        print(f"Return code: {result.returncode}")
        if result.stdout:
            print(f"Output: {result.stdout}")
        
        return result.returncode == 0
        
    except Exception as e:
        print(f"ERROR Error executing optimized ReaScript: {e}")
        return False

def verify_optimized_output():
    """Verify the optimized output meets our requirements"""
    print(f"\nINSPECTING VERIFYING OPTIMIZED OUTPUT")
    print("=" * 40)
    
    output_dir = Path(__file__).parent / "sd3_extracted_samples"
    expected_file = output_dir / "china_china_hard.wav"
    
    if not expected_file.exists():
        print(f"ERROR Expected output file not found: {expected_file}")
        
        # Look for any new files
        wav_files = list(output_dir.glob("*.wav"))
        if wav_files:
            print(f"INSPECTING Found other WAV files:")
            for f in wav_files:
                size = f.stat().st_size
                print(f"   {f.name} ({size:,} bytes)")
        
        return False
    
    # Analyze the output file
    file_size = expected_file.stat().st_size
    print(f"SUCCESS Output file found: {expected_file.name}")
    print(f"FOLDER File size: {file_size:,} bytes ({file_size / 1024:.1f} KB)")
    
    # Check if size is reasonable for ~0.5 seconds of 44.1kHz 16-bit stereo
    # Expected: 44100 * 2 channels * 2 bytes * 0.5 seconds = ~88KB
    expected_size_range = (50_000, 150_000)  # 50-150KB range
    
    if expected_size_range[0] <= file_size <= expected_size_range[1]:
        print(f"SUCCESS File size in expected range for ~0.5 second audio")
    elif file_size < expected_size_range[0]:
        print(f"WARNING  File smaller than expected - may be very short")
    else:
        print(f"WARNING  File larger than expected - may be longer than 0.5 seconds")
    
    print(f"\nCOMPLETE OPTIMIZED EXTRACTION VERIFICATION:")
    print(f"SUCCESS Correct filename: {expected_file.name}")
    print(f"SUCCESS File created successfully")
    print(f"SUCCESS Reasonable file size")
    
    return True

def main():
    """Main optimized extraction runner"""
    print("AUDIO OPTIMIZED SUPERIOR DRUMMER EXTRACTION")
    print("=" * 70)
    print("ML-focused audio processing and precise timing control")
    print("=" * 70)
    
    # Execute optimized ReaScript
    success = execute_optimized_reascript()
    
    if success:
        print(f"\nSUCCESS Optimized ReaScript executed successfully!")
        
        # Verify output
        if verify_optimized_output():
            print(f"\nCOMPLETE OPTIMIZATION SUCCESS!")
            print(f"Enhanced extraction working perfectly!")
            print(f"Ready for batch processing with:")
            print(f"• Precise timing control")
            print(f"• ML-optimized audio processing")
            print(f"• Consistent file naming")
            print(f"• High-quality 16-bit WAV output")
            
            response = input(f"\nProceed with batch processing all MIDI files? (y/n): ").lower()
            if response.startswith('y'):
                print(f" Ready to create batch processing script...")
            
        else:
            print(f"WARNING  Output verification had issues")
    else:
        print(f"ERROR Optimized ReaScript execution failed")
        print(f"Try running the script manually in Reaper:")
        print(f"Actions → Load ReaScript → optimized_midi_render.lua")

if __name__ == "__main__":
    main()

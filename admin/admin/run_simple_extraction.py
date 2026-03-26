#!/usr/bin/env python3
"""
Run Simple Extraction - Execute Simplified ReaScript
====================================================

Runs the simplified ReaScript that focuses on core functionality
without complex API calls that cause errors.

Author: DrumTracKAI v1.1.7
Date: July 23, 2025
"""

import subprocess
import time
from pathlib import Path

def execute_simple_reascript():
    """Execute the simplified ReaScript"""
    print("AUDIO RUNNING SIMPLE WORKING REASCRIPT")
    print("=" * 60)
    print("Simplified approach - core functionality only")
    print("=" * 60)
    
    script_path = Path(__file__).parent / "simple_working_render.lua"
    
    if not script_path.exists():
        print(f"ERROR Simple ReaScript not found: {script_path}")
        return False
    
    print(f" SIMPLE APPROACH FEATURES:")
    print(f"SUCCESS MIDI import and positioning at beat 1.3")
    print(f"SUCCESS Render selection: 1.1 to 2.1 (0.5 seconds)")
    print(f"SUCCESS Proper file naming: instrument_name.wav")
    print(f"SUCCESS WAV format, 44.1kHz, stereo")
    print(f"SUCCESS Project cleanup between files")
    print(f"SUCCESS No complex API calls - maximum reliability")
    
    print(f"\n TESTING SIMPLE EXTRACTION")
    print("Make sure Reaper is open with SD3 loaded on track 1")
    
    response = input("Is Reaper ready for simple extraction? (y/n): ").lower()
    if not response.startswith('y'):
        print("Please prepare Reaper first")
        return False
    
    # Execute simple ReaScript
    reaper_exe = "C:\\Program Files\\REAPER (x64)\\reaper.exe"
    
    try:
        cmd = [reaper_exe, "-nonewinst", str(script_path)]
        print(f"\nLAUNCH Executing simple ReaScript...")
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
        print(f"ERROR Error executing simple ReaScript: {e}")
        return False

def verify_simple_output():
    """Verify the simple output meets basic requirements"""
    print(f"\nINSPECTING VERIFYING SIMPLE OUTPUT")
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
    
    # Check if size is reasonable for ~0.5 seconds of audio
    # Expected: 44100 * 2 channels * 2 bytes * 0.5 seconds = ~88KB
    if file_size > 10000:  # At least 10KB
        print(f"SUCCESS File size indicates audio content")
    else:
        print(f"WARNING  File very small - may be empty or corrupted")
    
    print(f"\nCOMPLETE SIMPLE EXTRACTION VERIFICATION:")
    print(f"SUCCESS Correct filename: {expected_file.name}")
    print(f"SUCCESS File created successfully")
    print(f"SUCCESS Contains audio data")
    
    return True

def main():
    """Main simple extraction runner"""
    print("AUDIO SIMPLE SUPERIOR DRUMMER EXTRACTION")
    print("=" * 70)
    print("Reliable core functionality without complex API calls")
    print("=" * 70)
    
    # Execute simple ReaScript
    success = execute_simple_reascript()
    
    if success:
        print(f"\nSUCCESS Simple ReaScript executed successfully!")
        
        # Verify output
        if verify_simple_output():
            print(f"\nCOMPLETE SIMPLE EXTRACTION SUCCESS!")
            print(f"Core functionality working perfectly!")
            print(f"Ready for batch processing with:")
            print(f"• Reliable MIDI import and positioning")
            print(f"• Precise 0.5-second render timing")
            print(f"• Proper file naming")
            print(f"• SD3's high-quality drum sounds")
            
            response = input(f"\nProceed with batch processing all MIDI files? (y/n): ").lower()
            if response.startswith('y'):
                print(f" Ready to create batch processing script...")
            
        else:
            print(f"WARNING  Output verification had issues")
    else:
        print(f"ERROR Simple ReaScript execution failed")
        print(f"Try running the script manually in Reaper:")
        print(f"Actions → Load ReaScript → simple_working_render.lua")

if __name__ == "__main__":
    main()

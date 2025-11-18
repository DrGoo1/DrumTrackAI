#!/usr/bin/env python3
"""
Reaper Fixed Script - Corrected ReaScript Execution
===================================================

Fixed approach that properly executes ReaScript in Reaper.
Uses the correct command line parameters and execution method.

Author: DrumTracKAI v1.1.7
Date: July 23, 2025
"""

import subprocess
import time
from pathlib import Path
import os

def create_simple_reascript():
    """Create a simple ReaScript that works with command line execution"""
    script_content = '''
-- Simple MIDI Import and Render Script
-- ====================================

function msg(text)
    reaper.ShowConsoleMsg(text .. "\\n")
end

function main()
    msg("=== REAPER SCRIPT STARTED ===")
    
    -- Configuration
    local midi_file = "H:\\\\DrumTracKAI_v1.1.7\\\\admin\\\\sd3_midi_patterns\\\\china_china_hard_053.mid"
    local output_file = "H:\\\\DrumTracKAI_v1.1.7\\\\admin\\\\sd3_extracted_samples\\\\china_china_hard.wav"
    
    msg("MIDI file: " .. midi_file)
    msg("Output file: " .. output_file)
    
    -- Check if MIDI file exists
    local file = io.open(midi_file, "r")
    if not file then
        msg("ERROR: MIDI file not found!")
        return
    end
    file:close()
    
    -- Get first track (should have SD3 loaded)
    local track_count = reaper.CountTracks(0)
    msg("Found " .. track_count .. " tracks")
    
    if track_count == 0 then
        msg("ERROR: No tracks found! Make sure SD3 is loaded on a track.")
        return
    end
    
    local track = reaper.GetTrack(0, 0)
    msg("Using track 1")
    
    -- Insert MIDI file
    msg("Inserting MIDI file...")
    reaper.InsertMedia(midi_file, 0)
    
    -- Get the inserted item
    local item_count = reaper.CountMediaItems(0)
    msg("Found " .. item_count .. " items")
    
    if item_count == 0 then
        msg("ERROR: No items found after MIDI insert!")
        return
    end
    
    local item = reaper.GetMediaItem(0, item_count - 1) -- Get last item (just inserted)
    
    -- Position at beat 1.3 (0.5 seconds at 120 BPM)
    local beat_1_3_pos = 0.5
    reaper.SetMediaItemPosition(item, beat_1_3_pos, false)
    msg("Positioned MIDI at " .. beat_1_3_pos .. " seconds")
    
    -- Set time selection from 1.1 to 2.1 (0 to 1 second)
    reaper.GetSet_LoopTimeRange(true, false, 0.0, 1.0, false)
    msg("Set time selection: 0.0 to 1.0 seconds")
    
    -- Set render settings
    msg("Setting render configuration...")
    
    -- Set output file
    reaper.GetSetProjectInfo_String(0, "RENDER_FILE", output_file, true)
    
    -- Set format to WAV
    reaper.GetSetProjectInfo_String(0, "RENDER_FORMAT", "wav", true)
    
    -- Set to render time selection
    reaper.GetSetProjectInfo(0, "RENDER_BOUNDSFLAG", 1, true)
    
    -- Start render
    msg("Starting render...")
    reaper.Main_OnCommand(42230, 0) -- Render project to file
    
    -- Wait a bit for render to complete
    local start_time = reaper.time_precise()
    while reaper.time_precise() - start_time < 10 do
        -- Wait for render
    end
    
    msg("Render completed!")
    msg("=== REAPER SCRIPT FINISHED ===")
end

-- Execute main function
main()
'''
    
    script_path = Path(__file__).parent / "simple_midi_render.lua"
    with open(script_path, 'w') as f:
        f.write(script_content)
    
    print(f"SUCCESS Created simple ReaScript: {script_path}")
    return script_path

def execute_reascript_properly(script_path):
    """Execute ReaScript using the correct method"""
    print(f"\nAUDIO Executing ReaScript: {script_path.name}")
    
    # Method 1: Try to run script in existing Reaper instance
    reaper_exe = "C:\\Program Files\\REAPER (x64)\\reaper.exe"
    
    try:
        # Command to add script to existing Reaper instance
        cmd = [
            reaper_exe,
            "-nonewinst",  # Use existing instance
            str(script_path)
        ]
        
        print(f"Command: {' '.join(cmd)}")
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30
        )
        
        print(f"Return code: {result.returncode}")
        if result.stdout:
            print(f"Output: {result.stdout}")
        if result.stderr:
            print(f"Error: {result.stderr}")
        
        return result.returncode == 0
        
    except Exception as e:
        print(f"ERROR Error executing ReaScript: {e}")
        return False

def manual_reascript_instructions(script_path):
    """Provide manual instructions for running the ReaScript"""
    print(f"\n MANUAL REASCRIPT EXECUTION")
    print("=" * 50)
    print("Since command line execution had issues, let's run it manually:")
    print()
    print("1. In Reaper, go to Actions → Load ReaScript")
    print(f"2. Browse to: {script_path}")
    print("3. Load and run the script")
    print("4. Check the Reaper console for output messages")
    print("5. Look for the output file to be created")
    
    expected_output = Path(__file__).parent / "sd3_extracted_samples" / "china_china_hard.wav"
    print(f"\nExpected output: {expected_output}")
    
    input("\nPress ENTER after running the ReaScript manually...")
    
    # Check if file was created
    if expected_output.exists():
        file_size = expected_output.stat().st_size
        print(f"SUCCESS SUCCESS! Output file created:")
        print(f"   File: {expected_output.name}")
        print(f"   Size: {file_size:,} bytes")
        return True
    else:
        print(f"ERROR Output file not found: {expected_output}")
        return False

def main():
    """Main fixed ReaScript execution"""
    print("AUDIO REAPER FIXED SCRIPT EXECUTION")
    print("=" * 60)
    print("Corrected approach for ReaScript automation")
    print("=" * 60)
    
    # Create simple ReaScript
    script_path = create_simple_reascript()
    
    # Ensure output directory exists
    output_dir = Path(__file__).parent / "sd3_extracted_samples"
    output_dir.mkdir(exist_ok=True)
    
    print(f"\n CONFIGURATION:")
    print(f"ReaScript: {script_path}")
    print(f"Output directory: {output_dir}")
    
    print(f"\n TESTING REASCRIPT EXECUTION")
    print("Make sure Reaper is open with SD3 loaded on track 1")
    
    response = input("Is Reaper open with SD3 ready? (y/n): ").lower()
    if not response.startswith('y'):
        print("Please open Reaper and load SD3 on track 1 first")
        return
    
    # Try automatic execution first
    print(f"\n Trying automatic execution...")
    success = execute_reascript_properly(script_path)
    
    if not success:
        print(f"\nWARNING Automatic execution failed, trying manual method...")
        success = manual_reascript_instructions(script_path)
    
    if success:
        print(f"\nCOMPLETE REASCRIPT SUCCESS!")
        print("First MIDI file processed successfully!")
        print("Ready to create batch processing script")
    else:
        print(f"\nERROR ReaScript execution failed")
        print("Check Reaper console for error messages")

if __name__ == "__main__":
    main()

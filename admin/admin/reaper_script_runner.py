#!/usr/bin/env python3
"""
Reaper Script Runner - Execute ReaScript for MIDI Processing
===========================================================

This Python script executes the ReaScript directly in Reaper for
reliable MIDI import, positioning, and rendering without UI automation.

Author: DrumTracKAI v1.1.7
Date: July 23, 2025
"""

import subprocess
import time
from pathlib import Path
import os

def find_reaper_executable():
    """Find Reaper executable"""
    common_paths = [
        "C:\\Program Files\\REAPER (x64)\\reaper.exe",
        "C:\\Program Files\\REAPER\\reaper.exe",
        "C:\\Program Files (x86)\\REAPER\\reaper.exe"
    ]
    
    for path in common_paths:
        if Path(path).exists():
            print(f"SUCCESS Found Reaper: {path}")
            return path
    
    print("ERROR Reaper executable not found!")
    return None

def execute_reascript(script_path, reaper_exe):
    """Execute ReaScript in Reaper"""
    print(f"\nAUDIO Executing ReaScript: {script_path.name}")
    
    try:
        # Command to run ReaScript
        cmd = [
            str(reaper_exe),
            "-nosplash",  # Skip splash screen
            "-new",       # New project
            "-script",    # Execute script
            str(script_path)
        ]
        
        print(f"Command: {' '.join(cmd)}")
        
        # Execute ReaScript
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=120  # 2 minute timeout
        )
        
        if result.returncode == 0:
            print("SUCCESS ReaScript executed successfully!")
            if result.stdout:
                print(f"Output: {result.stdout}")
            return True
        else:
            print(f"ERROR ReaScript failed with return code: {result.returncode}")
            if result.stderr:
                print(f"Error: {result.stderr}")
            return False
            
    except subprocess.TimeoutExpired:
        print("ERROR ReaScript execution timed out")
        return False
    except Exception as e:
        print(f"ERROR Error executing ReaScript: {e}")
        return False

def check_output_file(expected_output):
    """Check if output file was created"""
    print(f"\nFOLDER Checking for output file...")
    print(f"Expected: {expected_output}")
    
    # Wait a bit for file to be written
    for i in range(10):
        if expected_output.exists() and expected_output.stat().st_size > 0:
            file_size = expected_output.stat().st_size
            print(f"SUCCESS Output file created!")
            print(f"   File: {expected_output.name}")
            print(f"   Size: {file_size:,} bytes")
            return True
        
        print(f"   Waiting... {i+1}/10")
        time.sleep(2)
    
    print(f"ERROR Output file not created")
    return False

def batch_process_all_midi(script_path, reaper_exe):
    """Modify script for batch processing and execute"""
    print(f"\n BATCH PROCESSING ALL MIDI FILES")
    
    # Read the base script
    with open(script_path, 'r') as f:
        script_content = f.read()
    
    # Create batch version
    batch_script_content = script_content.replace(
        'msg("Ready for batch processing")',
        '''
        -- Batch process all MIDI files
        local function get_midi_files(dir)
            local files = {}
            local i = 0
            for file in io.popen('dir "' .. dir .. '*.mid" /b'):lines() do
                table.insert(files, file)
                i = i + 1
            end
            return files
        end
        
        msg("Starting batch processing...")
        local midi_files = get_midi_files(midi_dir)
        msg("Found " .. #midi_files .. " MIDI files")
        
        local success_count = 0
        for i, midi_file in ipairs(midi_files) do
            msg("\\nProcessing " .. i .. "/" .. #midi_files .. ": " .. midi_file)
            if process_single_midi_file(midi_file) then
                success_count = success_count + 1
            end
        end
        
        msg("\\nBatch complete: " .. success_count .. "/" .. #midi_files .. " files processed")
        '''
    )
    
    # Write batch script
    batch_script_path = script_path.parent / "reaper_batch_automation.lua"
    with open(batch_script_path, 'w') as f:
        f.write(batch_script_content)
    
    print(f"Created batch script: {batch_script_path}")
    
    # Execute batch script
    return execute_reascript(batch_script_path, reaper_exe)

def main():
    """Main ReaScript runner"""
    print("AUDIO REAPER SCRIPT RUNNER")
    print("=" * 60)
    print("Direct ReaScript execution for reliable automation")
    print("=" * 60)
    
    # Setup paths
    base_path = Path(__file__).parent
    script_path = base_path / "reaper_script_automation.lua"
    output_dir = base_path / "sd3_extracted_samples"
    
    # Check script exists
    if not script_path.exists():
        print(f"ERROR ReaScript not found: {script_path}")
        return
    
    # Find Reaper
    reaper_exe = find_reaper_executable()
    if not reaper_exe:
        return
    
    # Ensure output directory exists
    output_dir.mkdir(exist_ok=True)
    
    print(f"\n CONFIGURATION:")
    print(f"ReaScript: {script_path}")
    print(f"Reaper: {reaper_exe}")
    print(f"Output: {output_dir}")
    
    print(f"\n TESTING SINGLE FILE FIRST")
    input("Press ENTER to execute ReaScript...")
    
    # Execute single file test
    success = execute_reascript(script_path, reaper_exe)
    
    if success:
        # Check for output
        expected_output = output_dir / "china_china_hard.wav"
        if check_output_file(expected_output):
            print(f"\nCOMPLETE REASCRIPT SUCCESS!")
            print("Single file processing working correctly")
            
            response = input(f"\nProcess all MIDI files with batch script? (y/n): ").lower()
            if response.startswith('y'):
                print(f"\n Starting batch processing...")
                batch_success = batch_process_all_midi(script_path, reaper_exe)
                
                if batch_success:
                    print(f"\nCOMPLETE BATCH PROCESSING COMPLETE!")
                    
                    # Count output files
                    wav_files = list(output_dir.glob("*.wav"))
                    print(f"SUCCESS Created {len(wav_files)} WAV files")
                    
                    for wav_file in wav_files[:5]:  # Show first 5
                        size = wav_file.stat().st_size
                        print(f"   {wav_file.name} ({size:,} bytes)")
                    
                    if len(wav_files) > 5:
                        print(f"   ... and {len(wav_files) - 5} more files")
                else:
                    print(f"ERROR Batch processing failed")
        else:
            print(f"ERROR Single file test failed - no output created")
    else:
        print(f"ERROR ReaScript execution failed")
        print("Check Reaper console for error messages")

if __name__ == "__main__":
    main()

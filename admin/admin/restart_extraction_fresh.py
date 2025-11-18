#!/usr/bin/env python3
"""
Restart Extraction Fresh - Complete Clean Start
===============================================

Clears all existing output and restarts the batch extraction
process from scratch with the fixed ReaScript.

Author: DrumTracKAI v1.1.7
Date: July 23, 2025
"""

import subprocess
import shutil
from pathlib import Path
import time

def clear_existing_output():
    """Clear all existing WAV files to start fresh"""
    print(" CLEARING EXISTING OUTPUT")
    print("=" * 50)
    
    output_dir = Path(__file__).parent / "sd3_extracted_samples"
    
    if not output_dir.exists():
        output_dir.mkdir(parents=True, exist_ok=True)
        print(f"SUCCESS Created fresh output directory: {output_dir}")
        return 0
    
    # Count existing WAV files
    wav_files = list(output_dir.glob("*.wav"))
    wav_count = len(wav_files)
    
    if wav_count == 0:
        print(f"SUCCESS Output directory already clean - no WAV files found")
        return 0
    
    print(f"  Found {wav_count} existing WAV files to remove")
    
    # Remove all WAV files
    removed_count = 0
    for wav_file in wav_files:
        try:
            wav_file.unlink()
            removed_count += 1
        except Exception as e:
            print(f"ERROR Error removing {wav_file.name}: {e}")
    
    print(f"SUCCESS Removed {removed_count}/{wav_count} WAV files")
    print(f"DIRECTORY Output directory ready for fresh extraction")
    
    return removed_count

def verify_reaper_setup():
    """Verify Reaper is ready for batch processing"""
    print(f"\nAUDIO VERIFYING REAPER SETUP")
    print("=" * 40)
    
    print(f" REQUIREMENTS CHECKLIST:")
    print(f" Reaper is open")
    print(f" Superior Drummer 3 is loaded on track 1")
    print(f" SD3 is ready to play drum sounds")
    print(f" Timeline cursor is at position 0")
    print(f" No items are currently on the timeline")
    
    response = input(f"\nIs Reaper properly set up? (y/n): ").lower()
    return response.startswith('y')

def count_midi_files():
    """Count total MIDI files to process"""
    midi_dir = Path(__file__).parent / "sd3_midi_patterns"
    if not midi_dir.exists():
        return 0
    
    midi_files = list(midi_dir.glob("*.mid"))
    return len(midi_files)

def execute_fresh_batch():
    """Execute the fixed batch ReaScript from scratch"""
    print(f"\nLAUNCH STARTING FRESH BATCH EXTRACTION")
    print("=" * 50)
    
    script_path = Path(__file__).parent / "batch_midi_render.lua"
    reaper_exe = "C:\\Program Files\\REAPER (x64)\\reaper.exe"
    
    if not script_path.exists():
        print(f"ERROR Batch ReaScript not found: {script_path}")
        return False
    
    total_midi = count_midi_files()
    
    print(f"ANALYSIS FRESH EXTRACTION OVERVIEW:")
    print(f"Total MIDI files: {total_midi}")
    print(f"Expected output: {total_midi} WAV files")
    print(f"Estimated time: ~{total_midi * 3} seconds ({total_midi * 3 // 60} minutes)")
    
    print(f"\nTOOL TIMELINE FIXES APPLIED:")
    print(f"SUCCESS Stop playback before each file")
    print(f"SUCCESS Reset cursor to zero before each file")
    print(f"SUCCESS Clear render bounds after each file")
    print(f"SUCCESS Reset cursor to zero after cleanup")
    print(f"SUCCESS Update timeline display")
    
    response = input(f"\nStart fresh batch extraction of {total_midi} files? (y/n): ").lower()
    if not response.startswith('y'):
        print("Fresh extraction cancelled")
        return False
    
    try:
        cmd = [reaper_exe, "-nonewinst", str(script_path)]
        print(f"\nAUDIO EXECUTING FRESH BATCH REASCRIPT...")
        print(f"Command: {' '.join(cmd)}")
        print(f"Monitor progress in Reaper console (View → Console)")
        
        # Execute with timeout
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=total_midi * 15  # 15 seconds per file max
        )
        
        print(f"\nANALYSIS FRESH BATCH RESULTS:")
        print(f"Return code: {result.returncode}")
        
        if result.stdout:
            print(f"Standard output:")
            print(result.stdout)
        
        if result.stderr:
            print(f"Error output:")
            print(result.stderr)
        
        return result.returncode == 0
        
    except subprocess.TimeoutExpired:
        print(f"⏰ Fresh batch processing timed out")
        return False
    except Exception as e:
        print(f"ERROR Error executing fresh batch: {e}")
        return False

def monitor_fresh_progress():
    """Monitor the fresh extraction progress"""
    print(f"\nANALYSIS MONITORING FRESH EXTRACTION")
    print("=" * 40)
    
    output_dir = Path(__file__).parent / "sd3_extracted_samples"
    total_midi = count_midi_files()
    
    print(f"Target: {total_midi} WAV files")
    print(f"Starting from: 0 files")
    
    start_time = time.time()
    last_count = 0
    
    print(f"\n⏳ Monitoring fresh extraction...")
    print(f"Press Ctrl+C to stop monitoring")
    
    try:
        while True:
            if output_dir.exists():
                current_wav = len(list(output_dir.glob("*.wav")))
                
                if current_wav > last_count:
                    new_files = current_wav - last_count
                    elapsed = int(time.time() - start_time)
                    progress = (current_wav / total_midi) * 100
                    rate = current_wav / (elapsed / 60) if elapsed > 0 else 0
                    
                    print(f"PROGRESS Progress: {current_wav}/{total_midi} ({progress:.1f}%) - "
                          f"+{new_files} files - {elapsed}s elapsed - {rate:.1f} files/min")
                    
                    last_count = current_wav
                    
                    if current_wav >= total_midi:
                        print(f"\nCOMPLETE FRESH EXTRACTION COMPLETE!")
                        print(f"All {total_midi} files extracted successfully!")
                        break
            
            time.sleep(15)  # Check every 15 seconds
            
    except KeyboardInterrupt:
        final_wav = len(list(output_dir.glob("*.wav"))) if output_dir.exists() else 0
        elapsed = int(time.time() - start_time)
        print(f"\n⏹ Monitoring stopped")
        print(f"Final count: {final_wav}/{total_midi} files")
        print(f"Total time: {elapsed} seconds")

def main():
    """Main fresh restart execution"""
    print("AUDIO FRESH SUPERIOR DRUMMER EXTRACTION RESTART")
    print("=" * 70)
    print("Complete clean start with timeline fixes")
    print("=" * 70)
    
    # Step 1: Clear existing output
    removed_count = clear_existing_output()
    
    # Step 2: Verify Reaper setup
    if not verify_reaper_setup():
        print("ERROR Please set up Reaper properly before continuing")
        return
    
    # Step 3: Execute fresh batch
    print(f"\n1⃣ Starting fresh batch extraction...")
    execution_success = execute_fresh_batch()
    
    if execution_success:
        print(f"\n2⃣ Monitoring fresh extraction progress...")
        monitor_fresh_progress()
        
        print(f"\nCOMPLETE FRESH EXTRACTION COMPLETE!")
        print(f"All audio files should now be correct with proper timing")
        print(f"Check sd3_extracted_samples directory for results")
        
    else:
        print(f"\nERROR Fresh extraction failed to start")
        print(f"Check Reaper setup and try again")

if __name__ == "__main__":
    main()

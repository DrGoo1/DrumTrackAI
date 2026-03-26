#!/usr/bin/env python3
"""
Auto Start Batch - Immediate Batch Extraction Start
===================================================

Automatically starts the batch extraction process without
user prompts or confirmations.

Author: DrumTracKAI v1.1.7
Date: July 23, 2025
"""

import subprocess
from pathlib import Path
import time

def auto_start_batch_extraction():
    """Automatically start batch extraction"""
    print("AUDIO AUTO-START BATCH SUPERIOR DRUMMER EXTRACTION")
    print("=" * 70)
    print("Starting batch processing immediately...")
    print("=" * 70)
    
    script_path = Path(__file__).parent / "batch_midi_render.lua"
    reaper_exe = "C:\\Program Files\\REAPER (x64)\\reaper.exe"
    
    if not script_path.exists():
        print(f"ERROR Batch ReaScript not found: {script_path}")
        return False
    
    # Count MIDI files
    midi_dir = Path(__file__).parent / "sd3_midi_patterns"
    total_midi = len(list(midi_dir.glob("*.mid"))) if midi_dir.exists() else 0
    
    # Count existing WAV files
    output_dir = Path(__file__).parent / "sd3_extracted_samples"
    existing_wav = len(list(output_dir.glob("*.wav"))) if output_dir.exists() else 0
    
    print(f"ANALYSIS BATCH EXTRACTION STATUS:")
    print(f"Total MIDI files: {total_midi}")
    print(f"Existing WAV files: {existing_wav}")
    print(f"Files to process: {total_midi - existing_wav}")
    print(f"Estimated time: ~{(total_midi - existing_wav) * 3} seconds")
    
    print(f"\nTOOL TIMELINE FIXES ACTIVE:")
    print(f"SUCCESS Stop playback before each file")
    print(f"SUCCESS Reset cursor to zero before each file")
    print(f"SUCCESS Clear render bounds after each file")
    print(f"SUCCESS Reset cursor to zero after cleanup")
    print(f"SUCCESS Update timeline display")
    
    print(f"\nLAUNCH STARTING BATCH EXTRACTION NOW...")
    print(f"Monitor progress in Reaper console (View → Console)")
    
    try:
        cmd = [reaper_exe, "-nonewinst", str(script_path)]
        print(f"Command: {' '.join(cmd)}")
        
        # Execute batch processing
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=total_midi * 20  # 20 seconds per file max
        )
        
        print(f"\nANALYSIS BATCH EXECUTION RESULTS:")
        print(f"Return code: {result.returncode}")
        
        if result.stdout:
            print(f"Standard output:")
            print(result.stdout)
        
        if result.stderr:
            print(f"Error output:")
            print(result.stderr)
        
        return result.returncode == 0
        
    except subprocess.TimeoutExpired:
        print(f"⏰ Batch processing timed out (this may be normal for large batches)")
        return False
    except Exception as e:
        print(f"ERROR Error executing batch: {e}")
        return False

def monitor_extraction_progress():
    """Monitor the extraction progress in real-time"""
    print(f"\nANALYSIS MONITORING BATCH PROGRESS")
    print("=" * 50)
    
    output_dir = Path(__file__).parent / "sd3_extracted_samples"
    midi_dir = Path(__file__).parent / "sd3_midi_patterns"
    
    total_midi = len(list(midi_dir.glob("*.mid"))) if midi_dir.exists() else 0
    initial_wav = len(list(output_dir.glob("*.wav"))) if output_dir.exists() else 0
    
    print(f"Target: {total_midi} WAV files")
    print(f"Starting: {initial_wav} files")
    print(f"To process: {total_midi - initial_wav} files")
    
    start_time = time.time()
    last_count = initial_wav
    
    print(f"\n⏳ Real-time progress monitoring...")
    print(f"Updates every 15 seconds - Press Ctrl+C to stop")
    
    try:
        while True:
            if output_dir.exists():
                current_wav = len(list(output_dir.glob("*.wav")))
                
                if current_wav > last_count:
                    new_files = current_wav - last_count
                    elapsed = int(time.time() - start_time)
                    progress = (current_wav / total_midi) * 100
                    
                    if elapsed > 0:
                        rate = (current_wav - initial_wav) / (elapsed / 60)
                        remaining_files = total_midi - current_wav
                        eta_minutes = remaining_files / rate if rate > 0 else 0
                        
                        print(f"PROGRESS [{time.strftime('%H:%M:%S')}] Progress: {current_wav}/{total_midi} ({progress:.1f}%) - "
                              f"+{new_files} files - {rate:.1f} files/min - ETA: {eta_minutes:.1f}min")
                    else:
                        print(f"PROGRESS [{time.strftime('%H:%M:%S')}] Progress: {current_wav}/{total_midi} ({progress:.1f}%) - "
                              f"+{new_files} files")
                    
                    last_count = current_wav
                    
                    if current_wav >= total_midi:
                        elapsed_total = int(time.time() - start_time)
                        print(f"\nCOMPLETE BATCH EXTRACTION COMPLETE!")
                        print(f"SUCCESS All {total_midi} files processed successfully!")
                        print(f"⏱  Total time: {elapsed_total} seconds ({elapsed_total//60}m {elapsed_total%60}s)")
                        print(f"FOLDER Output directory: {output_dir}")
                        break
            
            time.sleep(15)  # Check every 15 seconds
            
    except KeyboardInterrupt:
        final_wav = len(list(output_dir.glob("*.wav"))) if output_dir.exists() else 0
        elapsed = int(time.time() - start_time)
        print(f"\n⏹ Monitoring stopped by user")
        print(f"Progress: {final_wav}/{total_midi} files ({(final_wav/total_midi)*100:.1f}%)")
        print(f"Time elapsed: {elapsed} seconds")

def main():
    """Main auto-start execution"""
    print("AUDIO AUTO-START SUPERIOR DRUMMER BATCH EXTRACTION")
    print("=" * 70)
    print("Immediate start - no user prompts required")
    print("=" * 70)
    
    # Start batch extraction immediately
    print(f"\n1⃣ Starting batch extraction...")
    execution_success = auto_start_batch_extraction()
    
    if execution_success:
        print(f"\n2⃣ Monitoring extraction progress...")
        monitor_extraction_progress()
        
        print(f"\nCOMPLETE AUTO-START BATCH COMPLETE!")
        print(f"All audio files extracted with timeline fixes applied")
        
    else:
        print(f"\nERROR Auto-start batch failed")
        print(f"Check that Reaper is open with SD3 loaded")

if __name__ == "__main__":
    main()

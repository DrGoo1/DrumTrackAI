#!/usr/bin/env python3
"""
Run Batch Extraction - Process All MIDI Files
==============================================

Executes the batch ReaScript to process all 579 MIDI files
and extract Superior Drummer samples for ML training.

Author: DrumTracKAI v1.1.7
Date: July 23, 2025
"""

import subprocess
import time
from pathlib import Path
import os

def count_midi_files():
    """Count total MIDI files to process"""
    midi_dir = Path(__file__).parent / "sd3_midi_patterns"
    if not midi_dir.exists():
        return 0
    
    midi_files = list(midi_dir.glob("*.mid"))
    return len(midi_files)

def count_existing_wav_files():
    """Count existing WAV files in output directory"""
    output_dir = Path(__file__).parent / "sd3_extracted_samples"
    if not output_dir.exists():
        return 0
    
    wav_files = list(output_dir.glob("*.wav"))
    return len(wav_files)

def execute_batch_reascript():
    """Execute the batch processing ReaScript"""
    print("AUDIO BATCH SUPERIOR DRUMMER EXTRACTION")
    print("=" * 70)
    
    script_path = Path(__file__).parent / "batch_midi_render.lua"
    reaper_exe = "C:\\Program Files\\REAPER (x64)\\reaper.exe"
    
    if not script_path.exists():
        print(f"ERROR Batch ReaScript not found: {script_path}")
        return False
    
    # Count files
    total_midi = count_midi_files()
    existing_wav = count_existing_wav_files()
    
    print(f"ANALYSIS BATCH PROCESSING OVERVIEW:")
    print(f"Total MIDI files: {total_midi}")
    print(f"Existing WAV files: {existing_wav}")
    print(f"Files to process: {total_midi - existing_wav}")
    
    if total_midi == 0:
        print(f"ERROR No MIDI files found in sd3_midi_patterns directory")
        return False
    
    print(f"\nTARGET BATCH FEATURES:")
    print(f"SUCCESS Processes ALL {total_midi} MIDI files automatically")
    print(f"SUCCESS Skips files that already exist (resume capability)")
    print(f"SUCCESS Real-time progress updates every 10 files")
    print(f"SUCCESS Detailed success/failure tracking")
    print(f"SUCCESS Estimated time remaining")
    print(f"SUCCESS Comprehensive final summary")
    
    print(f"\nWARNING  IMPORTANT REQUIREMENTS:")
    print(f"• Reaper must be open with SD3 loaded on track 1")
    print(f"• SD3 must be ready to play drum sounds")
    print(f"• Estimated time: ~{total_midi * 3} seconds ({total_midi * 3 // 60} minutes)")
    
    response = input(f"\nStart batch processing of {total_midi} MIDI files? (y/n): ").lower()
    if not response.startswith('y'):
        print("Batch processing cancelled")
        return False
    
    try:
        cmd = [reaper_exe, "-nonewinst", str(script_path)]
        print(f"\nLAUNCH STARTING BATCH PROCESSING...")
        print(f"Command: {' '.join(cmd)}")
        print(f"Monitor progress in Reaper's console (View → Console)")
        
        # Execute with extended timeout for batch processing
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=total_midi * 10  # 10 seconds per file max
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
        print(f"⏰ Batch processing timed out")
        print(f"This may be normal for large batches - check output directory")
        return False
    except Exception as e:
        print(f"ERROR Error executing batch ReaScript: {e}")
        return False

def monitor_batch_progress():
    """Monitor batch processing progress"""
    print(f"\nANALYSIS MONITORING BATCH PROGRESS")
    print("=" * 50)
    
    output_dir = Path(__file__).parent / "sd3_extracted_samples"
    total_midi = count_midi_files()
    initial_wav = count_existing_wav_files()
    
    print(f"Initial WAV files: {initial_wav}")
    print(f"Target total: {total_midi}")
    print(f"Files to create: {total_midi - initial_wav}")
    
    print(f"\n⏳ Monitoring for new files...")
    print(f"Press Ctrl+C to stop monitoring")
    
    start_time = time.time()
    last_count = initial_wav
    
    try:
        while True:
            current_wav = count_existing_wav_files()
            
            if current_wav > last_count:
                new_files = current_wav - last_count
                elapsed = int(time.time() - start_time)
                progress = (current_wav / total_midi) * 100
                
                print(f"PROGRESS Progress: {current_wav}/{total_midi} ({progress:.1f}%) - "
                      f"+{new_files} files in last check - {elapsed}s elapsed")
                
                last_count = current_wav
                
                if current_wav >= total_midi:
                    print(f"\nCOMPLETE BATCH PROCESSING COMPLETE!")
                    print(f"All {total_midi} files processed successfully!")
                    break
            
            time.sleep(10)  # Check every 10 seconds
            
    except KeyboardInterrupt:
        final_wav = count_existing_wav_files()
        elapsed = int(time.time() - start_time)
        print(f"\n⏹ Monitoring stopped by user")
        print(f"Final count: {final_wav}/{total_midi} files")
        print(f"Total time: {elapsed} seconds")

def analyze_batch_results():
    """Analyze the results of batch processing"""
    print(f"\nANALYSIS BATCH RESULTS ANALYSIS")
    print("=" * 40)
    
    total_midi = count_midi_files()
    total_wav = count_existing_wav_files()
    
    print(f"MIDI files found: {total_midi}")
    print(f"WAV files created: {total_wav}")
    print(f"Success rate: {(total_wav/total_midi)*100:.1f}%")
    
    if total_wav == total_midi:
        print(f"COMPLETE PERFECT SUCCESS! All files processed!")
    elif total_wav > total_midi * 0.9:
        print(f"SUCCESS EXCELLENT! {total_wav} files processed successfully")
    elif total_wav > total_midi * 0.5:
        print(f"WARNING  PARTIAL SUCCESS: {total_wav} files processed")
    else:
        print(f"ERROR LOW SUCCESS RATE: Only {total_wav} files processed")
    
    # Show file size analysis
    output_dir = Path(__file__).parent / "sd3_extracted_samples"
    if output_dir.exists():
        wav_files = list(output_dir.glob("*.wav"))
        if wav_files:
            total_size = sum(f.stat().st_size for f in wav_files if f.is_file())
            avg_size = total_size / len(wav_files)
            
            print(f"\nFile size analysis:")
            print(f"Total size: {total_size / (1024*1024):.1f} MB")
            print(f"Average size: {avg_size / 1024:.1f} KB per file")
            
            if avg_size > 50000:  # > 50KB
                print(f"SUCCESS File sizes indicate good audio content")
            else:
                print(f"WARNING  Small file sizes - check audio quality")

def main():
    """Main batch processing execution"""
    print("AUDIO SUPERIOR DRUMMER BATCH EXTRACTION")
    print("=" * 70)
    print("Automated processing of ALL MIDI files")
    print("=" * 70)
    
    # Execute batch processing
    print(f"\n1⃣ Starting batch ReaScript execution...")
    execution_success = execute_batch_reascript()
    
    if execution_success:
        print(f"\n2⃣ Monitoring batch progress...")
        monitor_batch_progress()
        
        print(f"\n3⃣ Analyzing batch results...")
        analyze_batch_results()
        
        print(f"\nCOMPLETE BATCH PROCESSING COMPLETE!")
        print(f"Check sd3_extracted_samples directory for all WAV files")
        print(f"Ready for ML training with DrumTracKAI!")
        
    else:
        print(f"\nERROR Batch processing failed to start")
        print(f"Check that Reaper is open with SD3 loaded")

if __name__ == "__main__":
    main()

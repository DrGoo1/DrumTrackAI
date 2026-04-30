#!/usr/bin/env python3
"""
Monitor Extraction - Automatic ReaScript Execution with Monitoring
==================================================================

Automatically executes the ReaScript and monitors the process in real-time
without requiring user input prompts.

Author: DrumTracKAI v1.1.7
Date: July 23, 2025
"""

import subprocess
import time
from pathlib import Path
import os

def monitor_reaper_console():
    """Monitor Reaper console output if possible"""
    print("INSPECTING MONITORING REAPER CONSOLE OUTPUT")
    print("=" * 50)
    print("Note: Console output will appear in Reaper's console window")
    print("Go to View → Console in Reaper to see ReaScript messages")

def execute_reascript_direct():
    """Execute ReaScript directly without user prompts"""
    print("AUDIO EXECUTING REASCRIPT DIRECTLY")
    print("=" * 50)
    
    script_path = Path(__file__).parent / "simple_working_render.lua"
    reaper_exe = "C:\\Program Files\\REAPER (x64)\\reaper.exe"
    
    if not script_path.exists():
        print(f"ERROR ReaScript not found: {script_path}")
        return False
    
    print(f" EXECUTION DETAILS:")
    print(f"ReaScript: {script_path}")
    print(f"Reaper: {reaper_exe}")
    print(f"Method: Direct execution in existing Reaper instance")
    
    try:
        cmd = [reaper_exe, "-nonewinst", str(script_path)]
        print(f"\nLAUNCH Executing ReaScript...")
        print(f"Command: {' '.join(cmd)}")
        
        # Execute and capture output
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=120  # 2 minute timeout
        )
        
        print(f"\nANALYSIS EXECUTION RESULTS:")
        print(f"Return code: {result.returncode}")
        
        if result.stdout:
            print(f"Standard output:")
            print(result.stdout)
        
        if result.stderr:
            print(f"Error output:")
            print(result.stderr)
        
        return result.returncode == 0
        
    except subprocess.TimeoutExpired:
        print("⏰ ReaScript execution timed out (2 minutes)")
        return False
    except Exception as e:
        print(f"ERROR Error executing ReaScript: {e}")
        return False

def monitor_output_directory():
    """Monitor the output directory for new files"""
    print(f"\nDIRECTORY MONITORING OUTPUT DIRECTORY")
    print("=" * 40)
    
    output_dir = Path(__file__).parent / "sd3_extracted_samples"
    
    print(f"Watching: {output_dir}")
    
    # Get initial state
    initial_files = set()
    if output_dir.exists():
        initial_files = set(f.name for f in output_dir.iterdir() if f.is_file())
    
    print(f"Initial files: {len(initial_files)}")
    for f in sorted(initial_files):
        print(f"  {f}")
    
    # Monitor for changes
    print(f"\n⏳ Monitoring for new files (60 second timeout)...")
    
    start_time = time.time()
    timeout = 60
    
    while time.time() - start_time < timeout:
        if output_dir.exists():
            current_files = set(f.name for f in output_dir.iterdir() if f.is_file())
            new_files = current_files - initial_files
            
            if new_files:
                print(f"\nCOMPLETE NEW FILES DETECTED:")
                for new_file in sorted(new_files):
                    file_path = output_dir / new_file
                    size = file_path.stat().st_size
                    print(f"  SUCCESS {new_file} ({size:,} bytes)")
                
                return list(new_files)
        
        # Show progress
        elapsed = int(time.time() - start_time)
        if elapsed % 10 == 0 and elapsed > 0:
            print(f"  Monitoring... {elapsed}s/{timeout}s")
        
        time.sleep(2)
    
    print(f"⏰ Monitoring timeout after {timeout} seconds")
    return []

def analyze_extraction_results():
    """Analyze the results of the extraction"""
    print(f"\nANALYSIS ANALYZING EXTRACTION RESULTS")
    print("=" * 40)
    
    output_dir = Path(__file__).parent / "sd3_extracted_samples"
    expected_file = output_dir / "china_china_hard.wav"
    
    if expected_file.exists() and expected_file.is_file():
        file_size = expected_file.stat().st_size
        print(f"SUCCESS SUCCESS: Expected file created!")
        print(f"   File: {expected_file.name}")
        print(f"   Size: {file_size:,} bytes ({file_size/1024:.1f} KB)")
        
        # Check if size indicates audio content
        if file_size > 50000:  # > 50KB suggests real audio
            print(f"   SUCCESS File size indicates substantial audio content")
        elif file_size > 1000:  # > 1KB but < 50KB
            print(f"   WARNING  Small file - may be short audio or header only")
        else:
            print(f"   ERROR Very small file - likely empty or corrupted")
        
        return True
    else:
        print(f"ERROR Expected file not found: {expected_file}")
        
        # Look for any WAV files
        if output_dir.exists():
            wav_files = list(output_dir.glob("*.wav"))
            if wav_files:
                print(f"INSPECTING Found other WAV files:")
                for f in wav_files:
                    if f.is_file():
                        size = f.stat().st_size
                        print(f"   {f.name} ({size:,} bytes)")
            else:
                print(f"ERROR No WAV files found in output directory")
        
        return False

def main():
    """Main monitoring and execution"""
    print("AUDIO AUTOMATED REASCRIPT MONITORING")
    print("=" * 70)
    print("Executing and monitoring ReaScript without user prompts")
    print("=" * 70)
    
    # Show monitoring instructions
    monitor_reaper_console()
    
    print(f"\nLAUNCH STARTING AUTOMATED EXECUTION")
    print("Make sure Reaper is open with SD3 loaded on track 1")
    
    # Execute ReaScript
    print(f"\n1⃣ Executing ReaScript...")
    execution_success = execute_reascript_direct()
    
    # Monitor output directory
    print(f"\n2⃣ Monitoring output directory...")
    new_files = monitor_output_directory()
    
    # Analyze results
    print(f"\n3⃣ Analyzing results...")
    analysis_success = analyze_extraction_results()
    
    # Final summary
    print(f"\n MONITORING SUMMARY")
    print("=" * 30)
    print(f"ReaScript execution: {'SUCCESS Success' if execution_success else 'ERROR Failed'}")
    print(f"New files detected: {len(new_files)}")
    print(f"Expected output: {'SUCCESS Found' if analysis_success else 'ERROR Missing'}")
    
    if execution_success and analysis_success:
        print(f"\nCOMPLETE EXTRACTION SUCCESSFUL!")
        print("Ready for batch processing all MIDI files")
    elif execution_success:
        print(f"\nWARNING  ReaScript ran but output verification failed")
        print("Check Reaper console for error messages")
    else:
        print(f"\nERROR ReaScript execution failed")
        print("Check Reaper is open with SD3 loaded")

if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Reaper Working Automation - Based on Verified Manual Workflow
============================================================

This automation replicates the exact manual steps that were verified to work:
1. Import MIDI via Insert → Media File
2. Position MIDI at beat 1.3
3. Set render selection from 1.1 to 2.1
4. Render audio output
5. Verify output file creation

Author: DrumTracKAI v1.1.7
Date: July 23, 2025
"""

import time
from pathlib import Path
import subprocess

try:
    import pyautogui
    import pygetwindow as gw
    pyautogui.FAILSAFE = True
    pyautogui.PAUSE = 1.0
    print("SUCCESS Automation libraries loaded")
except ImportError as e:
    print(f"ERROR Import error: {e}")
    exit(1)

def find_reaper_window():
    """Find and focus Reaper window"""
    print("INSPECTING Finding Reaper window...")
    
    windows = gw.getAllWindows()
    for window in windows:
        if 'REAPER' in window.title.upper():
            print(f"SUCCESS Found Reaper: '{window.title}'")
            try:
                window.activate()
                time.sleep(2)
                return True
            except:
                print("WARNING  Click on Reaper window to focus it")
                input("Press ENTER when Reaper is focused...")
                return True
    
    print("ERROR Reaper not found!")
    return False

def import_midi_file_working(midi_file_path):
    """Import MIDI using the working Insert → Media File method"""
    print(f"\n Importing MIDI: {midi_file_path.name}")
    
    try:
        # Step 1: Insert menu
        print("Opening Insert menu...")
        pyautogui.click(x=100, y=50)  # Approximate Insert menu location
        time.sleep(1)
        pyautogui.press('alt')  # Activate menu bar
        time.sleep(0.5)
        pyautogui.press('i')  # Insert menu
        time.sleep(1)
        
        # Step 2: Media File
        print("Selecting Media File...")
        pyautogui.press('m')  # Media File
        time.sleep(2)
        
        # Step 3: Navigate to file
        print(f"Navigating to file...")
        pyautogui.write(str(midi_file_path))
        time.sleep(2)
        pyautogui.press('enter')
        time.sleep(3)
        
        print("SUCCESS MIDI import completed")
        return True
        
    except Exception as e:
        print(f"ERROR Import failed: {e}")
        return False

def position_midi_at_1_3():
    """Position MIDI at beat 1.3 using working method"""
    print(f"\n⏱ Positioning MIDI at beat 1.3...")
    
    try:
        # Select all items
        pyautogui.hotkey('ctrl', 'a')
        time.sleep(1)
        
        # Go to start of project
        pyautogui.press('home')
        time.sleep(1)
        
        # Move cursor to beat 1.3 (using arrow keys)
        print("Moving cursor to beat 1.3...")
        for i in range(3):  # 3 quarter notes = beat 1.3
            pyautogui.press('right')
            time.sleep(0.3)
        
        # Move items to cursor
        print("Moving MIDI to cursor position...")
        pyautogui.hotkey('ctrl', 'shift', 'm')
        time.sleep(2)
        
        print("SUCCESS MIDI positioned at beat 1.3")
        return True
        
    except Exception as e:
        print(f"ERROR Positioning failed: {e}")
        return False

def set_render_selection_1_1_to_2_1():
    """Set render selection from 1.1 to 2.1 using working method"""
    print(f"\n Setting render selection: 1.1 to 2.1...")
    
    try:
        # Go to start (beat 1.1)
        pyautogui.press('home')
        time.sleep(1)
        
        # Set selection start
        pyautogui.press('enter')
        time.sleep(1)
        
        # Move to beat 2.1 (4 quarter notes)
        for i in range(4):
            pyautogui.press('right')
            time.sleep(0.3)
        
        # Set selection end
        pyautogui.hotkey('shift', 'enter')
        time.sleep(1)
        
        print("SUCCESS Render selection set: 1.1 to 2.1")
        return True
        
    except Exception as e:
        print(f"ERROR Selection failed: {e}")
        return False

def render_audio_working(output_filename, output_dir):
    """Render audio using working File → Render method"""
    print(f"\nAUDIO Rendering audio: {output_filename}.wav")
    
    try:
        # Open File menu → Render
        print("Opening File → Render...")
        pyautogui.press('alt')
        time.sleep(0.5)
        pyautogui.press('f')  # File menu
        time.sleep(1)
        pyautogui.press('r')  # Render
        time.sleep(3)
        
        # Set filename
        print(f"Setting filename: {output_filename}")
        pyautogui.press('tab', presses=3)  # Navigate to filename field
        time.sleep(1)
        pyautogui.hotkey('ctrl', 'a')
        time.sleep(0.5)
        pyautogui.write(output_filename)
        time.sleep(1)
        
        # Set output directory
        print(f"Setting output directory...")
        pyautogui.press('tab', presses=2)  # Navigate to directory field
        time.sleep(1)
        pyautogui.hotkey('ctrl', 'a')
        time.sleep(0.5)
        pyautogui.write(str(output_dir))
        time.sleep(1)
        
        # Start render
        print("Starting render...")
        pyautogui.press('enter')
        time.sleep(2)
        
        print("SUCCESS Render initiated")
        return True
        
    except Exception as e:
        print(f"ERROR Render failed: {e}")
        return False

def wait_for_output_file(output_file, timeout=60):
    """Wait for output file to be created"""
    print(f"\n⏳ Waiting for output file...")
    print(f"Expected: {output_file}")
    
    start_time = time.time()
    
    while time.time() - start_time < timeout:
        if output_file.exists() and output_file.stat().st_size > 0:
            time.sleep(2)  # Ensure file is fully written
            file_size = output_file.stat().st_size
            print(f"SUCCESS Output file created!")
            print(f"   File: {output_file.name}")
            print(f"   Size: {file_size:,} bytes")
            return True
        
        elapsed = int(time.time() - start_time)
        if elapsed % 10 == 0 and elapsed > 0:
            print(f"   Waiting... {elapsed}s/{timeout}s")
        
        time.sleep(2)
    
    print(f"ERROR Timeout waiting for output file")
    return False

def clear_timeline():
    """Clear timeline for next file"""
    print(f"\n Clearing timeline...")
    
    try:
        pyautogui.hotkey('ctrl', 'a')  # Select all
        time.sleep(1)
        pyautogui.press('delete')  # Delete
        time.sleep(1)
        pyautogui.hotkey('ctrl', 'alt', 'z')  # Clear time selection
        time.sleep(1)
        
        print("SUCCESS Timeline cleared")
        return True
        
    except Exception as e:
        print(f"ERROR Clear failed: {e}")
        return False

def process_single_file(midi_file):
    """Process single MIDI file with working automation"""
    print(f"\n{'='*70}")
    print(f"PROCESSING: {midi_file.name}")
    print(f"Using verified working workflow")
    print(f"{'='*70}")
    
    # Setup
    instrument_name = midi_file.stem.rsplit('_', 1)[0] if '_' in midi_file.stem else midi_file.stem
    output_dir = Path(__file__).parent / "sd3_extracted_samples"
    output_file = output_dir / f"{instrument_name}.wav"
    
    print(f"Instrument: {instrument_name}")
    print(f"Output: {output_file}")
    
    # Check if already exists
    if output_file.exists():
        print(f"SUCCESS Already processed: {output_file.name}")
        return True
    
    # Execute working workflow
    workflow_steps = [
        ("Import MIDI file", lambda: import_midi_file_working(midi_file)),
        ("Position at beat 1.3", position_midi_at_1_3),
        ("Set render selection 1.1-2.1", set_render_selection_1_1_to_2_1),
        ("Render audio", lambda: render_audio_working(instrument_name, output_dir)),
        ("Wait for output", lambda: wait_for_output_file(output_file)),
        ("Clear timeline", clear_timeline)
    ]
    
    for step_name, step_func in workflow_steps:
        print(f"\n--- {step_name} ---")
        if not step_func():
            print(f"ERROR FAILED at: {step_name}")
            return False
        time.sleep(1)
    
    print(f"COMPLETE SUCCESS: {midi_file.name} → {instrument_name}.wav")
    return True

def main():
    """Main automation based on working manual workflow"""
    print("AUDIO REAPER WORKING AUTOMATION")
    print("=" * 70)
    print("Based on verified manual workflow that works!")
    print("=" * 70)
    
    # Setup
    base_path = Path(__file__).parent
    midi_dir = base_path / "sd3_midi_patterns"
    output_dir = base_path / "sd3_extracted_samples"
    output_dir.mkdir(exist_ok=True)
    
    # Find Reaper
    if not find_reaper_window():
        return
    
    # Get MIDI files
    midi_files = list(midi_dir.glob("*.mid"))
    if not midi_files:
        print("ERROR No MIDI files found!")
        return
    
    print(f"\nFOLDER Found {len(midi_files)} MIDI files")
    test_file = midi_files[0]
    
    print(f"\n Testing with: {test_file.name}")
    input("Press ENTER to start working automation...")
    
    # Test single file
    success = process_single_file(test_file)
    
    if success:
        print(f"\nCOMPLETE WORKING AUTOMATION SUCCESSFUL!")
        print(f"Ready for batch processing!")
        
        response = input(f"\nProcess all {len(midi_files)} files? (y/n): ").lower()
        if response.startswith('y'):
            print(f"\n Starting batch processing...")
            success_count = 1  # Already did first file
            
            for midi_file in midi_files[1:]:
                print(f"\nProcessing {success_count + 1}/{len(midi_files)}: {midi_file.name}")
                if process_single_file(midi_file):
                    success_count += 1
                    print(f"Progress: {success_count}/{len(midi_files)}")
                else:
                    print(f"Failed: {midi_file.name}")
                    response = input("Continue? (y/n): ").lower()
                    if not response.startswith('y'):
                        break
            
            print(f"\nCOMPLETE Batch complete: {success_count}/{len(midi_files)} files processed")
    else:
        print(f"\nERROR Automation failed - needs debugging")

if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Reaper Corrected Positioning Automation
=======================================

Fixes the MIDI positioning issue - ensures MIDI is moved from default
import position (1.1) to the required position (beat 1.3).

Based on diagnostic finding: MIDI imports at 1.1, needs to be moved to 1.3.

Author: DrumTracKAI v1.1.7
Date: July 23, 2025
"""

import time
from pathlib import Path
import re

try:
    import pyautogui
    import pygetwindow as gw
    pyautogui.FAILSAFE = True
    pyautogui.PAUSE = 1.5
    print("SUCCESS Automation libraries loaded")
except ImportError as e:
    print(f"ERROR Import error: {e}")
    exit(1)

def find_and_focus_reaper():
    """Find and focus Reaper window"""
    print("INSPECTING Finding Reaper window...")
    
    windows = gw.getAllWindows()
    for window in windows:
        if 'REAPER' in window.title.upper():
            print(f"SUCCESS Found Reaper: '{window.title}'")
            try:
                window.activate()
                time.sleep(2)
                print("SUCCESS Reaper focused")
                return True
            except:
                print("WARNING  Manual focus required")
                input("Please click on Reaper window, then press ENTER...")
                return True
    
    print("ERROR Reaper not found!")
    return False

def import_midi_file(midi_file):
    """Import MIDI file into Reaper"""
    print(f"\n Importing MIDI: {midi_file.name}")
    
    try:
        # Open Insert menu
        print("Opening Insert menu (Alt+I)...")
        pyautogui.hotkey('alt', 'i')
        time.sleep(2)
        
        # Select Media File
        print("Selecting Media File (M)...")
        pyautogui.press('m')
        time.sleep(3)
        
        # Type file path
        print(f"Typing file path...")
        pyautogui.write(str(midi_file))
        time.sleep(2)
        
        # Import
        print("Importing (Enter)...")
        pyautogui.press('enter')
        time.sleep(4)
        
        print("SUCCESS MIDI imported (at default position 1.1)")
        return True
        
    except Exception as e:
        print(f"ERROR Import error: {e}")
        return False

def move_midi_from_1_1_to_1_3():
    """Specifically move MIDI from beat 1.1 to beat 1.3"""
    print(f"\n⏱ CORRECTING POSITION: Moving MIDI from 1.1 to 1.3")
    
    try:
        # Step 1: Select all items (the imported MIDI)
        print("Step 1: Selecting imported MIDI items...")
        pyautogui.hotkey('ctrl', 'a')
        time.sleep(1)
        
        # Step 2: Set cursor to beat 1.3
        print("Step 2: Setting cursor to beat 1.3...")
        
        # Go to start first
        pyautogui.press('home')
        time.sleep(1)
        
        # Set grid to quarter notes for precise movement
        print("Setting grid to quarter notes...")
        pyautogui.hotkey('alt', '3')  # Grid to 1/4 notes
        time.sleep(1)
        
        # Move cursor 3 quarter notes forward (to beat 1.3)
        print("Moving cursor 3 quarter notes forward...")
        for i in range(3):
            pyautogui.press('right')
            time.sleep(0.5)
            print(f"  Moved to beat 1.{i+1}")
        
        # Step 3: Move selected items to cursor position
        print("Step 3: Moving MIDI items to cursor (beat 1.3)...")
        pyautogui.hotkey('ctrl', 'shift', 'm')  # Move items to cursor
        time.sleep(2)
        
        print("SUCCESS MIDI repositioned from 1.1 to 1.3")
        return True
        
    except Exception as e:
        print(f"ERROR Positioning error: {e}")
        return False

def verify_midi_position():
    """Verify MIDI is at correct position"""
    print(f"\nINSPECTING VERIFICATION: Check MIDI position")
    print(f"Please verify in Reaper:")
    print(f"1. MIDI items should now be positioned at beat 1.3")
    print(f"2. Timeline cursor should be at beat 1.3")
    print(f"3. MIDI should NOT be at the very beginning (1.1)")
    
    response = input(f"Is MIDI correctly positioned at beat 1.3? (y/n): ").lower()
    return response.startswith('y')

def set_render_bounds_around_midi():
    """Set render bounds around the repositioned MIDI"""
    print(f"\n Setting render bounds around MIDI at 1.3...")
    
    try:
        # Select all items
        pyautogui.hotkey('ctrl', 'a')
        time.sleep(1)
        
        # Set time selection to items
        print("Setting time selection to MIDI items...")
        pyautogui.hotkey('ctrl', 'alt', 'x')
        time.sleep(2)
        
        print("SUCCESS Render bounds set around MIDI")
        return True
        
    except Exception as e:
        print(f"ERROR Render bounds error: {e}")
        return False

def render_audio_output(instrument_name, output_dir):
    """Render the audio output"""
    print(f"\nAUDIO Rendering audio: {instrument_name}.wav")
    
    try:
        # Open render dialog
        print("Opening render dialog (Ctrl+Alt+R)...")
        pyautogui.hotkey('ctrl', 'alt', 'r')
        time.sleep(4)
        
        # Set filename
        print(f"Setting filename: {instrument_name}")
        pyautogui.press('tab', presses=5)  # Navigate to filename
        time.sleep(1)
        pyautogui.hotkey('ctrl', 'a')
        time.sleep(0.5)
        pyautogui.write(instrument_name)
        time.sleep(2)
        
        # Set output directory
        print(f"Setting output directory...")
        pyautogui.press('tab', presses=2)
        time.sleep(1)
        pyautogui.hotkey('ctrl', 'a')
        time.sleep(0.5)
        pyautogui.write(str(output_dir))
        time.sleep(2)
        
        # Start render
        print("Starting render (Enter)...")
        pyautogui.press('enter')
        time.sleep(3)
        
        print("SUCCESS Render started")
        return True
        
    except Exception as e:
        print(f"ERROR Render error: {e}")
        return False

def wait_for_render_completion(expected_file, timeout=120):
    """Wait for render to complete"""
    print(f"\n⏳ Waiting for render completion...")
    print(f"Expected: {expected_file}")
    
    start_time = time.time()
    
    while time.time() - start_time < timeout:
        if expected_file.exists() and expected_file.stat().st_size > 0:
            time.sleep(2)  # Ensure fully written
            
            file_size = expected_file.stat().st_size
            print(f"SUCCESS Render completed!")
            print(f"   File: {expected_file.name}")
            print(f"   Size: {file_size:,} bytes")
            return expected_file
        
        elapsed = int(time.time() - start_time)
        if elapsed % 15 == 0 and elapsed > 0:
            print(f"   Waiting... {elapsed}s/{timeout}s")
        
        time.sleep(3)
    
    print(f"ERROR Render timeout after {timeout}s")
    return None

def clear_project_for_next():
    """Clear project for next MIDI file"""
    print(f"\n Clearing project...")
    
    try:
        # Select all
        pyautogui.hotkey('ctrl', 'a')
        time.sleep(1)
        
        # Delete
        pyautogui.press('delete')
        time.sleep(1)
        
        # Clear time selection
        pyautogui.hotkey('ctrl', 'alt', 'z')
        time.sleep(1)
        
        print("SUCCESS Project cleared")
        return True
        
    except Exception as e:
        print(f"ERROR Clear error: {e}")
        return False

def extract_instrument_name(midi_filename):
    """Extract instrument name from MIDI filename"""
    name = midi_filename.replace('.mid', '')
    match = re.match(r'(.+)_(\d+)$', name)
    if match:
        return match.group(1)
    return name

def process_single_midi_corrected(midi_file):
    """Process single MIDI with corrected positioning"""
    print(f"\n{'='*70}")
    print(f"CORRECTED PROCESSING: {midi_file.name}")
    print(f"Focus: Proper positioning at beat 1.3")
    print(f"{'='*70}")
    
    instrument_name = extract_instrument_name(midi_file.name)
    output_dir = Path(__file__).parent / "sd3_extracted_samples"
    output_file = output_dir / f"{instrument_name}.wav"
    
    print(f"Instrument: {instrument_name}")
    print(f"Output: {output_file}")
    
    # Check if already exists
    if output_file.exists():
        print(f"SUCCESS Already processed: {output_file.name}")
        return True
    
    # Execute corrected workflow
    workflow_steps = [
        ("Import MIDI file", lambda: import_midi_file(midi_file)),
        ("Move MIDI from 1.1 to 1.3", move_midi_from_1_1_to_1_3),
        ("Verify position", verify_midi_position),
        ("Set render bounds", set_render_bounds_around_midi),
        ("Render audio", lambda: render_audio_output(instrument_name, output_dir)),
    ]
    
    for step_name, step_func in workflow_steps:
        print(f"\n--- {step_name} ---")
        if not step_func():
            print(f"ERROR Failed at: {step_name}")
            return False
        time.sleep(2)
    
    # Wait for completion
    rendered_file = wait_for_render_completion(output_file)
    if not rendered_file:
        print("ERROR Render failed")
        return False
    
    # Clear for next
    clear_project_for_next()
    
    print(f"COMPLETE SUCCESS: {midi_file.name} → {rendered_file.name}")
    return True

def main():
    """Main corrected automation"""
    print("AUDIO REAPER CORRECTED POSITIONING AUTOMATION")
    print("=" * 70)
    print("Fixes MIDI positioning: 1.1 → 1.3")
    print("Based on diagnostic findings")
    print("=" * 70)
    
    # Setup
    base_path = Path(__file__).parent
    midi_dir = base_path / "sd3_midi_patterns"
    output_dir = base_path / "sd3_extracted_samples"
    output_dir.mkdir(exist_ok=True)
    
    # Find Reaper
    if not find_and_focus_reaper():
        return
    
    # Get test file
    midi_files = list(midi_dir.glob("*.mid"))
    if not midi_files:
        print("ERROR No MIDI files found!")
        return
    
    test_file = midi_files[0]
    print(f"\n Testing corrected workflow with: {test_file.name}")
    
    input("Press ENTER to start corrected automation...")
    
    success = process_single_midi_corrected(test_file)
    
    if success:
        print(f"\nCOMPLETE CORRECTED AUTOMATION SUCCESSFUL!")
        print(f"MIDI positioning issue resolved!")
        print(f"Ready for batch processing all {len(midi_files)} files.")
        
        response = input(f"\nProcess all remaining files? (y/n): ").lower()
        if response.startswith('y'):
            print(f"\n Starting batch processing...")
            success_count = 1  # Already did first file
            
            for midi_file in midi_files[1:]:
                print(f"\nProcessing {success_count + 1}/{len(midi_files)}: {midi_file.name}")
                if process_single_midi_corrected(midi_file):
                    success_count += 1
                    print(f"Progress: {success_count}/{len(midi_files)}")
                else:
                    print(f"Failed: {midi_file.name}")
                    break
            
            print(f"\nCOMPLETE Batch complete: {success_count}/{len(midi_files)} files processed")
    else:
        print(f"\nERROR CORRECTED AUTOMATION FAILED!")
        print(f"Check positioning steps and try again")

if __name__ == "__main__":
    main()

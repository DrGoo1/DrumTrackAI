#!/usr/bin/env python3
"""
Reaper Diagnostic Automation
============================

Provides detailed step-by-step feedback and verification for each
automation action to identify where the workflow might be failing.

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
    pyautogui.PAUSE = 2.0  # Slower for better reliability
    print("SUCCESS Automation libraries loaded")
except ImportError as e:
    print(f"ERROR Import error: {e}")
    exit(1)

def wait_for_user_verification(step_description):
    """Wait for user to verify step completed successfully"""
    print(f"\n⏸  VERIFICATION REQUIRED:")
    print(f"   {step_description}")
    response = input("Did this step complete successfully? (y/n): ").lower()
    return response.startswith('y')

def find_reaper_window():
    """Find and focus Reaper window with verification"""
    print("INSPECTING Finding Reaper window...")
    
    windows = gw.getAllWindows()
    reaper_windows = []
    
    for window in windows:
        if 'REAPER' in window.title.upper():
            reaper_windows.append(window)
    
    if not reaper_windows:
        print("ERROR No Reaper windows found!")
        print("Available windows:")
        for window in windows[:10]:  # Show first 10 windows
            print(f"  - {window.title}")
        return False
    
    reaper_window = reaper_windows[0]
    print(f"SUCCESS Found Reaper: '{reaper_window.title}'")
    
    try:
        reaper_window.activate()
        time.sleep(3)
        print("SUCCESS Reaper window focused")
        
        # Verify with user
        return wait_for_user_verification("Reaper window is focused and active")
        
    except Exception as e:
        print(f"ERROR Window focus error: {e}")
        return False

def import_midi_with_verification(midi_file):
    """Import MIDI file with step-by-step verification"""
    print(f"\n IMPORTING MIDI: {midi_file.name}")
    print(f"Full path: {midi_file}")
    
    try:
        # Step 1: Open Insert menu
        print("\nStep 1: Opening Insert menu (Alt+I)...")
        pyautogui.hotkey('alt', 'i')
        time.sleep(3)
        
        if not wait_for_user_verification("Insert menu opened"):
            return False
        
        # Step 2: Select Media File
        print("\nStep 2: Selecting Media File (M key)...")
        pyautogui.press('m')
        time.sleep(4)
        
        if not wait_for_user_verification("Media file dialog opened"):
            return False
        
        # Step 3: Type file path
        print(f"\nStep 3: Typing file path...")
        print(f"Path to type: {midi_file}")
        pyautogui.write(str(midi_file))
        time.sleep(3)
        
        if not wait_for_user_verification("File path typed correctly in dialog"):
            return False
        
        # Step 4: Import file
        print("\nStep 4: Importing file (Enter)...")
        pyautogui.press('enter')
        time.sleep(5)
        
        if not wait_for_user_verification("MIDI file imported and visible in timeline"):
            return False
        
        print("SUCCESS MIDI import completed successfully")
        return True
        
    except Exception as e:
        print(f"ERROR Error during MIDI import: {e}")
        return False

def position_midi_with_verification():
    """Position MIDI at beat 1.3 with verification"""
    print(f"\n⏱ POSITIONING MIDI AT BEAT 1.3")
    
    try:
        # Step 1: Select all items
        print("\nStep 1: Selecting all items (Ctrl+A)...")
        pyautogui.hotkey('ctrl', 'a')
        time.sleep(2)
        
        if not wait_for_user_verification("All MIDI items selected (highlighted)"):
            return False
        
        # Step 2: Go to start
        print("\nStep 2: Going to project start (Home)...")
        pyautogui.press('home')
        time.sleep(2)
        
        if not wait_for_user_verification("Cursor moved to project start (position 0)"):
            return False
        
        # Step 3: Set grid to quarter notes
        print("\nStep 3: Setting grid to quarter notes (Alt+3)...")
        pyautogui.hotkey('alt', '3')
        time.sleep(2)
        
        if not wait_for_user_verification("Grid set to quarter notes"):
            return False
        
        # Step 4: Move cursor to beat 1.3
        print("\nStep 4: Moving cursor to beat 1.3 (3 right arrows)...")
        for i in range(3):
            print(f"  Moving to beat 1.{i+1}...")
            pyautogui.press('right')
            time.sleep(1)
        
        if not wait_for_user_verification("Cursor positioned at beat 1.3"):
            return False
        
        # Step 5: Move items to cursor
        print("\nStep 5: Moving items to cursor (Ctrl+Shift+M)...")
        pyautogui.hotkey('ctrl', 'shift', 'm')
        time.sleep(3)
        
        if not wait_for_user_verification("MIDI items moved to beat 1.3 position"):
            return False
        
        print("SUCCESS MIDI positioning completed successfully")
        return True
        
    except Exception as e:
        print(f"ERROR Error during positioning: {e}")
        return False

def set_render_bounds_with_verification():
    """Set render bounds with verification"""
    print(f"\n SETTING RENDER BOUNDS")
    
    try:
        # Step 1: Select all items
        print("\nStep 1: Selecting all items (Ctrl+A)...")
        pyautogui.hotkey('ctrl', 'a')
        time.sleep(2)
        
        if not wait_for_user_verification("All items selected"):
            return False
        
        # Step 2: Set time selection to items
        print("\nStep 2: Setting time selection to items (Ctrl+Alt+X)...")
        pyautogui.hotkey('ctrl', 'alt', 'x')
        time.sleep(3)
        
        if not wait_for_user_verification("Time selection set around MIDI items (yellow highlight in timeline)"):
            return False
        
        print("SUCCESS Render bounds set successfully")
        return True
        
    except Exception as e:
        print(f"ERROR Error setting render bounds: {e}")
        return False

def render_audio_with_verification(output_filename, output_dir):
    """Render audio with detailed verification"""
    print(f"\nAUDIO RENDERING AUDIO: {output_filename}")
    
    try:
        # Step 1: Open render dialog
        print("\nStep 1: Opening render dialog (Ctrl+Alt+R)...")
        pyautogui.hotkey('ctrl', 'alt', 'r')
        time.sleep(5)
        
        if not wait_for_user_verification("Render dialog opened"):
            return False
        
        # Step 2: Navigate to filename field
        print("\nStep 2: Navigating to filename field...")
        print("Using Tab key to navigate to filename field...")
        pyautogui.press('tab', presses=5)
        time.sleep(2)
        
        # Step 3: Set filename
        print(f"\nStep 3: Setting filename to: {output_filename}")
        pyautogui.hotkey('ctrl', 'a')  # Select all
        time.sleep(1)
        pyautogui.write(output_filename)
        time.sleep(2)
        
        if not wait_for_user_verification(f"Filename set to '{output_filename}' in render dialog"):
            return False
        
        # Step 4: Set output directory
        print(f"\nStep 4: Setting output directory...")
        print(f"Directory: {output_dir}")
        pyautogui.press('tab', presses=2)
        time.sleep(1)
        pyautogui.hotkey('ctrl', 'a')
        time.sleep(1)
        pyautogui.write(str(output_dir))
        time.sleep(2)
        
        if not wait_for_user_verification(f"Output directory set to '{output_dir}'"):
            return False
        
        # Step 5: Verify render settings
        print("\nStep 5: Please verify render settings:")
        print("  - Format: WAV")
        print("  - Sample rate: 44100 Hz")
        print("  - Bit depth: 24-bit (or 16-bit)")
        print("  - Source: Time selection")
        
        if not wait_for_user_verification("Render settings are correct"):
            return False
        
        # Step 6: Start render
        print("\nStep 6: Starting render (Enter)...")
        pyautogui.press('enter')
        time.sleep(3)
        
        if not wait_for_user_verification("Render process started (progress dialog or render in progress)"):
            return False
        
        print("SUCCESS Render initiated successfully")
        return True
        
    except Exception as e:
        print(f"ERROR Error during render: {e}")
        return False

def wait_for_render_completion_with_monitoring(expected_file, timeout=180):
    """Wait for render with active monitoring"""
    print(f"\n⏳ MONITORING RENDER COMPLETION")
    print(f"Expected file: {expected_file}")
    print(f"Timeout: {timeout} seconds")
    
    start_time = time.time()
    
    while time.time() - start_time < timeout:
        if expected_file.exists():
            file_size = expected_file.stat().st_size
            if file_size > 0:
                print(f"\nSUCCESS RENDER COMPLETED!")
                print(f"   File: {expected_file.name}")
                print(f"   Size: {file_size:,} bytes")
                print(f"   Path: {expected_file}")
                return expected_file
        
        elapsed = int(time.time() - start_time)
        if elapsed % 15 == 0 and elapsed > 0:
            print(f"   Still waiting... {elapsed}s/{timeout}s")
            print(f"   Checking: {expected_file}")
        
        time.sleep(3)
    
    print(f"\nERROR RENDER TIMEOUT after {timeout}s")
    print(f"Expected file not found: {expected_file}")
    
    # Check if any files were created in output directory
    output_files = list(expected_file.parent.glob("*.wav"))
    if output_files:
        print(f"\nFiles found in output directory:")
        for f in output_files:
            print(f"  - {f.name} ({f.stat().st_size:,} bytes)")
    else:
        print(f"\nNo WAV files found in: {expected_file.parent}")
    
    return None

def main():
    """Main diagnostic workflow"""
    print("AUDIO REAPER DIAGNOSTIC AUTOMATION")
    print("=" * 70)
    print("Step-by-step verification of Reaper + SD3 workflow")
    print("You will be asked to verify each step manually")
    print("=" * 70)
    
    # Setup
    base_path = Path(__file__).parent
    midi_dir = base_path / "sd3_midi_patterns"
    output_dir = base_path / "sd3_extracted_samples"
    output_dir.mkdir(exist_ok=True)
    
    # Get test file
    midi_files = list(midi_dir.glob("*.mid"))
    if not midi_files:
        print("ERROR No MIDI files found!")
        return
    
    test_file = midi_files[0]
    instrument_name = test_file.stem.rsplit('_', 1)[0] if '_' in test_file.stem else test_file.stem
    output_file = output_dir / f"{instrument_name}.wav"
    
    print(f"\n DIAGNOSTIC TEST")
    print(f"MIDI file: {test_file.name}")
    print(f"Instrument: {instrument_name}")
    print(f"Output: {output_file.name}")
    
    # Check if already exists
    if output_file.exists():
        print(f"\nWARNING  Output file already exists!")
        print(f"Size: {output_file.stat().st_size:,} bytes")
        response = input("Delete and recreate? (y/n): ").lower()
        if response.startswith('y'):
            output_file.unlink()
        else:
            return
    
    input(f"\nPress ENTER to start diagnostic workflow...")
    
    # Execute workflow with verification
    workflow_steps = [
        ("Find and focus Reaper", find_reaper_window),
        ("Import MIDI file", lambda: import_midi_with_verification(test_file)),
        ("Position at beat 1.3", position_midi_with_verification),
        ("Set render bounds", set_render_bounds_with_verification),
        ("Render audio", lambda: render_audio_with_verification(instrument_name, output_dir)),
    ]
    
    for step_name, step_func in workflow_steps:
        print(f"\n{'='*70}")
        print(f"DIAGNOSTIC STEP: {step_name}")
        print(f"{'='*70}")
        
        if not step_func():
            print(f"\nERROR DIAGNOSTIC FAILED AT: {step_name}")
            print(f"Please check Reaper and try again")
            return
        
        print(f"SUCCESS Step completed: {step_name}")
        time.sleep(2)
    
    # Monitor render completion
    print(f"\n{'='*70}")
    print(f"DIAGNOSTIC STEP: Monitor render completion")
    print(f"{'='*70}")
    
    rendered_file = wait_for_render_completion_with_monitoring(output_file)
    
    if rendered_file:
        print(f"\nCOMPLETE DIAGNOSTIC SUCCESSFUL!")
        print(f"=" * 70)
        print(f"SUCCESS All steps completed successfully")
        print(f"SUCCESS File created: {rendered_file.name}")
        print(f"SUCCESS Size: {rendered_file.stat().st_size:,} bytes")
        print(f"SUCCESS Workflow: Fully functional")
        print(f"=" * 70)
        print(f"\nLAUNCH READY FOR BATCH PROCESSING!")
    else:
        print(f"\nERROR DIAGNOSTIC FAILED!")
        print(f"Render did not complete or file not created")
        print(f"Check Reaper render settings and try again")

if __name__ == "__main__":
    main()

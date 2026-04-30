#!/usr/bin/env python3
"""
Reaper Keyboard Automation - Reliable Method
============================================

Uses only keyboard shortcuts to avoid mouse click issues.
Based on verified manual workflow but with precise keyboard commands.

Author: DrumTracKAI v1.1.7
Date: July 23, 2025
"""

import time
from pathlib import Path

try:
    import pyautogui
    import pygetwindow as gw
    pyautogui.FAILSAFE = True
    pyautogui.PAUSE = 0.5
    print("SUCCESS Automation libraries loaded")
except ImportError as e:
    print(f"ERROR Import error: {e}")
    exit(1)

def find_and_focus_reaper():
    """Find and focus Reaper window reliably"""
    print("INSPECTING Finding Reaper window...")
    
    windows = gw.getAllWindows()
    for window in windows:
        if 'REAPER' in window.title.upper():
            print(f"SUCCESS Found Reaper: '{window.title}'")
            try:
                window.activate()
                time.sleep(3)  # Longer wait to ensure focus
                print("SUCCESS Reaper focused")
                return True
            except:
                print("WARNING  Please click on Reaper window")
                input("Press ENTER when Reaper is focused...")
                return True
    
    print("ERROR Reaper not found!")
    return False

def import_midi_keyboard_method(midi_file_path):
    """Import MIDI using reliable keyboard shortcuts"""
    print(f"\n Importing MIDI: {midi_file_path.name}")
    print(f"Full path: {midi_file_path}")
    
    try:
        # Method 1: Ctrl+I (Insert Media Item)
        print("Using Ctrl+I to insert media item...")
        pyautogui.hotkey('ctrl', 'i')
        time.sleep(3)
        
        # Type the full file path
        print("Typing file path...")
        pyautogui.write(str(midi_file_path))
        time.sleep(2)
        
        # Press Enter to import
        print("Pressing Enter to import...")
        pyautogui.press('enter')
        time.sleep(4)
        
        print("SUCCESS MIDI import attempted")
        
        # Verify by asking user
        print("\nINSPECTING VERIFICATION NEEDED:")
        print("Look at Reaper timeline - do you see the MIDI data?")
        response = input("Did MIDI appear in timeline? (y/n): ").lower()
        
        if response.startswith('y'):
            print("SUCCESS MIDI import successful!")
            return True
        else:
            print("ERROR MIDI import failed")
            return False
        
    except Exception as e:
        print(f"ERROR Import error: {e}")
        return False

def position_midi_keyboard_method():
    """Position MIDI at beat 1.3 using keyboard"""
    print(f"\n⏱ Positioning MIDI at beat 1.3...")
    
    try:
        # Select all items
        print("Selecting all items (Ctrl+A)...")
        pyautogui.hotkey('ctrl', 'a')
        time.sleep(1)
        
        # Go to project start
        print("Going to start (Home)...")
        pyautogui.press('home')
        time.sleep(1)
        
        # Set grid to quarter notes for precise positioning
        print("Setting grid to quarter notes...")
        pyautogui.hotkey('alt', '3')  # 1/4 note grid
        time.sleep(1)
        
        # Move cursor to beat 1.3 (3 quarter note steps)
        print("Moving cursor to beat 1.3...")
        for i in range(3):
            pyautogui.press('right')
            time.sleep(0.5)
            print(f"  Step {i+1}/3")
        
        # Move selected items to cursor position
        print("Moving MIDI to cursor (Ctrl+Shift+M)...")
        pyautogui.hotkey('ctrl', 'shift', 'm')
        time.sleep(2)
        
        print("SUCCESS MIDI positioning attempted")
        
        # Verify positioning
        print("\nINSPECTING VERIFICATION NEEDED:")
        print("Look at Reaper timeline - is MIDI positioned at beat 1.3?")
        response = input("Is MIDI at beat 1.3? (y/n): ").lower()
        
        if response.startswith('y'):
            print("SUCCESS MIDI positioning successful!")
            return True
        else:
            print("ERROR MIDI positioning failed")
            return False
        
    except Exception as e:
        print(f"ERROR Positioning error: {e}")
        return False

def set_render_selection_keyboard():
    """Set render selection 1.1 to 2.1 using keyboard"""
    print(f"\n Setting render selection: 1.1 to 2.1...")
    
    try:
        # Go to start (beat 1.1)
        print("Going to start (Home)...")
        pyautogui.press('home')
        time.sleep(1)
        
        # Set selection start (Enter)
        print("Setting selection start (Enter)...")
        pyautogui.press('enter')
        time.sleep(1)
        
        # Move to beat 2.1 (4 quarter note steps)
        print("Moving to beat 2.1...")
        for i in range(4):
            pyautogui.press('right')
            time.sleep(0.5)
            print(f"  Step {i+1}/4")
        
        # Set selection end (Shift+Enter)
        print("Setting selection end (Shift+Enter)...")
        pyautogui.hotkey('shift', 'enter')
        time.sleep(1)
        
        print("SUCCESS Render selection attempted")
        
        # Verify selection
        print("\nINSPECTING VERIFICATION NEEDED:")
        print("Look at Reaper timeline - is there a selection from 1.1 to 2.1?")
        response = input("Is selection correct? (y/n): ").lower()
        
        if response.startswith('y'):
            print("SUCCESS Render selection successful!")
            return True
        else:
            print("ERROR Render selection failed")
            return False
        
    except Exception as e:
        print(f"ERROR Selection error: {e}")
        return False

def render_audio_keyboard(output_filename, output_dir):
    """Render audio using keyboard shortcuts"""
    print(f"\nAUDIO Rendering audio: {output_filename}.wav")
    
    try:
        # Open render dialog (Ctrl+Alt+R)
        print("Opening render dialog (Ctrl+Alt+R)...")
        pyautogui.hotkey('ctrl', 'alt', 'r')
        time.sleep(4)
        
        # Navigate to filename field and set name
        print(f"Setting filename: {output_filename}")
        # Use Tab to navigate to filename field
        pyautogui.press('tab', presses=5)
        time.sleep(1)
        pyautogui.hotkey('ctrl', 'a')  # Select all
        time.sleep(0.5)
        pyautogui.write(output_filename)
        time.sleep(1)
        
        # Navigate to directory field
        print("Setting output directory...")
        pyautogui.press('tab', presses=2)
        time.sleep(1)
        pyautogui.hotkey('ctrl', 'a')
        time.sleep(0.5)
        pyautogui.write(str(output_dir))
        time.sleep(1)
        
        # Start render (Enter)
        print("Starting render (Enter)...")
        pyautogui.press('enter')
        time.sleep(3)
        
        print("SUCCESS Render initiated")
        return True
        
    except Exception as e:
        print(f"ERROR Render error: {e}")
        return False

def wait_for_file_creation(output_file, timeout=60):
    """Wait for output file to be created"""
    print(f"\n⏳ Waiting for file creation...")
    print(f"Expected: {output_file}")
    
    start_time = time.time()
    
    while time.time() - start_time < timeout:
        if output_file.exists() and output_file.stat().st_size > 0:
            time.sleep(2)  # Ensure file is complete
            file_size = output_file.stat().st_size
            print(f"SUCCESS File created successfully!")
            print(f"   Name: {output_file.name}")
            print(f"   Size: {file_size:,} bytes")
            return True
        
        elapsed = int(time.time() - start_time)
        if elapsed % 10 == 0 and elapsed > 0:
            print(f"   Still waiting... {elapsed}s/{timeout}s")
        
        time.sleep(3)
    
    print(f"ERROR Timeout - file not created after {timeout}s")
    return False

def clear_timeline_keyboard():
    """Clear timeline using keyboard"""
    print(f"\n Clearing timeline...")
    
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
        
        print("SUCCESS Timeline cleared")
        return True
        
    except Exception as e:
        print(f"ERROR Clear error: {e}")
        return False

def process_single_file_keyboard(midi_file):
    """Process single file with keyboard automation"""
    print(f"\n{'='*70}")
    print(f"KEYBOARD AUTOMATION: {midi_file.name}")
    print(f"No mouse clicks - keyboard only!")
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
    
    # Execute keyboard workflow with verification
    workflow_steps = [
        ("Import MIDI file", lambda: import_midi_keyboard_method(midi_file)),
        ("Position at beat 1.3", position_midi_keyboard_method),
        ("Set render selection 1.1-2.1", set_render_selection_keyboard),
        ("Render audio", lambda: render_audio_keyboard(instrument_name, output_dir)),
        ("Wait for file creation", lambda: wait_for_file_creation(output_file)),
        ("Clear timeline", clear_timeline_keyboard)
    ]
    
    for step_name, step_func in workflow_steps:
        print(f"\n--- {step_name} ---")
        if not step_func():
            print(f"ERROR FAILED at: {step_name}")
            print(f"Stopping workflow for debugging")
            return False
        time.sleep(2)
    
    print(f"COMPLETE SUCCESS: {midi_file.name} → {instrument_name}.wav")
    return True

def main():
    """Main keyboard automation"""
    print("AUDIO REAPER KEYBOARD AUTOMATION")
    print("=" * 70)
    print("Keyboard shortcuts only - no mouse clicks!")
    print("Manual verification at each step")
    print("=" * 70)
    
    # Setup
    base_path = Path(__file__).parent
    midi_dir = base_path / "sd3_midi_patterns"
    output_dir = base_path / "sd3_extracted_samples"
    output_dir.mkdir(exist_ok=True)
    
    # Find Reaper
    if not find_and_focus_reaper():
        return
    
    # Get MIDI files
    midi_files = list(midi_dir.glob("*.mid"))
    if not midi_files:
        print("ERROR No MIDI files found!")
        return
    
    print(f"\nFOLDER Found {len(midi_files)} MIDI files")
    test_file = midi_files[0]
    
    print(f"\n Testing with: {test_file.name}")
    print("This will use ONLY keyboard shortcuts")
    print("You'll verify each step works before continuing")
    
    input("Press ENTER to start keyboard automation...")
    
    # Test single file
    success = process_single_file_keyboard(test_file)
    
    if success:
        print(f"\nCOMPLETE KEYBOARD AUTOMATION SUCCESSFUL!")
        print(f"All steps verified and working!")
        
        response = input(f"\nProcess all {len(midi_files)} files? (y/n): ").lower()
        if response.startswith('y'):
            print(f"\n Starting batch processing...")
            success_count = 1
            
            for midi_file in midi_files[1:]:
                print(f"\nProcessing {success_count + 1}/{len(midi_files)}: {midi_file.name}")
                if process_single_file_keyboard(midi_file):
                    success_count += 1
                    print(f"Progress: {success_count}/{len(midi_files)}")
                else:
                    print(f"Failed: {midi_file.name}")
                    break
            
            print(f"\nCOMPLETE Batch complete: {success_count}/{len(midi_files)} files")
    else:
        print(f"\nERROR Keyboard automation needs refinement")
        print(f"Check which step failed and we'll fix it")

if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Reaper Simple Focus - Guaranteed Window Focus
=============================================

Simple approach that ensures Reaper has focus before each command.
Manual confirmation that focus is correct before proceeding.

Author: DrumTracKAI v1.1.7
Date: July 23, 2025
"""

import time
from pathlib import Path

try:
    import pyautogui
    import pygetwindow as gw
    pyautogui.FAILSAFE = True
    pyautogui.PAUSE = 1.0
    print("SUCCESS Automation ready")
except ImportError as e:
    print(f"ERROR Import error: {e}")
    exit(1)

def ensure_reaper_focus():
    """Ensure Reaper has focus and wait for confirmation"""
    print("\nTARGET ENSURING REAPER FOCUS")
    print("=" * 40)
    
    # Find Reaper window
    windows = gw.getAllWindows()
    reaper_window = None
    
    for window in windows:
        if 'REAPER' in window.title.upper():
            reaper_window = window
            break
    
    if reaper_window:
        print(f"Found Reaper: {reaper_window.title}")
        try:
            reaper_window.activate()
            time.sleep(2)
            print("SUCCESS Reaper activated")
        except:
            print("WARNING  Could not activate automatically")
    else:
        print("ERROR Reaper window not found")
    
    print("\nINSPECTING MANUAL VERIFICATION:")
    print("1. Click on the Reaper window to ensure it has focus")
    print("2. Make sure Reaper is the active window")
    print("3. Verify no other applications are in front")
    
    response = input("\nIs Reaper focused and ready? (y/n): ").lower()
    if not response.startswith('y'):
        print("ERROR Please focus Reaper first")
        return False
    
    print("SUCCESS Reaper focus confirmed")
    return True

def import_midi_simple(midi_file_path):
    """Simple MIDI import with focus verification"""
    print(f"\n IMPORTING MIDI: {midi_file_path.name}")
    print("=" * 50)
    
    if not ensure_reaper_focus():
        return False
    
    print("Sending Ctrl+I to Reaper...")
    pyautogui.hotkey('ctrl', 'i')
    time.sleep(3)
    
    print("Typing file path...")
    pyautogui.write(str(midi_file_path))
    time.sleep(2)
    
    print("Pressing Enter...")
    pyautogui.press('enter')
    time.sleep(4)
    
    print("\nINSPECTING VERIFICATION:")
    print("Look at Reaper timeline - do you see MIDI data?")
    response = input("Did MIDI import successfully? (y/n): ").lower()
    
    if response.startswith('y'):
        print("SUCCESS MIDI import successful!")
        return True
    else:
        print("ERROR MIDI import failed")
        return False

def position_midi_simple():
    """Simple MIDI positioning with focus verification"""
    print(f"\n⏱ POSITIONING MIDI AT BEAT 1.3")
    print("=" * 40)
    
    if not ensure_reaper_focus():
        return False
    
    print("Selecting all items (Ctrl+A)...")
    pyautogui.hotkey('ctrl', 'a')
    time.sleep(1)
    
    print("Going to start (Home)...")
    pyautogui.press('home')
    time.sleep(1)
    
    print("Moving cursor to beat 1.3...")
    for i in range(3):
        pyautogui.press('right')
        time.sleep(0.5)
        print(f"  Step {i+1}/3")
    
    print("Moving MIDI to cursor (Ctrl+Shift+M)...")
    pyautogui.hotkey('ctrl', 'shift', 'm')
    time.sleep(2)
    
    print("\nINSPECTING VERIFICATION:")
    print("Is MIDI positioned at beat 1.3?")
    response = input("Is positioning correct? (y/n): ").lower()
    
    if response.startswith('y'):
        print("SUCCESS MIDI positioning successful!")
        return True
    else:
        print("ERROR MIDI positioning failed")
        return False

def set_render_selection_simple():
    """Simple render selection with focus verification"""
    print(f"\n SETTING RENDER SELECTION: 1.1 to 2.1")
    print("=" * 45)
    
    if not ensure_reaper_focus():
        return False
    
    print("Going to start (Home)...")
    pyautogui.press('home')
    time.sleep(1)
    
    print("Setting selection start (Enter)...")
    pyautogui.press('enter')
    time.sleep(1)
    
    print("Moving to beat 2.1...")
    for i in range(4):
        pyautogui.press('right')
        time.sleep(0.5)
        print(f"  Step {i+1}/4")
    
    print("Setting selection end (Shift+Enter)...")
    pyautogui.hotkey('shift', 'enter')
    time.sleep(1)
    
    print("\nINSPECTING VERIFICATION:")
    print("Is there a selection from beat 1.1 to 2.1?")
    response = input("Is selection correct? (y/n): ").lower()
    
    if response.startswith('y'):
        print("SUCCESS Render selection successful!")
        return True
    else:
        print("ERROR Render selection failed")
        return False

def render_audio_simple(instrument_name, output_dir):
    """Simple audio rendering with focus verification"""
    print(f"\nAUDIO RENDERING AUDIO: {instrument_name}.wav")
    print("=" * 50)
    
    if not ensure_reaper_focus():
        return False
    
    print("Opening render dialog (Ctrl+Alt+R)...")
    pyautogui.hotkey('ctrl', 'alt', 'r')
    time.sleep(4)
    
    print(f"Setting filename: {instrument_name}")
    # Navigate to filename field
    pyautogui.press('tab', presses=5)
    time.sleep(1)
    pyautogui.hotkey('ctrl', 'a')
    time.sleep(0.5)
    pyautogui.write(instrument_name)
    time.sleep(1)
    
    print("Setting output directory...")
    pyautogui.press('tab', presses=2)
    time.sleep(1)
    pyautogui.hotkey('ctrl', 'a')
    time.sleep(0.5)
    pyautogui.write(str(output_dir))
    time.sleep(1)
    
    print("Starting render (Enter)...")
    pyautogui.press('enter')
    time.sleep(3)
    
    print("SUCCESS Render initiated")
    return True

def main():
    """Main simple focus automation"""
    print("AUDIO REAPER SIMPLE FOCUS AUTOMATION")
    print("=" * 70)
    print("Ensures Reaper focus before each command")
    print("Manual verification at each step")
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
    
    print(f"\n TEST FILE: {test_file.name}")
    print(f"Instrument: {instrument_name}")
    print(f"Output: {output_file}")
    
    print(f"\nLAUNCH STARTING SIMPLE FOCUS AUTOMATION")
    print("This will ensure Reaper focus before each command")
    
    input("Press ENTER to start...")
    
    # Execute workflow with focus verification
    steps = [
        ("Import MIDI", lambda: import_midi_simple(test_file)),
        ("Position at 1.3", position_midi_simple),
        ("Set render selection", set_render_selection_simple),
        ("Render audio", lambda: render_audio_simple(instrument_name, output_dir))
    ]
    
    for step_name, step_func in steps:
        print(f"\n{'='*70}")
        print(f"STEP: {step_name}")
        print(f"{'='*70}")
        
        if not step_func():
            print(f"ERROR FAILED at: {step_name}")
            print("Stopping automation for debugging")
            return
        
        print(f"SUCCESS {step_name} completed successfully")
        time.sleep(2)
    
    # Check for output file
    print(f"\n⏳ Checking for output file...")
    time.sleep(5)
    
    if output_file.exists():
        file_size = output_file.stat().st_size
        print(f"COMPLETE SUCCESS!")
        print(f"SUCCESS Created: {output_file.name}")
        print(f"SUCCESS Size: {file_size:,} bytes")
        print(f"SUCCESS Automation working correctly!")
    else:
        print(f"ERROR Output file not found: {output_file}")
        print("Check render settings and try again")

if __name__ == "__main__":
    main()

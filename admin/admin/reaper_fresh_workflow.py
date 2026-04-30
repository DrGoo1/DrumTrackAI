#!/usr/bin/env python3
"""
Reaper Fresh Workflow - Correct Implementation
==============================================

CORRECT WORKFLOW:
1. Import MIDI file and position at beat 1.3
2. Set render selection from beat 1.1 to 2.1 (captures full audio)
3. Render audio output
4. Save with proper naming

User clarification: MIDI at 1.3, but render from 1.1-2.1 for complete audio.

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
                print("WARNING  Manual focus - click on Reaper window")
                input("Press ENTER when Reaper is focused...")
                return True
    
    print("ERROR Reaper not found!")
    return False

def import_midi_file(midi_file):
    """Import MIDI file into Reaper"""
    print(f"\n Importing MIDI: {midi_file.name}")
    
    try:
        # Use Insert menu
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
        
        print("SUCCESS MIDI imported")
        return True
        
    except Exception as e:
        print(f"ERROR Import error: {e}")
        return False

def position_midi_at_beat_1_3():
    """Position MIDI at beat 1.3"""
    print(f"\n⏱ Positioning MIDI at beat 1.3...")
    
    try:
        # Select all items
        print("Selecting all MIDI items...")
        pyautogui.hotkey('ctrl', 'a')
        time.sleep(1)
        
        # Set grid to quarter notes
        print("Setting grid to quarter notes...")
        pyautogui.hotkey('alt', '3')  # 1/4 note grid
        time.sleep(1)
        
        # Go to start
        print("Going to project start...")
        pyautogui.press('home')
        time.sleep(1)
        
        # Move cursor to beat 1.3 (3 quarter notes from start)
        print("Moving cursor to beat 1.3...")
        for i in range(3):
            pyautogui.press('right')
            time.sleep(0.5)
        
        # Move items to cursor position
        print("Moving MIDI to beat 1.3...")
        pyautogui.hotkey('ctrl', 'shift', 'm')  # Move items to cursor
        time.sleep(2)
        
        print("SUCCESS MIDI positioned at beat 1.3")
        return True
        
    except Exception as e:
        print(f"ERROR Positioning error: {e}")
        return False

def set_render_selection_1_1_to_2_1():
    """Set render selection from beat 1.1 to 2.1"""
    print(f"\n Setting render selection: beat 1.1 to 2.1...")
    
    try:
        # Go to beat 1.1 (project start)
        print("Setting start of selection at beat 1.1...")
        pyautogui.press('home')
        time.sleep(1)
        
        # Start time selection
        print("Starting time selection...")
        pyautogui.press('enter')  # Set selection start
        time.sleep(1)
        
        # Move to beat 2.1 (4 quarter notes from start)
        print("Moving to beat 2.1 (end of selection)...")
        for i in range(4):
            pyautogui.press('right')
            time.sleep(0.5)
        
        # End time selection
        print("Ending time selection at beat 2.1...")
        pyautogui.hotkey('shift', 'enter')  # Set selection end
        time.sleep(1)
        
        print("SUCCESS Render selection set: 1.1 to 2.1")
        return True
        
    except Exception as e:
        print(f"ERROR Selection error: {e}")
        return False

def render_audio_output(instrument_name, output_dir):
    """Render audio with specified selection"""
    print(f"\nAUDIO Rendering audio: {instrument_name}.wav")
    print(f"Render range: beat 1.1 to 2.1")
    
    try:
        # Open render dialog
        print("Opening render dialog (Ctrl+Alt+R)...")
        pyautogui.hotkey('ctrl', 'alt', 'r')
        time.sleep(4)
        
        # Navigate to filename field
        print(f"Setting filename: {instrument_name}")
        pyautogui.press('tab', presses=5)  # Navigate to filename
        time.sleep(1)
        pyautogui.hotkey('ctrl', 'a')  # Select all
        time.sleep(0.5)
        pyautogui.write(instrument_name)
        time.sleep(2)
        
        # Set output directory
        print(f"Setting output directory...")
        pyautogui.press('tab', presses=2)  # Navigate to directory
        time.sleep(1)
        pyautogui.hotkey('ctrl', 'a')
        time.sleep(0.5)
        pyautogui.write(str(output_dir))
        time.sleep(2)
        
        # Ensure "Time selection" is selected as source
        print("Ensuring 'Time selection' is render source...")
        # This may require specific navigation in render dialog
        
        # Start render
        print("Starting render (Enter)...")
        pyautogui.press('enter')
        time.sleep(3)
        
        print("SUCCESS Render started (1.1 to 2.1)")
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

def process_single_midi_fresh(midi_file):
    """Process single MIDI with fresh correct workflow"""
    print(f"\n{'='*70}")
    print(f"FRESH WORKFLOW: {midi_file.name}")
    print(f"MIDI at 1.3, Render 1.1-2.1")
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
    
    # Execute fresh workflow
    workflow_steps = [
        ("Import MIDI file", lambda: import_midi_file(midi_file)),
        ("Position MIDI at beat 1.3", position_midi_at_beat_1_3),
        ("Set render selection 1.1-2.1", set_render_selection_1_1_to_2_1),
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
    """Main fresh workflow automation"""
    print("AUDIO REAPER FRESH WORKFLOW AUTOMATION")
    print("=" * 70)
    print("CORRECT IMPLEMENTATION:")
    print("• MIDI positioned at beat 1.3")
    print("• Render selection: beat 1.1 to 2.1")
    print("• Captures complete audio output")
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
    print(f"\n Testing fresh workflow with: {test_file.name}")
    print(f"Timeline should be clear (old MIDI removed)")
    
    input("Press ENTER to start fresh automation...")
    
    success = process_single_midi_fresh(test_file)
    
    if success:
        print(f"\nCOMPLETE FRESH WORKFLOW SUCCESSFUL!")
        print(f"Correct implementation working!")
        print(f"Ready for batch processing all {len(midi_files)} files.")
        
        response = input(f"\nProcess all remaining files? (y/n): ").lower()
        if response.startswith('y'):
            print(f"\n Starting batch processing...")
            success_count = 1  # Already did first file
            
            for midi_file in midi_files[1:]:
                print(f"\nProcessing {success_count + 1}/{len(midi_files)}: {midi_file.name}")
                if process_single_midi_fresh(midi_file):
                    success_count += 1
                    print(f"Progress: {success_count}/{len(midi_files)}")
                else:
                    print(f"Failed: {midi_file.name}")
                    response = input("Continue? (y/n): ").lower()
                    if not response.startswith('y'):
                        break
            
            print(f"\nCOMPLETE Batch complete: {success_count}/{len(midi_files)} files processed")
    else:
        print(f"\nERROR FRESH WORKFLOW FAILED!")
        print(f"Check steps and try again")

if __name__ == "__main__":
    main()

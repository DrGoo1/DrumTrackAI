#!/usr/bin/env python3
"""
Reaper Single File Test - Streamlined
=====================================

Automatically tests the Reaper + SD3 workflow with a single MIDI file.
No user input required - proceeds directly to automation test.

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
                print("SUCCESS Reaper window focused")
                return True
            except Exception as e:
                print(f"WARNING  Window focus issue: {e}")
                print("Continuing anyway...")
                return True
    
    print("ERROR Reaper window not found!")
    return False

def import_midi_file(midi_file):
    """Import MIDI file into Reaper"""
    print(f"\n Importing MIDI: {midi_file.name}")
    
    try:
        # Use Insert menu approach
        print("Opening Insert menu...")
        pyautogui.hotkey('alt', 'i')  # Insert menu
        time.sleep(2)
        
        # Select Media File
        print("Selecting Media File...")
        pyautogui.press('m')  # Media File
        time.sleep(3)
        
        # Type file path
        print(f"Typing file path: {midi_file}")
        pyautogui.write(str(midi_file))
        time.sleep(2)
        
        # Import file
        print("Importing file...")
        pyautogui.press('enter')
        time.sleep(4)
        
        print("SUCCESS MIDI import completed")
        return True
        
    except Exception as e:
        print(f"ERROR Error importing MIDI: {e}")
        return False

def position_midi_at_beat_1_3():
    """Position MIDI item at beat 1.3"""
    print(f"\n⏱ Positioning MIDI at beat 1.3...")
    
    try:
        # Select all items
        print("Selecting all items...")
        pyautogui.hotkey('ctrl', 'a')
        time.sleep(1)
        
        # Go to project start
        print("Going to project start...")
        pyautogui.press('home')
        time.sleep(1)
        
        # Set grid to quarter notes for precise positioning
        print("Setting grid to quarter notes...")
        pyautogui.hotkey('alt', '3')  # Set grid to 1/4 note
        time.sleep(1)
        
        # Move cursor to beat 1.3 (3 quarter notes from start)
        print("Moving to beat 1.3...")
        for i in range(3):
            pyautogui.press('right')
            time.sleep(0.5)
            print(f"  Beat {i+1}/3")
        
        # Move selected items to cursor position
        print("Moving items to cursor position...")
        pyautogui.hotkey('ctrl', 'shift', 'm')  # Move items to cursor
        time.sleep(2)
        
        print("SUCCESS MIDI positioned at beat 1.3")
        return True
        
    except Exception as e:
        print(f"ERROR Error positioning MIDI: {e}")
        return False

def set_render_bounds():
    """Set render bounds around the MIDI item"""
    print(f"\n Setting render bounds...")
    
    try:
        # Select all items
        pyautogui.hotkey('ctrl', 'a')
        time.sleep(1)
        
        # Set time selection to selected items
        print("Setting time selection to items...")
        pyautogui.hotkey('ctrl', 'alt', 'x')  # Set time selection to items
        time.sleep(2)
        
        print("SUCCESS Render bounds set")
        return True
        
    except Exception as e:
        print(f"ERROR Error setting render bounds: {e}")
        return False

def render_audio(output_filename, output_dir):
    """Render audio to file"""
    print(f"\nAUDIO Rendering audio: {output_filename}")
    
    try:
        # Open render dialog
        print("Opening render dialog...")
        pyautogui.hotkey('ctrl', 'alt', 'r')  # Render dialog
        time.sleep(4)
        
        # Set filename (navigate to filename field)
        print("Setting output filename...")
        # Try different approaches to reach filename field
        pyautogui.press('tab', presses=5)  # Navigate to filename
        time.sleep(1)
        pyautogui.hotkey('ctrl', 'a')  # Select all
        time.sleep(0.5)
        pyautogui.write(output_filename)
        time.sleep(2)
        
        # Set output directory
        print(f"Setting output directory: {output_dir}")
        pyautogui.press('tab', presses=2)  # Navigate to directory
        time.sleep(1)
        pyautogui.hotkey('ctrl', 'a')
        time.sleep(0.5)
        pyautogui.write(str(output_dir))
        time.sleep(2)
        
        # Start render
        print("Starting render...")
        pyautogui.press('enter')  # Start render
        time.sleep(3)
        
        print("SUCCESS Render started")
        return True
        
    except Exception as e:
        print(f"ERROR Error starting render: {e}")
        return False

def wait_for_render_completion(expected_file, timeout=120):
    """Wait for render to complete"""
    print(f"\n⏳ Waiting for render completion...")
    print(f"Expected file: {expected_file}")
    
    start_time = time.time()
    
    while time.time() - start_time < timeout:
        if expected_file.exists() and expected_file.stat().st_size > 0:
            time.sleep(2)  # Ensure file is fully written
            
            file_size = expected_file.stat().st_size
            print(f"SUCCESS Render completed!")
            print(f"   File: {expected_file.name}")
            print(f"   Size: {file_size:,} bytes")
            return expected_file
        
        elapsed = int(time.time() - start_time)
        if elapsed % 15 == 0 and elapsed > 0:
            print(f"   Still waiting... {elapsed}s/{timeout}s")
        
        time.sleep(3)
    
    print(f"ERROR Render timeout after {timeout}s")
    return None

def clear_project():
    """Clear project for next file"""
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
        print(f"ERROR Error clearing project: {e}")
        return False

def extract_instrument_name(midi_filename):
    """Extract instrument name from MIDI filename"""
    name = midi_filename.replace('.mid', '')
    match = re.match(r'(.+)_(\d+)$', name)
    if match:
        return match.group(1)
    return name

def main():
    """Main single file test"""
    print("AUDIO REAPER SINGLE FILE TEST")
    print("=" * 60)
    print("Testing Reaper + SD3 automation with one MIDI file")
    print("=" * 60)
    
    # Setup paths
    base_path = Path(__file__).parent
    midi_dir = base_path / "sd3_midi_patterns"
    output_dir = base_path / "sd3_extracted_samples"
    output_dir.mkdir(exist_ok=True)
    
    print(f"FOLDER MIDI directory: {midi_dir}")
    print(f"FOLDER Output directory: {output_dir}")
    
    # Get first MIDI file
    midi_files = list(midi_dir.glob("*.mid"))
    if not midi_files:
        print("ERROR No MIDI files found!")
        return
    
    test_file = midi_files[0]
    instrument_name = extract_instrument_name(test_file.name)
    output_file = output_dir / f"{instrument_name}.wav"
    
    print(f"\n TEST FILE: {test_file.name}")
    print(f"TARGET INSTRUMENT: {instrument_name}")
    print(f"FILE OUTPUT: {output_file.name}")
    
    # Check if already processed
    if output_file.exists():
        print(f"SUCCESS File already exists: {output_file.name}")
        print(f"File size: {output_file.stat().st_size:,} bytes")
        return
    
    # Find Reaper window
    if not find_reaper_window():
        print("ERROR Cannot proceed without Reaper")
        return
    
    print(f"\nLAUNCH STARTING AUTOMATION TEST...")
    print(f"Watch Reaper window for automation actions")
    
    # Wait a moment for user to observe
    time.sleep(3)
    
    # Execute workflow
    workflow_steps = [
        ("Import MIDI file", lambda: import_midi_file(test_file)),
        ("Position at beat 1.3", position_midi_at_beat_1_3),
        ("Set render bounds", set_render_bounds),
        ("Render audio", lambda: render_audio(instrument_name, output_dir)),
    ]
    
    for step_name, step_func in workflow_steps:
        print(f"\n{'='*50}")
        print(f"STEP: {step_name}")
        print(f"{'='*50}")
        
        if not step_func():
            print(f"ERROR AUTOMATION FAILED AT: {step_name}")
            return
        
        # Pause between steps
        time.sleep(3)
    
    # Wait for render completion
    print(f"\n{'='*50}")
    print(f"STEP: Wait for render completion")
    print(f"{'='*50}")
    
    rendered_file = wait_for_render_completion(output_file)
    if not rendered_file:
        print("ERROR RENDER FAILED OR TIMED OUT")
        return
    
    # Clear project
    clear_project()
    
    print(f"\nCOMPLETE AUTOMATION TEST SUCCESSFUL!")
    print(f"=" * 60)
    print(f"SUCCESS Processed: {test_file.name}")
    print(f"SUCCESS Created: {rendered_file.name}")
    print(f"SUCCESS Size: {rendered_file.stat().st_size:,} bytes")
    print(f"SUCCESS Workflow: Complete")
    print(f"=" * 60)
    print(f"\nLAUNCH READY FOR BATCH PROCESSING!")
    print(f"The automation workflow is working correctly.")
    print(f"You can now process all {len(midi_files)} MIDI files.")

if __name__ == "__main__":
    main()

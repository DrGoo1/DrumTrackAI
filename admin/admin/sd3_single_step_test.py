#!/usr/bin/env python3
"""
Single Step SD3 Test - Load MIDI File Only
==========================================

Tests just the MIDI file loading step to verify basic automation works.

Author: DrumTracKAI v1.1.7
Date: July 23, 2025
"""

import time
from pathlib import Path

try:
    import pyautogui
    import pygetwindow as gw
    print("SUCCESS Libraries imported successfully")
except ImportError as e:
    print(f"ERROR Import error: {e}")
    exit(1)

# Configure pyautogui
pyautogui.FAILSAFE = True
pyautogui.PAUSE = 2.0

def main():
    print("AUDIO SD3 SINGLE STEP TEST - MIDI FILE LOADING")
    print("=" * 60)
    
    # Find SD3 window
    print("1. Finding SD3 window...")
    windows = gw.getAllWindows()
    sd3_window = None
    
    for window in windows:
        if 'Superior Drummer' in window.title or 'SD3' in window.title:
            sd3_window = window
            print(f"SUCCESS Found SD3: '{window.title}'")
            break
    
    if not sd3_window:
        print("ERROR SD3 window not found!")
        return
    
    # Focus SD3 window
    print("2. Focusing SD3 window...")
    try:
        sd3_window.activate()
        time.sleep(3)
        print("SUCCESS SD3 window focused")
    except Exception as e:
        print(f"ERROR Error focusing window: {e}")
        return
    
    # Get first MIDI file
    midi_dir = Path(__file__).parent / "sd3_midi_patterns"
    midi_files = list(midi_dir.glob("*.mid"))
    
    if not midi_files:
        print("ERROR No MIDI files found!")
        return
    
    test_midi = midi_files[0]
    print(f"3. Testing with MIDI file: {test_midi.name}")
    
    # Attempt to open file dialog
    print("4. Opening file dialog with Ctrl+O...")
    try:
        pyautogui.hotkey('ctrl', 'o')
        time.sleep(3)
        print("SUCCESS Ctrl+O command sent")
        
        # Type file path
        print(f"5. Typing file path: {test_midi}")
        pyautogui.write(str(test_midi))
        time.sleep(2)
        print("SUCCESS File path typed")
        
        # Press Enter
        print("6. Pressing Enter to load...")
        pyautogui.press('enter')
        time.sleep(3)
        print("SUCCESS Enter pressed")
        
        print("\nCOMPLETE Single step test completed!")
        print("Please check if the MIDI file loaded in SD3.")
        print("If it worked, we can proceed with the full workflow.")
        
    except Exception as e:
        print(f"ERROR Error during automation: {e}")

if __name__ == "__main__":
    main()

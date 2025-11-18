#!/usr/bin/env python3
"""
SD3 Key Press Test
==================

Simple test to verify if automation key presses are reaching SD3.
This will help diagnose the window focus/activation issue.

Author: DrumTracKAI v1.1.7
Date: July 23, 2025
"""

import time

try:
    import pyautogui
    pyautogui.FAILSAFE = True
    pyautogui.PAUSE = 2.0
    print("SUCCESS pyautogui imported successfully")
except ImportError as e:
    print(f"ERROR Import error: {e}")
    exit(1)

def main():
    print("AUDIO SD3 KEY PRESS TEST")
    print("=" * 50)
    print("This will test if key presses reach SD3 window")
    print("=" * 50)
    
    print("\nINSTRUCTIONS:")
    print("1. Click on Superior Drummer 3 window to focus it")
    print("2. Make sure SD3 is the active window")
    print("3. Watch for cursor movement or timeline changes")
    print("4. Press ENTER here when SD3 is focused")
    
    input("\nPress ENTER when SD3 is focused and ready...")
    
    print("\nINSPECTING Testing key presses...")
    print("You should see effects in SD3 if automation is working:")
    
    # Test 1: Home key (should move cursor to start)
    print("\nTest 1: Sending HOME key...")
    print("Expected: Timeline cursor should move to beginning")
    pyautogui.press('home')
    time.sleep(3)
    
    input("Did you see the cursor move to start? Press ENTER to continue...")
    
    # Test 2: Right arrow (should move cursor forward)
    print("\nTest 2: Sending RIGHT arrow key...")
    print("Expected: Timeline cursor should move forward")
    pyautogui.press('right')
    time.sleep(2)
    
    input("Did you see the cursor move forward? Press ENTER to continue...")
    
    # Test 3: Space bar (should play/pause)
    print("\nTest 3: Sending SPACE bar...")
    print("Expected: Should start/stop playback")
    pyautogui.press('space')
    time.sleep(2)
    
    input("Did playback start/stop? Press ENTER to continue...")
    
    # Test 4: Alt+T (Track menu)
    print("\nTest 4: Sending ALT+T...")
    print("Expected: Track menu should open")
    pyautogui.hotkey('alt', 't')
    time.sleep(3)
    
    input("Did the Track menu open? Press ENTER to continue...")
    
    # Test 5: Escape (close menu)
    print("\nTest 5: Sending ESCAPE...")
    print("Expected: Should close any open menu")
    pyautogui.press('escape')
    time.sleep(2)
    
    print("\n" + "="*50)
    print("KEY PRESS TEST RESULTS")
    print("="*50)
    
    print("\nPlease report which tests worked:")
    print("1. HOME key moved cursor to start: Y/N")
    print("2. RIGHT arrow moved cursor forward: Y/N") 
    print("3. SPACE bar started/stopped playback: Y/N")
    print("4. ALT+T opened Track menu: Y/N")
    print("5. ESCAPE closed menu: Y/N")
    
    print("\nIf NONE of these worked, the issue is:")
    print("- Window focus/activation problem")
    print("- SD3 not receiving key events")
    print("- Automation permissions issue")
    
    print("\nIf SOME worked but not others:")
    print("- Specific key combinations may be blocked")
    print("- SD3 may not respond to certain shortcuts")
    
    print("\nIf ALL worked:")
    print("- Basic automation is functional")
    print("- Issue is in the specific workflow sequence")

if __name__ == "__main__":
    main()

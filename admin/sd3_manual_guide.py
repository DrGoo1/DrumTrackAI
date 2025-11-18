#!/usr/bin/env python3
"""
Manual SD3 Step-by-Step Guide with Minimal Automation
=====================================================

Since window focusing is failing, this provides a manual guide with
minimal automation support - just the key presses you need.

Author: DrumTracKAI v1.1.7
Date: July 23, 2025
"""

import time
from pathlib import Path

try:
    import pyautogui
    pyautogui.FAILSAFE = True
    pyautogui.PAUSE = 1.0
    AUTOMATION_AVAILABLE = True
except ImportError:
    AUTOMATION_AVAILABLE = False

def main():
    print("AUDIO SD3 MANUAL STEP-BY-STEP GUIDE")
    print("=" * 60)
    print("Since automation is having window focus issues,")
    print("let's do this manually with minimal automation support.")
    print("=" * 60)
    
    # Get MIDI file info
    base_path = Path(__file__).parent
    midi_dir = base_path / "sd3_midi_patterns"
    output_dir = base_path / "sd3_extracted_samples"
    
    midi_files = list(midi_dir.glob("*.mid"))
    if not midi_files:
        print("ERROR No MIDI files found!")
        return
    
    test_midi = midi_files[0]
    instrument_name = test_midi.stem.rsplit('_', 1)[0]
    
    print(f"Test file: {test_midi.name}")
    print(f"Instrument: {instrument_name}")
    print(f"Full path: {test_midi}")
    print(f"Output dir: {output_dir}")
    
    print("\n" + "="*60)
    print("MANUAL STEPS TO FOLLOW:")
    print("="*60)
    
    print("\n1. FOLDER MANUALLY FOCUS SD3")
    print("   - Click on Superior Drummer 3 window to make it active")
    print("   - Ensure SD3 is ready and responsive")
    input("   Press ENTER when SD3 is focused and ready...")
    
    print("\n2. DIRECTORY LOAD MIDI FILE")
    print("   - I'll send Ctrl+O to open file dialog")
    print("   - Then I'll type the file path")
    print("   - Then press Enter to load")
    
    if AUTOMATION_AVAILABLE:
        input("   Press ENTER to execute Ctrl+O...")
        print("   Sending Ctrl+O...")
        pyautogui.hotkey('ctrl', 'o')
        time.sleep(3)
        
        input("   Press ENTER to type file path...")
        print(f"   Typing: {test_midi}")
        pyautogui.write(str(test_midi))
        time.sleep(2)
        
        input("   Press ENTER to load file...")
        print("   Pressing Enter...")
        pyautogui.press('enter')
        time.sleep(3)
    else:
        print(f"   MANUAL: Press Ctrl+O, then type: {test_midi}")
        print("   Then press Enter to load")
        input("   Press ENTER when MIDI file is loaded...")
    
    print("\n3. ⏱ POSITION AT BEAT 1.3")
    print("   - I'll send Home to go to start")
    print("   - Then move to beat 1.3")
    
    if AUTOMATION_AVAILABLE:
        input("   Press ENTER to go to start...")
        print("   Sending Home key...")
        pyautogui.press('home')
        time.sleep(2)
        
        input("   Press ENTER to move to beat 1.3...")
        print("   Moving to beat 1.3 (3 right arrows)...")
        for i in range(3):
            pyautogui.press('right')
            time.sleep(0.5)
    else:
        print("   MANUAL: Press Home, then Right arrow 3 times")
        input("   Press ENTER when positioned at beat 1.3...")
    
    print("\n4. AUDIO OPEN TRACK MENU -> BOUNCE")
    print("   WARNING  CRITICAL: This must open BOUNCE, not record!")
    print("   - I'll send Alt+T for Track menu")
    print("   - Then 'B' for Bounce")
    
    if AUTOMATION_AVAILABLE:
        input("   Press ENTER to open Track menu...")
        print("   Sending Alt+T...")
        pyautogui.hotkey('alt', 't')
        time.sleep(3)
        
        input("   Press ENTER to select Bounce...")
        print("   Sending 'B' for Bounce...")
        pyautogui.press('b')
        time.sleep(3)
    else:
        print("   MANUAL: Press Alt+T, then 'B' for Bounce")
        input("   Press ENTER when Bounce dialog is open...")
    
    print("\n5.  CONFIGURE ADVANCED SETTINGS")
    print("   - Navigate to Advanced tab")
    print("   - Select 'bounce output channels' radio button")
    print("   - Ensure 1 stereo file output")
    print("   MANUAL: Please configure these settings manually")
    input("   Press ENTER when Advanced settings are configured...")
    
    print("\n6. DIRECTORY SET OUTPUT FOLDER AND START BOUNCE")
    print("   - I'll type the output folder path")
    print("   - Then press Enter to start bounce")
    
    if AUTOMATION_AVAILABLE:
        input("   Press ENTER to set output folder...")
        print(f"   Typing output folder: {output_dir}")
        pyautogui.write(str(output_dir))
        time.sleep(2)
        
        input("   Press ENTER to start bounce...")
        print("   Starting bounce...")
        pyautogui.press('enter')
        time.sleep(2)
    else:
        print(f"   MANUAL: Type output folder: {output_dir}")
        print("   Then press Enter to start bounce")
        input("   Press ENTER when bounce has started...")
    
    print("\n7. ⏳ WAIT FOR BOUNCE COMPLETION")
    print("   - Wait for bounce to complete")
    print("   - Look for 'Out_1+2.wav' in output folder")
    print("   - File should appear in:", output_dir)
    input("   Press ENTER when bounce is complete and Out_1+2.wav exists...")
    
    print("\n8.  RENAME OUTPUT FILE")
    print(f"   - Rename 'Out_1+2.wav' to '{instrument_name}.wav'")
    
    try:
        original_file = output_dir / "Out_1+2.wav"
        new_file = output_dir / f"{instrument_name}.wav"
        
        if original_file.exists():
            original_file.rename(new_file)
            print(f"   SUCCESS Renamed: {original_file.name} → {new_file.name}")
        else:
            print(f"   ERROR Original file not found: {original_file}")
            print("   MANUAL: Please rename Out_1+2.wav manually")
    except Exception as e:
        print(f"   ERROR Rename error: {e}")
        print("   MANUAL: Please rename Out_1+2.wav manually")
    
    print("\n" + "="*60)
    print("COMPLETE MANUAL PROCESS COMPLETE!")
    print("="*60)
    print("If this worked, we know the workflow is correct.")
    print("Then we can fix the automation window focusing issue.")
    
    # Check if file was created
    final_file = output_dir / f"{instrument_name}.wav"
    if final_file.exists():
        print(f"SUCCESS SUCCESS: Found {final_file.name}")
        print("The manual workflow worked! Now we can automate it properly.")
    else:
        print("ERROR File not found. Please check which step failed.")

if __name__ == "__main__":
    main()

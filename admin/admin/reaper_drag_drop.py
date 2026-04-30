#!/usr/bin/env python3
"""
Reaper Drag and Drop - Alternative MIDI Import
==============================================

Since Ctrl+I isn't working, let's try drag and drop from File Explorer.
This mimics the manual process more closely.

Author: DrumTracKAI v1.1.7
Date: July 23, 2025
"""

import time
from pathlib import Path
import subprocess
import os

try:
    import pyautogui
    import pygetwindow as gw
    pyautogui.FAILSAFE = True
    pyautogui.PAUSE = 1.0
    print("SUCCESS Automation ready")
except ImportError as e:
    print(f"ERROR Import error: {e}")
    exit(1)

def open_file_explorer_to_midi(midi_file):
    """Open File Explorer to the MIDI file location"""
    print(f"\nDIRECTORY Opening File Explorer to MIDI location...")
    
    try:
        # Open File Explorer to the MIDI directory
        midi_dir = midi_file.parent
        subprocess.run(['explorer', str(midi_dir)], check=True)
        time.sleep(3)
        
        print(f"SUCCESS File Explorer opened to: {midi_dir}")
        print(f"Target file: {midi_file.name}")
        
        return True
        
    except Exception as e:
        print(f"ERROR Failed to open File Explorer: {e}")
        return False

def manual_drag_drop_instructions(midi_file):
    """Provide manual drag and drop instructions"""
    print(f"\n MANUAL DRAG AND DROP INSTRUCTIONS")
    print("=" * 50)
    print(f"1. File Explorer should be open showing: {midi_file.parent}")
    print(f"2. Find the file: {midi_file.name}")
    print(f"3. Drag the MIDI file from File Explorer")
    print(f"4. Drop it onto the Reaper timeline at beat 1.3")
    print(f"5. The MIDI should appear in the timeline")
    
    print(f"\nTARGET SPECIFIC STEPS:")
    print(f"• Click and hold on {midi_file.name} in File Explorer")
    print(f"• Drag it to the Reaper window")
    print(f"• Drop it at the beat 1.3 position on the timeline")
    print(f"• Release the mouse button")
    
    response = input(f"\nDid you successfully drag and drop the MIDI? (y/n): ").lower()
    
    if response.startswith('y'):
        print("SUCCESS Manual drag and drop successful!")
        return True
    else:
        print("ERROR Manual drag and drop failed")
        return False

def alternative_import_methods(midi_file):
    """Try alternative import methods"""
    print(f"\n ALTERNATIVE IMPORT METHODS")
    print("=" * 40)
    
    print(f"Let's try different ways to import the MIDI:")
    print(f"File: {midi_file}")
    
    methods = [
        "1. Drag and drop from File Explorer",
        "2. File → Import → MIDI File",
        "3. Right-click timeline → Insert → Media File",
        "4. Double-click on timeline and browse"
    ]
    
    for method in methods:
        print(f"   {method}")
    
    print(f"\n Let's try Method 1: Drag and Drop")
    
    # Open File Explorer
    if not open_file_explorer_to_midi(midi_file):
        return False
    
    # Manual drag and drop
    return manual_drag_drop_instructions(midi_file)

def verify_midi_in_timeline():
    """Verify MIDI appeared in timeline"""
    print(f"\nINSPECTING TIMELINE VERIFICATION")
    print("=" * 30)
    print("Look at the Reaper timeline:")
    print("• Do you see MIDI notes/data?")
    print("• Are there colored blocks showing the MIDI content?")
    print("• Is the MIDI on the track with SD3?")
    
    response = input(f"\nIs MIDI visible in the timeline? (y/n): ").lower()
    
    if response.startswith('y'):
        print("SUCCESS MIDI successfully imported!")
        
        # Check position
        print(f"\n POSITION CHECK:")
        print("Where is the MIDI positioned?")
        print("1. At beat 1.1 (start)")
        print("2. At beat 1.3 (correct position)")
        print("3. Somewhere else")
        
        position = input("Enter position (1, 2, or 3): ").strip()
        
        if position == "2":
            print("SUCCESS MIDI at correct position (1.3)!")
            return "positioned"
        elif position == "1":
            print("WARNING MIDI at 1.1 - needs repositioning to 1.3")
            return "needs_positioning"
        else:
            print("WARNING MIDI at wrong position - needs repositioning")
            return "needs_positioning"
    else:
        print("ERROR MIDI not visible - import failed")
        return "failed"

def reposition_midi_to_1_3():
    """Reposition MIDI from current location to beat 1.3"""
    print(f"\n⏱ REPOSITIONING MIDI TO BEAT 1.3")
    print("=" * 40)
    
    print("Manual repositioning steps:")
    print("1. Click on the MIDI item to select it")
    print("2. Drag it to beat 1.3 on the timeline")
    print("3. OR use Edit → Move items to cursor (after positioning cursor at 1.3)")
    
    response = input(f"\nDid you reposition MIDI to beat 1.3? (y/n): ").lower()
    
    if response.startswith('y'):
        print("SUCCESS MIDI repositioned to beat 1.3!")
        return True
    else:
        print("ERROR MIDI repositioning failed")
        return False

def main():
    """Main drag and drop automation"""
    print("AUDIO REAPER DRAG AND DROP AUTOMATION")
    print("=" * 70)
    print("Alternative MIDI import using drag and drop")
    print("=" * 70)
    
    # Setup
    base_path = Path(__file__).parent
    midi_dir = base_path / "sd3_midi_patterns"
    
    # Get test file
    midi_files = list(midi_dir.glob("*.mid"))
    if not midi_files:
        print("ERROR No MIDI files found!")
        return
    
    test_file = midi_files[0]
    print(f"\n TEST FILE: {test_file.name}")
    print(f"Full path: {test_file}")
    
    print(f"\nLAUNCH STARTING DRAG AND DROP IMPORT")
    input("Press ENTER to start...")
    
    # Try alternative import
    if not alternative_import_methods(test_file):
        print("ERROR All import methods failed")
        return
    
    # Verify import
    timeline_status = verify_midi_in_timeline()
    
    if timeline_status == "failed":
        print("ERROR MIDI import completely failed")
        return
    elif timeline_status == "needs_positioning":
        print("WARNING MIDI imported but needs repositioning")
        if not reposition_midi_to_1_3():
            print("ERROR Repositioning failed")
            return
    elif timeline_status == "positioned":
        print("SUCCESS MIDI imported and positioned correctly!")
    
    print(f"\nCOMPLETE SUCCESS!")
    print("MIDI is now in Reaper timeline at beat 1.3")
    print("Ready to continue with render selection and audio output")
    
    # Next steps
    print(f"\n NEXT STEPS:")
    print("1. Set render selection from beat 1.1 to 2.1")
    print("2. Render audio output")
    print("3. Verify WAV file creation")
    
    response = input(f"\nContinue with render steps? (y/n): ").lower()
    if response.startswith('y'):
        print(" Ready for render automation...")
        # Could call render functions here
    else:
        print("SUCCESS MIDI import phase complete!")

if __name__ == "__main__":
    main()

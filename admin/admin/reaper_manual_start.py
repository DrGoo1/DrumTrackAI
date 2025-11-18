#!/usr/bin/env python3
"""
Reaper Manual Start - Complete Reset
====================================

Let's start completely over with a simple manual approach.
First verify the workflow works manually, then automate step by step.

Author: DrumTracKAI v1.1.7
Date: July 23, 2025
"""

from pathlib import Path

def main():
    """Simple manual workflow guide"""
    print("AUDIO REAPER MANUAL START - COMPLETE RESET")
    print("=" * 60)
    print("Let's verify the basic workflow works manually first")
    print("=" * 60)
    
    # Get file info
    base_path = Path(__file__).parent
    midi_dir = base_path / "sd3_midi_patterns"
    output_dir = base_path / "sd3_extracted_samples"
    
    midi_files = list(midi_dir.glob("*.mid"))
    if not midi_files:
        print("ERROR No MIDI files found!")
        return
    
    test_file = midi_files[0]
    instrument_name = test_file.stem.rsplit('_', 1)[0] if '_' in test_file.stem else test_file.stem
    
    print(f"\nFOLDER DIRECTORIES:")
    print(f"MIDI files: {midi_dir}")
    print(f"Output: {output_dir}")
    
    print(f"\n TEST FILE:")
    print(f"MIDI: {test_file.name}")
    print(f"Instrument: {instrument_name}")
    print(f"Full path: {test_file}")
    
    print(f"\n MANUAL WORKFLOW TO TEST:")
    print(f"=" * 40)
    
    print(f"\n1. DIRECTORY IMPORT MIDI MANUALLY:")
    print(f"   In Reaper:")
    print(f"   - Go to Insert menu → Media File")
    print(f"   - Browse to: {test_file}")
    print(f"   - Import the MIDI file")
    print(f"   - Verify MIDI appears in timeline")
    
    print(f"\n2. ⏱ POSITION AT BEAT 1.3:")
    print(f"   - Select the MIDI item")
    print(f"   - Drag it to beat 1.3 position")
    print(f"   - OR use Edit → Move items to cursor")
    
    print(f"\n3.  SET RENDER SELECTION:")
    print(f"   - Set timeline selection from beat 1.1 to 2.1")
    print(f"   - This captures the full audio including pre-roll")
    
    print(f"\n4. AUDIO RENDER AUDIO:")
    print(f"   - Go to File → Render")
    print(f"   - Set filename: {instrument_name}")
    print(f"   - Set output folder: {output_dir}")
    print(f"   - Ensure 'Time selection' is selected")
    print(f"   - Click Render")
    
    print(f"\n5. SUCCESS VERIFY OUTPUT:")
    print(f"   - Check that {instrument_name}.wav was created")
    print(f"   - File should be in: {output_dir}")
    
    print(f"\n" + "=" * 60)
    print(f"TARGET GOAL: Get ONE file working manually first")
    print(f"Then we can automate each step that works")
    print(f"=" * 60)
    
    print(f"\n CURRENT STATUS:")
    print(f"SUCCESS Reaper is open with SD3 loaded")
    print(f"SUCCESS Timeline is cleared")
    print(f"SUCCESS Ready for manual test")
    
    print(f"\nLAUNCH NEXT STEPS:")
    print(f"1. Try the manual workflow above")
    print(f"2. Report which step fails (if any)")
    print(f"3. Once manual works, we'll automate it")
    
    input(f"\nPress ENTER when you've tried the manual workflow...")
    
    # Check if file was created
    output_file = output_dir / f"{instrument_name}.wav"
    if output_file.exists():
        file_size = output_file.stat().st_size
        print(f"\nCOMPLETE SUCCESS! Manual workflow worked!")
        print(f"SUCCESS Created: {output_file.name}")
        print(f"SUCCESS Size: {file_size:,} bytes")
        print(f"SUCCESS Ready to automate this workflow")
        
        response = input(f"\nCreate automation for this working workflow? (y/n): ").lower()
        if response.startswith('y'):
            print(f"\n Next: Create automation based on working manual steps")
        
    else:
        print(f"\nERROR File not created: {output_file}")
        print(f"Which step failed in the manual workflow?")
        print(f"1. MIDI import")
        print(f"2. Positioning at 1.3") 
        print(f"3. Setting render selection")
        print(f"4. Rendering audio")
        
        failed_step = input(f"\nWhich step failed? (1-4): ").strip()
        print(f"\nLet's troubleshoot step {failed_step} first")

if __name__ == "__main__":
    main()

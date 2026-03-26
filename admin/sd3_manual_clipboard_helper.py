#!/usr/bin/env python3
"""
SD3 Manual Workflow with Clipboard Helper
=========================================

Since automation commands aren't reaching SD3, this provides a manual workflow
with clipboard assistance to make the process faster and more reliable.

Author: DrumTracKAI v1.1.7
Date: July 23, 2025
"""

import time
from pathlib import Path
import re

try:
    import pyperclip
    CLIPBOARD_AVAILABLE = True
    print("SUCCESS Clipboard support available")
except ImportError:
    CLIPBOARD_AVAILABLE = False
    print("WARNING  Clipboard not available - install pyperclip for easier workflow")

class SD3ManualClipboardHelper:
    """Manual SD3 workflow with clipboard assistance"""
    
    def __init__(self):
        self.base_path = Path(__file__).parent
        self.midi_dir = self.base_path / "sd3_midi_patterns"
        self.output_dir = self.base_path / "sd3_extracted_samples"
        
        self.output_dir.mkdir(exist_ok=True)
        
        print(f"FOLDER MIDI directory: {self.midi_dir}")
        print(f"FOLDER Output directory: {self.output_dir}")
    
    def get_midi_files(self):
        """Get list of all MIDI files to process"""
        midi_files = list(self.midi_dir.glob("*.mid"))
        midi_files.sort()
        return midi_files
    
    def extract_instrument_name(self, midi_filename):
        """Extract instrument name from MIDI filename"""
        name = midi_filename.replace('.mid', '')
        match = re.match(r'(.+)_(\d+)$', name)
        if match:
            return match.group(1)
        return name
    
    def copy_to_clipboard(self, text):
        """Copy text to clipboard if available"""
        if CLIPBOARD_AVAILABLE:
            pyperclip.copy(text)
            print(f" Copied to clipboard: {text}")
            return True
        else:
            print(f" COPY MANUALLY: {text}")
            return False
    
    def get_next_unprocessed_file(self):
        """Get next MIDI file that hasn't been processed"""
        midi_files = self.get_midi_files()
        
        for midi_file in midi_files:
            instrument_name = self.extract_instrument_name(midi_file.name)
            output_file = self.output_dir / f"{instrument_name}.wav"
            
            if not output_file.exists():
                return midi_file, instrument_name
        
        return None, None
    
    def monitor_for_output_and_rename(self, expected_instrument_name, timeout=300):
        """Monitor for Out_1+2.wav and auto-rename when found"""
        print(f"\n Monitoring for Out_1+2.wav...")
        print(f"Will auto-rename to: {expected_instrument_name}.wav")
        print(f"Timeout: {timeout} seconds")
        
        original_file = self.output_dir / "Out_1+2.wav"
        target_file = self.output_dir / f"{expected_instrument_name}.wav"
        
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            if original_file.exists() and original_file.stat().st_size > 0:
                try:
                    # Wait a moment to ensure file is fully written
                    time.sleep(2)
                    
                    # Rename the file
                    original_file.rename(target_file)
                    file_size = target_file.stat().st_size
                    
                    print(f"\nSUCCESS SUCCESS! Auto-renamed:")
                    print(f"   {original_file.name} → {target_file.name}")
                    print(f"   File size: {file_size:,} bytes")
                    
                    return target_file
                    
                except Exception as e:
                    print(f"ERROR Rename error: {e}")
                    print(f"Manual rename needed: {original_file} → {target_file}")
                    return None
            
            # Show progress every 15 seconds
            elapsed = int(time.time() - start_time)
            if elapsed % 15 == 0 and elapsed > 0:
                print(f"   Still waiting... {elapsed}s/{timeout}s")
            
            time.sleep(3)
        
        print(f"\nERROR Timeout: No Out_1+2.wav found after {timeout}s")
        return None
    
    def process_single_file_manual(self, midi_file, instrument_name):
        """Process one file with manual workflow and clipboard assistance"""
        print(f"\n{'='*70}")
        print(f"MANUAL PROCESSING: {midi_file.name}")
        print(f"Target instrument: {instrument_name}")
        print(f"{'='*70}")
        
        # Check if already processed
        final_file = self.output_dir / f"{instrument_name}.wav"
        if final_file.exists():
            print(f"SUCCESS Already processed: {final_file.name}")
            return True
        
        print(f"\n STEP 1: LOAD MIDI FILE")
        print(f"File path ready for clipboard...")
        self.copy_to_clipboard(str(midi_file))
        
        print(f"\nMANUAL STEPS:")
        print(f"1. Focus Superior Drummer 3 window")
        print(f"2. Press Ctrl+O to open file dialog")
        print(f"3. Paste the file path (Ctrl+V)")
        print(f"4. Press Enter to load the MIDI file")
        print(f"5. Verify MIDI appears in timeline")
        
        input(f"\nPress ENTER when MIDI file is loaded in SD3...")
        
        print(f"\n⏱ STEP 2: POSITION AT BEAT 1.3")
        print(f"MANUAL STEPS:")
        print(f"1. Press STOP key to return cursor to start")
        print(f"2. Press Right arrow 3 times to reach beat 1.3")
        print(f"3. Verify cursor is at beat 1.3")
        
        input(f"\nPress ENTER when positioned at beat 1.3...")
        
        print(f"\nAUDIO STEP 3: OPEN TRACK → BOUNCE")
        print(f"MANUAL STEPS:")
        print(f"1. Press Alt+T to open Track menu")
        print(f"2. Press B to select Bounce")
        print(f"3. Verify Bounce dialog opens (NOT record dialog)")
        
        input(f"\nPress ENTER when Bounce dialog is open...")
        
        print(f"\n STEP 4: CONFIGURE BOUNCE SETTINGS")
        print(f"MANUAL STEPS:")
        print(f"1. Navigate to Advanced tab")
        print(f"2. Select 'bounce output channels' radio button")
        print(f"3. Ensure single stereo file output")
        
        input(f"\nPress ENTER when Advanced settings are configured...")
        
        print(f"\nDIRECTORY STEP 5: SET OUTPUT FOLDER")
        print(f"Output folder ready for clipboard...")
        self.copy_to_clipboard(str(self.output_dir))
        
        print(f"MANUAL STEPS:")
        print(f"1. In bounce dialog, set output folder")
        print(f"2. Paste the output path (Ctrl+V)")
        print(f"3. Press Enter to start bounce")
        print(f"4. Wait for bounce to complete")
        
        input(f"\nPress ENTER when bounce has started...")
        
        print(f"\n⏳ STEP 6: WAITING FOR BOUNCE COMPLETION")
        print(f"Starting automatic monitoring for Out_1+2.wav...")
        
        # Start monitoring in background
        result_file = self.monitor_for_output_and_rename(instrument_name, timeout=180)
        
        if result_file:
            print(f"\nCOMPLETE SUCCESS: {midi_file.name} → {result_file.name}")
            return True
        else:
            print(f"\nERROR FAILED: Bounce did not complete or file not found")
            print(f"Check SD3 for errors or manually rename Out_1+2.wav")
            return False
    
    def get_progress_stats(self):
        """Get processing progress statistics"""
        midi_files = self.get_midi_files()
        total_files = len(midi_files)
        
        completed_count = 0
        for midi_file in midi_files:
            instrument_name = self.extract_instrument_name(midi_file.name)
            output_file = self.output_dir / f"{instrument_name}.wav"
            if output_file.exists():
                completed_count += 1
        
        remaining_count = total_files - completed_count
        progress_percent = (completed_count / total_files) * 100 if total_files > 0 else 0
        
        return {
            'total': total_files,
            'completed': completed_count,
            'remaining': remaining_count,
            'progress_percent': progress_percent
        }

def main():
    """Main manual workflow with clipboard assistance"""
    print("AUDIO SD3 MANUAL WORKFLOW WITH CLIPBOARD HELPER")
    print("=" * 70)
    print("Since automation isn't working, this provides manual workflow")
    print("with clipboard assistance to speed up the process.")
    print("=" * 70)
    
    helper = SD3ManualClipboardHelper()
    
    # Show progress stats
    stats = helper.get_progress_stats()
    print(f"\nANALYSIS PROGRESS STATISTICS:")
    print(f"Total files: {stats['total']}")
    print(f"Completed: {stats['completed']}")
    print(f"Remaining: {stats['remaining']}")
    print(f"Progress: {stats['progress_percent']:.1f}%")
    
    if stats['remaining'] == 0:
        print(f"\nCOMPLETE ALL FILES PROCESSED!")
        return
    
    # Get next file to process
    next_file, instrument_name = helper.get_next_unprocessed_file()
    
    if not next_file:
        print(f"\nSUCCESS No unprocessed files found!")
        return
    
    print(f"\nTARGET NEXT FILE TO PROCESS:")
    print(f"MIDI file: {next_file.name}")
    print(f"Instrument: {instrument_name}")
    print(f"Full path: {next_file}")
    
    print(f"\n CLIPBOARD FEATURES:")
    if CLIPBOARD_AVAILABLE:
        print(f"SUCCESS File paths will be copied to clipboard automatically")
        print(f"SUCCESS Just paste with Ctrl+V in SD3 dialogs")
    else:
        print(f"ERROR Install pyperclip for clipboard features")
        print(f"   pip install pyperclip")
    
    input(f"\nPress ENTER to start manual processing...")
    
    success = helper.process_single_file_manual(next_file, instrument_name)
    
    if success:
        print(f"\nCOMPLETE MANUAL PROCESSING SUCCESSFUL!")
        print(f"File extracted: {instrument_name}.wav")
        
        # Show updated progress
        updated_stats = helper.get_progress_stats()
        print(f"\nUpdated progress: {updated_stats['completed']}/{updated_stats['total']} ({updated_stats['progress_percent']:.1f}%)")
        print(f"Remaining: {updated_stats['remaining']} files")
        
    else:
        print(f"\nERROR MANUAL PROCESSING FAILED!")
        print(f"Check SD3 for errors or try again.")

if __name__ == "__main__":
    main()

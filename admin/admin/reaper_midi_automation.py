#!/usr/bin/env python3
"""
Reaper MIDI Automation - Focused Workflow
=========================================

Automates the specific Reaper workflow:
1. Import MIDI clip into first track
2. Position at beat 1.3
3. Render/capture audio output
4. Save with proper naming

Since Reaper is already open with SD3 loaded, this focuses on the 
automation steps needed for each MIDI file.

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
    pyautogui.PAUSE = 1.0
    print("SUCCESS Automation libraries loaded")
except ImportError as e:
    print(f"ERROR Import error: {e}")
    exit(1)

class ReaperMIDIAutomation:
    """Focused Reaper automation for MIDI processing"""
    
    def __init__(self):
        self.base_path = Path(__file__).parent
        self.midi_dir = self.base_path / "sd3_midi_patterns"
        self.output_dir = self.base_path / "sd3_extracted_samples"
        
        self.output_dir.mkdir(exist_ok=True)
        
        print(f"FOLDER MIDI directory: {self.midi_dir}")
        print(f"FOLDER Output directory: {self.output_dir}")
        
        # Reaper window reference
        self.reaper_window = None
    
    def find_reaper_window(self):
        """Find and focus Reaper window"""
        print("\nINSPECTING Finding Reaper window...")
        
        windows = gw.getAllWindows()
        for window in windows:
            if 'REAPER' in window.title.upper():
                self.reaper_window = window
                print(f"SUCCESS Found Reaper: '{window.title}'")
                
                try:
                    window.activate()
                    time.sleep(2)
                    print("SUCCESS Reaper window focused")
                    return True
                except Exception as e:
                    print(f"WARNING  Window focus issue: {e}")
                    print("Please manually click on Reaper window")
                    input("Press ENTER when Reaper is focused...")
                    return True
        
        print("ERROR Reaper window not found!")
        print("Please ensure Reaper is open")
        return False
    
    def import_midi_file(self, midi_file):
        """Import MIDI file into Reaper"""
        print(f"\n Importing MIDI: {midi_file.name}")
        
        try:
            # Method 1: Drag and drop simulation
            print("Attempting drag and drop import...")
            
            # First, try the Insert menu approach
            print("Using Insert menu...")
            pyautogui.hotkey('alt', 'i')  # Insert menu
            time.sleep(1)
            
            # Look for Media File option
            pyautogui.press('m')  # Media File
            time.sleep(2)
            
            # Type file path in dialog
            print(f"Typing file path: {midi_file}")
            pyautogui.write(str(midi_file))
            time.sleep(1)
            
            # Import file
            pyautogui.press('enter')
            time.sleep(3)
            
            print("SUCCESS MIDI import command sent")
            return True
            
        except Exception as e:
            print(f"ERROR Error importing MIDI: {e}")
            return False
    
    def position_midi_at_beat_1_3(self):
        """Position MIDI item at beat 1.3"""
        print(f"\n⏱ Positioning MIDI at beat 1.3...")
        
        try:
            # Select all items first
            print("Selecting all items...")
            pyautogui.hotkey('ctrl', 'a')
            time.sleep(1)
            
            # Move cursor to start of project
            print("Moving to project start...")
            pyautogui.press('home')
            time.sleep(1)
            
            # Set cursor position to beat 1.3
            # In Reaper, we can use the position field or grid navigation
            print("Setting position to beat 1.3...")
            
            # Method 1: Use position field (Ctrl+Shift+P)
            pyautogui.hotkey('ctrl', 'shift', 'p')
            time.sleep(1)
            
            # Type position (assuming 4/4 time, beat 1.3 = 0.75 beats from start)
            # This might need adjustment based on tempo and time signature
            pyautogui.write("1.3")  # or "0.75" depending on Reaper's format
            time.sleep(1)
            pyautogui.press('enter')
            time.sleep(1)
            
            # Alternative method: Use grid navigation
            print("Using grid navigation as backup...")
            # Set grid to beats
            pyautogui.hotkey('alt', '3')  # Set grid to 1/4 note
            time.sleep(1)
            
            # Move selected items to cursor position
            pyautogui.press('home')  # Go to start
            time.sleep(0.5)
            
            # Move 3 grid units (to beat 1.3)
            for i in range(3):
                pyautogui.press('right')
                time.sleep(0.3)
            
            # Move items to cursor position
            pyautogui.hotkey('ctrl', 'shift', 'm')  # Move items to cursor
            time.sleep(1)
            
            print("SUCCESS MIDI positioning completed")
            return True
            
        except Exception as e:
            print(f"ERROR Error positioning MIDI: {e}")
            return False
    
    def set_render_bounds(self):
        """Set render bounds around the MIDI item"""
        print(f"\n Setting render bounds...")
        
        try:
            # Select all items
            pyautogui.hotkey('ctrl', 'a')
            time.sleep(1)
            
            # Set time selection to selected items
            pyautogui.hotkey('ctrl', 'alt', 'x')  # Set time selection to items
            time.sleep(1)
            
            # Add a bit of padding (optional)
            # Extend selection by 1 second at the end
            pyautogui.press('end')  # Go to end of selection
            time.sleep(0.5)
            pyautogui.press('right', presses=4)  # Add some padding
            time.sleep(0.5)
            
            print("SUCCESS Render bounds set")
            return True
            
        except Exception as e:
            print(f"ERROR Error setting render bounds: {e}")
            return False
    
    def render_audio(self, output_filename):
        """Render audio to file"""
        print(f"\nAUDIO Rendering audio: {output_filename}")
        
        try:
            # Open render dialog
            print("Opening render dialog...")
            pyautogui.hotkey('ctrl', 'alt', 'r')  # Render dialog
            time.sleep(3)
            
            # Navigate to filename field
            print("Setting output filename...")
            # The render dialog layout may vary, try multiple approaches
            
            # Method 1: Tab to filename field
            pyautogui.press('tab', presses=3)
            time.sleep(1)
            
            # Clear existing filename and set new one
            pyautogui.hotkey('ctrl', 'a')
            time.sleep(0.5)
            pyautogui.write(output_filename)
            time.sleep(1)
            
            # Set output directory
            print(f"Setting output directory...")
            # Navigate to directory field (this may need adjustment)
            pyautogui.press('tab', presses=2)
            time.sleep(1)
            pyautogui.hotkey('ctrl', 'a')
            time.sleep(0.5)
            pyautogui.write(str(self.output_dir))
            time.sleep(1)
            
            # Ensure WAV format is selected
            print("Ensuring WAV format...")
            # This depends on Reaper's render dialog layout
            # May need to click on format dropdown or use keyboard navigation
            
            # Start render
            print("Starting render...")
            pyautogui.press('enter')  # Start render
            time.sleep(2)
            
            print("SUCCESS Render started")
            return True
            
        except Exception as e:
            print(f"ERROR Error starting render: {e}")
            return False
    
    def wait_for_render_completion(self, expected_file, timeout=120):
        """Wait for render to complete"""
        print(f"\n⏳ Waiting for render completion...")
        
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            if expected_file.exists() and expected_file.stat().st_size > 0:
                # Wait a bit more to ensure file is fully written
                time.sleep(2)
                
                file_size = expected_file.stat().st_size
                print(f"SUCCESS Render completed!")
                print(f"   File: {expected_file.name}")
                print(f"   Size: {file_size:,} bytes")
                return expected_file
            
            elapsed = int(time.time() - start_time)
            if elapsed % 10 == 0 and elapsed > 0:
                print(f"   Waiting... {elapsed}s/{timeout}s")
            
            time.sleep(2)
        
        print(f"ERROR Render timeout after {timeout}s")
        return None
    
    def clear_project_items(self):
        """Clear all items from project for next MIDI file"""
        print(f"\n Clearing project items...")
        
        try:
            # Select all items
            pyautogui.hotkey('ctrl', 'a')
            time.sleep(1)
            
            # Delete selected items
            pyautogui.press('delete')
            time.sleep(1)
            
            # Clear time selection
            pyautogui.hotkey('ctrl', 'alt', 'z')  # Clear time selection
            time.sleep(1)
            
            print("SUCCESS Project cleared")
            return True
            
        except Exception as e:
            print(f"ERROR Error clearing project: {e}")
            return False
    
    def extract_instrument_name(self, midi_filename):
        """Extract instrument name from MIDI filename"""
        name = midi_filename.replace('.mid', '')
        match = re.match(r'(.+)_(\d+)$', name)
        if match:
            return match.group(1)
        return name
    
    def process_single_midi(self, midi_file):
        """Process single MIDI file through complete workflow"""
        print(f"\n{'='*70}")
        print(f"PROCESSING: {midi_file.name}")
        print(f"{'='*70}")
        
        instrument_name = self.extract_instrument_name(midi_file.name)
        output_file = self.output_dir / f"{instrument_name}.wav"
        
        print(f"Instrument: {instrument_name}")
        print(f"Output file: {output_file}")
        
        # Check if already processed
        if output_file.exists():
            print(f"SUCCESS Already processed: {output_file.name}")
            return True
        
        # Workflow steps
        workflow_steps = [
            ("Import MIDI file", lambda: self.import_midi_file(midi_file)),
            ("Position at beat 1.3", self.position_midi_at_beat_1_3),
            ("Set render bounds", self.set_render_bounds),
            ("Render audio", lambda: self.render_audio(instrument_name)),
        ]
        
        for step_name, step_func in workflow_steps:
            print(f"\n--- {step_name} ---")
            if not step_func():
                print(f"ERROR Failed at step: {step_name}")
                return False
            
            # Pause between steps for stability
            time.sleep(2)
        
        # Wait for render completion
        rendered_file = self.wait_for_render_completion(output_file)
        if not rendered_file:
            print("ERROR Render failed or timed out")
            return False
        
        # Clear project for next file
        self.clear_project_items()
        
        print(f"COMPLETE SUCCESS: {midi_file.name} → {rendered_file.name}")
        return True
    
    def run_batch_processing(self):
        """Run batch processing for all MIDI files"""
        midi_files = list(self.midi_dir.glob("*.mid"))
        if not midi_files:
            print("ERROR No MIDI files found!")
            return
        
        midi_files.sort()
        total_files = len(midi_files)
        
        print(f"\n BATCH PROCESSING: {total_files} files")
        print(f"=" * 50)
        
        success_count = 0
        failed_files = []
        
        for i, midi_file in enumerate(midi_files, 1):
            print(f"\nFOLDER Processing {i}/{total_files}: {midi_file.name}")
            
            if self.process_single_midi(midi_file):
                success_count += 1
                print(f"SUCCESS Progress: {success_count}/{total_files}")
            else:
                failed_files.append(midi_file.name)
                print(f"ERROR Failed: {midi_file.name}")
                
                # Ask user if they want to continue after failure
                response = input(f"Continue with remaining files? (y/n/q): ").lower()
                if response == 'q':
                    break
                elif response == 'n':
                    # Skip to next file
                    continue
        
        print(f"\nCOMPLETE BATCH PROCESSING COMPLETE!")
        print(f"Successfully processed: {success_count}/{total_files}")
        if failed_files:
            print(f"Failed files: {len(failed_files)}")
            for failed_file in failed_files[:5]:  # Show first 5 failed files
                print(f"  - {failed_file}")
            if len(failed_files) > 5:
                print(f"  ... and {len(failed_files) - 5} more")

def main():
    """Main Reaper MIDI automation"""
    print("AUDIO REAPER MIDI AUTOMATION")
    print("=" * 50)
    print("Focused workflow for MIDI processing in Reaper")
    print("Assumes Reaper is open with SD3 loaded")
    print("=" * 50)
    
    automation = ReaperMIDIAutomation()
    
    # Find and focus Reaper
    if not automation.find_reaper_window():
        print("ERROR Cannot proceed without Reaper window")
        return
    
    # Get MIDI files
    midi_files = list(automation.midi_dir.glob("*.mid"))
    if not midi_files:
        print("ERROR No MIDI files found!")
        return
    
    print(f"\nANALYSIS Found {len(midi_files)} MIDI files to process")
    
    # Processing options
    print(f"\nTARGET PROCESSING OPTIONS:")
    print(f"1. Test with single file")
    print(f"2. Batch process all files")
    
    choice = input(f"Select option (1/2): ").strip()
    
    if choice == "1":
        # Test with first file
        test_file = midi_files[0]
        print(f"\n Testing with: {test_file.name}")
        
        input(f"Press ENTER to start test...")
        success = automation.process_single_midi(test_file)
        
        if success:
            print(f"\nCOMPLETE TEST SUCCESSFUL!")
            response = input(f"Process all remaining files? (y/n): ").lower()
            if response.startswith('y'):
                automation.run_batch_processing()
        else:
            print(f"\nERROR TEST FAILED!")
            print(f"Check Reaper setup and automation steps")
            
    elif choice == "2":
        # Batch process all files
        print(f"\n Starting batch processing...")
        input(f"Press ENTER to begin...")
        automation.run_batch_processing()
    
    else:
        print("Invalid choice")

if __name__ == "__main__":
    main()

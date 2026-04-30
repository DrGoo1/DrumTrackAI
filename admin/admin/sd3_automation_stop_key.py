#!/usr/bin/env python3
"""
SD3 Automation with Stop Key Correction
=======================================

Uses the stop key to return cursor to start, then positions at beat 1.3.
This should resolve the cursor positioning issue.

Key insight: Stop key in SD3 returns cursor to start automatically.

Author: DrumTracKAI v1.1.7
Date: July 23, 2025
"""

import time
from pathlib import Path
import re

try:
    import pyautogui
    pyautogui.FAILSAFE = True
    pyautogui.PAUSE = 1.5
    print("SUCCESS Automation libraries loaded")
except ImportError as e:
    print(f"ERROR Import error: {e}")
    exit(1)

class SD3StopKeyAutomation:
    """SD3 automation using stop key for cursor positioning"""
    
    def __init__(self):
        self.base_path = Path(__file__).parent
        self.midi_dir = self.base_path / "sd3_midi_patterns"
        self.output_dir = self.base_path / "sd3_extracted_samples"
        
        self.output_dir.mkdir(exist_ok=True)
        
        print(f"MIDI directory: {self.midi_dir}")
        print(f"Output directory: {self.output_dir}")
    
    def stop_and_position_cursor(self):
        """Use stop key to return cursor to start, then move to beat 1.3"""
        print("\n⏹ Using STOP key to return cursor to start...")
        
        try:
            # Stop playback and return cursor to start
            print("Sending STOP key (should return cursor to start)...")
            pyautogui.press('space')  # Stop/pause key
            time.sleep(2)
            
            # Alternative stop keys to try
            print("Trying additional stop methods...")
            pyautogui.press('s')  # S key for stop
            time.sleep(1)
            
            # Now move to beat 1.3
            print("Moving to beat 1.3 (3 right arrows)...")
            for i in range(3):
                pyautogui.press('right')
                time.sleep(0.5)
                print(f"  Step {i+1}/3")
            
            print("SUCCESS Cursor positioning completed")
            return True
            
        except Exception as e:
            print(f"ERROR Error positioning cursor: {e}")
            return False
    
    def load_midi_file(self, midi_file):
        """Load MIDI file into SD3"""
        print(f"\nFOLDER Loading MIDI: {midi_file.name}")
        
        try:
            # Open file dialog
            print("Opening file dialog (Ctrl+O)...")
            pyautogui.hotkey('ctrl', 'o')
            time.sleep(3)
            
            # Type file path
            print(f"Typing file path: {midi_file}")
            pyautogui.write(str(midi_file))
            time.sleep(2)
            
            # Load file
            print("Loading file (Enter)...")
            pyautogui.press('enter')
            time.sleep(3)
            
            print("SUCCESS MIDI file load command sent")
            return True
            
        except Exception as e:
            print(f"ERROR Error loading MIDI: {e}")
            return False
    
    def open_track_bounce(self):
        """Open Track menu and select Bounce"""
        print("\nAUDIO Opening Track → Bounce...")
        
        try:
            # Method 1: Alt+T for Track menu
            print("Opening Track menu (Alt+T)...")
            pyautogui.hotkey('alt', 't')
            time.sleep(2)
            
            # Select Bounce
            print("Selecting Bounce (B key)...")
            pyautogui.press('b')
            time.sleep(3)
            
            print("SUCCESS Track → Bounce command sent")
            return True
            
        except Exception as e:
            print(f"ERROR Error opening Track → Bounce: {e}")
            return False
    
    def configure_and_start_bounce(self, output_path):
        """Configure bounce settings and start"""
        print(f"\nLAUNCH Configuring bounce for: {output_path}")
        
        try:
            # Navigate to Advanced tab (if needed)
            print("Navigating to Advanced settings...")
            pyautogui.press('tab')
            time.sleep(1)
            
            # Select bounce output channels
            print("Selecting bounce output channels...")
            pyautogui.press('space')  # Select radio button
            time.sleep(1)
            
            # Set output path
            print(f"Setting output path: {output_path}")
            pyautogui.write(str(output_path))
            time.sleep(2)
            
            # Start bounce
            print("Starting bounce (Enter)...")
            pyautogui.press('enter')
            time.sleep(2)
            
            print("SUCCESS Bounce configuration and start completed")
            return True
            
        except Exception as e:
            print(f"ERROR Error configuring bounce: {e}")
            return False
    
    def wait_for_bounce_completion(self, timeout=120):
        """Wait for Out_1+2.wav to be created"""
        print(f"\n⏳ Waiting for bounce completion (timeout: {timeout}s)...")
        
        expected_file = self.output_dir / "Out_1+2.wav"
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            if expected_file.exists() and expected_file.stat().st_size > 0:
                file_size = expected_file.stat().st_size
                print(f"SUCCESS Bounce completed! File: {expected_file.name} ({file_size:,} bytes)")
                return expected_file
            
            elapsed = int(time.time() - start_time)
            if elapsed % 10 == 0 and elapsed > 0:
                print(f"   Waiting... {elapsed}s/{timeout}s")
            
            time.sleep(2)
        
        print(f"ERROR Bounce timeout after {timeout}s")
        return None
    
    def rename_output_file(self, original_file, instrument_name):
        """Rename Out_1+2.wav to instrument name"""
        print(f"\n Renaming to: {instrument_name}.wav")
        
        try:
            new_file = self.output_dir / f"{instrument_name}.wav"
            original_file.rename(new_file)
            print(f"SUCCESS Renamed: {original_file.name} → {new_file.name}")
            return new_file
        except Exception as e:
            print(f"ERROR Error renaming file: {e}")
            return None
    
    def extract_instrument_name(self, midi_filename):
        """Extract instrument name from MIDI filename"""
        name = midi_filename.replace('.mid', '')
        match = re.match(r'(.+)_(\d+)$', name)
        if match:
            return match.group(1)
        return name
    
    def process_single_midi(self, midi_file):
        """Process one MIDI file with corrected workflow"""
        print(f"\n{'='*60}")
        print(f"PROCESSING: {midi_file.name}")
        print(f"Using STOP KEY for cursor positioning")
        print(f"{'='*60}")
        
        instrument_name = self.extract_instrument_name(midi_file.name)
        print(f"Instrument: {instrument_name}")
        
        # Check if already processed
        final_file = self.output_dir / f"{instrument_name}.wav"
        if final_file.exists():
            print(f"SUCCESS Already processed: {final_file.name}")
            return True
        
        print("\nTARGET CORRECTED WORKFLOW STEPS:")
        print("1. Load MIDI file")
        print("2. Use STOP key to return cursor to start")
        print("3. Move to beat 1.3")
        print("4. Open Track → Bounce")
        print("5. Configure and start bounce")
        print("6. Wait for completion and rename")
        
        input("\nPress ENTER to start corrected workflow...")
        
        # Step 1: Load MIDI
        if not self.load_midi_file(midi_file):
            print("ERROR Failed to load MIDI file")
            return False
        
        # Step 2 & 3: Stop and position cursor (CORRECTED)
        if not self.stop_and_position_cursor():
            print("ERROR Failed to position cursor")
            return False
        
        # Step 4: Open Track → Bounce
        if not self.open_track_bounce():
            print("ERROR Failed to open Track → Bounce")
            return False
        
        # Step 5: Configure and start bounce
        if not self.configure_and_start_bounce(self.output_dir):
            print("ERROR Failed to configure bounce")
            return False
        
        # Step 6: Wait for completion
        bounced_file = self.wait_for_bounce_completion()
        if not bounced_file:
            print("ERROR Bounce failed or timed out")
            return False
        
        # Step 7: Rename file
        final_file = self.rename_output_file(bounced_file, instrument_name)
        if not final_file:
            print("ERROR File rename failed")
            return False
        
        print(f"COMPLETE SUCCESS: {midi_file.name} → {final_file.name}")
        return True

def main():
    """Main execution with stop key correction"""
    print("AUDIO SD3 AUTOMATION WITH STOP KEY CORRECTION")
    print("=" * 60)
    print("KEY INSIGHT: Stop key returns cursor to start automatically")
    print("This should resolve cursor positioning issues")
    print("=" * 60)
    
    automation = SD3StopKeyAutomation()
    
    # Get first MIDI file for testing
    midi_files = list(automation.midi_dir.glob("*.mid"))
    if not midi_files:
        print("ERROR No MIDI files found!")
        return
    
    test_file = midi_files[0]
    print(f"\nTesting with: {test_file.name}")
    print("\nMANUAL PREPARATION:")
    print("1. Click on Superior Drummer 3 window to focus it")
    print("2. Ensure SD3 is ready and responsive")
    print("3. Make sure no playback is currently running")
    
    input("\nPress ENTER when SD3 is focused and ready...")
    
    success = automation.process_single_midi(test_file)
    
    if success:
        print("\nCOMPLETE STOP KEY AUTOMATION SUCCESSFUL!")
        print("The corrected workflow is working!")
    else:
        print("\nERROR STOP KEY AUTOMATION FAILED!")
        print("Check the steps above to identify remaining issues.")

if __name__ == "__main__":
    main()

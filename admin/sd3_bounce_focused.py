#!/usr/bin/env python3
"""
Focused SD3 Bounce Automation
=============================

Focuses specifically on the Track menu -> Bounce workflow to avoid
triggering recording instead of bouncing.

Based on user workflow:
1. Load MIDI and position at beat 1.3
2. Track menu -> Bounce (NOT record)
3. Configure Advanced settings for bounce output channels
4. Select folder and start bounce
5. Rename Out_1+2.wav to instrument name

Author: DrumTracKAI v1.1.7
Date: July 23, 2025
"""

import time
from pathlib import Path
import re

try:
    import pyautogui
    import pygetwindow as gw
    print("SUCCESS Automation libraries loaded")
except ImportError as e:
    print(f"ERROR Import error: {e}")
    exit(1)

# Configure pyautogui for reliable operation
pyautogui.FAILSAFE = True
pyautogui.PAUSE = 2.0  # Slower for reliability

class SD3BounceAutomation:
    """Focused bounce automation to avoid recording issues"""
    
    def __init__(self):
        self.base_path = Path(__file__).parent
        self.midi_dir = self.base_path / "sd3_midi_patterns"
        self.output_dir = self.base_path / "sd3_extracted_samples"
        
        # Ensure output directory exists
        self.output_dir.mkdir(exist_ok=True)
        
        print(f"MIDI directory: {self.midi_dir}")
        print(f"Output directory: {self.output_dir}")
    
    def find_and_focus_sd3(self):
        """Find and focus SD3 window"""
        print("\nINSPECTING Finding SD3 window...")
        
        windows = gw.getAllWindows()
        sd3_window = None
        
        for window in windows:
            if 'Superior Drummer' in window.title or 'SD3' in window.title:
                sd3_window = window
                print(f"SUCCESS Found SD3: '{window.title}'")
                break
        
        if not sd3_window:
            print("ERROR SD3 window not found!")
            return False
        
        try:
            sd3_window.activate()
            time.sleep(3)
            print("SUCCESS SD3 window focused")
            return True
        except Exception as e:
            print(f"ERROR Error focusing SD3: {e}")
            return False
    
    def load_midi_file(self, midi_file):
        """Load MIDI file into SD3"""
        print(f"\nFOLDER Loading MIDI: {midi_file.name}")
        
        try:
            # Open file dialog
            print("Opening file dialog (Ctrl+O)...")
            pyautogui.hotkey('ctrl', 'o')
            time.sleep(3)
            
            # Clear any existing path and type new one
            print("Clearing and typing file path...")
            pyautogui.hotkey('ctrl', 'a')  # Select all
            time.sleep(0.5)
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
    
    def position_timeline(self):
        """Position timeline at beat 1.3"""
        print("\n⏱ Positioning timeline at beat 1.3...")
        
        try:
            # Go to beginning
            print("Going to start (Home)...")
            pyautogui.press('home')
            time.sleep(2)
            
            # Move to beat 1.3 - try different approaches
            print("Moving to beat 1.3...")
            
            # Method 1: Right arrow keys (assuming each press = 1 beat)
            for i in range(3):
                pyautogui.press('right')
                time.sleep(0.5)
            
            print("SUCCESS Timeline positioning attempted")
            return True
            
        except Exception as e:
            print(f"ERROR Error positioning timeline: {e}")
            return False
    
    def open_bounce_dialog(self):
        """Open bounce dialog via Track menu - CRITICAL STEP"""
        print("\nAUDIO Opening bounce dialog...")
        print("WARNING  CRITICAL: This must open BOUNCE, not RECORD!")
        
        try:
            # Method 1: Alt+T for Track menu
            print("Opening Track menu (Alt+T)...")
            pyautogui.hotkey('alt', 't')
            time.sleep(3)
            
            # Look for Bounce option - try different keys
            print("Looking for Bounce option...")
            
            # Try 'B' for Bounce
            print("Trying 'B' for Bounce...")
            pyautogui.press('b')
            time.sleep(3)
            
            print("SUCCESS Bounce dialog command sent")
            print("WARNING  Please verify this opened BOUNCE dialog, not record!")
            return True
            
        except Exception as e:
            print(f"ERROR Error opening bounce dialog: {e}")
            return False
    
    def configure_bounce_settings(self):
        """Configure bounce settings for single stereo output"""
        print("\n Configuring bounce settings...")
        print("Need to set: 'bounce output channels' for 1 stereo file")
        
        try:
            # This step may require manual intervention or specific UI navigation
            print("Attempting to configure Advanced settings...")
            
            # Try to navigate to Advanced tab
            print("Looking for Advanced tab...")
            pyautogui.press('tab')
            time.sleep(2)
            
            # Try to select bounce output channels option
            print("Looking for 'bounce output channels' option...")
            pyautogui.press('space')  # Select radio button
            time.sleep(2)
            
            print("SUCCESS Bounce settings configuration attempted")
            print("WARNING  Please manually verify Advanced settings are correct!")
            return True
            
        except Exception as e:
            print(f"ERROR Error configuring bounce settings: {e}")
            return False
    
    def start_bounce(self):
        """Start the bounce process by selecting output folder"""
        print("\nLAUNCH Starting bounce process...")
        
        try:
            # Set output folder
            print(f"Setting output folder: {self.output_dir}")
            pyautogui.write(str(self.output_dir))
            time.sleep(2)
            
            # Start bounce
            print("Starting bounce (Enter)...")
            pyautogui.press('enter')
            time.sleep(2)
            
            print("SUCCESS Bounce start command sent")
            print("WARNING  Bounce should now be processing...")
            return True
            
        except Exception as e:
            print(f"ERROR Error starting bounce: {e}")
            return False
    
    def wait_for_bounce_completion(self, timeout=120):
        """Wait for bounce to complete and find Out_1+2.wav"""
        print(f"\n⏳ Waiting for bounce completion (timeout: {timeout}s)...")
        
        expected_file = self.output_dir / "Out_1+2.wav"
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            if expected_file.exists() and expected_file.stat().st_size > 0:
                file_size = expected_file.stat().st_size
                print(f"SUCCESS Bounce completed! File: {expected_file.name} ({file_size} bytes)")
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
        # Remove .mid extension and numeric suffix
        name = midi_filename.replace('.mid', '')
        match = re.match(r'(.+)_(\d+)$', name)
        if match:
            return match.group(1)
        return name
    
    def process_single_midi(self, midi_file):
        """Process one MIDI file through complete bounce workflow"""
        print(f"\n{'='*60}")
        print(f"PROCESSING: {midi_file.name}")
        print(f"{'='*60}")
        
        instrument_name = self.extract_instrument_name(midi_file.name)
        print(f"Instrument: {instrument_name}")
        
        # Check if already processed
        final_file = self.output_dir / f"{instrument_name}.wav"
        if final_file.exists():
            print(f"SUCCESS Already processed: {final_file.name}")
            return True
        
        # Execute workflow steps
        steps = [
            ("Focus SD3", self.find_and_focus_sd3),
            ("Load MIDI", lambda: self.load_midi_file(midi_file)),
            ("Position Timeline", self.position_timeline),
            ("Open Bounce Dialog", self.open_bounce_dialog),
            ("Configure Settings", self.configure_bounce_settings),
            ("Start Bounce", self.start_bounce)
        ]
        
        for step_name, step_func in steps:
            print(f"\n--- {step_name} ---")
            if not step_func():
                print(f"ERROR Failed at step: {step_name}")
                return False
            
            # Pause between steps for observation
            time.sleep(2)
        
        # Wait for completion
        bounced_file = self.wait_for_bounce_completion()
        if not bounced_file:
            print("ERROR Bounce failed or timed out")
            return False
        
        # Rename file
        final_file = self.rename_output_file(bounced_file, instrument_name)
        if not final_file:
            print("ERROR File rename failed")
            return False
        
        print(f"COMPLETE SUCCESS: {midi_file.name} → {final_file.name}")
        return True

def main():
    """Main execution"""
    print("AUDIO SD3 FOCUSED BOUNCE AUTOMATION")
    print("=" * 60)
    print("Focuses on correct Track menu → Bounce workflow")
    print("Avoids triggering recording instead of bouncing")
    print("=" * 60)
    
    automation = SD3BounceAutomation()
    
    # Get first MIDI file for testing
    midi_files = list(automation.midi_dir.glob("*.mid"))
    if not midi_files:
        print("ERROR No MIDI files found!")
        return
    
    test_file = midi_files[0]
    print(f"\nTesting with: {test_file.name}")
    
    input("\nPress ENTER to start focused bounce test...")
    
    success = automation.process_single_midi(test_file)
    
    if success:
        print("\nCOMPLETE FOCUSED BOUNCE TEST SUCCESSFUL!")
        print("The workflow is working correctly.")
    else:
        print("\nERROR FOCUSED BOUNCE TEST FAILED!")
        print("Check the steps above to identify the issue.")

if __name__ == "__main__":
    main()

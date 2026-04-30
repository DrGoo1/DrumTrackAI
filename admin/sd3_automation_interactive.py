#!/usr/bin/env python3
"""
Interactive Step-by-Step Superior Drummer 3 Automation
======================================================

Performs each SD3 export step individually and waits for user confirmation
to ensure each step is executed correctly before proceeding.

Author: DrumTracKAI v1.1.7
Date: July 23, 2025
"""

import os
import sys
import time
import logging
from pathlib import Path
from datetime import datetime

# GUI automation imports
try:
    import pyautogui
    import pygetwindow as gw
    from PIL import Image, ImageGrab
    AUTOMATION_AVAILABLE = True
    
    # Configure pyautogui for interactive mode
    pyautogui.FAILSAFE = True
    pyautogui.PAUSE = 1.0
    
except ImportError:
    AUTOMATION_AVAILABLE = False
    print("ERROR: GUI automation libraries not available")
    sys.exit(1)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('sd3_interactive.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class SD3InteractiveAutomation:
    """Interactive step-by-step SD3 automation with user confirmation"""
    
    def __init__(self):
        self.base_path = Path(__file__).parent
        self.midi_dir = self.base_path / "sd3_midi_patterns"
        self.output_dir = self.base_path / "sd3_extracted_samples"
        
        # SD3 application settings
        self.sd3_window_titles = ["Superior Drummer 3", "Superior Drummer", "SD3"]
        
        # Interactive settings
        self.automation_delay = 2.0  # Longer delays for observation
        
        logger.info("SD3 Interactive Automation System initialized")
    
    def wait_for_confirmation(self, step_description: str) -> bool:
        """Wait for user confirmation before proceeding"""
        print(f"\n{'='*60}")
        print(f"STEP: {step_description}")
        print(f"{'='*60}")
        
        while True:
            response = input("Press ENTER to continue, 'r' to retry this step, or 'q' to quit: ").strip().lower()
            
            if response == '':
                print("SUCCESS Continuing to next step...")
                return True
            elif response == 'r':
                print(" Retrying this step...")
                return False
            elif response == 'q':
                print("ERROR Quitting automation...")
                return None
            else:
                print("Invalid input. Please press ENTER, 'r', or 'q'.")
    
    def find_sd3_window(self) -> bool:
        """Find and focus SD3 window"""
        print("\nINSPECTING STEP 0: Finding and focusing SD3 window...")
        
        try:
            for title in self.sd3_window_titles:
                windows = gw.getWindowsWithTitle(title)
                if windows:
                    window = windows[0]
                    print(f"SUCCESS Found SD3 window: '{window.title}'")
                    
                    # Bring window to front
                    window.activate()
                    time.sleep(self.automation_delay)
                    
                    print(f"SUCCESS SD3 window focused and ready")
                    return True
            
            print("ERROR SD3 window not found!")
            print("Available windows:")
            all_windows = gw.getAllWindows()
            for i, window in enumerate(all_windows[:10]):
                print(f"   {i+1}. '{window.title}'")
            
            return False
            
        except Exception as e:
            print(f"ERROR Error finding SD3 window: {e}")
            return False
    
    def step_1_load_midi_file(self, midi_file: Path) -> bool:
        """Step 1: Load MIDI file"""
        while True:
            print(f"\nFOLDER STEP 1: Loading MIDI file: {midi_file.name}")
            print("This will:")
            print("  - Open file dialog with Ctrl+O")
            print("  - Type the MIDI file path")
            print("  - Press Enter to load")
            
            confirmation = self.wait_for_confirmation("Load MIDI file")
            if confirmation is None:
                return False
            elif not confirmation:
                continue  # Retry
            
            try:
                # Open file dialog
                print("Opening file dialog with Ctrl+O...")
                pyautogui.hotkey('ctrl', 'o')
                time.sleep(self.automation_delay * 2)
                
                # Type file path
                print(f"Typing file path: {midi_file}")
                pyautogui.write(str(midi_file))
                time.sleep(self.automation_delay)
                
                # Press Enter
                print("Pressing Enter to load file...")
                pyautogui.press('enter')
                time.sleep(self.automation_delay * 2)
                
                print("SUCCESS MIDI file load command sent")
                
                # Wait for user confirmation that file loaded
                print("\nPlease verify that the MIDI file loaded correctly in SD3.")
                confirmation = self.wait_for_confirmation("MIDI file loaded successfully")
                if confirmation is None:
                    return False
                elif confirmation:
                    return True
                # If not confirmed, loop will retry
                
            except Exception as e:
                print(f"ERROR Error loading MIDI file: {e}")
                # Loop will continue for retry
    
    def step_2_position_at_beat_1_3(self) -> bool:
        """Step 2: Position timeline at beat 1.3"""
        while True:
            print(f"\n⏱ STEP 2: Position timeline at beat 1.3")
            print("This will:")
            print("  - Go to beginning with Home key")
            print("  - Move forward to beat 1.3")
            print("  - Ensure MIDI starts at correct position")
            
            confirmation = self.wait_for_confirmation("Position at beat 1.3")
            if confirmation is None:
                return False
            elif not confirmation:
                continue  # Retry
            
            try:
                # Go to beginning
                print("Going to beginning with Home key...")
                pyautogui.press('home')
                time.sleep(self.automation_delay)
                
                # Move to beat 1.3 (this may need adjustment based on SD3 interface)
                print("Moving to beat 1.3...")
                # Try different approaches
                print("Trying right arrow keys...")
                for i in range(3):
                    pyautogui.press('right')
                    time.sleep(0.5)
                
                print("SUCCESS Timeline positioning command sent")
                
                # Wait for user confirmation
                print("\nPlease verify that the timeline is positioned at beat 1.3.")
                print("The MIDI should be ready to play from the correct starting position.")
                confirmation = self.wait_for_confirmation("Timeline positioned at beat 1.3")
                if confirmation is None:
                    return False
                elif confirmation:
                    return True
                # If not confirmed, loop will retry
                
            except Exception as e:
                print(f"ERROR Error positioning timeline: {e}")
                # Loop will continue for retry
    
    def step_3_open_track_menu(self) -> bool:
        """Step 3: Open Track menu"""
        while True:
            print(f"\n STEP 3: Open Track menu")
            print("This will:")
            print("  - Press Alt+T to open Track menu")
            print("  - Look for Bounce option")
            
            confirmation = self.wait_for_confirmation("Open Track menu")
            if confirmation is None:
                return False
            elif not confirmation:
                continue  # Retry
            
            try:
                # Open Track menu
                print("Opening Track menu with Alt+T...")
                pyautogui.hotkey('alt', 't')
                time.sleep(self.automation_delay)
                
                print("SUCCESS Track menu command sent")
                
                # Wait for user confirmation
                print("\nPlease verify that the Track menu is open.")
                print("You should see the Bounce option in the menu.")
                confirmation = self.wait_for_confirmation("Track menu is open")
                if confirmation is None:
                    return False
                elif confirmation:
                    return True
                # If not confirmed, loop will retry
                
            except Exception as e:
                print(f"ERROR Error opening Track menu: {e}")
                # Loop will continue for retry
    
    def step_4_select_bounce(self) -> bool:
        """Step 4: Select Bounce from Track menu"""
        while True:
            print(f"\nAUDIO STEP 4: Select Bounce option")
            print("This will:")
            print("  - Press 'B' to select Bounce")
            print("  - Open the bounce dialog/window")
            
            confirmation = self.wait_for_confirmation("Select Bounce option")
            if confirmation is None:
                return False
            elif not confirmation:
                continue  # Retry
            
            try:
                # Select Bounce
                print("Pressing 'B' to select Bounce...")
                pyautogui.press('b')
                time.sleep(self.automation_delay * 2)
                
                print("SUCCESS Bounce selection command sent")
                
                # Wait for user confirmation
                print("\nPlease verify that the Bounce dialog/window opened.")
                print("You should see bounce settings and options.")
                confirmation = self.wait_for_confirmation("Bounce dialog is open")
                if confirmation is None:
                    return False
                elif confirmation:
                    return True
                # If not confirmed, loop will retry
                
            except Exception as e:
                print(f"ERROR Error selecting Bounce: {e}")
                # Loop will continue for retry
    
    def step_5_configure_advanced_settings(self) -> bool:
        """Step 5: Configure Advanced tab settings"""
        while True:
            print(f"\n STEP 5: Configure Advanced settings")
            print("This will:")
            print("  - Navigate to Advanced tab")
            print("  - Select 'bounce output channels' radio button")
            print("  - Ensure 1 stereo file output")
            
            confirmation = self.wait_for_confirmation("Configure Advanced settings")
            if confirmation is None:
                return False
            elif not confirmation:
                continue  # Retry
            
            try:
                # Navigate to Advanced tab (this may need manual guidance)
                print("Attempting to navigate to Advanced tab...")
                print("(This step may require manual navigation)")
                
                # Try Tab key navigation
                pyautogui.press('tab')
                time.sleep(self.automation_delay)
                
                # Try to select radio button
                print("Attempting to select 'bounce output channels' option...")
                pyautogui.press('space')
                time.sleep(self.automation_delay)
                
                print("SUCCESS Advanced settings configuration attempted")
                
                # Wait for user confirmation (this step likely needs manual intervention)
                print("\nPlease manually verify and configure the Advanced settings:")
                print("  1. Navigate to the Advanced tab")
                print("  2. Select the 'bounce output channels' radio button")
                print("  3. Ensure it's set for 1 stereo file output")
                confirmation = self.wait_for_confirmation("Advanced settings configured")
                if confirmation is None:
                    return False
                elif confirmation:
                    return True
                # If not confirmed, loop will retry
                
            except Exception as e:
                print(f"ERROR Error configuring Advanced settings: {e}")
                # Loop will continue for retry
    
    def step_6_select_output_folder(self) -> bool:
        """Step 6: Select output folder and start bounce"""
        while True:
            print(f"\nDIRECTORY STEP 6: Select output folder and start bounce")
            print("This will:")
            print(f"  - Set output folder to: {self.output_dir}")
            print("  - Start the bounce process")
            print("  - According to user: folder selection triggers bounce")
            
            confirmation = self.wait_for_confirmation("Select output folder and start bounce")
            if confirmation is None:
                return False
            elif not confirmation:
                continue  # Retry
            
            try:
                # Type output folder path
                print(f"Typing output folder path: {self.output_dir}")
                pyautogui.write(str(self.output_dir))
                time.sleep(self.automation_delay)
                
                # Press Enter to confirm/start
                print("Pressing Enter to start bounce...")
                pyautogui.press('enter')
                time.sleep(self.automation_delay)
                
                print("SUCCESS Bounce start command sent")
                
                # Wait for user confirmation
                print("\nPlease verify that the bounce process started.")
                print("You should see bounce progress or the process beginning.")
                confirmation = self.wait_for_confirmation("Bounce process started")
                if confirmation is None:
                    return False
                elif confirmation:
                    return True
                # If not confirmed, loop will retry
                
            except Exception as e:
                print(f"ERROR Error starting bounce: {e}")
                # Loop will continue for retry
    
    def step_7_wait_for_completion(self) -> bool:
        """Step 7: Wait for bounce completion"""
        print(f"\n⏳ STEP 7: Wait for bounce completion")
        print("Waiting for bounce to complete...")
        print("The output file should be named 'Out_1+2.wav'")
        print(f"Expected location: {self.output_dir}")
        
        # Manual wait with user confirmation
        print("\nPlease wait for the bounce to complete.")
        print("When finished, you should see 'Out_1+2.wav' in the output folder.")
        confirmation = self.wait_for_confirmation("Bounce completed successfully")
        
        if confirmation is None:
            return False
        elif confirmation:
            return True
        else:
            return False
    
    def step_8_rename_output_file(self, instrument_name: str) -> bool:
        """Step 8: Rename output file"""
        while True:
            print(f"\n STEP 8: Rename output file")
            print(f"This will rename 'Out_1+2.wav' to '{instrument_name}.wav'")
            
            confirmation = self.wait_for_confirmation("Rename output file")
            if confirmation is None:
                return False
            elif not confirmation:
                continue  # Retry
            
            try:
                original_file = self.output_dir / "Out_1+2.wav"
                new_file = self.output_dir / f"{instrument_name}.wav"
                
                if original_file.exists():
                    original_file.rename(new_file)
                    print(f"SUCCESS File renamed: {original_file.name} → {new_file.name}")
                    return True
                else:
                    print(f"ERROR Original file not found: {original_file}")
                    print("Please check if the bounce completed successfully.")
                    confirmation = self.wait_for_confirmation("Try rename again")
                    if confirmation is None:
                        return False
                    elif not confirmation:
                        continue  # Retry
                    else:
                        return False
                
            except Exception as e:
                print(f"ERROR Error renaming file: {e}")
                # Loop will continue for retry
    
    def run_interactive_test(self):
        """Run interactive test with a single MIDI file"""
        print("AUDIO SD3 INTERACTIVE STEP-BY-STEP AUTOMATION")
        print("=" * 60)
        print("This will process one MIDI file step-by-step with confirmation.")
        print("You can retry any step or quit at any time.")
        print("=" * 60)
        
        # Get first MIDI file for testing
        midi_files = list(self.midi_dir.glob("*.mid"))
        if not midi_files:
            print("ERROR No MIDI files found!")
            return
        
        test_midi = midi_files[0]
        instrument_name = test_midi.stem.rsplit('_', 1)[0]  # Remove numeric suffix
        
        print(f"Test file: {test_midi.name}")
        print(f"Instrument: {instrument_name}")
        print(f"Output will be: {instrument_name}.wav")
        
        input("\nPress ENTER to begin step-by-step process...")
        
        # Step 0: Find SD3 window
        if not self.find_sd3_window():
            print("ERROR Cannot proceed without SD3 window")
            return
        
        # Execute each step with confirmation
        steps = [
            (self.step_1_load_midi_file, test_midi),
            (self.step_2_position_at_beat_1_3,),
            (self.step_3_open_track_menu,),
            (self.step_4_select_bounce,),
            (self.step_5_configure_advanced_settings,),
            (self.step_6_select_output_folder,),
            (self.step_7_wait_for_completion,),
            (self.step_8_rename_output_file, instrument_name)
        ]
        
        for i, step_info in enumerate(steps, 1):
            step_func = step_info[0]
            step_args = step_info[1:] if len(step_info) > 1 else ()
            
            print(f"\n{'='*60}")
            print(f"EXECUTING STEP {i}/{len(steps)}")
            print(f"{'='*60}")
            
            success = step_func(*step_args)
            if not success:
                print(f"ERROR Step {i} failed or was cancelled")
                return
        
        print(f"\nCOMPLETE SUCCESS! Interactive test completed!")
        print(f"Check output folder for: {instrument_name}.wav")

def main():
    """Main entry point for interactive automation"""
    if not AUTOMATION_AVAILABLE:
        print("ERROR: GUI automation libraries not available")
        return
    
    automation = SD3InteractiveAutomation()
    automation.run_interactive_test()

if __name__ == "__main__":
    main()

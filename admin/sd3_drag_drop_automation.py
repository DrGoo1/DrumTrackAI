#!/usr/bin/env python3
"""
SD3 Click and Drag Automation
============================

Uses click and drag method to load MIDI files into SD3, since this method
works while keyboard shortcuts don't reach the SD3 window properly.

Author: DrumTracKAI v1.1.7
Date: July 23, 2025
"""

import time
from pathlib import Path
import re
import os

try:
    import pyautogui
    import pygetwindow as gw
    pyautogui.FAILSAFE = True
    pyautogui.PAUSE = 1.0
    print("SUCCESS Automation libraries loaded")
except ImportError as e:
    print(f"ERROR Import error: {e}")
    exit(1)

class SD3DragDropAutomation:
    """SD3 automation using click and drag for MIDI loading"""
    
    def __init__(self):
        self.base_path = Path(__file__).parent
        self.midi_dir = self.base_path / "sd3_midi_patterns"
        self.output_dir = self.base_path / "sd3_extracted_samples"
        
        self.output_dir.mkdir(exist_ok=True)
        
        print(f"MIDI directory: {self.midi_dir}")
        print(f"Output directory: {self.output_dir}")
        
        # SD3 window coordinates (will be detected)
        self.sd3_window = None
        self.sd3_timeline_area = None
    
    def find_sd3_window(self):
        """Find and get SD3 window coordinates"""
        print("\nINSPECTING Finding SD3 window...")
        
        windows = gw.getAllWindows()
        for window in windows:
            if 'Superior Drummer' in window.title or 'SD3' in window.title:
                self.sd3_window = window
                print(f"SUCCESS Found SD3: '{window.title}'")
                print(f"   Position: ({window.left}, {window.top})")
                print(f"   Size: {window.width} x {window.height}")
                
                # Estimate timeline area (center-bottom area of SD3 window)
                timeline_x = window.left + window.width // 2
                timeline_y = window.top + int(window.height * 0.7)  # Lower part of window
                self.sd3_timeline_area = (timeline_x, timeline_y)
                
                print(f"   Timeline drop area: ({timeline_x}, {timeline_y})")
                return True
        
        print("ERROR SD3 window not found!")
        return False
    
    def open_file_explorer_to_midi(self, midi_file):
        """Open Windows File Explorer to the MIDI file location"""
        print(f"\nDIRECTORY Opening File Explorer to: {midi_file}")
        
        try:
            # Open File Explorer to the MIDI directory
            os.startfile(str(self.midi_dir))
            time.sleep(3)
            
            print("SUCCESS File Explorer opened")
            print(f"Please locate file: {midi_file.name}")
            return True
            
        except Exception as e:
            print(f"ERROR Error opening File Explorer: {e}")
            return False
    
    def drag_midi_to_sd3(self, midi_file):
        """Drag MIDI file from Explorer to SD3 timeline"""
        print(f"\n Preparing to drag {midi_file.name} to SD3...")
        
        if not self.sd3_timeline_area:
            print("ERROR SD3 timeline area not detected!")
            return False
        
        print(f"Target drop area: {self.sd3_timeline_area}")
        print(f"\nMANUAL DRAG INSTRUCTIONS:")
        print(f"1. In File Explorer, locate: {midi_file.name}")
        print(f"2. Click and hold on the MIDI file")
        print(f"3. Drag it to the SD3 timeline area")
        print(f"4. Release to drop the file")
        print(f"5. Verify MIDI appears in SD3 timeline")
        
        # Alternative: Try automated drag if we can find the file icon
        print(f"\n ATTEMPTING AUTOMATED DRAG...")
        
        try:
            # This is experimental - try to find and drag the file
            # First, try to locate the MIDI file in Explorer
            print("Looking for MIDI file in File Explorer...")
            
            # Take a screenshot to find the file
            screenshot = pyautogui.screenshot()
            
            # Try to find the file by searching for its name on screen
            # This is a basic approach - may need refinement
            try:
                file_location = pyautogui.locateOnScreen(None)  # Would need file icon image
                if file_location:
                    file_center = pyautogui.center(file_location)
                    print(f"Found file at: {file_center}")
                    
                    # Drag from file to SD3 timeline
                    print(f"Dragging from {file_center} to {self.sd3_timeline_area}")
                    pyautogui.drag(
                        self.sd3_timeline_area[0] - file_center[0],
                        self.sd3_timeline_area[1] - file_center[1],
                        duration=2.0
                    )
                    
                    print("SUCCESS Automated drag completed")
                    return True
                    
            except Exception:
                print("Automated drag failed - using manual method")
        
        except Exception as e:
            print(f"ERROR Drag automation error: {e}")
        
        # Fall back to manual confirmation
        input(f"\nPress ENTER when you've dragged {midi_file.name} to SD3...")
        return True
    
    def verify_midi_loaded(self):
        """Verify MIDI file was loaded into timeline"""
        print(f"\nSUCCESS Verifying MIDI loaded...")
        print(f"Check SD3 timeline for MIDI data")
        
        response = input(f"Did the MIDI file load into the timeline? (y/n): ").lower()
        return response.startswith('y')
    
    def position_at_beat_1_3(self):
        """Position cursor at beat 1.3 using stop key method"""
        print(f"\n⏱ Positioning at beat 1.3...")
        
        try:
            # Make sure SD3 is focused
            if self.sd3_window:
                try:
                    self.sd3_window.activate()
                    time.sleep(1)
                except:
                    print("Manual focus: Click on SD3 window")
                    input("Press ENTER when SD3 is focused...")
            
            # Use stop key to return to start
            print("Using stop key to return to start...")
            pyautogui.press('space')  # Stop/pause
            time.sleep(1)
            
            # Move to beat 1.3
            print("Moving to beat 1.3 (3 right arrows)...")
            for i in range(3):
                pyautogui.press('right')
                time.sleep(0.5)
            
            print("SUCCESS Cursor positioning completed")
            return True
            
        except Exception as e:
            print(f"ERROR Error positioning cursor: {e}")
            print("Manual positioning required")
            input("Press ENTER when positioned at beat 1.3...")
            return True
    
    def open_track_bounce_menu(self):
        """Open Track menu and select Bounce"""
        print(f"\nAUDIO Opening Track → Bounce...")
        
        try:
            # Try Alt+T for Track menu
            print("Trying Alt+T for Track menu...")
            pyautogui.hotkey('alt', 't')
            time.sleep(2)
            
            # Try B for Bounce
            print("Trying B for Bounce...")
            pyautogui.press('b')
            time.sleep(2)
            
            print("SUCCESS Track → Bounce command sent")
            
            # Verify bounce dialog opened
            response = input("Did the Bounce dialog open? (y/n): ").lower()
            return response.startswith('y')
            
        except Exception as e:
            print(f"ERROR Error opening Track → Bounce: {e}")
            print("Manual menu navigation required")
            input("Press ENTER when Bounce dialog is open...")
            return True
    
    def configure_bounce_settings(self):
        """Configure bounce settings"""
        print(f"\n Configuring bounce settings...")
        print(f"Manual configuration required:")
        print(f"1. Navigate to Advanced tab")
        print(f"2. Select 'bounce output channels' radio button")
        print(f"3. Ensure single stereo file output")
        print(f"4. Set output folder to: {self.output_dir}")
        
        input(f"Press ENTER when bounce settings are configured...")
        return True
    
    def start_bounce_and_monitor(self, instrument_name):
        """Start bounce and monitor for completion"""
        print(f"\nLAUNCH Starting bounce...")
        print(f"Press Enter in bounce dialog to start")
        
        input(f"Press ENTER when bounce has started...")
        
        # Monitor for Out_1+2.wav
        print(f"\n⏳ Monitoring for bounce completion...")
        original_file = self.output_dir / "Out_1+2.wav"
        target_file = self.output_dir / f"{instrument_name}.wav"
        
        start_time = time.time()
        timeout = 180
        
        while time.time() - start_time < timeout:
            if original_file.exists() and original_file.stat().st_size > 0:
                # Auto-rename
                try:
                    time.sleep(2)  # Ensure file is fully written
                    original_file.rename(target_file)
                    file_size = target_file.stat().st_size
                    
                    print(f"SUCCESS Bounce completed and renamed!")
                    print(f"   {original_file.name} → {target_file.name}")
                    print(f"   File size: {file_size:,} bytes")
                    return target_file
                    
                except Exception as e:
                    print(f"ERROR Rename error: {e}")
                    return None
            
            elapsed = int(time.time() - start_time)
            if elapsed % 15 == 0 and elapsed > 0:
                print(f"   Waiting... {elapsed}s/{timeout}s")
            
            time.sleep(3)
        
        print(f"ERROR Bounce timeout after {timeout}s")
        return None
    
    def extract_instrument_name(self, midi_filename):
        """Extract instrument name from MIDI filename"""
        name = midi_filename.replace('.mid', '')
        match = re.match(r'(.+)_(\d+)$', name)
        if match:
            return match.group(1)
        return name
    
    def process_single_midi_drag_drop(self, midi_file):
        """Process one MIDI file using drag and drop method"""
        print(f"\n{'='*70}")
        print(f"DRAG & DROP PROCESSING: {midi_file.name}")
        print(f"{'='*70}")
        
        instrument_name = self.extract_instrument_name(midi_file.name)
        print(f"Instrument: {instrument_name}")
        
        # Check if already processed
        final_file = self.output_dir / f"{instrument_name}.wav"
        if final_file.exists():
            print(f"SUCCESS Already processed: {final_file.name}")
            return True
        
        # Step 1: Find SD3 window
        if not self.find_sd3_window():
            print("ERROR Cannot proceed without SD3 window")
            return False
        
        # Step 2: Open File Explorer to MIDI location
        if not self.open_file_explorer_to_midi(midi_file):
            print("ERROR Failed to open File Explorer")
            return False
        
        # Step 3: Drag MIDI to SD3
        if not self.drag_midi_to_sd3(midi_file):
            print("ERROR Failed to drag MIDI to SD3")
            return False
        
        # Step 4: Verify MIDI loaded
        if not self.verify_midi_loaded():
            print("ERROR MIDI file not loaded properly")
            return False
        
        # Step 5: Position at beat 1.3
        if not self.position_at_beat_1_3():
            print("ERROR Failed to position cursor")
            return False
        
        # Step 6: Open Track → Bounce
        if not self.open_track_bounce_menu():
            print("ERROR Failed to open bounce dialog")
            return False
        
        # Step 7: Configure bounce settings
        if not self.configure_bounce_settings():
            print("ERROR Failed to configure bounce")
            return False
        
        # Step 8: Start bounce and monitor
        result_file = self.start_bounce_and_monitor(instrument_name)
        if not result_file:
            print("ERROR Bounce failed")
            return False
        
        print(f"COMPLETE SUCCESS: {midi_file.name} → {result_file.name}")
        return True

def main():
    """Main drag and drop automation"""
    print("AUDIO SD3 DRAG & DROP AUTOMATION")
    print("=" * 70)
    print("Uses click and drag method to load MIDI files")
    print("This should work better than keyboard shortcuts")
    print("=" * 70)
    
    automation = SD3DragDropAutomation()
    
    # Get first MIDI file for testing
    midi_files = list(automation.midi_dir.glob("*.mid"))
    if not midi_files:
        print("ERROR No MIDI files found!")
        return
    
    test_file = midi_files[0]
    print(f"\nTesting with: {test_file.name}")
    
    print(f"\nPREPARATION:")
    print(f"1. Ensure Superior Drummer 3 is running")
    print(f"2. Position SD3 window where you can see it")
    print(f"3. Clear any existing MIDI from timeline")
    
    input(f"\nPress ENTER to start drag & drop automation...")
    
    success = automation.process_single_midi_drag_drop(test_file)
    
    if success:
        print(f"\nCOMPLETE DRAG & DROP AUTOMATION SUCCESSFUL!")
        print(f"This method works! We can now automate the full process.")
    else:
        print(f"\nERROR DRAG & DROP AUTOMATION FAILED!")
        print(f"Check the steps above to identify issues.")

if __name__ == "__main__":
    main()

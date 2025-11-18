#!/usr/bin/env python3
"""
SD3 Automation Diagnostic Script
================================

This script provides detailed step-by-step diagnostics for SD3 automation
to identify exactly where the export process is failing.

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
    
    # Configure pyautogui for diagnostic mode
    pyautogui.FAILSAFE = True
    pyautogui.PAUSE = 1.0  # Slower for better observation
    
except ImportError:
    AUTOMATION_AVAILABLE = False
    print("ERROR: GUI automation libraries not available")
    sys.exit(1)

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('sd3_diagnostic.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class SD3DiagnosticAutomation:
    """Diagnostic automation with detailed step-by-step feedback"""
    
    def __init__(self):
        self.base_path = Path(__file__).parent
        self.midi_dir = self.base_path / "sd3_midi_patterns"
        self.output_dir = self.base_path / "sd3_extracted_samples"
        
        # SD3 application settings
        self.sd3_window_titles = ["Superior Drummer 3", "Superior Drummer", "SD3"]
        
        # Diagnostic settings
        self.step_delay = 3.0  # Long delays for observation
        self.screenshot_dir = self.base_path / "sd3_diagnostic_screenshots"
        self.screenshot_dir.mkdir(exist_ok=True)
        
        logger.info("SD3 Diagnostic Automation initialized")
    
    def take_screenshot(self, step_name: str):
        """Take a screenshot for diagnostic purposes"""
        try:
            timestamp = datetime.now().strftime("%H%M%S")
            screenshot_path = self.screenshot_dir / f"{timestamp}_{step_name}.png"
            screenshot = ImageGrab.grab()
            screenshot.save(screenshot_path)
            logger.info(f"Screenshot saved: {screenshot_path.name}")
        except Exception as e:
            logger.warning(f"Failed to take screenshot: {e}")
    
    def find_sd3_window(self):
        """Find and return SD3 window with detailed logging"""
        logger.info("=== STEP 1: Finding SD3 Window ===")
        
        for title in self.sd3_window_titles:
            windows = gw.getWindowsWithTitle(title)
            if windows:
                window = windows[0]
                logger.info(f"SUCCESS Found SD3 window: '{window.title}'")
                logger.info(f"   Position: ({window.left}, {window.top})")
                logger.info(f"   Size: {window.width}x{window.height}")
                logger.info(f"   Visible: {window.visible}")
                logger.info(f"   Active: {window.isActive}")
                return window
        
        # List all windows for debugging
        logger.error("ERROR SD3 window not found. Available windows:")
        all_windows = gw.getAllWindows()
        for i, window in enumerate(all_windows[:10]):  # Show first 10 windows
            logger.info(f"   {i+1}. '{window.title}' ({window.width}x{window.height})")
        
        return None
    
    def focus_sd3_window(self, window):
        """Focus SD3 window with detailed feedback"""
        logger.info("=== STEP 2: Focusing SD3 Window ===")
        
        try:
            # Take screenshot before focusing
            self.take_screenshot("before_focus")
            
            logger.info("Activating SD3 window...")
            window.activate()
            time.sleep(self.step_delay)
            
            # Verify focus
            active_window = gw.getActiveWindow()
            if active_window and active_window.title == window.title:
                logger.info("SUCCESS SD3 window successfully focused")
                self.take_screenshot("after_focus")
                return True
            else:
                logger.error(f"ERROR Failed to focus SD3. Active window: {active_window.title if active_window else 'None'}")
                return False
                
        except Exception as e:
            logger.error(f"ERROR Error focusing SD3 window: {e}")
            return False
    
    def stop_and_rewind(self):
        """Stop playback and rewind with detailed feedback"""
        logger.info("=== STEP 3: Stop and Rewind ===")
        
        try:
            self.take_screenshot("before_stop_rewind")
            
            logger.info("Pressing SPACE to stop playback...")
            pyautogui.press('space')
            time.sleep(self.step_delay)
            
            logger.info("Pressing HOME to rewind to start...")
            pyautogui.press('home')
            time.sleep(self.step_delay)
            
            logger.info("Pressing Ctrl+HOME as alternative rewind...")
            pyautogui.hotkey('ctrl', 'home')
            time.sleep(self.step_delay)
            
            logger.info("Pressing '0' to go to position 0...")
            pyautogui.press('0')
            time.sleep(self.step_delay)
            
            self.take_screenshot("after_stop_rewind")
            logger.info("SUCCESS Stop and rewind sequence completed")
            return True
            
        except Exception as e:
            logger.error(f"ERROR Error in stop and rewind: {e}")
            return False
    
    def load_midi_file(self, midi_file: Path):
        """Load MIDI file with detailed feedback"""
        logger.info(f"=== STEP 4: Loading MIDI File: {midi_file.name} ===")
        
        try:
            self.take_screenshot("before_midi_load")
            
            logger.info("Opening file dialog with Ctrl+O...")
            pyautogui.hotkey('ctrl', 'o')
            time.sleep(self.step_delay * 2)
            
            self.take_screenshot("file_dialog_opened")
            
            logger.info(f"Typing file path: {midi_file}")
            pyautogui.write(str(midi_file))
            time.sleep(self.step_delay)
            
            self.take_screenshot("file_path_entered")
            
            logger.info("Pressing ENTER to open file...")
            pyautogui.press('enter')
            time.sleep(self.step_delay * 2)
            
            self.take_screenshot("after_midi_load")
            logger.info("SUCCESS MIDI file load sequence completed")
            return True
            
        except Exception as e:
            logger.error(f"ERROR Error loading MIDI file: {e}")
            return False
    
    def export_song_via_track_menu(self, output_path: Path):
        """Export song via Track menu with detailed feedback"""
        logger.info("=== STEP 5: Export Song via Track Menu ===")
        
        try:
            self.take_screenshot("before_track_menu")
            
            logger.info("Opening Track menu with Alt+T...")
            pyautogui.hotkey('alt', 't')
            time.sleep(self.step_delay)
            
            self.take_screenshot("track_menu_opened")
            
            logger.info("Pressing 'E' for Export...")
            pyautogui.press('e')
            time.sleep(self.step_delay)
            
            self.take_screenshot("export_submenu")
            
            logger.info("Pressing 'S' for Song...")
            pyautogui.press('s')
            time.sleep(self.step_delay * 2)
            
            self.take_screenshot("export_dialog_opened")
            
            logger.info(f"Typing output path: {output_path}")
            pyautogui.write(str(output_path))
            time.sleep(self.step_delay)
            
            self.take_screenshot("output_path_entered")
            
            logger.info("Pressing ENTER to start export...")
            pyautogui.press('enter')
            time.sleep(self.step_delay)
            
            self.take_screenshot("export_started")
            logger.info("SUCCESS Export Song sequence completed")
            return True
            
        except Exception as e:
            logger.error(f"ERROR Error in export sequence: {e}")
            return False
    
    def wait_for_export_completion(self, output_path: Path, timeout: int = 60):
        """Wait for export to complete with detailed feedback"""
        logger.info("=== STEP 6: Waiting for Export Completion ===")
        
        start_time = time.time()
        while time.time() - start_time < timeout:
            if output_path.exists() and output_path.stat().st_size > 0:
                file_size = output_path.stat().st_size
                logger.info(f"SUCCESS Export completed! File size: {file_size} bytes")
                self.take_screenshot("export_completed")
                return True
            
            elapsed = int(time.time() - start_time)
            logger.info(f"Waiting for export... ({elapsed}s/{timeout}s)")
            time.sleep(2)
        
        logger.error(f"ERROR Export timeout after {timeout} seconds")
        if output_path.exists():
            file_size = output_path.stat().st_size
            logger.error(f"File exists but size is: {file_size} bytes")
        else:
            logger.error("Output file was not created")
        
        self.take_screenshot("export_timeout")
        return False
    
    def run_diagnostic_test(self):
        """Run complete diagnostic test"""
        logger.info("INSPECTING Starting SD3 Automation Diagnostic Test")
        logger.info("=" * 60)
        
        # Test with one MIDI file
        midi_files = list(self.midi_dir.glob("*.mid"))
        if not midi_files:
            logger.error("ERROR No MIDI files found for testing")
            return False
        
        test_midi = midi_files[0]
        output_path = self.output_dir / f"{test_midi.stem}_diagnostic.wav"
        
        logger.info(f"Testing with: {test_midi.name}")
        logger.info(f"Output path: {output_path}")
        logger.info("=" * 60)
        
        # Step 1: Find SD3 window
        window = self.find_sd3_window()
        if not window:
            return False
        
        # Step 2: Focus window
        if not self.focus_sd3_window(window):
            return False
        
        # Step 3: Stop and rewind
        if not self.stop_and_rewind():
            return False
        
        # Step 4: Load MIDI file
        if not self.load_midi_file(test_midi):
            return False
        
        # Step 5: Export song
        if not self.export_song_via_track_menu(output_path):
            return False
        
        # Step 6: Wait for completion
        if not self.wait_for_export_completion(output_path):
            return False
        
        logger.info("COMPLETE DIAGNOSTIC TEST COMPLETED SUCCESSFULLY!")
        logger.info(f"Screenshots saved to: {self.screenshot_dir}")
        return True

def main():
    """Main diagnostic entry point"""
    if not AUTOMATION_AVAILABLE:
        print("ERROR: GUI automation libraries not available")
        return
    
    diagnostic = SD3DiagnosticAutomation()
    
    print("\nINSPECTING SD3 AUTOMATION DIAGNOSTIC TEST")
    print("=" * 50)
    print("This will test the complete SD3 automation workflow")
    print("with detailed logging and screenshots at each step.")
    print("=" * 50)
    
    input("Press ENTER to start diagnostic test...")
    
    success = diagnostic.run_diagnostic_test()
    
    if success:
        print("\nSUCCESS DIAGNOSTIC TEST PASSED!")
        print("The automation workflow is working correctly.")
    else:
        print("\nERROR DIAGNOSTIC TEST FAILED!")
        print("Check the logs and screenshots for details.")
        print(f"Screenshots: {diagnostic.screenshot_dir}")
        print(f"Log file: sd3_diagnostic.log")

if __name__ == "__main__":
    main()

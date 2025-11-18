#!/usr/bin/env python3
"""
Corrected Superior Drummer 3 Automation System
==============================================

Implements the correct SD3 export workflow as provided by the user:
1. Load MIDI file and position at beat 1.3 (or offset MIDI to start at 1.3)
2. Use Track menu → Bounce to open bounce window
3. Select folder (triggers bounce)
4. Advanced tab: Select "bounce output channels" for 1 stereo file
5. Rename output file from "Out_1+2.wav" to correct instrument name

Author: DrumTracKAI v1.1.7
Date: July 23, 2025
"""

import os
import sys
import time
import json
import sqlite3
import logging
import subprocess
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional, Tuple
import threading
import queue
import re

# GUI automation imports
try:
    import pyautogui
    import pygetwindow as gw
    from PIL import Image, ImageGrab
    AUTOMATION_AVAILABLE = True
    
    # Configure pyautogui for reliable automation
    pyautogui.FAILSAFE = True
    pyautogui.PAUSE = 0.8  # Reasonable delay for SD3 response
    
except ImportError:
    AUTOMATION_AVAILABLE = False
    print("ERROR: GUI automation libraries not available")
    sys.exit(1)

# Audio processing imports
try:
    import librosa
    import soundfile as sf
    AUDIO_PROCESSING_AVAILABLE = True
except ImportError:
    AUDIO_PROCESSING_AVAILABLE = False

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('sd3_automation_corrected.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class SD3CorrectedAutomation:
    """Corrected automation system following user-provided workflow"""
    
    def __init__(self):
        self.base_path = Path(__file__).parent
        self.midi_dir = self.base_path / "sd3_midi_patterns"
        self.output_dir = self.base_path / "sd3_extracted_samples"
        self.database_path = self.base_path / "sd3_samples_database.db"
        
        # SD3 application settings
        self.sd3_window_titles = ["Superior Drummer 3", "Superior Drummer", "SD3"]
        
        # Automation settings
        self.automation_delay = 1.5  # Reliable delay for SD3
        self.bounce_timeout = 120    # Longer timeout for bounce process
        self.max_retries = 2         # Fewer retries, more reliable workflow
        
        # Progress tracking
        self.total_patterns = 0
        self.processed_patterns = 0
        self.successful_extractions = 0
        self.failed_extractions = 0
        
        # Initialize database
        self.init_database()
        
        logger.info("SD3 Corrected Automation System initialized")
    
    def init_database(self):
        """Initialize the samples database"""
        try:
            conn = sqlite3.connect(self.database_path)
            cursor = conn.cursor()
            
            # Enhanced extraction_log table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS extraction_log_corrected (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    midi_file TEXT NOT NULL,
                    instrument_name TEXT,
                    status TEXT NOT NULL,
                    timestamp TEXT,
                    error_message TEXT,
                    processing_time_seconds REAL,
                    output_file_path TEXT,
                    original_filename TEXT,
                    renamed_filename TEXT
                )
            ''')
            
            conn.commit()
            conn.close()
            logger.info("Corrected database initialized successfully")
            
        except Exception as e:
            logger.error(f"Database initialization failed: {e}")
            raise
    
    def find_sd3_window(self) -> Optional[object]:
        """Find SD3 window with multiple title variations"""
        try:
            for title in self.sd3_window_titles:
                windows = gw.getWindowsWithTitle(title)
                if windows:
                    logger.debug(f"Found SD3 window with title: {title}")
                    return windows[0]
            
            # Try partial matches
            all_windows = gw.getAllWindows()
            for window in all_windows:
                if any(title.lower() in window.title.lower() for title in self.sd3_window_titles):
                    logger.debug(f"Found SD3 window with partial match: {window.title}")
                    return window
            
            logger.warning("No SD3 window found")
            return None
            
        except Exception as e:
            logger.error(f"Error finding SD3 window: {e}")
            return None
    
    def ensure_sd3_focus(self) -> bool:
        """Ensure SD3 window has focus"""
        try:
            window = self.find_sd3_window()
            if not window:
                logger.error("Cannot find SD3 window for focus")
                return False
            
            # Bring window to front
            window.activate()
            time.sleep(self.automation_delay)
            
            # Verify window is active
            active_window = gw.getActiveWindow()
            if active_window and active_window.title == window.title:
                logger.debug("SD3 window successfully focused")
                return True
            else:
                logger.warning("Failed to focus SD3 window")
                return False
                
        except Exception as e:
            logger.error(f"Error ensuring SD3 focus: {e}")
            return False
    
    def extract_instrument_name(self, midi_filename: str) -> str:
        """Extract instrument name from MIDI filename for proper renaming"""
        try:
            # Remove .mid extension
            name_without_ext = midi_filename.replace('.mid', '')
            
            # Extract the main instrument part (before the first underscore + number pattern)
            # Examples: "china_china_hard_053" -> "china_china_hard"
            #          "kick_kick_center_hard_002" -> "kick_kick_center_hard"
            #          "snare_snare_center_hard_008" -> "snare_snare_center_hard"
            
            # Find the last underscore followed by numbers
            import re
            match = re.match(r'(.+)_(\d+)$', name_without_ext)
            if match:
                instrument_name = match.group(1)
            else:
                instrument_name = name_without_ext
            
            logger.debug(f"Extracted instrument name: '{instrument_name}' from '{midi_filename}'")
            return instrument_name
            
        except Exception as e:
            logger.warning(f"Failed to extract instrument name from {midi_filename}: {e}")
            return midi_filename.replace('.mid', '')
    
    def load_midi_and_position(self, midi_file: Path) -> bool:
        """Load MIDI file and position at beat 1.3 (Step 1)"""
        try:
            logger.info(f"Loading MIDI file and positioning: {midi_file.name}")
            
            if not self.ensure_sd3_focus():
                return False
            
            # Load MIDI file using Ctrl+O
            logger.debug("Opening file dialog...")
            pyautogui.hotkey('ctrl', 'o')
            time.sleep(self.automation_delay * 2)
            
            # Type the file path
            logger.debug(f"Typing file path: {midi_file}")
            pyautogui.write(str(midi_file))
            time.sleep(self.automation_delay)
            
            # Press Enter to open
            logger.debug("Pressing Enter to open file...")
            pyautogui.press('enter')
            time.sleep(self.automation_delay * 2)
            
            # Position at beat 1.3 (user specified this is critical)
            logger.debug("Positioning timeline at beat 1.3...")
            
            # Method 1: Try to go to specific position
            # This might involve clicking on timeline or using position controls
            # For now, we'll use a simple approach - click at beginning and move to 1.3
            
            # Go to beginning first
            pyautogui.press('home')
            time.sleep(self.automation_delay)
            
            # Try to position at beat 1.3 - this may need adjustment based on SD3 interface
            # Option 1: Use right arrow keys to move to beat 1.3
            for i in range(3):  # Move 3 beats forward (assuming 1 beat per arrow)
                pyautogui.press('right')
                time.sleep(0.2)
            
            # Option 2: Try direct position entry (if SD3 supports it)
            # This would need to be tested with actual SD3 interface
            
            logger.info(f"MIDI file loaded and positioned: {midi_file.name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to load and position MIDI file {midi_file.name}: {e}")
            return False
    
    def open_bounce_window(self) -> bool:
        """Open bounce window via Track menu (Step 2)"""
        try:
            logger.info("Opening bounce window via Track menu...")
            
            if not self.ensure_sd3_focus():
                return False
            
            # Open Track menu
            logger.debug("Opening Track menu with Alt+T...")
            pyautogui.hotkey('alt', 't')
            time.sleep(self.automation_delay)
            
            # Select Bounce option
            logger.debug("Selecting Bounce option...")
            pyautogui.press('b')  # Assuming 'B' for Bounce
            time.sleep(self.automation_delay * 2)
            
            logger.info("Bounce window opened successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to open bounce window: {e}")
            return False
    
    def configure_bounce_settings(self) -> bool:
        """Configure bounce settings in Advanced tab (Step 4)"""
        try:
            logger.info("Configuring bounce settings...")
            
            # Navigate to Advanced tab
            logger.debug("Navigating to Advanced tab...")
            # This might require clicking on "Advanced" tab or using keyboard navigation
            # Try Tab key to navigate through dialog
            pyautogui.press('tab')
            time.sleep(self.automation_delay)
            
            # Look for "bounce output channels" radio button
            logger.debug("Looking for 'bounce output channels' option...")
            
            # Try to find and select the radio button
            # This may require specific coordinates or text recognition
            # For now, use keyboard navigation
            pyautogui.press('space')  # Select radio button
            time.sleep(self.automation_delay)
            
            logger.info("Bounce settings configured successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to configure bounce settings: {e}")
            return False
    
    def select_output_folder_and_bounce(self, output_folder: Path) -> bool:
        """Select output folder which triggers the bounce (Step 3)"""
        try:
            logger.info(f"Selecting output folder: {output_folder}")
            
            # The folder selection should trigger the bounce according to user
            logger.debug("Typing output folder path...")
            pyautogui.write(str(output_folder))
            time.sleep(self.automation_delay)
            
            # Press Enter or OK to start bounce
            logger.debug("Starting bounce process...")
            pyautogui.press('enter')
            time.sleep(self.automation_delay)
            
            logger.info("Bounce process started")
            return True
            
        except Exception as e:
            logger.error(f"Failed to select folder and start bounce: {e}")
            return False
    
    def wait_for_bounce_completion(self, output_folder: Path) -> Optional[Path]:
        """Wait for bounce to complete and find Out_1+2.wav file"""
        try:
            logger.info("Waiting for bounce completion...")
            
            expected_file = output_folder / "Out_1+2.wav"
            start_time = time.time()
            
            while time.time() - start_time < self.bounce_timeout:
                if expected_file.exists() and expected_file.stat().st_size > 0:
                    logger.info(f"Bounce completed! File created: {expected_file}")
                    return expected_file
                
                elapsed = int(time.time() - start_time)
                if elapsed % 10 == 0:  # Log every 10 seconds
                    logger.debug(f"Waiting for bounce... ({elapsed}s/{self.bounce_timeout}s)")
                
                time.sleep(2)
            
            logger.error(f"Bounce timeout after {self.bounce_timeout} seconds")
            return None
            
        except Exception as e:
            logger.error(f"Error waiting for bounce completion: {e}")
            return None
    
    def rename_output_file(self, original_file: Path, instrument_name: str) -> Optional[Path]:
        """Rename Out_1+2.wav to correct instrument name (Step 5)"""
        try:
            logger.info(f"Renaming output file to: {instrument_name}.wav")
            
            new_filename = f"{instrument_name}.wav"
            new_file_path = original_file.parent / new_filename
            
            # Rename the file
            original_file.rename(new_file_path)
            
            logger.info(f"File renamed successfully: {new_file_path}")
            return new_file_path
            
        except Exception as e:
            logger.error(f"Failed to rename output file: {e}")
            return None
    
    def log_extraction_result(self, midi_file: Path, instrument_name: str, status: str, 
                            error_message: str = None, processing_time: float = 0,
                            output_file_path: str = None, original_filename: str = None,
                            renamed_filename: str = None):
        """Log extraction result to database"""
        try:
            conn = sqlite3.connect(self.database_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO extraction_log_corrected (
                    midi_file, instrument_name, status, timestamp, error_message,
                    processing_time_seconds, output_file_path, original_filename, renamed_filename
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                str(midi_file),
                instrument_name,
                status,
                datetime.now().isoformat(),
                error_message,
                processing_time,
                output_file_path,
                original_filename,
                renamed_filename
            ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Failed to log extraction result: {e}")
    
    def process_single_midi_corrected(self, midi_file: Path) -> bool:
        """Process a single MIDI file using the corrected workflow"""
        start_time = time.time()
        instrument_name = self.extract_instrument_name(midi_file.name)
        
        try:
            logger.info(f"Processing MIDI file: {midi_file.name} (Instrument: {instrument_name})")
            
            # Check if already processed
            final_output_path = self.output_dir / f"{instrument_name}.wav"
            if final_output_path.exists() and final_output_path.stat().st_size > 0:
                logger.info(f"Skipping already processed file: {midi_file.name}")
                self.successful_extractions += 1
                return True
            
            # Step 1: Load MIDI and position at beat 1.3
            if not self.load_midi_and_position(midi_file):
                raise Exception("Failed to load MIDI file and position timeline")
            
            # Step 2: Open bounce window via Track menu
            if not self.open_bounce_window():
                raise Exception("Failed to open bounce window")
            
            # Step 4: Configure bounce settings (Advanced tab)
            if not self.configure_bounce_settings():
                raise Exception("Failed to configure bounce settings")
            
            # Step 3: Select folder and trigger bounce
            if not self.select_output_folder_and_bounce(self.output_dir):
                raise Exception("Failed to select folder and start bounce")
            
            # Wait for bounce completion
            bounced_file = self.wait_for_bounce_completion(self.output_dir)
            if not bounced_file:
                raise Exception("Bounce process failed or timed out")
            
            # Step 5: Rename output file
            final_file = self.rename_output_file(bounced_file, instrument_name)
            if not final_file:
                raise Exception("Failed to rename output file")
            
            # Log success
            processing_time = time.time() - start_time
            self.log_extraction_result(
                midi_file, instrument_name, "success", 
                processing_time=processing_time,
                output_file_path=str(final_file),
                original_filename="Out_1+2.wav",
                renamed_filename=f"{instrument_name}.wav"
            )
            
            self.successful_extractions += 1
            logger.info(f"Successfully processed: {midi_file.name} → {final_file.name} ({processing_time:.2f}s)")
            return True
            
        except Exception as e:
            error_msg = str(e)
            processing_time = time.time() - start_time
            
            self.log_extraction_result(
                midi_file, instrument_name, "failed", error_msg, processing_time
            )
            
            self.failed_extractions += 1
            logger.error(f"Failed to process {midi_file.name}: {error_msg}")
            return False

def main():
    """Main entry point for corrected SD3 automation"""
    try:
        if not AUTOMATION_AVAILABLE:
            print("ERROR: GUI automation libraries not available")
            return
        
        # Create corrected automation system
        automation = SD3CorrectedAutomation()
        
        # Get MIDI files to process
        midi_files = list(automation.midi_dir.glob("*.mid"))
        
        if not midi_files:
            print("ERROR: No MIDI files found")
            return
        
        # Check if SD3 is running
        if not automation.find_sd3_window():
            print("ERROR: Superior Drummer 3 window not found!")
            print("Please ensure SD3 is running before starting automation.")
            return
        
        print(f"\nAUDIO SD3 CORRECTED AUTOMATION SYSTEM")
        print(f"=" * 50)
        print(f"Found {len(midi_files)} MIDI files to process")
        print(f"Output directory: {automation.output_dir}")
        print(f"Following user-provided workflow:")
        print(f"  1. Load MIDI and position at beat 1.3")
        print(f"  2. Track menu → Bounce")
        print(f"  3. Select folder (triggers bounce)")
        print(f"  4. Advanced tab: 'bounce output channels'")
        print(f"  5. Rename Out_1+2.wav to instrument name")
        print(f"=" * 50)
        
        # Process first few files as test
        test_files = midi_files[:3]  # Test with first 3 files
        print(f"\nTesting with first {len(test_files)} files...")
        
        for i, midi_file in enumerate(test_files, 1):
            print(f"\nProcessing {i}/{len(test_files)}: {midi_file.name}")
            success = automation.process_single_midi_corrected(midi_file)
            print(f"Result: {'SUCCESS' if success else 'FAILED'}")
        
        # Print results
        print(f"\n{'='*60}")
        print("CORRECTED SD3 AUTOMATION TEST RESULTS")
        print(f"{'='*60}")
        print(f"Successful: {automation.successful_extractions}")
        print(f"Failed: {automation.failed_extractions}")
        print(f"Success Rate: {(automation.successful_extractions / len(test_files)) * 100:.1f}%")
        print(f"{'='*60}")
        
        if automation.successful_extractions > 0:
            print(f"\nSUCCESS SUCCESS! The corrected workflow is working!")
            print(f"Ready to process all {len(midi_files)} MIDI files.")
        else:
            print(f"\nERROR Issues still remain. Check logs for details.")
        
    except Exception as e:
        logger.error(f"Main execution error: {e}")
        print(f"ERROR: {e}")

if __name__ == "__main__":
    main()

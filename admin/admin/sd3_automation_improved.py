#!/usr/bin/env python3
"""
Improved Superior Drummer 3 Automation System
=============================================

Addresses the rendering failures with:
1. More robust GUI automation with better error handling
2. Alternative export methods (drag-and-drop, menu navigation)
3. Better window management and focus handling
4. Detailed debugging and error reporting
5. Manual fallback options

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

# GUI automation imports
try:
    import pyautogui
    import pygetwindow as gw
    from PIL import Image, ImageGrab
    AUTOMATION_AVAILABLE = True
    
    # Configure pyautogui for more reliable automation
    pyautogui.FAILSAFE = True
    pyautogui.PAUSE = 0.5  # Slower, more reliable automation
    
except ImportError:
    AUTOMATION_AVAILABLE = False
    print("WARNING: GUI automation libraries not available")

# Audio processing imports
try:
    import librosa
    import soundfile as sf
    AUDIO_PROCESSING_AVAILABLE = True
except ImportError:
    AUDIO_PROCESSING_AVAILABLE = False

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,  # More detailed logging
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('sd3_automation_improved.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class SD3ImprovedAutomation:
    """Improved automation system with better error handling and multiple export methods"""
    
    def __init__(self):
        self.base_path = Path(__file__).parent
        self.midi_dir = self.base_path / "sd3_midi_patterns"
        self.output_dir = self.base_path / "sd3_extracted_samples"
        self.database_path = self.base_path / "sd3_samples_database.db"
        
        # SD3 application settings
        self.sd3_exe = Path("C:/Program Files/Toontrack/Superior Drummer/Superior Drummer 3.exe")
        self.sd3_window_titles = ["Superior Drummer 3", "Superior Drummer", "SD3"]  # Multiple possible titles
        
        # Improved automation settings
        self.automation_delay = 2.0  # Longer delays for reliability
        self.render_timeout = 60  # Longer timeout for complex renders
        self.max_retries = 3  # Retry failed operations
        
        # Export methods to try
        self.export_methods = [
            self.export_method_menu,
            self.export_method_keyboard,
            self.export_method_drag_drop
        ]
        
        # Progress tracking
        self.total_patterns = 0
        self.processed_patterns = 0
        self.successful_extractions = 0
        self.failed_extractions = 0
        
        # Initialize database
        self.init_database()
        
        logger.info("SD3 Improved Automation System initialized")
    
    def init_database(self):
        """Initialize the samples database with improved schema"""
        try:
            conn = sqlite3.connect(self.database_path)
            cursor = conn.cursor()
            
            # Enhanced extraction_log table with more debugging info
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS extraction_log_improved (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    midi_file TEXT NOT NULL,
                    status TEXT NOT NULL,
                    timestamp TEXT,
                    error_message TEXT,
                    processing_time_seconds REAL,
                    export_method_used TEXT,
                    window_found BOOLEAN,
                    file_created BOOLEAN,
                    retry_count INTEGER,
                    debug_info TEXT
                )
            ''')
            
            conn.commit()
            conn.close()
            logger.info("Improved database initialized successfully")
            
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
        """Ensure SD3 window has focus and is ready for automation"""
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
    
    def stop_and_rewind_playback(self) -> bool:
        """Stop playback and rewind to position 0 before processing"""
        try:
            logger.debug("Stopping playback and rewinding to position 0")
            
            if not self.ensure_sd3_focus():
                return False
            
            # Stop playback (spacebar is common stop key)
            pyautogui.press('space')
            time.sleep(self.automation_delay)
            
            # Rewind to beginning (Home key or Ctrl+Home)
            pyautogui.press('home')
            time.sleep(self.automation_delay)
            
            # Alternative: Try Ctrl+Home for rewind to start
            pyautogui.hotkey('ctrl', 'home')
            time.sleep(self.automation_delay)
            
            # Alternative: Try pressing '0' key to go to position 0
            pyautogui.press('0')
            time.sleep(self.automation_delay)
            
            logger.debug("Playback stopped and rewound to position 0")
            return True
            
        except Exception as e:
            logger.error(f"Failed to stop and rewind playback: {e}")
            return False
    
    def load_midi_to_timeline_improved(self, midi_file: Path) -> bool:
        """Improved MIDI loading with stop/rewind and better error handling"""
        try:
            logger.info(f"Loading MIDI file: {midi_file.name}")
            
            if not self.ensure_sd3_focus():
                return False
            
            # CRITICAL: Stop and rewind before loading new MIDI
            if not self.stop_and_rewind_playback():
                logger.warning("Failed to stop and rewind, continuing anyway...")
            
            # Method 1: Try keyboard shortcut
            try:
                pyautogui.hotkey('ctrl', 'o')
                time.sleep(self.automation_delay * 2)
                
                # Type the file path
                pyautogui.write(str(midi_file))
                time.sleep(self.automation_delay)
                
                # Press Enter to open
                pyautogui.press('enter')
                time.sleep(self.automation_delay * 2)
                
                logger.info(f"MIDI file loaded via keyboard shortcut: {midi_file.name}")
                return True
                
            except Exception as e:
                logger.warning(f"Keyboard shortcut method failed: {e}")
            
            # Method 2: Try menu navigation
            try:
                # Click File menu
                pyautogui.hotkey('alt', 'f')
                time.sleep(self.automation_delay)
                
                # Click Open
                pyautogui.press('o')
                time.sleep(self.automation_delay * 2)
                
                # Type the file path
                pyautogui.write(str(midi_file))
                time.sleep(self.automation_delay)
                
                # Press Enter to open
                pyautogui.press('enter')
                time.sleep(self.automation_delay * 2)
                
                logger.info(f"MIDI file loaded via menu navigation: {midi_file.name}")
                return True
                
            except Exception as e:
                logger.warning(f"Menu navigation method failed: {e}")
            
            return False
            
        except Exception as e:
            logger.error(f"Failed to load MIDI file {midi_file.name}: {e}")
            return False
    
    def export_method_menu(self, output_path: Path) -> bool:
        """Export via Track menu -> Export Song (correct SD3 command)"""
        try:
            logger.debug("Trying export via Track menu -> Export Song")
            
            # Track menu (correct menu for SD3 rendering)
            pyautogui.hotkey('alt', 't')
            time.sleep(self.automation_delay)
            
            # Navigate to "Export Song" option
            # First press 'e' for Export
            pyautogui.press('e')
            time.sleep(self.automation_delay)
            
            # Then press 's' for Song (Export Song)
            pyautogui.press('s')
            time.sleep(self.automation_delay * 2)
            
            # Set output path in the export dialog
            pyautogui.write(str(output_path))
            time.sleep(self.automation_delay)
            
            # Start export
            pyautogui.press('enter')
            time.sleep(self.automation_delay)
            
            return True
            
        except Exception as e:
            logger.debug(f"Track menu Export Song method failed: {e}")
            return False
    
    def export_method_keyboard(self, output_path: Path) -> bool:
        """Export via keyboard shortcuts"""
        try:
            logger.debug("Trying export via keyboard shortcuts")
            
            # Try common export shortcuts including Export Song
            shortcuts = [
                ['alt', 't', 'e', 's'],  # Track menu -> Export -> Song
                ['alt', 't', 'e'],       # Track menu -> Export
                ['ctrl', 'e'],
                ['ctrl', 'shift', 'e']
            ]
            
            for shortcut in shortcuts:
                try:
                    pyautogui.hotkey(*shortcut)
                    time.sleep(self.automation_delay * 2)
                    
                    # Set output path
                    pyautogui.write(str(output_path))
                    time.sleep(self.automation_delay)
                    
                    # Start export
                    pyautogui.press('enter')
                    
                    return True
                    
                except Exception as e:
                    logger.debug(f"Shortcut {shortcut} failed: {e}")
                    continue
            
            return False
            
        except Exception as e:
            logger.debug(f"Keyboard export method failed: {e}")
            return False
    
    def export_method_drag_drop(self, output_path: Path) -> bool:
        """Export via drag and drop (if supported)"""
        try:
            logger.debug("Trying export via drag and drop")
            
            # This would require more complex implementation
            # For now, return False to indicate not implemented
            return False
            
        except Exception as e:
            logger.debug(f"Drag drop export method failed: {e}")
            return False
    
    def render_audio_output_improved(self, output_filename: str) -> Tuple[bool, str, str]:
        """Improved audio rendering with stop/rewind and multiple methods"""
        try:
            logger.info(f"Rendering audio: {output_filename}")
            
            if not self.ensure_sd3_focus():
                return False, "focus_failed", "Could not focus SD3 window"
            
            # CRITICAL: Stop and rewind to position 0 before export
            if not self.stop_and_rewind_playback():
                logger.warning("Failed to stop and rewind before export, continuing anyway...")
            
            output_path = self.output_dir / f"{output_filename}.wav"
            
            # Try each export method
            for i, export_method in enumerate(self.export_methods):
                method_name = export_method.__name__
                logger.debug(f"Trying export method {i+1}/{len(self.export_methods)}: {method_name}")
                
                try:
                    if export_method(output_path):
                        # Wait for render to complete
                        render_start = time.time()
                        while time.time() - render_start < self.render_timeout:
                            if output_path.exists() and output_path.stat().st_size > 0:
                                logger.info(f"Audio rendered successfully with {method_name}: {output_filename}.wav")
                                return True, method_name, "Success"
                            time.sleep(1)
                        
                        # Check if file was created but is empty
                        if output_path.exists():
                            return False, method_name, f"File created but empty (size: {output_path.stat().st_size})"
                        else:
                            return False, method_name, f"File not created within timeout ({self.render_timeout}s)"
                    
                except Exception as e:
                    logger.debug(f"Export method {method_name} exception: {e}")
                    continue
            
            return False, "all_methods_failed", "All export methods failed"
            
        except Exception as e:
            logger.error(f"Failed to render audio {output_filename}: {e}")
            return False, "exception", str(e)
    
    def log_extraction_result_improved(self, midi_file: Path, status: str, error_message: str = None, 
                                     processing_time: float = 0, export_method: str = None, 
                                     window_found: bool = False, file_created: bool = False, 
                                     retry_count: int = 0, debug_info: str = None):
        """Enhanced logging with more debugging information"""
        try:
            conn = sqlite3.connect(self.database_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO extraction_log_improved (
                    midi_file, status, timestamp, error_message, processing_time_seconds,
                    export_method_used, window_found, file_created, retry_count, debug_info
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                str(midi_file),
                status,
                datetime.now().isoformat(),
                error_message,
                processing_time,
                export_method,
                window_found,
                file_created,
                retry_count,
                debug_info
            ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Failed to log extraction result: {e}")
    
    def process_single_midi_improved(self, midi_file: Path) -> bool:
        """Process a single MIDI file with improved error handling and retries"""
        start_time = time.time()
        
        for attempt in range(self.max_retries):
            try:
                logger.info(f"Processing MIDI file (attempt {attempt + 1}/{self.max_retries}): {midi_file.name}")
                
                output_filename = midi_file.stem
                output_path = self.output_dir / f"{output_filename}.wav"
                
                # Skip if already processed
                if output_path.exists() and output_path.stat().st_size > 0:
                    logger.info(f"Skipping already processed file: {midi_file.name}")
                    self.successful_extractions += 1
                    return True
                
                # Check if SD3 window exists
                window_found = self.find_sd3_window() is not None
                
                # Step 1: Load MIDI into timeline
                if not self.load_midi_to_timeline_improved(midi_file):
                    raise Exception("Failed to load MIDI file")
                
                # Step 2: Render audio output
                success, export_method, error_detail = self.render_audio_output_improved(output_filename)
                
                if not success:
                    raise Exception(f"Failed to render audio: {error_detail}")
                
                # Step 3: Verify output file
                file_created = output_path.exists() and output_path.stat().st_size > 0
                
                if not file_created:
                    raise Exception("Output file was not created or is empty")
                
                processing_time = time.time() - start_time
                self.log_extraction_result_improved(
                    midi_file, "success", processing_time=processing_time,
                    export_method=export_method, window_found=window_found,
                    file_created=file_created, retry_count=attempt
                )
                
                self.successful_extractions += 1
                logger.info(f"Successfully processed: {midi_file.name} ({processing_time:.2f}s)")
                return True
                
            except Exception as e:
                error_msg = str(e)
                logger.warning(f"Attempt {attempt + 1} failed for {midi_file.name}: {error_msg}")
                
                if attempt == self.max_retries - 1:  # Last attempt
                    processing_time = time.time() - start_time
                    window_found = self.find_sd3_window() is not None
                    output_path = self.output_dir / f"{midi_file.stem}.wav"
                    file_created = output_path.exists()
                    
                    self.log_extraction_result_improved(
                        midi_file, "failed", error_msg, processing_time,
                        window_found=window_found, file_created=file_created,
                        retry_count=attempt + 1, debug_info=f"All {self.max_retries} attempts failed"
                    )
                    
                    self.failed_extractions += 1
                    logger.error(f"Failed to process {midi_file.name} after {self.max_retries} attempts: {error_msg}")
                    return False
                
                # Wait before retry
                time.sleep(self.automation_delay * 2)
        
        return False

def main():
    """Main entry point for improved SD3 automation"""
    try:
        if not AUTOMATION_AVAILABLE:
            print("ERROR: GUI automation libraries not available")
            print("Install with: pip install pyautogui pygetwindow pillow")
            return
        
        # Create improved automation system
        automation = SD3ImprovedAutomation()
        
        # Get a small sample of MIDI files for testing
        midi_files = list(automation.midi_dir.glob("*.mid"))[:5]  # Test with first 5 files
        
        if not midi_files:
            print("ERROR: No MIDI files found")
            return
        
        print(f"\nTesting improved automation with {len(midi_files)} MIDI files...")
        print("This will help diagnose the rendering issues.")
        
        # Check if SD3 is running
        if not automation.find_sd3_window():
            print("WARNING: Superior Drummer 3 window not found!")
            print("Please ensure SD3 is running before starting automation.")
            return
        
        # Process test files
        for i, midi_file in enumerate(midi_files, 1):
            print(f"\nProcessing test file {i}/{len(midi_files)}: {midi_file.name}")
            success = automation.process_single_midi_improved(midi_file)
            print(f"Result: {'SUCCESS' if success else 'FAILED'}")
        
        # Print results
        print(f"\n{'='*60}")
        print("IMPROVED SD3 AUTOMATION TEST RESULTS")
        print(f"{'='*60}")
        print(f"Successful: {automation.successful_extractions}")
        print(f"Failed: {automation.failed_extractions}")
        print(f"Success Rate: {(automation.successful_extractions / len(midi_files)) * 100:.1f}%")
        print(f"{'='*60}")
        
        if automation.failed_extractions > 0:
            print("\nCheck the database for detailed error information:")
            print("python -c \"import sqlite3; conn = sqlite3.connect('sd3_samples_database.db'); cursor = conn.cursor(); cursor.execute('SELECT * FROM extraction_log_improved ORDER BY id DESC LIMIT 5'); [print(f'Status: {row[2]}, Error: {row[4]}, Method: {row[6]}, Window: {row[7]}, File: {row[8]}') for row in cursor.fetchall()]; conn.close()\"")
        
    except Exception as e:
        logger.error(f"Main execution error: {e}")
        print(f"ERROR: {e}")

if __name__ == "__main__":
    main()

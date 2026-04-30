#!/usr/bin/env python3
"""
Superior Drummer 3 Complete Automation System
=============================================

Fully automated SD3 sample extraction with:
1. Automatic MIDI clip loading into timeline
2. Automatic audio rendering and export
3. Automatic database storage and organization
4. Real-time progress monitoring and error handling

Author: DrumTracKAI v1.1.7
Date: July 22, 2025
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
    AUTOMATION_AVAILABLE = True
except ImportError:
    AUTOMATION_AVAILABLE = False
    print("WARNING: pyautogui and pygetwindow not available. Install with: pip install pyautogui pygetwindow")

# Audio processing imports
try:
    import librosa
    import soundfile as sf
    AUDIO_PROCESSING_AVAILABLE = True
except ImportError:
    AUDIO_PROCESSING_AVAILABLE = False
    print("WARNING: librosa and soundfile not available. Install with: pip install librosa soundfile")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('sd3_automation_complete.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class SD3CompleteAutomation:
    """Complete automation system for Superior Drummer 3 sample extraction"""
    
    def __init__(self):
        self.base_path = Path(__file__).parent
        self.midi_dir = self.base_path / "sd3_midi_patterns"
        self.output_dir = self.base_path / "sd3_extracted_samples"
        self.database_path = self.base_path / "sd3_samples_database.db"
        
        # SD3 application settings
        self.sd3_exe = Path("C:/Program Files/Toontrack/Superior Drummer/Superior Drummer 3.exe")
        self.sd3_window_title = "Superior Drummer 3"
        
        # Automation settings
        self.automation_delay = 1.0  # Delay between automation steps
        self.render_timeout = 30  # Max time to wait for render completion
        
        # Progress tracking
        self.total_patterns = 0
        self.processed_patterns = 0
        self.successful_extractions = 0
        self.failed_extractions = 0
        self.extraction_queue = queue.Queue()
        
        # Initialize database
        self.init_database()
        
        logger.info("SD3 Complete Automation System initialized")
    
    def init_database(self):
        """Initialize the samples database"""
        try:
            conn = sqlite3.connect(self.database_path)
            cursor = conn.cursor()
            
            # Create samples table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS samples (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    filename TEXT UNIQUE NOT NULL,
                    drum_component TEXT NOT NULL,
                    articulation TEXT NOT NULL,
                    velocity TEXT NOT NULL,
                    timing_pattern TEXT NOT NULL,
                    file_path TEXT NOT NULL,
                    file_size INTEGER,
                    duration_seconds REAL,
                    sample_rate INTEGER,
                    bit_depth INTEGER,
                    created_timestamp TEXT,
                    extraction_metadata TEXT
                )
            ''')
            
            # Create extraction_log table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS extraction_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    midi_file TEXT NOT NULL,
                    status TEXT NOT NULL,
                    timestamp TEXT,
                    error_message TEXT,
                    processing_time_seconds REAL
                )
            ''')
            
            conn.commit()
            conn.close()
            logger.info("Database initialized successfully")
            
        except Exception as e:
            logger.error(f"Database initialization failed: {e}")
            raise
    
    def find_sd3_window(self) -> Optional[object]:
        """Find and return the Superior Drummer 3 window"""
        try:
            windows = gw.getWindowsWithTitle(self.sd3_window_title)
            if windows:
                return windows[0]
            return None
        except Exception as e:
            logger.error(f"Error finding SD3 window: {e}")
            return None
    
    def wait_for_sd3_ready(self, timeout: int = 60) -> bool:
        """Wait for Superior Drummer 3 to be ready for automation"""
        logger.info("Waiting for Superior Drummer 3 to be ready...")
        
        start_time = time.time()
        while time.time() - start_time < timeout:
            window = self.find_sd3_window()
            if window and window.isActive:
                logger.info("Superior Drummer 3 is ready")
                return True
            time.sleep(2)
        
        logger.error("Timeout waiting for Superior Drummer 3 to be ready")
        return False
    
    def load_midi_to_timeline(self, midi_file: Path) -> bool:
        """Automatically load MIDI file into SD3 timeline"""
        try:
            logger.info(f"Loading MIDI file: {midi_file.name}")
            
            # Find and activate SD3 window
            window = self.find_sd3_window()
            if not window:
                logger.error("SD3 window not found")
                return False
            
            window.activate()
            time.sleep(self.automation_delay)
            
            # Open file dialog (Ctrl+O)
            pyautogui.hotkey('ctrl', 'o')
            time.sleep(self.automation_delay * 2)
            
            # Type the file path
            pyautogui.write(str(midi_file))
            time.sleep(self.automation_delay)
            
            # Press Enter to open
            pyautogui.press('enter')
            time.sleep(self.automation_delay * 2)
            
            logger.info(f"MIDI file loaded: {midi_file.name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to load MIDI file {midi_file.name}: {e}")
            return False
    
    def render_audio_output(self, output_filename: str) -> bool:
        """Automatically render and export audio from SD3"""
        try:
            logger.info(f"Rendering audio: {output_filename}")
            
            # Find and activate SD3 window
            window = self.find_sd3_window()
            if not window:
                logger.error("SD3 window not found")
                return False
            
            window.activate()
            time.sleep(self.automation_delay)
            
            # Open export dialog (typically Ctrl+E or File > Export)
            pyautogui.hotkey('ctrl', 'e')
            time.sleep(self.automation_delay * 2)
            
            # Set output filename
            output_path = self.output_dir / f"{output_filename}.wav"
            pyautogui.write(str(output_path))
            time.sleep(self.automation_delay)
            
            # Start export/render
            pyautogui.press('enter')
            
            # Wait for render to complete
            render_start = time.time()
            while time.time() - render_start < self.render_timeout:
                if output_path.exists():
                    logger.info(f"Audio rendered successfully: {output_filename}.wav")
                    return True
                time.sleep(1)
            
            logger.error(f"Render timeout for {output_filename}")
            return False
            
        except Exception as e:
            logger.error(f"Failed to render audio {output_filename}: {e}")
            return False
    
    def analyze_audio_file(self, audio_file: Path) -> Dict:
        """Analyze extracted audio file and return metadata"""
        try:
            if not AUDIO_PROCESSING_AVAILABLE:
                return {"error": "Audio processing libraries not available"}
            
            # Load audio file
            y, sr = librosa.load(audio_file)
            duration = librosa.get_duration(y=y, sr=sr)
            
            # Get file info
            file_info = sf.info(audio_file)
            
            metadata = {
                "duration_seconds": duration,
                "sample_rate": file_info.samplerate,
                "channels": file_info.channels,
                "frames": file_info.frames,
                "file_size": audio_file.stat().st_size,
                "bit_depth": file_info.subtype_info.name if hasattr(file_info, 'subtype_info') else "Unknown"
            }
            
            logger.info(f"Audio analysis complete: {audio_file.name}")
            return metadata
            
        except Exception as e:
            logger.error(f"Audio analysis failed for {audio_file.name}: {e}")
            return {"error": str(e)}
    
    def parse_midi_filename(self, midi_file: Path) -> Dict:
        """Parse MIDI filename to extract drum component and articulation info"""
        try:
            # Example filename: kick_kick_center_hard_single_001.mid
            parts = midi_file.stem.split('_')
            
            if len(parts) >= 5:
                return {
                    "drum_component": parts[0],
                    "sub_component": parts[1] if len(parts) > 1 else "",
                    "position": parts[2] if len(parts) > 2 else "",
                    "velocity": parts[3] if len(parts) > 3 else "",
                    "timing_pattern": parts[4] if len(parts) > 4 else "",
                    "variation": parts[5] if len(parts) > 5 else "000"
                }
            else:
                return {
                    "drum_component": "unknown",
                    "sub_component": "",
                    "position": "",
                    "velocity": "medium",
                    "timing_pattern": "single",
                    "variation": "000"
                }
                
        except Exception as e:
            logger.error(f"Failed to parse filename {midi_file.name}: {e}")
            return {"drum_component": "unknown", "velocity": "medium", "timing_pattern": "single"}
    
    def store_sample_in_database(self, midi_file: Path, audio_file: Path, metadata: Dict) -> bool:
        """Store extracted sample information in database"""
        try:
            conn = sqlite3.connect(self.database_path)
            cursor = conn.cursor()
            
            # Parse MIDI filename
            file_info = self.parse_midi_filename(midi_file)
            
            # Analyze audio
            audio_metadata = self.analyze_audio_file(audio_file)
            
            # Insert sample record
            cursor.execute('''
                INSERT OR REPLACE INTO samples (
                    filename, drum_component, articulation, velocity, timing_pattern,
                    file_path, file_size, duration_seconds, sample_rate, bit_depth,
                    created_timestamp, extraction_metadata
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                audio_file.name,
                file_info.get("drum_component", "unknown"),
                f"{file_info.get('position', '')} {file_info.get('sub_component', '')}".strip(),
                file_info.get("velocity", "medium"),
                file_info.get("timing_pattern", "single"),
                str(audio_file),
                audio_metadata.get("file_size", 0),
                audio_metadata.get("duration_seconds", 0),
                audio_metadata.get("sample_rate", 44100),
                str(audio_metadata.get("bit_depth", "16")),
                datetime.now().isoformat(),
                json.dumps({"midi_source": str(midi_file), "audio_metadata": audio_metadata})
            ))
            
            conn.commit()
            conn.close()
            
            logger.info(f"Sample stored in database: {audio_file.name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to store sample in database: {e}")
            return False
    
    def log_extraction_result(self, midi_file: Path, status: str, error_message: str = None, processing_time: float = 0):
        """Log extraction result to database"""
        try:
            conn = sqlite3.connect(self.database_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO extraction_log (
                    midi_file, status, timestamp, error_message, processing_time_seconds
                ) VALUES (?, ?, ?, ?, ?)
            ''', (
                str(midi_file),
                status,
                datetime.now().isoformat(),
                error_message,
                processing_time
            ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Failed to log extraction result: {e}")
    
    def process_single_midi(self, midi_file: Path) -> bool:
        """Process a single MIDI file through the complete automation pipeline"""
        start_time = time.time()
        
        try:
            logger.info(f"Processing MIDI file: {midi_file.name}")
            
            # Generate output filename
            output_filename = midi_file.stem
            output_path = self.output_dir / f"{output_filename}.wav"
            
            # Skip if already processed
            if output_path.exists():
                logger.info(f"Skipping already processed file: {midi_file.name}")
                self.successful_extractions += 1
                return True
            
            # Step 1: Load MIDI into timeline
            if not self.load_midi_to_timeline(midi_file):
                raise Exception("Failed to load MIDI file")
            
            # Step 2: Render audio output
            if not self.render_audio_output(output_filename):
                raise Exception("Failed to render audio")
            
            # Step 3: Verify output file exists
            if not output_path.exists():
                raise Exception("Output file was not created")
            
            # Step 4: Store in database
            if not self.store_sample_in_database(midi_file, output_path, {}):
                logger.warning(f"Failed to store in database, but extraction succeeded: {midi_file.name}")
            
            processing_time = time.time() - start_time
            self.log_extraction_result(midi_file, "success", processing_time=processing_time)
            
            self.successful_extractions += 1
            logger.info(f"Successfully processed: {midi_file.name} ({processing_time:.2f}s)")
            return True
            
        except Exception as e:
            processing_time = time.time() - start_time
            error_msg = str(e)
            
            self.log_extraction_result(midi_file, "failed", error_msg, processing_time)
            self.failed_extractions += 1
            
            logger.error(f"Failed to process {midi_file.name}: {error_msg}")
            return False
        
        finally:
            self.processed_patterns += 1
    
    def run_automated_extraction(self) -> Dict:
        """Run the complete automated extraction process"""
        logger.info("Starting automated SD3 extraction process")
        
        if not AUTOMATION_AVAILABLE:
            logger.error("GUI automation libraries not available")
            return {"error": "Automation libraries not available"}
        
        # Get all MIDI files
        midi_files = list(self.midi_dir.glob("*.mid"))
        self.total_patterns = len(midi_files)
        
        if self.total_patterns == 0:
            logger.error("No MIDI files found")
            return {"error": "No MIDI files found"}
        
        logger.info(f"Found {self.total_patterns} MIDI patterns to process")
        
        # Wait for SD3 to be ready
        if not self.wait_for_sd3_ready():
            return {"error": "Superior Drummer 3 not ready"}
        
        # Process each MIDI file
        start_time = time.time()
        
        for i, midi_file in enumerate(midi_files, 1):
            logger.info(f"Processing {i}/{self.total_patterns}: {midi_file.name}")
            
            success = self.process_single_midi(midi_file)
            
            # Progress update
            progress = (i / self.total_patterns) * 100
            logger.info(f"Progress: {progress:.1f}% ({i}/{self.total_patterns})")
            
            # Small delay between files
            time.sleep(0.5)
        
        total_time = time.time() - start_time
        
        # Final results
        results = {
            "total_patterns": self.total_patterns,
            "processed_patterns": self.processed_patterns,
            "successful_extractions": self.successful_extractions,
            "failed_extractions": self.failed_extractions,
            "success_rate": (self.successful_extractions / self.total_patterns) * 100 if self.total_patterns > 0 else 0,
            "total_time_seconds": total_time,
            "average_time_per_sample": total_time / self.total_patterns if self.total_patterns > 0 else 0
        }
        
        logger.info("Automated extraction completed")
        logger.info(f"Results: {json.dumps(results, indent=2)}")
        
        return results

def main():
    """Main entry point for automated SD3 extraction"""
    try:
        # Create automation system
        automation = SD3CompleteAutomation()
        
        # Run automated extraction
        results = automation.run_automated_extraction()
        
        # Print final summary
        print("\n" + "="*60)
        print("SD3 AUTOMATED EXTRACTION COMPLETED")
        print("="*60)
        print(f"Total Patterns: {results.get('total_patterns', 0)}")
        print(f"Successful Extractions: {results.get('successful_extractions', 0)}")
        print(f"Failed Extractions: {results.get('failed_extractions', 0)}")
        print(f"Success Rate: {results.get('success_rate', 0):.1f}%")
        print(f"Total Time: {results.get('total_time_seconds', 0):.1f} seconds")
        print(f"Average Time per Sample: {results.get('average_time_per_sample', 0):.2f} seconds")
        print("="*60)
        
        # Save results to file
        results_file = Path(__file__).parent / f"sd3_automation_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(results_file, 'w') as f:
            json.dump(results, f, indent=2)
        
        print(f"Results saved to: {results_file}")
        
    except Exception as e:
        logger.error(f"Main execution error: {e}")
        print(f"ERROR: {e}")

if __name__ == "__main__":
    main()

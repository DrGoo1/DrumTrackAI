#!/usr/bin/env python3
"""
Superior Drummer 3 Sample Extraction Launcher
Starts the SD3 extraction process and monitors progress
"""

import os
import subprocess
import time
import json
from pathlib import Path
from typing import List, Dict
import shutil

class SD3ExtractionLauncher:
    """Launch and monitor Superior Drummer 3 sample extraction"""
    
    def __init__(self):
        self.sd3_exe = Path("C:/Program Files/Toontrack/Superior Drummer/Superior Drummer 3.exe")
        self.midi_dir = Path("./sd3_midi_patterns")
        self.output_dir = Path("./sd3_extracted_samples")
        self.batch_script = self.output_dir / "extract_samples.bat"
        
        print(f"AUDIO Superior Drummer 3 Extraction Launcher")
        print(f"=" * 50)
        print(f"SD3 Executable: {self.sd3_exe}")
        print(f"MIDI Patterns: {self.midi_dir}")
        print(f"Output Directory: {self.output_dir}")
    
    def check_prerequisites(self):
        """Check if all prerequisites are met"""
        print(f"\nINSPECTING Checking Prerequisites...")
        
        # Check if SD3 is installed
        if not self.sd3_exe.exists():
            print(f"ERROR Superior Drummer 3 not found at: {self.sd3_exe}")
            print(f"Please ensure Superior Drummer 3 is properly installed")
            return False
        else:
            print(f" Superior Drummer 3 found")
        
        # Check if MIDI patterns exist
        if not self.midi_dir.exists():
            print(f"ERROR MIDI patterns directory not found: {self.midi_dir}")
            print(f"Please run the SD3 sample extractor first")
            return False
        
        midi_files = list(self.midi_dir.glob("*.mid"))
        if not midi_files:
            print(f"ERROR No MIDI files found in: {self.midi_dir}")
            return False
        else:
            print(f" Found {len(midi_files)} MIDI patterns")
        
        # Create output directory
        self.output_dir.mkdir(exist_ok=True)
        print(f" Output directory ready: {self.output_dir}")
        
        return True
    
    def launch_superior_drummer_3(self):
        """Launch Superior Drummer 3 application"""
        print(f"\nLAUNCH Launching Superior Drummer 3...")
        
        try:
            # Launch SD3 in the background
            process = subprocess.Popen([str(self.sd3_exe)], 
                                     shell=True,
                                     stdout=subprocess.PIPE,
                                     stderr=subprocess.PIPE)
            
            print(f" Superior Drummer 3 launched (PID: {process.pid})")
            print(f"⏳ Waiting for SD3 to fully load...")
            time.sleep(10)  # Give SD3 time to load
            
            return process
        
        except Exception as e:
            print(f"ERROR Error launching Superior Drummer 3: {e}")
            return None
    
    def create_extraction_instructions(self):
        """Create step-by-step extraction instructions"""
        instructions = f"""
AUDIO SUPERIOR DRUMMER 3 SAMPLE EXTRACTION INSTRUCTIONS
{"=" * 60}

Superior Drummer 3 should now be running. Follow these steps:

STEP 1: LOAD STATE OF THE ART LIBRARY
1. In Superior Drummer 3, click on the library browser
2. Select "State of the Art" library (any variation: Library, ISO, or Live)
3. Load a drum kit from the State of the Art collection

STEP 2: SET UP BATCH EXPORT
1. Go to File → Export → Audio
2. Set export settings:
   - Format: WAV
   - Sample Rate: 44.1 kHz  
   - Bit Depth: 24-bit
   - Channels: Stereo
   - Output Directory: {self.output_dir.absolute()}

STEP 3: IMPORT MIDI PATTERNS
1. Go to File → Import → MIDI
2. Navigate to: {self.midi_dir.absolute()}
3. Select ALL MIDI files (Ctrl+A)
4. Import all {len(list(self.midi_dir.glob('*.mid')))} patterns

STEP 4: BATCH RENDER
1. Select all imported MIDI patterns
2. Click "Export Audio" or "Render"
3. Choose "Batch Export" if available
4. Start the rendering process

STEP 5: MONITOR PROGRESS
- Watch the web monitor for real-time progress updates
- The system will automatically detect extracted WAV files
- Progress will be shown as: {len(list(self.midi_dir.glob('*.mid')))} total patterns

EXTRACTION BREAKDOWN:
- Hi-hat samples: 336 patterns (enhanced sensitivity)
- Ride samples: 192 patterns (comprehensive articulations)  
- Other drums: 54 patterns (kick, snare, toms, cymbals)
- Total: 582 patterns for maximum DrumTracKAI accuracy

The web monitor will automatically update as samples are extracted!
"""
        
        instructions_file = self.output_dir / "EXTRACTION_STEPS.txt"
        with open(instructions_file, 'w', encoding='utf-8') as f:
            f.write(instructions)
        
        print(f" Created extraction instructions: {instructions_file}")
        return instructions_file
    
    def monitor_extraction_progress(self):
        """Monitor the extraction progress"""
        print(f"\nANALYSIS Monitoring Extraction Progress...")
        print(f"Watch the web monitor for real-time updates!")
        print(f"Expected files: {len(list(self.midi_dir.glob('*.mid')))}")
        
        total_patterns = len(list(self.midi_dir.glob("*.mid")))
        
        while True:
            try:
                # Count extracted WAV files
                wav_files = list(self.output_dir.glob("*.wav"))
                extracted_count = len(wav_files)
                
                if extracted_count > 0:
                    progress = (extracted_count / total_patterns) * 100
                    print(f"\rAUDIO Progress: {extracted_count}/{total_patterns} ({progress:.1f}%) extracted", end="")
                    
                    if extracted_count >= total_patterns:
                        print(f"\nSUCCESS Extraction Complete! All {total_patterns} samples extracted")
                        break
                
                time.sleep(5)  # Check every 5 seconds
                
            except KeyboardInterrupt:
                print(f"\n⏹ Monitoring stopped by user")
                break
            except Exception as e:
                print(f"\nERROR Error monitoring progress: {e}")
                break
    
    def open_directories(self):
        """Open relevant directories for user convenience"""
        print(f"\nFOLDER Opening directories...")
        
        try:
            # Open MIDI patterns directory
            subprocess.run(f'explorer "{self.midi_dir.absolute()}"', shell=True)
            print(f" Opened MIDI patterns directory")
            
            # Open output directory  
            subprocess.run(f'explorer "{self.output_dir.absolute()}"', shell=True)
            print(f" Opened output directory")
            
        except Exception as e:
            print(f"ERROR Error opening directories: {e}")

def main():
    """Main execution"""
    print(f"DRUM Starting Superior Drummer 3 Sample Extraction")
    print(f"Real-time monitoring available in the web monitor!")
    print()
    
    launcher = SD3ExtractionLauncher()
    
    # Step 1: Check prerequisites
    if not launcher.check_prerequisites():
        print(f"\nERROR Prerequisites not met. Please resolve issues and try again.")
        return
    
    # Step 2: Create extraction instructions
    instructions_file = launcher.create_extraction_instructions()
    
    # Step 3: Launch Superior Drummer 3
    sd3_process = launcher.launch_superior_drummer_3()
    
    if not sd3_process:
        print(f"\nERROR Failed to launch Superior Drummer 3")
        return
    
    # Step 4: Open directories for convenience
    launcher.open_directories()
    
    # Step 5: Display instructions
    print(f"\n NEXT STEPS:")
    print(f"1. Superior Drummer 3 is now running")
    print(f"2. Follow the instructions in: {instructions_file}")
    print(f"3. Monitor progress in the web monitor")
    print(f"4. This script will monitor extraction progress")
    print(f"\nPress Enter to start monitoring, or Ctrl+C to exit...")
    
    try:
        input()
        launcher.monitor_extraction_progress()
    except KeyboardInterrupt:
        print(f"\n Extraction launcher stopped")
    
    print(f"\nSUCCESS Superior Drummer 3 Sample Extraction Setup Complete!")
    print(f"Continue monitoring in the web monitor for real-time updates.")

if __name__ == "__main__":
    main()

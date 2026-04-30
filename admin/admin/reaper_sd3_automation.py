#!/usr/bin/env python3
"""
Reaper + SD3 Automation Script
==============================

Uses Reaper DAW with Superior Drummer 3 loaded as a plugin to automate
the entire MIDI to WAV extraction process. This bypasses all the automation
issues we encountered with SD3 standalone.

Workflow:
1. Setup Reaper project with SD3 plugin
2. Import MIDI files programmatically
3. Position at beat 1.3 (or appropriate location)
4. Render audio output
5. Save with proper naming
6. Batch process all files

Author: DrumTracKAI v1.1.7
Date: July 23, 2025
"""

import time
import os
from pathlib import Path
import re
import subprocess

try:
    import pyautogui
    pyautogui.FAILSAFE = True
    pyautogui.PAUSE = 1.0
    print("SUCCESS Automation libraries loaded")
except ImportError as e:
    print(f"ERROR Import error: {e}")
    exit(1)

class ReaperSD3Automation:
    """Reaper automation for SD3 sample extraction"""
    
    def __init__(self):
        self.base_path = Path(__file__).parent
        self.midi_dir = self.base_path / "sd3_midi_patterns"
        self.output_dir = self.base_path / "sd3_extracted_samples"
        self.reaper_project_dir = self.base_path / "reaper_projects"
        
        # Create directories
        self.output_dir.mkdir(exist_ok=True)
        self.reaper_project_dir.mkdir(exist_ok=True)
        
        # Reaper executable path (common locations)
        self.reaper_exe = self.find_reaper_executable()
        
        print(f"FOLDER MIDI directory: {self.midi_dir}")
        print(f"FOLDER Output directory: {self.output_dir}")
        print(f"FOLDER Reaper projects: {self.reaper_project_dir}")
        print(f"AUDIO Reaper executable: {self.reaper_exe}")
    
    def find_reaper_executable(self):
        """Find Reaper executable in common locations"""
        common_paths = [
            "C:/Program Files/REAPER (x64)/reaper.exe",
            "C:/Program Files/REAPER/reaper.exe",
            "C:/Program Files (x86)/REAPER/reaper.exe",
        ]
        
        for path in common_paths:
            if Path(path).exists():
                return Path(path)
        
        print("WARNING  Reaper executable not found in common locations")
        return None
    
    def create_reaper_project_template(self):
        """Create a Reaper project template with SD3 loaded"""
        template_path = self.reaper_project_dir / "SD3_Template.RPP"
        
        # Basic Reaper project file with SD3 plugin
        reaper_project_content = '''<REAPER_PROJECT 0.1 "6.82/win64" 1640995200
  RIPPLE 0
  GROUPOVERRIDE 0 0 0
  AUTOXFADE 1
  ENVATTACH 1
  POOLEDENVATTACH 0
  MIXERUIFLAGS 11 48
  PEAKGAIN 1
  FEEDBACK 0
  PANLAW 1
  PROJOFFS 0 0 0
  MAXPROJLEN 0 600
  GRID 3199 8 1 8 1 0 0 0
  TIMEMODE 1 5 -1 30 0 0 -1
  VIDEO_CONFIG 0 0 1
  PANMODE 3
  CURSOR 0
  ZOOM 100 0 0
  VZOOMEX 6 0
  USE_REC_CFG 0
  RECMODE 1
  SMPTESYNC 0 30 100 40 1000 300 0 0 1 0 0
  <RECORD_CFG
    ZXZhdxgAAQ==
  >
  <APPLYFX_CFG
  >
  RENDER_FILE ""
  RENDER_PATTERN ""
  RENDER_FMT 0 2 0
  RENDER_1X 0
  RENDER_RANGE 1 0 0 18 1000
  RENDER_RESAMPLE 3 0 1
  RENDER_ADDTOPROJ 0
  RENDER_STEMS 0
  RENDER_DITHER 0
  TIMELOCKMODE 1
  TEMPOENVLOCKMODE 1
  ITEMMIX 0
  DEFPITCHMODE 589824 0
  TAKELANE 1
  SAMPLERATE 44100 0 0
  <TRACK {GUID}
    NAME "SD3 Drums"
    PEAKCOL 16576
    BEAT -1
    AUTOMODE 0
    VOLPAN 1 0 -1 -1 1
    MUTESOLO 0 0 0
    IPHASE 0
    PLAYOFFS 0 1
    ISBUS 0 0
    BUSCOMP 0 0 0 0 0
    SHOWINMIX 1 0.6667 0.5 1 0.5 0 0 0
    FREEMODE 0
    SEL 0
    REC 0 0 1 0 0 0 0 0
    VU 2
    TRACKHEIGHT 0 0 0 0 0 0
    INQ 0 0 0 0.5 100 0 0 100
    NCHAN 2
    FX 1
    TRACKID {GUID}
    PERF 0
    MIDIOUT -1
    MAINSEND 1 0
    <FXCHAIN
      WNDRECT 0 0 0 0
      SHOW 0
      LASTSEL 0
      DOCKED 0
      BYPASS 0 0 0
      <VST "VST3: Superior Drummer 3 (Toontrack)" "Superior Drummer 3.vst3" 0 "" 1953718636{56535433-0000-5344-3300-000000000000}
        VSTi 1
        PRESETNAME ""
        BYPASS 0
        FXID {GUID}
        WAK 0 0
      >
      FLOATPOS 0 0 0 0
      FXID {GUID}
      WAK 0
    >
  >
>'''
        
        # Write template file
        with open(template_path, 'w') as f:
            f.write(reaper_project_content)
        
        print(f"SUCCESS Created Reaper template: {template_path}")
        return template_path
    
    def launch_reaper_with_project(self, project_path):
        """Launch Reaper with specific project"""
        if not self.reaper_exe:
            print("ERROR Reaper executable not found!")
            return False
        
        try:
            print(f"LAUNCH Launching Reaper with project: {project_path}")
            subprocess.Popen([str(self.reaper_exe), str(project_path)])
            time.sleep(5)  # Wait for Reaper to load
            return True
        except Exception as e:
            print(f"ERROR Error launching Reaper: {e}")
            return False
    
    def import_midi_to_reaper(self, midi_file):
        """Import MIDI file into Reaper track"""
        print(f"\n Importing MIDI: {midi_file.name}")
        
        try:
            # Use Ctrl+Alt+I to import media
            print("Opening import dialog...")
            pyautogui.hotkey('ctrl', 'alt', 'i')
            time.sleep(2)
            
            # Type file path
            print(f"Typing file path: {midi_file}")
            pyautogui.write(str(midi_file))
            time.sleep(1)
            
            # Import file
            print("Importing file...")
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
            # Select all items
            print("Selecting all items...")
            pyautogui.hotkey('ctrl', 'a')
            time.sleep(1)
            
            # Move to start
            print("Moving to project start...")
            pyautogui.press('home')
            time.sleep(1)
            
            # Move to beat 1.3 (assuming 4/4 time, move 3 beats)
            # This may need adjustment based on Reaper's grid settings
            print("Moving to beat 1.3...")
            for i in range(3):
                pyautogui.press('right')
                time.sleep(0.5)
            
            print("SUCCESS MIDI positioning completed")
            return True
            
        except Exception as e:
            print(f"ERROR Error positioning MIDI: {e}")
            return False
    
    def render_audio_output(self, output_filename):
        """Render audio output from Reaper"""
        print(f"\nAUDIO Rendering audio: {output_filename}")
        
        try:
            # Open render dialog
            print("Opening render dialog...")
            pyautogui.hotkey('ctrl', 'alt', 'r')
            time.sleep(3)
            
            # Set output filename
            print(f"Setting output filename: {output_filename}")
            # Navigate to filename field and set it
            pyautogui.press('tab', presses=5)  # Navigate to filename field
            pyautogui.hotkey('ctrl', 'a')  # Select all
            pyautogui.write(output_filename)
            time.sleep(1)
            
            # Set output directory
            output_path = str(self.output_dir)
            print(f"Setting output directory: {output_path}")
            # This may require specific navigation in Reaper's render dialog
            
            # Start render
            print("Starting render...")
            pyautogui.press('enter')  # Or click Render button
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
    
    def clear_reaper_project(self):
        """Clear current project for next MIDI file"""
        print(f"\n Clearing project for next file...")
        
        try:
            # Select all
            pyautogui.hotkey('ctrl', 'a')
            time.sleep(1)
            
            # Delete selected items
            pyautogui.press('delete')
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
    
    def process_single_midi_reaper(self, midi_file):
        """Process single MIDI file through Reaper workflow"""
        print(f"\n{'='*70}")
        print(f"REAPER PROCESSING: {midi_file.name}")
        print(f"{'='*70}")
        
        instrument_name = self.extract_instrument_name(midi_file.name)
        output_file = self.output_dir / f"{instrument_name}.wav"
        
        # Check if already processed
        if output_file.exists():
            print(f"SUCCESS Already processed: {output_file.name}")
            return True
        
        print(f"Instrument: {instrument_name}")
        print(f"Output file: {output_file}")
        
        # Workflow steps
        steps = [
            ("Import MIDI", lambda: self.import_midi_to_reaper(midi_file)),
            ("Position at beat 1.3", self.position_midi_at_beat_1_3),
            ("Render audio", lambda: self.render_audio_output(instrument_name)),
        ]
        
        for step_name, step_func in steps:
            print(f"\n--- {step_name} ---")
            if not step_func():
                print(f"ERROR Failed at step: {step_name}")
                return False
            time.sleep(2)
        
        # Wait for render completion
        rendered_file = self.wait_for_render_completion(output_file)
        if not rendered_file:
            print("ERROR Render failed or timed out")
            return False
        
        # Clear project for next file
        self.clear_reaper_project()
        
        print(f"COMPLETE SUCCESS: {midi_file.name} → {rendered_file.name}")
        return True
    
    def setup_reaper_environment(self):
        """Setup Reaper environment for automation"""
        print(f"\nAUDIO SETTING UP REAPER ENVIRONMENT")
        print(f"=" * 50)
        
        # Create project template
        template_path = self.create_reaper_project_template()
        
        # Launch Reaper
        if not self.launch_reaper_with_project(template_path):
            return False
        
        print(f"\n MANUAL SETUP REQUIRED:")
        print(f"1. Verify Superior Drummer 3 plugin is loaded on track")
        print(f"2. Configure SD3 with desired drum kit")
        print(f"3. Set Reaper project settings:")
        print(f"   - Sample rate: 44.1 kHz")
        print(f"   - Bit depth: 24-bit")
        print(f"   - Render format: WAV")
        print(f"4. Position Reaper window for automation visibility")
        
        input(f"\nPress ENTER when Reaper is setup and ready...")
        return True

def main():
    """Main Reaper automation workflow"""
    print("AUDIO REAPER + SD3 AUTOMATION")
    print("=" * 70)
    print("Uses Reaper DAW with SD3 plugin for reliable automation")
    print("This should bypass all SD3 standalone automation issues")
    print("=" * 70)
    
    automation = ReaperSD3Automation()
    
    # Check prerequisites
    if not automation.reaper_exe:
        print("ERROR Reaper not found! Please install Reaper or update the path.")
        return
    
    midi_files = list(automation.midi_dir.glob("*.mid"))
    if not midi_files:
        print("ERROR No MIDI files found!")
        return
    
    print(f"\nANALYSIS FOUND {len(midi_files)} MIDI FILES TO PROCESS")
    
    # Setup Reaper environment
    if not automation.setup_reaper_environment():
        print("ERROR Failed to setup Reaper environment")
        return
    
    # Process first file as test
    test_file = midi_files[0]
    print(f"\n TESTING WITH: {test_file.name}")
    
    success = automation.process_single_midi_reaper(test_file)
    
    if success:
        print(f"\nCOMPLETE REAPER AUTOMATION TEST SUCCESSFUL!")
        print(f"Ready to process all {len(midi_files)} files!")
        
        # Ask if user wants to continue with batch processing
        response = input(f"\nProcess all remaining files? (y/n): ").lower()
        if response.startswith('y'):
            print(f"\n STARTING BATCH PROCESSING...")
            
            success_count = 1  # Already processed test file
            for midi_file in midi_files[1:]:  # Skip first file (already processed)
                print(f"\nFOLDER Processing {success_count + 1}/{len(midi_files)}: {midi_file.name}")
                
                if automation.process_single_midi_reaper(midi_file):
                    success_count += 1
                    print(f"SUCCESS Progress: {success_count}/{len(midi_files)}")
                else:
                    print(f"ERROR Failed: {midi_file.name}")
                    
                    # Ask if user wants to continue after failure
                    response = input(f"Continue with remaining files? (y/n): ").lower()
                    if not response.startswith('y'):
                        break
            
            print(f"\nCOMPLETE BATCH PROCESSING COMPLETE!")
            print(f"Successfully processed: {success_count}/{len(midi_files)} files")
    else:
        print(f"\nERROR REAPER AUTOMATION TEST FAILED!")
        print(f"Check Reaper setup and try again.")

if __name__ == "__main__":
    main()

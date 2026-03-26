#!/usr/bin/env python3
"""
Jamstix/Reaper Training System - Activation Script
===================================================
Simple Python script to check and activate the Jamstix training system
"""

import os
import sys
import subprocess
from pathlib import Path

def print_header(text):
    """Print formatted header"""
    print("\n" + "="*70)
    print(f"  {text}")
    print("="*70 + "\n")

def print_status(step, status, message):
    """Print step status"""
    icon = "✅" if status else "⚠️ "
    print(f"[{step}] {icon} {message}")

def check_reaper():
    """Check if REAPER is installed"""
    print_status("1/5", True, "Checking for REAPER...")
    
    reaper_paths = [
        Path("C:/Program Files/REAPER/reaper.exe"),
        Path("C:/Program Files (x86)/REAPER/reaper.exe"),
        Path("C:/Program Files/REAPER (x64)/reaper.exe"),
    ]
    
    for path in reaper_paths:
        if path.exists():
            print(f"      Found: {path}")
            return True
    
    print("      Not found in standard locations")
    print("      Install from: https://www.reaper.fm/download.php")
    return False

def check_directories():
    """Check and create required directories"""
    print_status("2/5", True, "Checking directories...")
    
    template_dir = Path("C:/Users/dagol/ReaperTemplates")
    output_dir = Path("F:/DrumTrackAI_Jamstix_Dataset")
    
    # Create template directory
    if not template_dir.exists():
        template_dir.mkdir(parents=True, exist_ok=True)
        print(f"      Created: {template_dir}")
    else:
        print(f"      Exists: {template_dir}")
    
    # Create output directory
    if not output_dir.exists():
        output_dir.mkdir(parents=True, exist_ok=True)
        print(f"      Created: {output_dir}")
    else:
        print(f"      Exists: {output_dir}")
    
    return True

def check_python_deps():
    """Check and install Python dependencies"""
    print_status("3/5", True, "Checking Python dependencies...")
    
    try:
        import mido
        print("      mido: Installed")
        return True
    except ImportError:
        print("      mido: Not installed, installing...")
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", "mido"])
            print("      mido: Installed successfully")
            return True
        except:
            print("      mido: Installation failed")
            return False

def check_template():
    """Check for Jamstix template"""
    print_status("4/5", True, "Checking for Jamstix template...")
    
    template_path = Path("C:/Users/dagol/ReaperTemplates/JamstixTemplate.rpp")
    
    if template_path.exists():
        print(f"      Found: {template_path}")
        return True
    else:
        print(f"      Not found: {template_path}")
        return False

def check_lua_script():
    """Check for Lua script"""
    print_status("5/5", True, "Checking for Lua script...")
    
    script_path = Path(__file__).parent / "phase1_data_generation/reaper_automation/JamstixBatchGenerator_COMPLETE.lua"
    
    if script_path.exists():
        print(f"      Found: {script_path.name}")
        return True
    else:
        print(f"      Not found: {script_path}")
        return False

def main():
    """Main activation routine"""
    print("\n" + "╔" + "="*68 + "╗")
    print("║" + " "*15 + "Jamstix/Reaper Training System" + " "*23 + "║")
    print("║" + " "*25 + "Activation Check" + " "*27 + "║")
    print("╚" + "="*68 + "╝")
    
    # Run checks
    has_reaper = check_reaper()
    has_dirs = check_directories()
    has_deps = check_python_deps()
    has_template = check_template()
    has_script = check_lua_script()
    
    print("\n" + "="*70)
    print("  SYSTEM STATUS")
    print("="*70 + "\n")
    
    all_ready = has_reaper and has_dirs and has_deps and has_template and has_script
    
    if all_ready:
        print("🎉 ✅ SYSTEM FULLY ACTIVATED!")
        print("\nReady to generate Jamstix training data!\n")
        print("Next steps:")
        print("  1. Open REAPER")
        print("  2. Actions → Load ReaScript...")
        print("  3. Select: JamstixBatchGenerator_COMPLETE.lua")
        print("  4. Run the script\n")
    else:
        print("⚠️  SETUP REQUIRED\n")
        
        if not has_reaper:
            print("❌ Install REAPER from: https://www.reaper.fm/download.php")
        
        if not has_template:
            print("❌ Create Jamstix template:")
            print("   1. Open REAPER")
            print("   2. Track 1: Add Jamstix plugin")
            print("   3. Track 2: MIDI Capture (record from Track 1)")
            print("   4. Save as: C:\\Users\\dagol\\ReaperTemplates\\JamstixTemplate.rpp")
            print("\n   See: JAMSTIX_COMPLETE_SETUP.md for details")
        
        if has_template and has_script:
            print("\n✅ Template and script ready - just install REAPER!")
    
    print("\n" + "="*70)
    print("  DIRECTORIES")
    print("="*70)
    print(f"  Template:  C:\\Users\\dagol\\ReaperTemplates\\")
    print(f"  Output:    F:\\DrumTrackAI_Jamstix_Dataset\\")
    print(f"  Script:    phase1_data_generation\\reaper_automation\\")
    print("="*70 + "\n")
    
    return 0 if all_ready else 1

if __name__ == "__main__":
    sys.exit(main())

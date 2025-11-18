#!/usr/bin/env python3
"""
Clean Restart Guide - Step-by-Step Fresh Start
==============================================

Guide for cleanly restarting the batch extraction process
with only one Reaper instance and proper timeline reset.

Author: DrumTracKAI v1.1.7
Date: July 23, 2025
"""

import subprocess
from pathlib import Path
import time

def check_reaper_processes():
    """Check if any Reaper processes are still running"""
    print("INSPECTING CHECKING FOR REAPER PROCESSES")
    print("=" * 40)
    
    try:
        result = subprocess.run(
            ['tasklist', '/FI', 'IMAGENAME eq reaper.exe'],
            capture_output=True,
            text=True
        )
        
        if "reaper.exe" in result.stdout:
            print("WARNING  Reaper processes still running:")
            print(result.stdout)
            return True
        else:
            print("SUCCESS No Reaper processes found - all clear!")
            return False
    except Exception as e:
        print(f"ERROR Error checking processes: {e}")
        return False

def print_clean_restart_steps():
    """Print step-by-step restart instructions"""
    print("\nAUDIO CLEAN RESTART STEPS")
    print("=" * 50)
    print("Follow these steps EXACTLY for proper timeline reset:")
    print()
    
    print("1⃣ REAPER SETUP:")
    print("   • Open ONLY ONE instance of Reaper")
    print("   • Load Superior Drummer 3 on track 1")
    print("   • Verify SD3 is ready to play drum sounds")
    print("   • Ensure timeline cursor is at position 0:00")
    print("   • Clear any existing items from the timeline")
    print("   • Go to View → Console to monitor ReaScript output")
    
    print("\n2⃣ TIMELINE VERIFICATION:")
    print("   • Press spacebar to play - should start at 0:00")
    print("   • Press stop - cursor should return to 0:00")
    print("   • If cursor doesn't return to 0:00, check Options → Preferences")
    print("   • Under Audio → Playback, ensure 'Stop playback returns cursor to start' is checked")
    
    print("\n3⃣ PROJECT SETTINGS:")
    print("   • Set project tempo to 120 BPM")
    print("   • Set time signature to 4/4")
    print("   • Set project sample rate to 44.1kHz")
    print("   • Save project as template for consistency")
    
    print("\n4⃣ BATCH EXTRACTION:")
    print("   • Run the batch extraction script")
    print("   • Monitor Reaper console for timeline reset messages")
    print("   • Watch for 'FORCING timeline reset to zero...' messages")
    print("   • Verify cursor returns to 0:00 between each file")

def create_single_file_test():
    """Create a single file test script to verify timeline reset"""
    print("\n CREATING SINGLE FILE TEST")
    print("=" * 40)
    
    test_script = """-- Single File Timeline Test
-- Test timeline reset with one MIDI file

function msg(text)
    reaper.ShowConsoleMsg(text .. "\\n")
end

function force_timeline_reset()
    msg("=== FORCING TIMELINE RESET ===")
    
    -- Stop everything
    reaper.Main_OnCommand(1016, 0)  -- Stop
    reaper.Main_OnCommand(1017, 0)  -- Pause
    
    -- Multiple cursor reset attempts
    reaper.SetEditCurPos(0, false, false)
    reaper.Main_OnCommand(40042, 0)  -- Go to start of project
    reaper.SetEditCurPos(0, true, true)  -- Move cursor and seek
    
    -- Clear selections
    reaper.Main_OnCommand(40020, 0)  -- Clear time selection
    reaper.GetSet_LoopTimeRange(true, false, 0, 0, false)
    
    -- Update display
    reaper.UpdateTimeline()
    reaper.UpdateArrange()
    
    -- Verify cursor position
    local cursor_pos = reaper.GetCursorPosition()
    msg("Cursor position after reset: " .. cursor_pos)
    
    if cursor_pos > 0.001 then
        msg("WARNING: Cursor not at zero! Position: " .. cursor_pos)
        return false
    else
        msg("SUCCESS: Cursor at zero")
        return true
    end
end

function main()
    msg("SINGLE FILE TIMELINE RESET TEST")
    msg("================================")
    
    -- Test timeline reset
    local success = force_timeline_reset()
    
    if success then
        msg("SUCCESS Timeline reset test PASSED")
    else
        msg("ERROR Timeline reset test FAILED")
    end
    
    msg("Test complete - check cursor position in Reaper")
end

main()"""
    
    test_file = Path(__file__).parent / "test_timeline_reset.lua"
    with open(test_file, 'w') as f:
        f.write(test_script)
    
    print(f"SUCCESS Created timeline test script: {test_file}")
    print(f"   Run this first to verify timeline reset works")

def main():
    """Main clean restart guide"""
    print("AUDIO CLEAN RESTART GUIDE FOR SUPERIOR DRUMMER EXTRACTION")
    print("=" * 70)
    print("Ensuring proper timeline reset and single Reaper instance")
    print("=" * 70)
    
    # Check for remaining Reaper processes
    if check_reaper_processes():
        print("\nWARNING  Please close all Reaper instances manually and run this script again")
        return
    
    # Print restart steps
    print_clean_restart_steps()
    
    # Create test script
    create_single_file_test()
    
    print(f"\nTARGET NEXT STEPS:")
    print(f"1. Follow the restart steps above")
    print(f"2. Run 'python test_timeline_reset.py' to test timeline reset")
    print(f"3. If test passes, run the batch extraction")
    print(f"4. Monitor Reaper console for timeline reset confirmations")
    
    print(f"\nSUCCESS All Reaper processes stopped - ready for clean restart!")

if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Test Timeline Reset - Verify Timeline Behavior
==============================================

Simple test to verify that timeline cursor resets properly
before running the full batch extraction.

Author: DrumTracKAI v1.1.7
Date: July 23, 2025
"""

import subprocess
from pathlib import Path

def create_timeline_test_script():
    """Create a simple ReaScript to test timeline reset"""
    test_script = '''-- Timeline Reset Test Script
-- Simple test to verify cursor returns to zero

function msg(text)
    reaper.ShowConsoleMsg(text .. "\\n")
end

function test_timeline_reset()
    msg("=== TIMELINE RESET TEST ===")
    
    -- Get initial cursor position
    local initial_pos = reaper.GetCursorPosition()
    msg("Initial cursor position: " .. initial_pos)
    
    -- Move cursor to a different position (2 seconds)
    reaper.SetEditCurPos(2.0, false, false)
    local moved_pos = reaper.GetCursorPosition()
    msg("Moved cursor to: " .. moved_pos)
    
    -- Now test our reset methods
    msg("Testing timeline reset methods...")
    
    -- Method 1: Stop command
    reaper.Main_OnCommand(1016, 0)  -- Stop
    
    -- Method 2: Go to start
    reaper.Main_OnCommand(40042, 0)  -- Go to start of project
    
    -- Method 3: Set cursor directly
    reaper.SetEditCurPos(0, false, false)
    
    -- Method 4: Update display
    reaper.UpdateTimeline()
    
    -- Check final position
    local final_pos = reaper.GetCursorPosition()
    msg("Final cursor position: " .. final_pos)
    
    if final_pos < 0.001 then
        msg("SUCCESS SUCCESS: Timeline reset working correctly!")
        msg("Cursor is at zero (" .. final_pos .. ")")
        return true
    else
        msg("ERROR FAILED: Timeline reset not working!")
        msg("Cursor is at " .. final_pos .. " (should be 0)")
        return false
    end
end

function main()
    msg("SUPERIOR DRUMMER TIMELINE RESET TEST")
    msg("====================================")
    msg("Testing if timeline cursor resets properly...")
    msg("")
    
    local success = test_timeline_reset()
    
    msg("")
    if success then
        msg("COMPLETE TIMELINE TEST PASSED!")
        msg("Ready for batch extraction")
    else
        msg("WARNING  TIMELINE TEST FAILED!")
        msg("Check Reaper playback settings:")
        msg("Options → Preferences → Audio → Playback")
        msg("Enable: 'Stop playback returns cursor to start'")
    end
    
    msg("")
    msg("Test complete - check Reaper timeline cursor position")
end

main()'''
    
    return test_script

def run_timeline_test():
    """Run the timeline reset test"""
    print(" TIMELINE RESET TEST")
    print("=" * 40)
    
    # Create test script
    test_script_content = create_timeline_test_script()
    test_script_path = Path(__file__).parent / "timeline_test.lua"
    
    with open(test_script_path, 'w') as f:
        f.write(test_script_content)
    
    print(f"SUCCESS Created test script: {test_script_path}")
    
    # Check if Reaper is ready
    print(f"\n REQUIREMENTS:")
    print(f"• Reaper is open with SD3 loaded on track 1")
    print(f"• Timeline cursor can be seen in Reaper")
    print(f"• Reaper console is open (View → Console)")
    
    response = input(f"\nIs Reaper ready for timeline test? (y/n): ").lower()
    if not response.startswith('y'):
        print("Please set up Reaper first, then run this test")
        return False
    
    # Execute test
    reaper_exe = "C:\\Program Files\\REAPER (x64)\\reaper.exe"
    
    try:
        cmd = [reaper_exe, "-nonewinst", str(test_script_path)]
        print(f"\nLAUNCH Running timeline test...")
        print(f"Command: {' '.join(cmd)}")
        print(f"Watch Reaper console for test results")
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30
        )
        
        print(f"\nANALYSIS TEST RESULTS:")
        print(f"Return code: {result.returncode}")
        
        if result.stdout:
            print(f"Output: {result.stdout}")
        
        if result.stderr:
            print(f"Errors: {result.stderr}")
        
        print(f"\nINSPECTING CHECK REAPER:")
        print(f"• Look at Reaper console for detailed test results")
        print(f"• Verify timeline cursor is at position 0:00")
        print(f"• If test passed, timeline reset is working correctly")
        
        return result.returncode == 0
        
    except Exception as e:
        print(f"ERROR Error running test: {e}")
        return False

def main():
    """Main timeline test execution"""
    print("AUDIO SUPERIOR DRUMMER TIMELINE RESET TEST")
    print("=" * 60)
    print("Verify timeline cursor resets before batch extraction")
    print("=" * 60)
    
    success = run_timeline_test()
    
    if success:
        print(f"\nSUCCESS Timeline test completed successfully!")
        print(f"If Reaper console shows 'SUCCESS', timeline reset is working")
        print(f"Ready to proceed with batch extraction")
    else:
        print(f"\nWARNING  Timeline test had issues")
        print(f"Check Reaper console for detailed results")

if __name__ == "__main__":
    main()

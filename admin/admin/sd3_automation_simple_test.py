#!/usr/bin/env python3
"""
Simple SD3 Automation Test
==========================

A simple test to verify SD3 window detection and basic automation setup
without interactive input requirements.

Author: DrumTracKAI v1.1.7
Date: July 23, 2025
"""

import os
import sys
import time
from pathlib import Path

# GUI automation imports
try:
    import pyautogui
    import pygetwindow as gw
    print("SUCCESS GUI automation libraries imported successfully")
    
    # Configure pyautogui
    pyautogui.FAILSAFE = True
    pyautogui.PAUSE = 1.0
    
except ImportError as e:
    print(f"ERROR ERROR: GUI automation libraries not available: {e}")
    sys.exit(1)

def test_sd3_detection():
    """Test SD3 window detection"""
    print("\nINSPECTING Testing SD3 Window Detection...")
    print("=" * 50)
    
    sd3_window_titles = ["Superior Drummer 3", "Superior Drummer", "SD3"]
    
    # Try to find SD3 window
    sd3_window = None
    for title in sd3_window_titles:
        windows = gw.getWindowsWithTitle(title)
        if windows:
            sd3_window = windows[0]
            print(f"SUCCESS Found SD3 window: '{sd3_window.title}'")
            print(f"   Position: ({sd3_window.left}, {sd3_window.top})")
            print(f"   Size: {sd3_window.width}x{sd3_window.height}")
            print(f"   Visible: {sd3_window.visible}")
            print(f"   Active: {sd3_window.isActive}")
            break
    
    if not sd3_window:
        print("ERROR SD3 window not found!")
        print("\nAvailable windows:")
        all_windows = gw.getAllWindows()
        for i, window in enumerate(all_windows[:15]):  # Show first 15 windows
            if window.title.strip():  # Only show windows with titles
                print(f"   {i+1:2d}. '{window.title}' ({window.width}x{window.height})")
        return False
    
    return sd3_window

def test_midi_files():
    """Test MIDI files detection"""
    print("\nFOLDER Testing MIDI Files Detection...")
    print("=" * 50)
    
    base_path = Path(__file__).parent
    midi_dir = base_path / "sd3_midi_patterns"
    
    if not midi_dir.exists():
        print(f"ERROR MIDI directory not found: {midi_dir}")
        return False
    
    midi_files = list(midi_dir.glob("*.mid"))
    print(f"SUCCESS Found {len(midi_files)} MIDI files")
    
    if midi_files:
        print("First 5 MIDI files:")
        for i, midi_file in enumerate(midi_files[:5], 1):
            print(f"   {i}. {midi_file.name}")
    
    return len(midi_files) > 0

def test_output_directory():
    """Test output directory setup"""
    print("\nDIRECTORY Testing Output Directory...")
    print("=" * 50)
    
    base_path = Path(__file__).parent
    output_dir = base_path / "sd3_extracted_samples"
    
    if not output_dir.exists():
        print(f"Creating output directory: {output_dir}")
        output_dir.mkdir(exist_ok=True)
    
    print(f"SUCCESS Output directory ready: {output_dir}")
    return True

def test_basic_automation():
    """Test basic automation capabilities"""
    print("\n Testing Basic Automation...")
    print("=" * 50)
    
    try:
        # Get current mouse position
        x, y = pyautogui.position()
        print(f"SUCCESS Current mouse position: ({x}, {y})")
        
        # Test screen size
        screen_width, screen_height = pyautogui.size()
        print(f"SUCCESS Screen size: {screen_width}x{screen_height}")
        
        # Test failsafe
        print(f"SUCCESS Failsafe enabled: {pyautogui.FAILSAFE}")
        print(f"SUCCESS Pause setting: {pyautogui.PAUSE}")
        
        return True
        
    except Exception as e:
        print(f"ERROR Basic automation test failed: {e}")
        return False

def main():
    """Main test function"""
    print("AUDIO SD3 AUTOMATION SIMPLE TEST")
    print("=" * 60)
    print("This will test basic automation setup without user interaction.")
    print("=" * 60)
    
    tests = [
        ("SD3 Window Detection", test_sd3_detection),
        ("MIDI Files Detection", test_midi_files),
        ("Output Directory Setup", test_output_directory),
        ("Basic Automation", test_basic_automation)
    ]
    
    results = {}
    
    for test_name, test_func in tests:
        print(f"\n{'='*60}")
        print(f"RUNNING TEST: {test_name}")
        print(f"{'='*60}")
        
        try:
            result = test_func()
            results[test_name] = result
            print(f"SUCCESS {test_name}: {'PASSED' if result else 'FAILED'}")
        except Exception as e:
            results[test_name] = False
            print(f"ERROR {test_name}: FAILED with error: {e}")
    
    # Summary
    print(f"\n{'='*60}")
    print("TEST RESULTS SUMMARY")
    print(f"{'='*60}")
    
    passed = sum(1 for result in results.values() if result)
    total = len(results)
    
    for test_name, result in results.items():
        status = "SUCCESS PASSED" if result else "ERROR FAILED"
        print(f"{test_name:25s}: {status}")
    
    print(f"\nOverall: {passed}/{total} tests passed")
    
    if passed == total:
        print("\nCOMPLETE All tests passed! SD3 automation setup is ready.")
        print("The issue with the interactive script may be input handling.")
    else:
        print(f"\nWARNING  {total - passed} test(s) failed. Please resolve issues before proceeding.")
    
    return passed == total

if __name__ == "__main__":
    main()

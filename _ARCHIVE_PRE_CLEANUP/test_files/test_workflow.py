#!/usr/bin/env python3
"""
DrumTracKAI v1.1.16 Complete Workflow Test
Tests all advanced features including groove presets, fill library, and benchmarking.
"""

import os
import sys
import time
import json
import requests
from pathlib import Path

# Configuration
API_BASE = "http://localhost:8000"
TEST_AUDIO = "uploads/test.wav"  # Replace with actual uploaded file
BPM = 120
BARS = 8

def test_endpoint(name, url, expected_keys=None):
    """Test an API endpoint and validate response"""
    print(f"Testing {name}...")
    try:
        response = requests.get(url, timeout=30)
        if response.status_code == 200:
            data = response.json()
            if expected_keys:
                missing = [k for k in expected_keys if k not in data]
                if missing:
                    print(f"  ❌ Missing keys: {missing}")
                    return False
            print(f"  ✅ Success")
            return True
        else:
            print(f"  ❌ HTTP {response.status_code}: {response.text}")
            return False
    except Exception as e:
        print(f"  ❌ Error: {e}")
        return False

def test_generate_with_presets():
    """Test drum generation with all groove presets and fill types"""
    print("\nTesting Groove Presets & Fill Library...")
    
    swing_presets = ["off", "light", "heavy"]
    vel_presets = ["flat", "accent24", "funk16"]
    fill_presets = ["none", "random", "tomrun", "snarebuzz", "edmriser"]
    styles = ["rock", "funk", "edm", "hiphop", "jazz", "pop"]
    
    success_count = 0
    total_tests = 0
    
    for style in styles:
        for swing in swing_presets:
            for vel in vel_presets[:2]:  # Test subset to avoid too many requests
                for fill in fill_presets[:3]:
                    total_tests += 1
                    url = f"{API_BASE}/dcsm/generate"
                    payload = {
                        "start": 0.0,
                        "end": BARS * (60.0/BPM) * 4.0,
                        "density": 0.7,
                        "swing": 0.1,
                        "humanize": 0.15,
                        "style": style,
                        "label": "verse",
                        "swing_preset": swing,
                        "vel_preset": vel,
                        "fill_preset": fill
                    }
                    
                    try:
                        response = requests.post(f"{url}?bpm={BPM}", json=payload, timeout=15)
                        if response.status_code == 200:
                            data = response.json()
                            if "notes" in data and "midi" in data:
                                success_count += 1
                                print(f"  ✅ {style}/{swing}/{vel}/{fill}")
                            else:
                                print(f"  ❌ {style}/{swing}/{vel}/{fill} - Missing data")
                        else:
                            print(f"  ❌ {style}/{swing}/{vel}/{fill} - HTTP {response.status_code}")
                    except Exception as e:
                        print(f"  ❌ {style}/{swing}/{vel}/{fill} - {e}")
    
    print(f"\nGeneration Tests: {success_count}/{total_tests} passed")
    return success_count == total_tests

def test_benchmarks():
    """Test benchmarking suite"""
    print("\nTesting Benchmarking Suite...")
    
    endpoints = [
        ("Peaks", f"{API_BASE}/bench/peaks?key={TEST_AUDIO}&impl=both"),
        ("Analysis", f"{API_BASE}/bench/analysis?key={TEST_AUDIO}&impl=both"),
        ("Generate", f"{API_BASE}/bench/generate?bpm={BPM}&bars={BARS}&style=rock")
    ]
    
    all_passed = True
    for name, url in endpoints:
        success = test_endpoint(f"Benchmark {name}", url)
        if not success:
            all_passed = False
    
    return all_passed

def test_smart_sectionization():
    """Test smart sectionization with repetition labeling"""
    print("\nTesting Smart Sectionization...")
    
    url = f"{API_BASE}/dcsm/sectionize"
    params = {
        "key": TEST_AUDIO,
        "bpm": BPM,
        "mode": "smart",
        "min_bars": 4,
        "max_bars": 16
    }
    
    try:
        response = requests.get(url, params=params, timeout=30)
        if response.status_code == 200:
            data = response.json()
            if "sections" in data:
                sections = data["sections"]
                print(f"  ✅ Found {len(sections)} sections")
                
                # Check for section labels
                labels = [s.get("label", "unknown") for s in sections]
                unique_labels = set(labels)
                print(f"  ✅ Section labels: {', '.join(unique_labels)}")
                
                return True
            else:
                print("  ❌ No sections in response")
                return False
        else:
            print(f"  ❌ HTTP {response.status_code}")
            return False
    except Exception as e:
        print(f"  ❌ Error: {e}")
        return False

def test_midi_export():
    """Test Type-1 multi-track MIDI export"""
    print("\nTesting MIDI Type-1 Export...")
    
    # Generate some notes first
    url = f"{API_BASE}/dcsm/generate"
    payload = {
        "start": 0.0,
        "end": 4.0,  # 1 bar at 120 BPM
        "density": 0.8,
        "swing": 0.0,
        "humanize": 0.1,
        "style": "rock",
        "label": "verse",
        "swing_preset": "off",
        "vel_preset": "flat",
        "fill_preset": "none"
    }
    
    try:
        response = requests.post(f"{url}?bpm={BPM}", json=payload, timeout=15)
        if response.status_code == 200:
            data = response.json()
            if "midi" in data:
                midi_b64 = data["midi"]
                print(f"  ✅ MIDI export successful ({len(midi_b64)} chars)")
                
                # Decode and check for Type-1 header
                import base64
                midi_bytes = base64.b64decode(midi_b64)
                
                # Check MIDI header for Type-1 format
                if len(midi_bytes) >= 10:
                    header = midi_bytes[:10]
                    if header[:4] == b'MThd' and header[8:10] == b'\x00\x01':
                        print("  ✅ Confirmed Type-1 MIDI format")
                        return True
                    else:
                        print("  ❌ Not Type-1 MIDI format")
                        return False
                else:
                    print("  ❌ MIDI data too short")
                    return False
            else:
                print("  ❌ No MIDI in response")
                return False
        else:
            print(f"  ❌ HTTP {response.status_code}")
            return False
    except Exception as e:
        print(f"  ❌ Error: {e}")
        return False

def main():
    """Run complete v1.1.16 workflow test"""
    print("🥁 DrumTracKAI v1.1.16 Complete Workflow Test")
    print("=" * 50)
    
    # Check if server is running
    try:
        response = requests.get(f"{API_BASE}/healthz", timeout=5)
        if response.status_code != 200:
            print("❌ Server not responding. Please start the backend first.")
            return False
    except:
        print("❌ Cannot connect to server. Please start the backend first.")
        return False
    
    print("✅ Server is running")
    
    # Run all tests
    tests = [
        ("Smart Sectionization", test_smart_sectionization),
        ("Groove Presets & Fill Library", test_generate_with_presets),
        ("MIDI Type-1 Export", test_midi_export),
        ("Benchmarking Suite", test_benchmarks),
    ]
    
    results = []
    for test_name, test_func in tests:
        print(f"\n{'='*20} {test_name} {'='*20}")
        try:
            success = test_func()
            results.append((test_name, success))
        except Exception as e:
            print(f"❌ Test failed with exception: {e}")
            results.append((test_name, False))
    
    # Summary
    print(f"\n{'='*50}")
    print("📊 Test Results Summary:")
    print("=" * 50)
    
    passed = 0
    for test_name, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} {test_name}")
        if success:
            passed += 1
    
    print(f"\nOverall: {passed}/{len(results)} tests passed")
    
    if passed == len(results):
        print("\n🎉 All v1.1.16 features working correctly!")
        return True
    else:
        print(f"\n⚠️  {len(results) - passed} tests failed. Check logs above.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

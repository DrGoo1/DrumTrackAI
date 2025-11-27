#!/usr/bin/env python3
"""
Test Jamstix Brain Backend Integration
=======================================
Tests the Jamstix brain API endpoints
"""

import requests
import json
import time

BASE_URL = "http://localhost:8000"

def test_jamstix_status():
    """Test Jamstix status endpoint"""
    print("\n" + "="*70)
    print("TEST 1: Jamstix Brain Status")
    print("="*70)
    
    response = requests.get(f"{BASE_URL}/api/jamstix/status")
    data = response.json()
    
    print(f"Status Code: {response.status_code}")
    print(f"Available: {data.get('available')}")
    print(f"Version: {data.get('version')}")
    print(f"Features: {', '.join(data.get('features', []))}")
    
    return data.get('available')

def test_jamstix_enrich():
    """Test pattern enrichment endpoint"""
    print("\n" + "="*70)
    print("TEST 2: Pattern Enrichment")
    print("="*70)
    
    # Sample pattern events
    events = [
        {"time_sec": 0.0, "instrument_id": "kick", "velocity": 100, "barIndex": 0, "barStartTime": 0.0, "barEndTime": 2.0},
        {"time_sec": 0.5, "instrument_id": "hihat_closed", "velocity": 70, "barIndex": 0, "barStartTime": 0.0, "barEndTime": 2.0},
        {"time_sec": 1.0, "instrument_id": "snare_center", "velocity": 90, "barIndex": 0, "barStartTime": 0.0, "barEndTime": 2.0},
        {"time_sec": 1.5, "instrument_id": "hihat_closed", "velocity": 65, "barIndex": 0, "barStartTime": 0.0, "barEndTime": 2.0},
    ]
    
    payload = {
        "events": events,
        "feel": "laid_back",
        "hatOpenness": 0.3,
        "fillBars": []
    }
    
    response = requests.post(
        f"{BASE_URL}/api/jamstix/enrich",
        json=payload,
        headers={"Content-Type": "application/json"}
    )
    
    data = response.json()
    
    print(f"Status Code: {response.status_code}")
    print(f"Success: {data.get('success')}")
    print(f"Events Enriched: {data.get('total_events')}")
    print(f"Conflicts Resolved: {data.get('conflicts_resolved')}")
    
    if data.get('success') and data.get('events'):
        print("\nFirst Event Attributes:")
        first_event = data['events'][0]
        attrs = first_event.get('jamstix_attrs', {})
        print(f"  Limb: {attrs.get('limbId')}")
        print(f"  Priority: {attrs.get('priority')}")
        print(f"  Timing Offset: {attrs.get('timingOffsetMs')}ms")
        print(f"  Aspect: {attrs.get('aspect')}")
        print(f"  Hit Style: {attrs.get('hitStyle')}")
    
    return data.get('success')

def test_jamstix_build_track():
    """Test DCSM track building endpoint"""
    print("\n" + "="*70)
    print("TEST 3: DCSM Track Building")
    print("="*70)
    
    # Sample pattern events
    events = [
        {"time_sec": 0.0, "instrument_id": "kick", "velocity": 100, "barIndex": 0, "barStartTime": 0.0, "barEndTime": 2.0},
        {"time_sec": 0.5, "instrument_id": "hihat_closed", "velocity": 70, "barIndex": 0, "barStartTime": 0.0, "barEndTime": 2.0},
        {"time_sec": 1.0, "instrument_id": "snare_center", "velocity": 90, "barIndex": 0, "barStartTime": 0.0, "barEndTime": 2.0},
        {"time_sec": 1.5, "instrument_id": "hihat_closed", "velocity": 65, "barIndex": 0, "barStartTime": 0.0, "barEndTime": 2.0},
        {"time_sec": 2.0, "instrument_id": "kick", "velocity": 100, "barIndex": 1, "barStartTime": 2.0, "barEndTime": 4.0},
        {"time_sec": 2.5, "instrument_id": "hihat_closed", "velocity": 70, "barIndex": 1, "barStartTime": 2.0, "barEndTime": 4.0},
        {"time_sec": 3.0, "instrument_id": "snare_center", "velocity": 90, "barIndex": 1, "barStartTime": 2.0, "barEndTime": 4.0},
    ]
    
    sections = [
        {"type": "verse", "startBar": 0, "endBar": 2}
    ]
    
    payload = {
        "events": events,
        "sections": sections,
        "tempo": 120.0,
        "timeSignature": "4/4",
        "performanceSpec": {
            "feel": "laid_back",
            "swing": 0.0,
            "intensity": 0.8,
            "hatOpenness": 0.3,
            "fillStyle": "tom_run"
        }
    }
    
    response = requests.post(
        f"{BASE_URL}/api/jamstix/build-track",
        json=payload,
        headers={"Content-Type": "application/json"}
    )
    
    data = response.json()
    
    print(f"Status Code: {response.status_code}")
    print(f"Success: {data.get('success')}")
    print(f"Bars: {data.get('bars')}")
    print(f"Total Notes: {data.get('total_notes')}")
    
    if data.get('success') and data.get('track'):
        track = data['track']
        print(f"\nTrack Info:")
        print(f"  Tempo: {track.get('tempo')} BPM")
        print(f"  Time Signature: {track.get('timeSignature')}")
        print(f"  Bars: {len(track.get('bars', []))}")
        print(f"  Sections: {len(track.get('sections', []))}")
    
    return data.get('success')

def main():
    """Run all tests"""
    print("\n" + "╔" + "="*68 + "╗")
    print("║" + " "*15 + "Jamstix Backend Integration Test" + " "*21 + "║")
    print("╚" + "="*68 + "╝")
    
    print(f"\nTesting against: {BASE_URL}")
    print("Make sure backend is running: python dcsm_backend.py")
    print()
    
    try:
        # Test 1: Status
        available = test_jamstix_status()
        
        if not available:
            print("\n⚠️  Jamstix brain not available in backend")
            print("   This is normal if backend.jamstix_brain import failed")
            print("   Check backend logs for import errors")
            return
        
        # Test 2: Enrich
        enrich_ok = test_jamstix_enrich()
        
        # Test 3: Build Track
        build_ok = test_jamstix_build_track()
        
        # Summary
        print("\n" + "="*70)
        print("TEST SUMMARY")
        print("="*70)
        print(f"Status Check:      {'✅ PASS' if available else '❌ FAIL'}")
        print(f"Pattern Enrich:    {'✅ PASS' if enrich_ok else '❌ FAIL'}")
        print(f"Track Building:    {'✅ PASS' if build_ok else '❌ FAIL'}")
        print("="*70)
        
        if available and enrich_ok and build_ok:
            print("\n🎉 ✅ All tests PASSED!")
            print("   Jamstix brain is fully integrated into your backend!")
        
    except requests.exceptions.ConnectionError:
        print("\n❌ ERROR: Could not connect to backend")
        print(f"   Make sure backend is running on {BASE_URL}")
        print("   Start with: python dcsm_backend.py")
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()

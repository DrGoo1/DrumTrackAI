"""
Test Per-Section Tempo Detection
Tests the complete workflow of per-section tempo analysis
"""
import requests
import json
import os
from pathlib import Path

BASE_URL = "http://localhost:8000"
UPLOADS_DIR = Path("uploads")

def test_per_section_tempo():
    print("🧪 Testing Per-Section Tempo Detection\n")
    
    # Find uploaded audio files
    audio_files = []
    if UPLOADS_DIR.exists():
        audio_files = list(UPLOADS_DIR.glob("*.mp3")) + list(UPLOADS_DIR.glob("*.wav"))
    
    if not audio_files:
        print("❌ No audio files found in uploads/ directory")
        print("   Please upload an audio file through the web interface first")
        return False
    
    print(f"✅ Found {len(audio_files)} audio file(s)")
    test_file = audio_files[0]
    file_key = test_file.name
    print(f"   Testing with: {file_key}\n")
    
    # Step 1: Analyze global tempo
    print("📊 Step 1: Analyzing global tempo...")
    try:
        response = requests.get(f"{BASE_URL}/analyze/tempo", params={"key": file_key}, timeout=30)
        response.raise_for_status()
        tempo_result = response.json()
        global_tempo = tempo_result.get("tempo", 120)
        beats = tempo_result.get("beats", [])
        print(f"   ✅ Global tempo: {global_tempo:.1f} BPM")
        print(f"   ✅ Detected {len(beats)} beats\n")
    except Exception as e:
        print(f"   ❌ Failed: {e}\n")
        return False
    
    # Step 2: Smart sectionization
    print("🎵 Step 2: Creating smart sections...")
    try:
        response = requests.get(
            f"{BASE_URL}/dcsm/sectionize",
            params={"key": file_key, "bpm": global_tempo, "min_bars": 4, "max_bars": 16},
            timeout=30
        )
        response.raise_for_status()
        section_result = response.json()
        sections = section_result.get("sections", [])
        print(f"   ✅ Created {len(sections)} sections")
        for i, s in enumerate(sections):
            duration = s['end'] - s['start']
            bars = int(duration / (60.0 / global_tempo * 4))
            print(f"      {i+1}. {s.get('label', 'Section').upper()}: {s['start']:.2f}s - {s['end']:.2f}s ({bars} bars)")
        print()
    except Exception as e:
        print(f"   ❌ Failed: {e}\n")
        return False
    
    if not sections:
        print("❌ No sections created\n")
        return False
    
    # Step 3: Analyze tempo for each section
    print("🎯 Step 3: Analyzing tempo per section...")
    try:
        payload = {
            "key": file_key,
            "sections": [{"start": s["start"], "end": s["end"]} for s in sections]
        }
        response = requests.post(
            f"{BASE_URL}/analyze/tempo_sections",
            json=payload,
            timeout=60
        )
        response.raise_for_status()
        tempo_sections = response.json()
        results = tempo_sections.get("results", [])
        global_avg = tempo_sections.get("global_tempo", global_tempo)
        
        print(f"   ✅ Analyzed {len(results)} sections")
        print(f"   ✅ Global average: {global_avg:.1f} BPM\n")
        
        print("📊 Results:")
        print("   ┌─────────┬──────────┬──────────┬────────────────────┬────────────┐")
        print("   │ Section │ Start    │ End      │ Tempo              │ Confidence │")
        print("   ├─────────┼──────────┼──────────┼────────────────────┼────────────┤")
        
        for i, result in enumerate(results):
            section = sections[i]
            label = section.get('label', 'Section')
            start = result['start']
            end = result['end']
            tempo = result['tempo']
            confidence = result['confidence']
            
            # Confidence indicator
            if confidence > 0.85:
                indicator = "🟢"
            elif confidence > 0.6:
                indicator = "🟡"
            else:
                indicator = "🔴"
            
            print(f"   │ {label:7s} │ {start:5.1f}s   │ {end:5.1f}s  │ {tempo:6.1f} BPM {indicator}   │ {confidence*100:3.0f}%       │")
        
        print("   └─────────┴──────────┴──────────┴────────────────────┴────────────┘\n")
        
        # Analysis summary
        tempos = [r['tempo'] for r in results]
        confidences = [r['confidence'] for r in results]
        
        min_tempo = min(tempos)
        max_tempo = max(tempos)
        tempo_range = max_tempo - min_tempo
        avg_confidence = sum(confidences) / len(confidences)
        
        print("📈 Summary:")
        print(f"   Tempo Range: {min_tempo:.1f} - {max_tempo:.1f} BPM (Δ {tempo_range:.1f} BPM)")
        print(f"   Average Confidence: {avg_confidence*100:.1f}%")
        
        if tempo_range < 2.0:
            print(f"   ✅ Tight performance - tempo very consistent")
        elif tempo_range < 5.0:
            print(f"   ✅ Good performance - minor tempo variations")
        elif tempo_range < 10.0:
            print(f"   ⚠️  Notable tempo changes detected")
        else:
            print(f"   🎵 Significant tempo changes - multi-tempo song")
        
        if avg_confidence > 0.85:
            print(f"   ✅ High confidence - tempo detection very reliable")
        elif avg_confidence > 0.6:
            print(f"   ⚠️  Medium confidence - manual review recommended")
        else:
            print(f"   ❌ Low confidence - complex or non-rhythmic audio")
        
        print()
        return True
        
    except Exception as e:
        print(f"   ❌ Failed: {e}\n")
        import traceback
        traceback.print_exc()
        return False

def test_edge_cases():
    print("\n🧪 Testing Edge Cases\n")
    
    # Test with empty sections array
    print("Test 1: Empty sections array...")
    try:
        response = requests.post(
            f"{BASE_URL}/analyze/tempo_sections",
            json={"key": "test.mp3", "sections": []},
            timeout=5
        )
        if response.status_code == 400:
            print("   ✅ Correctly rejected empty sections\n")
        else:
            print("   ⚠️  Should have returned 400 error\n")
    except Exception as e:
        print(f"   ⚠️  Error: {e}\n")
    
    # Test with missing key
    print("Test 2: Missing audio key...")
    try:
        response = requests.post(
            f"{BASE_URL}/analyze/tempo_sections",
            json={"sections": [{"start": 0, "end": 1}]},
            timeout=5
        )
        if response.status_code == 400:
            print("   ✅ Correctly rejected missing key\n")
        else:
            print("   ⚠️  Should have returned 400 error\n")
    except Exception as e:
        print(f"   ⚠️  Error: {e}\n")
    
    # Test with non-existent file
    print("Test 3: Non-existent audio file...")
    try:
        response = requests.post(
            f"{BASE_URL}/analyze/tempo_sections",
            json={"key": "nonexistent.mp3", "sections": [{"start": 0, "end": 1}]},
            timeout=5
        )
        if response.status_code == 404:
            print("   ✅ Correctly returned 404 for missing file\n")
        else:
            print("   ⚠️  Should have returned 404 error\n")
    except Exception as e:
        print(f"   ⚠️  Error: {e}\n")

if __name__ == "__main__":
    print("=" * 70)
    print("  DrumTracKAI - Per-Section Tempo Detection Test Suite")
    print("=" * 70 + "\n")
    
    # Check if backend is running
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=5)
        print("✅ Backend is running\n")
    except:
        print("❌ Backend is not responding at http://localhost:8000")
        print("   Please start the backend first\n")
        exit(1)
    
    # Run main test
    success = test_per_section_tempo()
    
    # Run edge case tests
    test_edge_cases()
    
    # Final summary
    print("=" * 70)
    if success:
        print("✅ PER-SECTION TEMPO DETECTION: WORKING")
        print("\nNext steps:")
        print("1. Open http://localhost:3000")
        print("2. Upload an audio file")
        print("3. Check Section Manager sidebar for tempo per section")
        print("4. Look for color-coded confidence indicators:")
        print("   🟢 Green (>85%) = High confidence")
        print("   🟡 Yellow (60-85%) = Medium confidence")
        print("   🔴 Red (<60%) = Low confidence")
    else:
        print("❌ PER-SECTION TEMPO DETECTION: FAILED")
        print("\nTroubleshooting:")
        print("1. Check Docker containers are running: docker ps")
        print("2. Check backend logs: docker logs backend")
        print("3. Upload an audio file first through the web interface")
    print("=" * 70)

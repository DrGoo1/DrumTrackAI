#!/usr/bin/env python3
"""
Test tempo detection endpoint to ensure it's working
"""
import requests
import sys

API_BASE = "http://localhost:8000"

def test_tempo_endpoint():
    """Test that tempo analysis endpoint exists and works"""
    
    # Check if there are any uploaded files
    import os
    from pathlib import Path
    
    uploads_dir = Path("uploads")
    if not uploads_dir.exists():
        print("❌ uploads directory not found")
        return False
    
    audio_files = list(uploads_dir.glob("*.mp3")) + list(uploads_dir.glob("*.wav"))
    
    if not audio_files:
        print("❌ No audio files found in uploads/")
        print("   Please upload a file first via the UI")
        return False
    
    # Test with the first file
    test_file = audio_files[0]
    key = test_file.name
    
    print(f"🎵 Testing tempo detection with: {key}")
    print(f"   File path: {test_file}")
    print(f"   File size: {test_file.stat().st_size / 1024:.1f} KB")
    
    # Test analyze tempo endpoint
    url = f"{API_BASE}/analyze/tempo?key={key}"
    print(f"\n📡 Calling: {url}")
    
    try:
        response = requests.get(url, timeout=30)
        print(f"   Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"\n✅ SUCCESS!")
            print(f"   Detected Tempo: {data.get('tempo', 'N/A')} BPM")
            print(f"   Beats detected: {len(data.get('beats', []))} beats")
            
            if 'tempo' in data and data['tempo'] > 0:
                print(f"\n🎉 Tempo detection is working correctly!")
                return True
            else:
                print(f"\n⚠️  Tempo was 0 or missing")
                return False
        else:
            print(f"❌ HTTP {response.status_code}: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("  DrumTracKAI Tempo Detection Test")
    print("=" * 60)
    
    success = test_tempo_endpoint()
    
    print("\n" + "=" * 60)
    if success:
        print("✅ TEMPO DETECTION: WORKING")
        sys.exit(0)
    else:
        print("❌ TEMPO DETECTION: FAILED")
        print("\n💡 Troubleshooting:")
        print("   1. Check if backend is running: docker ps")
        print("   2. Check backend logs: docker logs backend")
        print("   3. Verify USE_RUST=1 is set")
        print("   4. Try uploading a file via UI first")
        sys.exit(1)

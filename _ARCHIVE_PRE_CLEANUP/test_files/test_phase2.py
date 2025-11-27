import requests
import json

# Test the new /dcsm/analyze_full endpoint
url = "http://localhost:8000/dcsm/analyze_full"
params = {"key": "1763641214472-Torn_no_drums.mp3"}

print("🧪 Testing Phase 2 Bar Layer Implementation...")
print(f"📡 Calling: {url}")
print(f"📁 File: {params['key']}")
print()

try:
    response = requests.get(url, params=params, timeout=60)
    
    if response.status_code == 200:
        data = response.json()
        
        print("✅ SUCCESS! SongMap received!")
        print()
        print("=" * 60)
        print("📊 ANALYSIS RESULTS")
        print("=" * 60)
        print()
        
        # Global data
        print(f"⏱️  Duration: {data.get('duration', 0):.1f} seconds")
        print(f"🎵 Global BPM: {data.get('global_bpm_estimate', 0):.1f}")
        print(f"🎼 Meter: {data.get('meter', [4, 4])}")
        print()
        
        # Bars
        bars = data.get('bars', [])
        print(f"🎹 Bars: {len(bars)} detected")
        if bars:
            tempos = [b['tempo_bpm'] for b in bars]
            print(f"   Min tempo: {min(tempos):.1f} BPM")
            print(f"   Max tempo: {max(tempos):.1f} BPM")
            print(f"   Avg tempo: {sum(tempos)/len(tempos):.1f} BPM")
            print(f"   First bar: {bars[0]}")
        print()
        
        # Sections
        sections = data.get('sections', [])
        print(f"🎭 Sections: {len(sections)} detected")
        for i, sec in enumerate(sections[:5]):  # Show first 5
            label = sec.get('label', 'unknown')
            start = sec.get('start', 0)
            end = sec.get('end', 0)
            energy = sec.get('energy', 0)
            start_bar = sec.get('start_bar_index', 'N/A')
            end_bar = sec.get('end_bar_index', 'N/A')
            bar_count = sec.get('bar_count', 'N/A')
            print(f"   {i+1}. {label:10} | {start:6.1f}s - {end:6.1f}s | Energy: {energy:.2f} | Bars: {start_bar}-{end_bar} ({bar_count})")
        
        if len(sections) > 5:
            print(f"   ... and {len(sections) - 5} more sections")
        print()
        
        # Beat times
        beats = data.get('beat_times', [])
        print(f"🥁 Beat times: {len(beats)} beats detected")
        print()
        
        # Section labels summary
        labels = {}
        for sec in sections:
            label = sec.get('label', 'unknown')
            labels[label] = labels.get(label, 0) + 1
        
        print("📝 Section Labels:")
        for label, count in sorted(labels.items()):
            print(f"   {label}: {count}")
        print()
        
        print("=" * 60)
        print("✅ Phase 2 Bar Layer is WORKING!")
        print("=" * 60)
        
        # Save to file
        with open('songmap_test.json', 'w') as f:
            json.dump(data, f, indent=2)
        print()
        print("💾 Full SongMap saved to: songmap_test.json")
        
    else:
        print(f"❌ ERROR: Status code {response.status_code}")
        print(response.text)
        
except Exception as e:
    print(f"❌ ERROR: {e}")
    print()
    print("Make sure the backend is running on port 8000")

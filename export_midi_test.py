import requests
import json
import base64
from pathlib import Path

url = "http://localhost:8000/api/generate_with_drummer"

# Generate drums for first 32 seconds of Peg (2 sections)
payload = {
    "drummer_id": "studio_groove_master",
    "bpm": 156.6,
    "sections": [
        {
            "start": 0.0,
            "end": 16.0,
            "fill_in": False,
            "fill_out": False,
            "label": "verse",
            "density": 0.7
        },
        {
            "start": 16.0,
            "end": 32.0,
            "fill_in": False,
            "fill_out": True,  # Add fill at end
            "label": "chorus",
            "density": 0.8
        }
    ],
    "song_analysis": {},
    "export_midi": True  # Request MIDI export
}

print("🎵 Generating drums with Jeff Porcaro style...")
print(f"   Tempo: {payload['bpm']} BPM")
print(f"   Sections: {len(payload['sections'])}")
print()

response = requests.post(url, json=payload)

if response.status_code == 200:
    data = response.json()
    note_count = len(data.get("notes", []))
    print(f"✓ Generated {note_count} notes")
    
    # Check if we got MIDI data
    midi_b64 = data.get("midi_base64")
    
    if midi_b64:
        # Decode and save MIDI
        midi_bytes = base64.b64decode(midi_b64)
        output_file = Path("generated_peg_drums.mid")
        output_file.write_bytes(midi_bytes)
        print(f"✓ MIDI saved to: {output_file.absolute()}")
        print(f"  File size: {len(midi_bytes)} bytes")
        print()
        print("🎹 You can now open 'generated_peg_drums.mid' in:")
        print("   - Your DAW (Reaper, Ableton, FL Studio, etc.)")
        print("   - Windows Media Player")
        print("   - Any MIDI player")
        print()
        print("   GM Drum Map:")
        print("   - Channel 10: Drums")
        print("   - Note 36: Kick")
        print("   - Note 38: Snare")
        print("   - Note 42: Closed Hi-Hat")
        print("   - Note 46: Open Hi-Hat")
        print("   - Note 51: Ride")
        print("   - Note 41/43/45: Toms")
        print("   - Note 49: Crash")
    else:
        print("⚠ No MIDI data in response")
        print("Response keys:", list(data.keys()))
        
        # Generate MIDI from notes using Rust CLI directly
        print()
        print("Generating MIDI via Rust CLI...")
        import subprocess
        
        # Save notes to temp file for Rust
        notes_json = json.dumps(data["notes"])
        
        # Call rust to generate MIDI from notes
        # (We'll need to check if Rust CLI supports this)
        print("Note: MIDI generation from notes requires Rust CLI update")
        
else:
    print(f"✗ Error: {response.status_code}")
    print(response.text)

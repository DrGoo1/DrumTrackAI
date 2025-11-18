import requests
import json

# Test the endpoint with the uploaded Peg file
payload = {
    "key": "1763323550267-Peg_No_Drums.mp3",
    "sections": [
        {"start": 0.0, "end": 10.0},
        {"start": 10.0, "end": 20.0},
        {"start": 20.0, "end": 30.0},
        {"start": 30.0, "end": 40.0}
    ]
}

print("🧪 Testing /analyze/tempo_sections endpoint...\n")
print(f"Request: POST /analyze/tempo_sections")
print(f"Payload: {json.dumps(payload, indent=2)}\n")

try:
    response = requests.post(
        "http://localhost:8000/analyze/tempo_sections",
        json=payload,
        timeout=30
    )
    
    print(f"Status: {response.status_code}")
    
    if response.status_code == 200:
        result = response.json()
        print("\n✅ SUCCESS! Response:\n")
        print(json.dumps(result, indent=2))
        
        print("\n📊 Per-Section Tempos:")
        for i, r in enumerate(result.get('results', [])):
            tempo = r['tempo']
            conf = r['confidence']
            indicator = "🟢" if conf > 0.85 else "🟡" if conf > 0.6 else "🔴"
            print(f"  Section {i+1}: {tempo:.1f} BPM ({conf*100:.0f}%) {indicator}")
        
        global_tempo = result.get('global_tempo', 0)
        print(f"\n  Global Average: {global_tempo:.1f} BPM")
    else:
        print(f"\n❌ FAILED")
        print(f"Response: {response.text}")
        
except Exception as e:
    print(f"❌ ERROR: {e}")

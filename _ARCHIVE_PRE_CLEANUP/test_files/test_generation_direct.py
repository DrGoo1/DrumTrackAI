import requests
import json

url = "http://localhost:8000/api/generate_with_drummer"
payload = {
    "drummer_id": "studio_groove_master",
    "bpm": 156.6,
    "sections": [{
        "start": 0.0,
        "end": 24.5,
        "fill_in": False,
        "fill_out": True,
        "label": "verse",
        "density": 0.7
    }],
    "song_analysis": {}
}

print("Sending request...")
print(f"Payload: {json.dumps(payload, indent=2)}")

response = requests.post(url, json=payload)
print(f"\nStatus: {response.status_code}")
print(f"Response: {json.dumps(response.json(), indent=2)}")


from typing import List, Dict

def detect_flam(events: List[Dict]) -> List[Dict]:
    out = []
    for i in range(len(events)-1):
        if abs(events[i]["time"] - events[i+1]["time"]) < 0.03:
            out.append({"type": "flam", "index": i})
    return out

def detect_drag(events: List[Dict]) -> List[Dict]:
    out = []
    for i in range(len(events)-2):
        gap1 = events[i+1]["time"] - events[i]["time"]
        gap2 = events[i+2]["time"] - events[i+1]["time"]
        if gap1 < 0.05 and gap2 < 0.05:
            out.append({"type": "drag", "index": i})
    return out

def detect_paradiddle(events: List[Dict]) -> List[Dict]:
    out = []
    for i in range(len(events)-3):
        seq = [e.get("hand") for e in events[i:i+4]]
        if seq in [["R","L","R","R"],["L","R","L","L"]]:
            out.append({"type": "paradiddle", "index": i})
    return out

def detect_rudiments(events: List[Dict]) -> List[Dict]:
    results = []
    results += detect_flam(events)
    results += detect_drag(events)
    results += detect_paradiddle(events)
    return results


from typing import Dict, List

def detect_six_stroke_roll(events: List[Dict]) -> List[Dict]:
    out = []
    for i in range(len(events) - 5):
        seq = [events[j].get("hand") for j in range(i, i + 6)]
        if seq in (["R","L","L","R","R","L"], ["L","R","R","L","L","R"]):
            out.append({"type": "six_stroke_roll", "index": i, "confidence": 0.78})
    return out

def detect_swiss_triplet(events: List[Dict]) -> List[Dict]:
    out = []
    for i in range(len(events) - 2):
        near = abs(events[i]["time"] - events[i+1]["time"]) < 0.03
        if near and events[i+2].get("instrument") in ("tom1", "tom2", "snare"):
            out.append({"type": "swiss_triplet", "index": i, "confidence": 0.72})
    return out

def detect_rudiment_hybrids(events: List[Dict]) -> List[Dict]:
    out = []
    for i in range(len(events) - 3):
        inst = [events[j].get("instrument") for j in range(i, i + 4)]
        if len(set(inst)) >= 3:
            out.append({"type": "linear_hybrid", "index": i, "confidence": 0.60})
    return out

def detect_extended_rudiments(events: List[Dict]) -> List[Dict]:
    out = []
    out += detect_six_stroke_roll(events)
    out += detect_swiss_triplet(events)
    out += detect_rudiment_hybrids(events)
    return out

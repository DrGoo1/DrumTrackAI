
from typing import Dict, List

def phrase_signature(phrase: Dict) -> Dict:
    events = phrase.get("events", [])
    instruments = [e.get("instrument") for e in events]
    return {
        "event_count": len(events),
        "instruments": tuple(sorted(set(i for i in instruments if i))),
        "section_type": phrase.get("sectionType") or phrase.get("type"),
        "rudiment_type": ((phrase.get("rudimentPhrase") or {}).get("type")),
        "family": ((phrase.get("phraseSelection") or {}).get("grooveFamily") or phrase.get("family")),
    }

def build_continuity_memory(phrases: List[Dict], window: int = 4) -> List[Dict]:
    memory = []
    for p in (phrases or [])[-window:]:
        memory.append(phrase_signature(p))
    return memory

def similarity_score(sig_a: Dict, sig_b: Dict) -> float:
    score = 0.0
    if sig_a.get("family") and sig_a.get("family") == sig_b.get("family"):
        score += 0.35
    if sig_a.get("rudiment_type") and sig_a.get("rudiment_type") == sig_b.get("rudiment_type"):
        score += 0.20
    if sig_a.get("section_type") and sig_a.get("section_type") == sig_b.get("section_type"):
        score += 0.15

    a_inst = set(sig_a.get("instruments") or [])
    b_inst = set(sig_b.get("instruments") or [])
    if a_inst or b_inst:
        overlap = len(a_inst & b_inst)
        union = max(1, len(a_inst | b_inst))
        score += 0.30 * (overlap / union)
    return min(1.0, score)

def continuity_bias(candidate_phrase: Dict, memory: List[Dict]) -> Dict:
    out = dict(candidate_phrase or {})
    sig = phrase_signature(out)
    sims = [similarity_score(sig, m) for m in (memory or [])]
    best = max(sims) if sims else 0.0
    avg = sum(sims) / len(sims) if sims else 0.0
    out["continuityMeta"] = {
        "bestSimilarity": best,
        "avgSimilarity": avg,
        "memoryDepth": len(memory or []),
    }
    out["continuityScore"] = 0.6 * best + 0.4 * avg
    return out

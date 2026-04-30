
from typing import Dict, List
from .phrase_continuity_memory import build_continuity_memory, continuity_bias
from .phrase_variation_engine import apply_phrase_variation

def apply_phrase_continuity_runtime(phrases: List[Dict], variation_mode: str = "light") -> List[Dict]:
    out = []
    for p in phrases or []:
        memory = build_continuity_memory(out, window=4)
        biased = continuity_bias(p, memory)
        continuity_score = float(biased.get("continuityScore", 0.0))

        # Very repetitive candidates get light variation before committing.
        if continuity_score >= 0.65:
            biased = apply_phrase_variation(biased, mode=variation_mode, continuity_score=continuity_score)

        out.append(biased)
    return out

def continuity_plan_for_sections(sections: List[Dict]) -> List[Dict]:
    planned = []
    for idx, s in enumerate(sections or []):
        s2 = dict(s)
        section_type = s2.get("sectionType") or s2.get("type") or "verse"
        if section_type in ("intro", "verse"):
            mode = "light"
        elif section_type in ("prechorus", "bridge"):
            mode = "medium"
        else:
            mode = "strong" if idx > 0 else "medium"

        s2["continuityPlan"] = {
            "variationMode": mode,
            "memoryWindow": 4,
            "strategy": "repeat_then_vary",
        }
        planned.append(s2)
    return planned

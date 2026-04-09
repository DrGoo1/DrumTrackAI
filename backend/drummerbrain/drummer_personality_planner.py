from typing import Dict, List

def plan_personality_for_sections(sections: List[Dict], personality: Dict) -> List[Dict]:
    out = []
    aggressiveness = float((personality or {}).get("aggressiveness", 0.5))
    restraint = float((personality or {}).get("restraint", 0.5))
    chaos = float((personality or {}).get("chaos", 0.3))

    for s in sections or []:
        s2 = dict(s)
        t = s2.get("sectionType") or s2.get("type") or "verse"

        local_aggr = aggressiveness
        local_rest = restraint
        local_chaos = chaos

        if t in ("intro", "verse"):
            local_aggr *= 0.8
            local_rest = min(1.0, local_rest + 0.1)
        elif t in ("chorus",):
            local_aggr = min(1.0, local_aggr + 0.15)
            local_chaos = min(1.0, local_chaos + 0.05)
        elif t in ("bridge", "prechorus"):
            local_chaos = min(1.0, local_chaos + 0.1)

        s2["personalityPlan"] = {
            "aggressiveness": local_aggr,
            "restraint": local_rest,
            "chaos": local_chaos,
            "signatureHabits": (personality or {}).get("signatureHabits", {}),
        }
        out.append(s2)
    return out

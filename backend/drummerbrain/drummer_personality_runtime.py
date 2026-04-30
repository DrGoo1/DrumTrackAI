from typing import Dict, List

def apply_drummer_personality(phrases: List[Dict], sections: List[Dict]) -> List[Dict]:
    out = []
    sec_map = {}
    for s in sections or []:
        key = s.get("id") or s.get("sectionId") or s.get("sectionType") or s.get("type")
        if key:
            sec_map[key] = s

    for p in phrases or []:
        p2 = dict(p)
        sid = p2.get("sectionId") or p2.get("sectionType") or p2.get("type")
        section = sec_map.get(sid, {})
        plan = section.get("personalityPlan", {})
        aggr = float(plan.get("aggressiveness", 0.5))
        rest = float(plan.get("restraint", 0.5))
        chaos = float(plan.get("chaos", 0.3))
        habits = plan.get("signatureHabits", {})

        evs = []
        for i, e in enumerate(p2.get("events", []) or []):
            e2 = dict(e)
            inst = e2.get("instrument")
            vel = float(e2.get("velocity", 0.6))

            # Aggressiveness boosts accents/crashes/backbeats
            if e2.get("accent") or inst in ("crash", "ride"):
                vel = min(1.0, vel + 0.15 * aggr)

            # Restraint suppresses random embellishment
            if rest >= 0.65 and e2.get("role") == "ghost":
                vel = max(0.0, vel - 0.08)

            # Chaos slightly perturbs non-accent notes
            if chaos >= 0.5 and not e2.get("accent"):
                delta = 0.04 if (i % 2 == 0) else -0.03
                vel = max(0.0, min(1.0, vel + delta * chaos))

            # Signature crash bias
            if inst == "crash":
                vel = max(vel, min(1.0, 0.75 + 0.2 * float(habits.get("crashBias", 0.0))))

            e2["velocity"] = vel
            evs.append(e2)

        p2["events"] = evs
        p2["personalityApplied"] = True
        p2["personalityMeta"] = {
            "aggressiveness": aggr,
            "restraint": rest,
            "chaos": chaos,
        }
        out.append(p2)
    return out

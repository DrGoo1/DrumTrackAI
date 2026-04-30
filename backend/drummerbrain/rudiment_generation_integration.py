
from typing import Dict
from .rudiment_phrase_generator import choose_rudiment_phrase
from .rudiment_orchestration import orchestrate_rudiment_events

def inject_rudiment_phrase(phrase: Dict, section: Dict, rudiment_profile: Dict) -> Dict:
    out = dict(phrase or {})
    chosen = choose_rudiment_phrase(section or {}, rudiment_profile or {})
    events = orchestrate_rudiment_events(chosen["events"], section or {})

    out.setdefault("generatedTechniques", [])
    out["generatedTechniques"].append({
        "type": chosen["rudimentType"],
        "source": "phase33_rudiment_generator",
        "sectionType": chosen["sectionType"],
    })

    out.setdefault("events", [])
    out["events"].extend(events)
    out["rudimentPhrase"] = {
        "type": chosen["rudimentType"],
        "orchestrated": chosen["orchestrated"],
        "eventCount": len(events),
    }
    return out

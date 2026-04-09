from typing import Dict

def style_consistency_score(profile: Dict, generated: Dict) -> float:
    # simple proxy: match preferred family
    fam = generated.get("family")
    prefs = profile.get("preferredGrooveFamilies", [])
    return 1.0 if fam in prefs else 0.0

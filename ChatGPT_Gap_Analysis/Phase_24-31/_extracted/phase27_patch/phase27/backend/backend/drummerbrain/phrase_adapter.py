def adapt_phrase_to_section(phrase, section):
    # simple scaling example
    factor = section.get("energy", 0.5)
    for e in phrase.get("events", []):
        e["velocity"] = min(1.0, e.get("velocity",0.5) * (0.5 + factor))
    return phrase

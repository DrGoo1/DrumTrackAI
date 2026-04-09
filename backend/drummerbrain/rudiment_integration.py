
def tag_phrase_with_rudiments(phrase, rudiments):
    phrase["rudiments"] = rudiments
    return phrase

def bias_phrase_selection(phrase, profile):
    score = phrase.get("score", 0)
    for r in phrase.get("rudiments", []):
        if r["type"] in profile.get("usage_rate", {}):
            score += profile["usage_rate"][r["type"]]
    phrase["score"] = score
    return phrase

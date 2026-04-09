def enforce_limb_constraints(events):
    cleaned = []
    active = 0
    for e in events:
        if active < 2:
            cleaned.append(e)
            active += 1
    return cleaned

def build_simple_embedding(phrase):
    events = phrase.get("events", [])
    if not events:
        return [0,0,0,0,0]

    density = len(events)
    vel = sum(e.get("velocity",0.5) for e in events)/len(events)
    kick = sum(e["instrument"]=="kick" for e in events)
    snare = sum(e["instrument"]=="snare" for e in events)
    sync = sum(e.get("subdivision",0)%2!=0 for e in events)

    return [
        density/32,
        sync/len(events),
        vel,
        kick/len(events),
        snare/len(events)
    ]

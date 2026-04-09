import json, math
from pathlib import Path

MEMORY_PATH = Path("database/phrase_memory")

def save_phrase(drummer_id, phrase):
    MEMORY_PATH.mkdir(parents=True, exist_ok=True)
    path = MEMORY_PATH / f"{drummer_id}.json"
    data = json.loads(path.read_text()) if path.exists() else []
    data.append(phrase)
    path.write_text(json.dumps(data, indent=2))

def load_phrases(drummer_id):
    path = MEMORY_PATH / f"{drummer_id}.json"
    return json.loads(path.read_text()) if path.exists() else []

def _cosine(a, b):
    dot = sum(x*y for x,y in zip(a,b))
    mag_a = math.sqrt(sum(x*x for x in a))
    mag_b = math.sqrt(sum(x*x for x in b))
    return dot/(mag_a*mag_b) if mag_a and mag_b else 0

def retrieve_similar_phrases(drummer_id, emb, k=5):
    phrases = load_phrases(drummer_id)
    scored = [(_cosine(emb, p.get("embedding",[])), p) for p in phrases]
    scored.sort(reverse=True)
    return [p for _,p in scored[:k]]

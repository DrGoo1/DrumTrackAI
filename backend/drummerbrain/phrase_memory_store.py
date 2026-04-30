from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any, Dict, List, Sequence


MEMORY_PATH = Path("database/phrase_memory")


def save_phrase(drummer_id: str, phrase: Dict[str, Any]) -> Path:
    MEMORY_PATH.mkdir(parents=True, exist_ok=True)
    path = MEMORY_PATH / f"{drummer_id}.json"
    data = json.loads(path.read_text(encoding="utf-8")) if path.exists() else []
    if not isinstance(data, list):
        data = []
    data.append(phrase)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    return path


def load_phrases(drummer_id: str) -> List[Dict[str, Any]]:
    path = MEMORY_PATH / f"{drummer_id}.json"
    payload = json.loads(path.read_text(encoding="utf-8")) if path.exists() else []
    return payload if isinstance(payload, list) else []


def _cosine(a: Sequence[float], b: Sequence[float]) -> float:
    dot = sum(float(x) * float(y) for x, y in zip(a, b))
    mag_a = math.sqrt(sum(float(x) * float(x) for x in a))
    mag_b = math.sqrt(sum(float(x) * float(x) for x in b))
    return dot / (mag_a * mag_b) if mag_a and mag_b else 0.0


def retrieve_similar_phrases(drummer_id: str, emb: Sequence[float], k: int = 5) -> List[Dict[str, Any]]:
    phrases = load_phrases(drummer_id)
    scored = [(_cosine(emb, p.get("embedding", []) or []), p) for p in phrases if isinstance(p, dict)]
    scored.sort(key=lambda item: item[0], reverse=True)
    return [p for _, p in scored[: max(1, int(k))]]


__all__ = ["save_phrase", "load_phrases", "retrieve_similar_phrases", "MEMORY_PATH"]

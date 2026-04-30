from __future__ import annotations

from pathlib import Path

import backend.drummerbrain.phrase_memory_store as store
from backend.drummerbrain.phrase_memory_store import retrieve_similar_phrases, save_phrase


def test_memory(tmp_path, monkeypatch):
    monkeypatch.setattr(store, "MEMORY_PATH", Path(tmp_path) / "phrase_memory")

    p = {"events": [{"instrument": "kick"}, {"instrument": "snare"}], "embedding": [1, 0, 0, 0, 0]}
    save_phrase("test", p)

    r = retrieve_similar_phrases("test", p["embedding"], 1)
    assert len(r) >= 1

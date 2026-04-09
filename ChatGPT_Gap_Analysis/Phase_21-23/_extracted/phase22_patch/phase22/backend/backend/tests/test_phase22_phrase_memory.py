from backend.backend.drummerbrain.phrase_memory_store import save_phrase, retrieve_similar_phrases

def test_memory():
    p = {"events":[{"instrument":"kick"},{"instrument":"snare"}], "embedding":[1,0,0,0,0]}
    save_phrase("test", p)
    r = retrieve_similar_phrases("test", p["embedding"], 1)
    assert len(r) >= 1

from typing import Dict

DEFAULT_FLAGS = {
    "sentient_enabled": True,
    "sentient_phrase_memory": True,
    "sentient_similarity_ranking": True,
    "sentient_eval": True,
    "sentient_plugin_render": True,
}

def merge_sentient_flags(overrides: Dict | None = None) -> Dict:
    flags = dict(DEFAULT_FLAGS)
    if overrides:
        flags.update(overrides)
    return flags

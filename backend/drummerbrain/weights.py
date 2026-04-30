import json
import os
from pathlib import Path
from typing import Any, Dict, Optional


def default_weights() -> Dict[str, Any]:
    # Keep defaults aligned with the original hard-coded policy terms in runtime_selection.py.
    return {
        "tempo_div": 25.0,
        "bar_multiple_w": 0.35,
        "loop_fit_w": 0.75,
        "confidence_w": 1.25,
        "variant_bonus": {
            "drum": -0.25,
            "original": 0.10,
        },
        "skeleton_penalty": {
            "missing_kick": 0.35,
            "missing_snare": 0.45,
        },
        "backbeat": {"target": 0.8, "w": 0.20},
        "syncopation": {"target": 0.25, "w": 0.15},
        "density": {"target": 2.0, "w": 0.05},
    }


def _try_parse_json(text: str) -> Optional[Dict[str, Any]]:
    try:
        obj = json.loads(text)
        return obj if isinstance(obj, dict) else None
    except Exception:
        return None


def load_weights(*, explicit_path: Optional[str] = None) -> Dict[str, Any]:
    """Load deterministic scoring weights.

    Priority:
    - explicit_path (if provided)
    - env DRUMMERBRAIN_WEIGHTS_PATH
    - env DRUMMERBRAIN_WEIGHTS_JSON (literal JSON object string)
    - defaults
    """

    if explicit_path:
        p = Path(str(explicit_path))
        try:
            obj = _try_parse_json(p.read_text(encoding="utf-8"))
            if obj is not None:
                return obj
        except Exception:
            pass

    env_path = os.getenv("DRUMMERBRAIN_WEIGHTS_PATH")
    if env_path:
        p = Path(str(env_path))
        try:
            obj = _try_parse_json(p.read_text(encoding="utf-8"))
            if obj is not None:
                return obj
        except Exception:
            pass

    env_json = os.getenv("DRUMMERBRAIN_WEIGHTS_JSON")
    if env_json:
        obj = _try_parse_json(str(env_json))
        if obj is not None:
            return obj

    return default_weights()

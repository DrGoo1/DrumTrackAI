from __future__ import annotations

from typing import Dict, Optional

from .feature_flags_sentient import merge_sentient_flags


def build_sentient_runtime_config(base: Optional[Dict] = None, overrides: Optional[Dict] = None) -> Dict:
    cfg = dict(base or {})
    cfg["sentientFlags"] = merge_sentient_flags(overrides)
    cfg.setdefault("routing", {})
    cfg["routing"]["defaultGenerateRoute"] = "/v1/render_sentient_take"
    return cfg


__all__ = ["build_sentient_runtime_config"]

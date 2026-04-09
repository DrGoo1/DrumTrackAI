from typing import Dict
from .feature_flags_sentient import merge_sentient_flags

def build_sentient_runtime_config(base: Dict | None = None, overrides: Dict | None = None) -> Dict:
    cfg = dict(base or {})
    cfg["sentientFlags"] = merge_sentient_flags(overrides)
    cfg.setdefault("routing", {})
    cfg["routing"]["defaultGenerateRoute"] = "/v1/render_sentient_take"
    return cfg

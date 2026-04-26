from __future__ import annotations

from typing import Any, Dict


def make_transform_audit(before_features: Dict[str, Any], after_features: Dict[str, Any]) -> Dict[str, Any]:
    before = dict(before_features or {})
    after = dict(after_features or {})

    added_keys = [k for k in after.keys() if k not in before]
    removed_keys = [k for k in before.keys() if k not in after]
    shared_keys = [k for k in before.keys() if k in after]

    numeric_deltas: Dict[str, float] = {}
    absolute_delta_sum = 0.0
    changed_keys = []
    for key in shared_keys:
        b = before.get(key)
        a = after.get(key)
        if b != a:
            changed_keys.append(key)
        try:
            if isinstance(b, (int, float)) and isinstance(a, (int, float)):
                delta = float(a) - float(b)
                numeric_deltas[key] = delta
                absolute_delta_sum += abs(delta)
        except Exception:
            continue

    max_delta_key = None
    max_delta_value = 0.0
    for key, delta in numeric_deltas.items():
        if abs(delta) > abs(max_delta_value):
            max_delta_key = key
            max_delta_value = delta

    total_keys = max(1, len(set(before.keys()).union(set(after.keys()))))
    structural_change_ratio = float((len(added_keys) + len(removed_keys) + len(changed_keys)) / total_keys)

    return {
        "before_features": before,
        "after_features": after,
        "transform_delta": {
            "added_keys": added_keys,
            "removed_keys": removed_keys,
            "changed_keys": changed_keys,
            "numeric_deltas": numeric_deltas,
            "absolute_numeric_delta_sum": absolute_delta_sum,
            "max_numeric_delta_key": max_delta_key,
            "max_numeric_delta_value": max_delta_value,
            "structural_change_ratio": structural_change_ratio,
        },
    }

from __future__ import annotations

from typing import Any, Dict, List


def apply_personality_transform(events: List[Dict[str, Any]], controls: Dict[str, Any]) -> List[Dict[str, Any]]:
    """No-op personality transform stub.

    Real implementation would nudge timing/velocity per style controls.
    For bootstrapping the calibration API pipeline, we keep the input events.
    """
    return list(events or [])

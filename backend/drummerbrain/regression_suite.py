from __future__ import annotations

from typing import Any, Dict


def basic_regression_check(output: Dict[str, Any]) -> bool:
    assert "drum_track" in output
    assert len((output.get("drum_track") or {}).get("events", []) or []) > 0
    return True


__all__ = ["basic_regression_check"]

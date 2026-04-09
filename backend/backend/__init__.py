"""Compatibility package.

Some patch zips and tests reference modules under `backend.backend.*`.
This repository's canonical layout is `backend.*`.

This package provides import-time aliases so both import styles work.
"""

from __future__ import annotations

import importlib
import sys


def _alias(module_name: str, target: str) -> None:
    try:
        sys.modules[module_name] = importlib.import_module(target)
    except Exception:
        # If the target doesn't exist, leave it unresolved.
        return


# Alias common subpackages
_alias(__name__ + ".drummerbrain", "backend.drummerbrain")
_alias(__name__ + ".drum_generation", "backend.drum_generation")
_alias(__name__ + ".jamstix_brain", "backend.jamstix_brain")
_alias(__name__ + ".dcsmpiano", "backend.dcsmpiano")

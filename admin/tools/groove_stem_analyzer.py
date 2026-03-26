from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List

from groove_event_extractor import GrooveConfig, GrooveEvent, GrooveAnalyzer

PROJECT_ROOT = Path(__file__).resolve().parents[2]
STEMS_ROOT = PROJECT_ROOT / "admin" / "data" / "mvsep_grooves"

STEM_TO_INSTR = {
    "kick": "kick",
    "snare": "snare",
    "hh": "hat_closed",
    "ride": "ride",
    "crash": "crash",
    "toms": "tom1",
    "drums": "drums",
    "residual": "drums",
}


def find_stems_for_archetype(archetype_id: str) -> Dict[str, str]:
    """Scan the mvsep_grooves folder for this archetype's stems."""
    archetype_dir = STEMS_ROOT / archetype_id
    drumsep_dir = archetype_dir / "drumsep_components"
    if not drumsep_dir.exists():
        raise FileNotFoundError(f"No drumsep_components folder for archetype_id={archetype_id}")

    stems: Dict[str, str] = {}
    for wav in drumsep_dir.glob("drumsep_*.wav"):
        # filenames like drumsep_kick.wav, drumsep_snare.wav, etc.
        name = wav.stem.replace("drumsep_", "")
        stems[name] = str(wav.resolve())
    return stems


def analyze_from_stems(cfg: GrooveConfig, archetype_id: str) -> List[GrooveEvent]:
    stems = find_stems_for_archetype(archetype_id)
    if not stems:
        raise KeyError(f"No stems for archetype_id={archetype_id}")

    analyzer = GrooveAnalyzer(cfg)
    all_events: List[GrooveEvent] = []

    for stem_key, path in stems.items():
        instr = STEM_TO_INSTR.get(stem_key)
        if not instr:
            continue

        stem_events = analyzer.process_audio(path)
        for ev in stem_events:
            ev.instrument = instr
            all_events.append(ev)

    all_events.sort(key=lambda e: e.time_sec)
    return all_events

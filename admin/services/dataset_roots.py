import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass(frozen=True)
class DatasetRoots:
    drumbeats_root: Optional[str]
    snare_rudiments_root: Optional[str]
    soundtracksloops_root: Optional[str]


def _repo_root() -> Optional[Path]:
    try:
        return Path(__file__).resolve().parents[2]
    except Exception:
        return None


def resolve_dataset_roots() -> DatasetRoots:
    repo_root = _repo_root()

    drumbeats_default = str(repo_root / "DrumBeats") if repo_root else None

    # Defaults mirrored from admin UI/training pipeline configs.
    snare_default = r"E:\Snare Rudiments"
    stl_default = r"E:\SoundTracksLoops Dataset"

    return DatasetRoots(
        drumbeats_root=os.getenv("DRUMBEATS_ROOT") or drumbeats_default,
        snare_rudiments_root=os.getenv("SNARE_RUDIMENTS_ROOT") or snare_default,
        soundtracksloops_root=os.getenv("SOUNDTRACKSLOOPS_ROOT") or stl_default,
    )

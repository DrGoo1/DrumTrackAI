from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

PROJECT_ROOT = Path(__file__).resolve().parents[2]
ADMIN_ROOT = PROJECT_ROOT / "admin"
if str(ADMIN_ROOT) not in sys.path:
    sys.path.insert(0, str(ADMIN_ROOT))

try:
    from services.central_database_service import get_database_service
except Exception:
    from admin.services.central_database_service import get_database_service


DEFAULT_DB = PROJECT_ROOT / "admin" / "drumtrackai.db"
DEFAULT_DRUMBEATS_DIR = PROJECT_ROOT / "DrumBeats"


def _get_db_path() -> str:
    env = os.getenv("DRUMTRACKAI_DB_PATH")
    return env or str(DEFAULT_DB)


def _titleize_song_key(song_key: str) -> str:
    s = (song_key or "").strip().replace("_", " ")
    s = " ".join([w for w in s.split(" ") if w])
    return s.title() if s else "Untitled"


def _infer_profile_type(song_key: str, default_profile_type: str) -> str:
    k = (song_key or "").lower()
    if "take_five" in k or "sing_sing_sing" in k:
        return "jazz"
    if "cissy_strut" in k or "funky" in k or "superstitious" in k:
        return "funk"
    if "hot_for_teacher" in k or "crazy_train" in k or "tom_sawyer" in k:
        return "rock"
    if "we_will_rock_you" in k or "walk_this_way" in k or "come_together" in k:
        return "rock"
    if "fifty_ways" in k:
        return "pop"
    if "rosanna" in k or "fool_in_the_rain" in k:
        return "rock"
    return (default_profile_type or "rock").strip().lower() or "rock"


def _base_deltas_for_profile(profile_type: str) -> Dict[str, Any]:
    pt = (profile_type or "").strip().lower()
    if pt == "jazz":
        return {
            "humanizeAmount": 0.78,
            "ghostNoteAmount": 0.72,
            "swingAmount": 0.45,
            "fillControls": {"fillType": "auto", "density": 0.35, "frequency": "section_transitions"},
            "cymbalFocusMode": "continuous",
            "hatsToRideBlend": 0.7,
            "rideBellPercent": 0.12,
            "chorusRidePreference": 0.65,
        }
    if pt == "funk":
        return {
            "humanizeAmount": 0.62,
            "ghostNoteAmount": 0.82,
            "swingAmount": 0.08,
            "fillControls": {"fillType": "auto", "density": 0.5, "frequency": "section_transitions"},
            "cymbalFocusMode": "continuous",
            "hatsToRideBlend": 0.25,
            "rideBellPercent": 0.08,
            "chorusRidePreference": 0.25,
        }
    if pt == "pop":
        return {
            "humanizeAmount": 0.68,
            "ghostNoteAmount": 0.55,
            "swingAmount": 0.02,
            "fillControls": {"fillType": "auto", "density": 0.45, "frequency": "every_4_bars"},
            "cymbalFocusMode": "continuous",
            "hatsToRideBlend": 0.15,
            "rideBellPercent": 0.12,
            "chorusRidePreference": 0.35,
        }
    return {
        "humanizeAmount": 0.7,
        "ghostNoteAmount": 0.65,
        "swingAmount": 0.03,
        "fillControls": {"fillType": "auto", "density": 0.6, "frequency": "section_transitions"},
        "cymbalFocusMode": "continuous",
        "hatsToRideBlend": 0.18,
        "rideBellPercent": 0.2,
        "chorusRidePreference": 0.4,
    }


def _song_overrides(song_key: str) -> Dict[str, Any]:
    k = (song_key or "").lower()

    if "we_will_rock_you" in k:
        return {
            "fillControls": {"fillType": "auto", "density": 0.25, "frequency": "none"},
            "ghostNoteAmount": 0.2,
            "humanizeAmount": 0.55,
            "hatsToRideBlend": 0.05,
        }

    if "fool_in_the_rain" in k:
        return {"swingAmount": 0.35, "ghostNoteAmount": 0.78, "humanizeAmount": 0.74}

    if "rosanna" in k:
        return {"ghostNoteAmount": 0.72, "hatsToRideBlend": 0.4, "chorusRidePreference": 0.55}

    if "hot_for_teacher" in k:
        return {
            "fillControls": {"fillType": "auto", "density": 0.75, "frequency": "all_transitions"},
            "humanizeAmount": 0.62,
            "ghostNoteAmount": 0.45,
            "rideBellPercent": 0.35,
        }

    if "crazy_train" in k:
        return {"fillControls": {"fillType": "auto", "density": 0.7, "frequency": "all_transitions"}, "rideBellPercent": 0.28}

    if "take_five" in k:
        return {"swingAmount": 0.5, "hatsToRideBlend": 0.85, "chorusRidePreference": 0.75}

    if "sing_sing_sing" in k:
        return {"swingAmount": 0.55, "fillControls": {"fillType": "auto", "density": 0.5, "frequency": "every_4_bars"}}

    if "funky" in k or "cissy_strut" in k:
        return {"ghostNoteAmount": 0.9, "humanizeAmount": 0.58, "fillControls": {"fillType": "auto", "density": 0.35, "frequency": "section_transitions"}}

    if "walk_this_way" in k:
        return {"ghostNoteAmount": 0.55, "fillControls": {"fillType": "auto", "density": 0.65, "frequency": "every_4_bars"}}

    return {}


def _merge_dict(a: Dict[str, Any], b: Dict[str, Any]) -> Dict[str, Any]:
    out = dict(a)
    for k, v in (b or {}).items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _merge_dict(out[k], v)
        else:
            out[k] = v
    return out


def _list_drum_stems(drumbeats_dir: Path) -> List[Tuple[str, Path]]:
    if not drumbeats_dir.exists() or not drumbeats_dir.is_dir():
        return []
    out: List[Tuple[str, Path]] = []
    for p in sorted(drumbeats_dir.glob("*.wav")):
        name = p.name.lower()
        if name.endswith("_drum.wav"):
            song_key = p.stem[: -len("_drum")]
            song_key = song_key.replace(" ", "_")
            song_key = "_".join([x for x in song_key.split("_") if x])
            out.append((song_key, p))
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", type=str, default=None)
    ap.add_argument("--drumbeats", type=str, default=None)
    ap.add_argument("--default_profile", type=str, default="rock")
    ap.add_argument("--tier", type=str, default="song")
    ap.add_argument("--dry_run", action="store_true")
    args = ap.parse_args()

    db_path = args.db or _get_db_path()
    os.environ.setdefault("DRUMTRACKAI_DB_PATH", str(db_path))

    drumbeats_dir = Path(args.drumbeats) if args.drumbeats else DEFAULT_DRUMBEATS_DIR

    db = get_database_service()
    if not db.initialize(db_path):
        return 1

    stems = _list_drum_stems(drumbeats_dir)
    if not stems:
        print(f"No *_drum.wav files found in: {drumbeats_dir}")
        return 0

    created = 0
    for song_key, wav_path in stems:
        profile_type = _infer_profile_type(song_key, args.default_profile)
        name = f"{_titleize_song_key(song_key)} (DrumBeats)"
        preset_id = f"drumbeats:{song_key}"
        deltas = _merge_dict(_base_deltas_for_profile(profile_type), _song_overrides(song_key))

        if args.dry_run:
            print({"preset_id": preset_id, "profile_type": profile_type, "name": name, "tier": args.tier, "deltas": deltas, "source_ref": str(wav_path)})
            continue

        ok = db.upsert_drummer_preset(
            preset_id=preset_id,
            profile_type=profile_type,
            name=name,
            tier=str(args.tier),
            deltas=deltas,
            policies={},
            source_type="drumbeats",
            source_song_name=_titleize_song_key(song_key),
            source_ref=str(wav_path),
        )
        if ok:
            created += 1

    if args.dry_run:
        print(f"Dry run complete. Would upsert {len(stems)} presets.")
        return 0

    print(f"Upserted {created} presets into {db_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

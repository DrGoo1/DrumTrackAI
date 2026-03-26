import argparse
import logging
import re
import sqlite3
from pathlib import Path
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

DEFAULT_DB_PATH = Path(__file__).parent.parent / "data" / "drum_training.db"
DEFAULT_OUT_DIR = Path(__file__).parent.parent / "data" / "rudiment_midis"


def _slugify(name: str) -> str:
    s = re.sub(r"[^a-zA-Z0-9]+", "_", name.strip().lower())
    s = re.sub(r"_+", "_", s).strip("_")
    return s or "rudiment"


def _db_connect(db_path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    return conn


def _get_rudiment_pattern(family: str, name: str) -> Tuple[List[str], str]:
    """Return (steps, grid) where steps is a sequence of hits and grid is '16' or 'triplet'.

    Steps contain tokens like:
      - 'S' snare normal
      - 'G' snare ghost
      - 'A' snare accent
      - 'f' flam grace
    """
    n = name.lower()
    fam = (family or "").lower()

    if "paradiddle" in n or fam == "paradiddle":
        return list("ASGSASGG"), "16"
    if "flam" in n or fam == "flam":
        return ["f", "A", "f", "A", "f", "A", "f", "A"], "16"
    if "drag" in n or fam == "drag":
        return ["G", "G", "A", "G", "G", "A", "G", "G", "A", "G", "G", "A"], "16"
    if "triplet" in n:
        return ["A", "G", "G", "A", "G", "G", "A", "G", "G", "A", "G", "G"], "triplet"
    if "roll" in n or fam == "roll":
        return ["A", "G", "A", "G", "A", "G", "A", "G"], "16"

    return ["A", "G", "A", "G", "A", "G", "A", "G"], "16"


def _token_to_velocity(token: str) -> int:
    if token == "A":
        return 108
    if token == "G":
        return 32
    if token == "S":
        return 84
    if token == "f":
        return 28
    return 80


def _write_rudiment_midi(path: Path, *, bpm: float, steps: List[str], grid: str) -> None:
    try:
        import mido
    except Exception as exc:
        raise RuntimeError("mido is required to build rudiment MIDI assets") from exc

    ppq = 480
    mid = mido.MidiFile(type=1)
    mid.ticks_per_beat = ppq
    track = mido.MidiTrack()
    mid.tracks.append(track)

    tempo_us = mido.bpm2tempo(bpm)
    track.append(mido.MetaMessage("set_tempo", tempo=tempo_us, time=0))

    # 1 bar at 4/4
    if grid == "triplet":
        total_steps = 12
        ticks_per_step = int(ppq / 3)  # 8th-triplet grid
    else:
        total_steps = 16
        ticks_per_step = int(ppq / 4)  # 16th grid

    # We'll place the provided steps starting at step 0
    events: List[Tuple[int, int]] = []

    for i, tok in enumerate(steps[:total_steps]):
        tick = i * ticks_per_step
        # flam grace: add a grace note 1/64 before the main hit
        if tok == "f":
            grace_tick = max(0, tick - max(1, ticks_per_step // 4))
            events.append((grace_tick, _token_to_velocity(tok)))
            # next token (if any) becomes the main hit; if not, add a main hit too
            main_vel = 104
            events.append((tick, main_vel))
        else:
            events.append((tick, _token_to_velocity(tok)))

    events.sort(key=lambda x: x[0])

    last_tick = 0
    for tick, vel in events:
        delta = max(0, tick - last_tick)
        track.append(mido.Message("note_on", channel=9, note=38, velocity=int(vel), time=delta))
        track.append(mido.Message("note_off", channel=9, note=38, velocity=0, time=max(1, ticks_per_step // 4)))
        last_tick = tick + max(1, ticks_per_step // 4)

    track.append(mido.MetaMessage("end_of_track", time=0))
    path.parent.mkdir(parents=True, exist_ok=True)
    mid.save(str(path))


def build_midi_assets(*, db_path: Path, out_dir: Path, bpm: float = 120.0, limit: Optional[int] = None) -> int:
    conn = _db_connect(db_path)
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT id, rudiment_name, rudiment_family
            FROM rudiment_fragments
            ORDER BY id
            """
        )
        rows = cur.fetchall()
        if limit:
            rows = rows[:limit]

        built = 0
        for r in rows:
            rid = int(r["id"])
            name = r["rudiment_name"]
            family = r["rudiment_family"]

            steps, grid = _get_rudiment_pattern(family, name)
            midi_path = out_dir / f"{_slugify(name)}.mid"

            try:
                _write_rudiment_midi(midi_path, bpm=bpm, steps=steps, grid=grid)
            except Exception as exc:
                logger.warning("Failed building MIDI for %s: %s", name, exc)
                continue

            cur.execute(
                """
                UPDATE rudiment_fragments
                SET midi_path = ?, midi_generated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (str(midi_path), rid),
            )
            built += 1

            if built % 50 == 0:
                conn.commit()
                logger.info("Built %s rudiment MIDI assets...", built)

        conn.commit()
        return built
    finally:
        conn.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate MIDI assets for rudiment_fragments and store paths in DB")
    parser.add_argument("--db", type=Path, default=DEFAULT_DB_PATH)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--bpm", type=float, default=120.0)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--log-level", default="INFO")
    args = parser.parse_args()

    logging.basicConfig(level=getattr(logging, str(args.log_level).upper(), logging.INFO))
    built = build_midi_assets(db_path=args.db, out_dir=args.out_dir, bpm=float(args.bpm), limit=args.limit)
    logger.info("Done. Built %s MIDI assets into %s", built, args.out_dir)


if __name__ == "__main__":
    main()

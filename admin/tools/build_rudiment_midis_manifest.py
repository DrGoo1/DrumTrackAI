from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import List


def _tags_from_name(stem: str) -> List[str]:
    s = stem.lower()
    tags = {"rudiment"}
    if "paradiddle" in s:
        tags.add("paradiddle")
    if "flam" in s:
        tags.add("flam")
    if "drag" in s or "ruff" in s:
        tags.add("drag")
    if "ratamacue" in s:
        tags.add("ratamacue")
    if "roll" in s:
        tags.add("roll")
    if "tap" in s:
        tags.add("tap")
    return sorted(tags)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--midis-dir",
        default=str(Path("admin") / "data" / "rudiment_midis"),
    )
    ap.add_argument(
        "--out",
        default=str(Path("Drum_Education") / "extracted" / "RUDIMENTS_manifest.jsonl"),
    )
    args = ap.parse_args()

    midis_dir = Path(args.midis_dir)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)

    if not midis_dir.exists():
        raise FileNotFoundError(str(midis_dir))

    midi_files = sorted(list(midis_dir.rglob("*.mid")) + list(midis_dir.rglob("*.midi")))

    written = 0
    with out.open("w", encoding="utf-8") as f:
        for i, p in enumerate(midi_files, 1):
            stem = p.stem
            entry = {
                "id": f"rudiment_midi:{stem}",
                "source": "rudiments",
                "name": stem.replace("_", " ").title(),
                "midi_path": str(p),
                "tags": _tags_from_name(stem),
            }
            f.write(json.dumps(entry, ensure_ascii=False))
            f.write("\n")
            written += 1

    print(f"Wrote {written} entries")
    print(out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

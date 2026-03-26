#!/usr/bin/env python3
"""Rudiment fragments (MP3 assets) -> Admin LLM JSONL.

Emits multitask records using the same {task,input,output,meta} structure.
"""

import argparse
import json
import random
import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Optional


def _db_connect(db_path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    return conn


def export_rudiment_fragments_to_jsonl(
    *,
    db_path: Path,
    output_file: Path,
    seed: int,
    num_examples: int,
) -> None:
    conn = _db_connect(db_path)
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT id, rudiment_name, rudiment_family, audio_path
            FROM rudiment_fragments
            ORDER BY id
            """
        )
        rows = cur.fetchall()
        if not rows:
            raise RuntimeError("No rudiment_fragments rows found. Run ingestion first.")

        rng = random.Random(seed)
        output_file.parent.mkdir(parents=True, exist_ok=True)

        with output_file.open("w", encoding="utf-8") as f_out:
            for i in range(num_examples):
                row = rng.choice(rows)
                family = row["rudiment_family"] or "other"
                name = row["rudiment_name"]

                # Task: suggest_rudiment
                suggest = {
                    "task": "suggest_rudiment",
                    "input": {
                        "context": rng.choice([
                            "fill", "transition", "snare_lead", "ghost_note_texture", "build_up"
                        ]),
                        "style_group": rng.choice(["rock", "funk", "jazz", "metal", "blues", "pop", "latin"]),
                        "rudiment_family": rng.choice([family, family, "roll", "flam", "drag", "paradiddle"]),
                        "intensity": round(rng.uniform(0.2, 0.95), 2),
                    },
                    "output": {
                        "rudiment_name": name,
                        "rudiment_family": family,
                        "asset": {
                            "type": "audio",
                            "format": "mp3",
                            "path": row["audio_path"],
                        },
                    },
                    "meta": {
                        "source": "snare_rudiments",
                        "db": str(db_path),
                        "row_id": int(row["id"]),
                        "example_index": i,
                    },
                }
                f_out.write(json.dumps(suggest) + "\n")

                # Task: identify_rudiment (name recognition from filename or context)
                identify = {
                    "task": "identify_rudiment",
                    "input": {
                        "audio_path": row["audio_path"],
                        "hint": rng.choice([
                            "from_snare_rudiments_library",
                            "mp3_demo",
                            "practice_track"
                        ]),
                    },
                    "output": {
                        "rudiment_name": name,
                        "rudiment_family": family,
                    },
                    "meta": {
                        "source": "snare_rudiments",
                        "db": str(db_path),
                        "row_id": int(row["id"]),
                        "example_index": i,
                    },
                }
                f_out.write(json.dumps(identify) + "\n")

    finally:
        conn.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Export rudiment_fragments to Admin LLM JSONL")
    parser.add_argument("--db", type=Path, default=Path("admin/data/drum_training.db"))
    parser.add_argument(
        "--out",
        type=Path,
        default=Path("llm_training_project/training_datasets/rudiment_fragments_train.jsonl"),
    )
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--num-examples", type=int, default=5000)
    args = parser.parse_args()

    export_rudiment_fragments_to_jsonl(
        db_path=args.db,
        output_file=args.out,
        seed=int(args.seed),
        num_examples=int(args.num_examples),
    )

    print(f"Wrote: {args.out}")


if __name__ == "__main__":
    main()

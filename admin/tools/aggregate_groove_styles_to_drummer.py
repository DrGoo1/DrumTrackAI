"""Aggregate groove_style_vectors into a simple drummer style summary.

This helper lets you specify a public drummer name and a list of groove
archetype_ids, and computes averaged timing, density, and dynamics metrics
from groove_style_vectors for those archetypes.

It does NOT write into any existing tables yet; it just prints the
aggregated style so you can decide how to map it into DrummerStyleVector /
DrummerGenerationBrain.
"""

import argparse
import json
import sqlite3
from pathlib import Path
from typing import List

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DB_PATH = PROJECT_ROOT / "admin" / "drumtrackai.db"


METRIC_COLUMNS = [
    "bpm",
    "backbeat_late_ms",
    "hat_open_ratio",
    "ghost_snare_ratio",
    "kick_density",
    "snare_density",
    "cymbal_density",
    "dynamics_spread",
    "ride_density",
    "ride_mean_velocity",
    "ride_bell_ratio",
]


def fetch_vectors(conn: sqlite3.Connection, archetype_ids: List[str]):
    cur = conn.cursor()
    placeholders = ",".join(["?"] * len(archetype_ids))
    cur.execute(
        f"""
        SELECT archetype_id,
               bpm,
               backbeat_late_ms,
               hat_open_ratio,
               ghost_snare_ratio,
               kick_density,
               snare_density,
               cymbal_density,
               dynamics_spread
        FROM groove_style_vectors
        WHERE archetype_id IN ({placeholders})
        ORDER BY archetype_id
        """,
        archetype_ids,
    )
    return cur.fetchall()


def aggregate_metrics(rows):
    if not rows:
        return None

    sums = {col: 0.0 for col in METRIC_COLUMNS}
    counts = {col: 0 for col in METRIC_COLUMNS}

    for _archetype_id, *metric_vals in rows:
        for col, val in zip(METRIC_COLUMNS, metric_vals):
            if val is None:
                continue
            sums[col] += float(val)
            counts[col] += 1

    means = {}
    for col in METRIC_COLUMNS:
        if counts[col] > 0:
            means[col] = sums[col] / counts[col]
        else:
            means[col] = None
    return means


def main():
    parser = argparse.ArgumentParser(
        description="Aggregate groove_style_vectors into a drummer style summary.",
    )
    parser.add_argument(
        "drummer_name",
        type=str,
        help="Public drummer persona name (for labeling only)",
    )
    parser.add_argument(
        "archetypes",
        nargs="+",
        help="One or more groove archetype_ids to aggregate (e.g. rosanna fool_in_the_rain)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print only a single JSON object with aggregated style (for programmatic use)",
    )
    args = parser.parse_args()

    conn = sqlite3.connect(DB_PATH)
    try:
        rows = fetch_vectors(conn, args.archetypes)
    finally:
        conn.close()

    if not rows:
        print("No groove_style_vectors found for the given archetype_ids.")
        return

    agg = aggregate_metrics(rows)
    if agg is None:
        print("No numeric metrics to aggregate.")
        return

    payload = {
        "drummer_name": args.drummer_name,
        "archetypes": args.archetypes,
        "aggregated_style": agg,
    }

    if args.json:
        print(json.dumps(payload, indent=2))
        return

    # Human-readable output
    print(f"Using DB: {DB_PATH}")
    print(f"Drummer persona: {args.drummer_name}")
    print(f"Archetypes: {', '.join(args.archetypes)}")

    print("\nPer-groove metrics:")
    for archetype_id, *metric_vals in rows:
        print(f"  == {archetype_id} ==")
        for col, val in zip(METRIC_COLUMNS, metric_vals):
            print(f"    {col:18s}: {val}")
        print()

    print("Aggregated drummer style (simple mean over grooves):")
    for col in METRIC_COLUMNS:
        print(f"  {col:18s}: {agg[col]}")


if __name__ == "__main__":
    main()

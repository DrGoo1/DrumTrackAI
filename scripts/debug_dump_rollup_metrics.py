#!/usr/bin/env python
"""Inspect Phase 4/5 drummer metrics to understand stored units."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Dict, Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from admin.services.central_database_service import CentralDatabaseService  # noqa: E402


def _safe_sample_shares(shares: Dict[str, Any], limit: int = 5) -> Dict[str, Any]:
    if not shares:
        return {}
    out: Dict[str, Any] = {}
    for key in list(shares.keys())[:limit]:
        out[key] = shares[key]
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description="Inspect stored drummer metrics for scale/units")
    parser.add_argument(
        "drummers",
        nargs="*",
        default=["john_bonham", "ringo_starr", "clyde_stubblefield"],
        help="Drummer slugs to inspect",
    )
    parser.add_argument("--limit", type=int, default=3, help="Max analyses to sample per drummer")
    args = parser.parse_args()

    svc = CentralDatabaseService.get_instance()
    svc.initialize()

    conn = svc._get_connection()  # pylint: disable=protected-access
    cursor = conn.cursor()

    for slug in args.drummers:
        print(f"=== {slug} ===")
        drummer_fk = svc._get_drummer_fk_by_slug(cursor=cursor, drummer_slug=slug)  # pylint: disable=protected-access
        if drummer_fk is None:
            print("  ! drummer slug not found")
            print()
            continue

        rollup = svc.compute_drummer_profile_rollup(drummer_fk=int(drummer_fk))
        shares_preview = _safe_sample_shares(rollup.get("instrument_shares") or {})
        print("  rollup velocity_mean:", rollup.get("velocity_mean"))
        print("  rollup velocity_std:", rollup.get("velocity_std"))
        print("  rollup timing_std_ms:", rollup.get("timing_std_ms"))
        print("  rollup fills_per_min:", rollup.get("fills_per_min"))
        print("  instrument share preview:", json.dumps(shares_preview, indent=2))

        cursor.execute(
            """
            SELECT analysis_id, dynamics_json, groove_micro_timing_variance,
                   groove_pocket_tightness, humanness_score
            FROM song_performance_analysis
            WHERE drummer_id = ?
            ORDER BY created_at DESC
            LIMIT ?
            """,
            (drummer_fk, int(args.limit)),
        )
        rows = cursor.fetchall() or []
        if not rows:
            print("  (no analyses found)")
            print()
            continue

        for analysis_id, dynamics_json, timing_var, pocket, humanness in rows:
            print(f"  analysis {analysis_id}:")
            print(f"    groove_micro_timing_variance: {timing_var}")
            print(f"    groove_pocket_tightness: {pocket}")
            print(f"    humanness_score: {humanness}")
            dyn: Dict[str, Any] = {}
            if isinstance(dynamics_json, str) and dynamics_json.strip():
                try:
                    dyn = json.loads(dynamics_json)
                except json.JSONDecodeError:
                    pass
            print("    dynamics_json:", json.dumps(dyn, indent=6))
        print()


if __name__ == "__main__":
    main()

from __future__ import annotations

import argparse
from pathlib import Path

from backend.drummerbrain.sentient_profile import build_sentient_profile, export_sentient_profile_json


def main() -> int:
    ap = argparse.ArgumentParser(description="Build a sentient drummer profile JSON from the Admin SQLite DB")
    ap.add_argument("--db", dest="db_path", default=None, help="Path to admin/drumtrackai.db (default: repo/admin/drumtrackai.db)")
    ap.add_argument("--drummer", dest="drummer_slug", required=True, help="Drummer slug (drummers.drummer_id)")
    ap.add_argument(
        "--out",
        dest="out_path",
        default=None,
        help="Output JSON path (default: database/sentient_profiles/<drummer>/sentient_profile.json)",
    )

    args = ap.parse_args()

    repo_root = Path(__file__).resolve().parents[2]
    if args.out_path:
        out_path = Path(args.out_path)
    else:
        out_path = repo_root / "database" / "sentient_profiles" / args.drummer_slug / "sentient_profile.json"

    profile = build_sentient_profile(admin_db_path=args.db_path, drummer_slug=args.drummer_slug)
    export_sentient_profile_json(profile=profile, out_path=str(out_path))
    print(str(out_path))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

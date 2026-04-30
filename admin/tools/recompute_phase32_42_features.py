from __future__ import annotations

import argparse
import sys
from pathlib import Path

repo_root = Path(__file__).resolve().parents[2]
repo_root_str = str(repo_root)
if repo_root_str not in sys.path:
    sys.path.insert(0, repo_root_str)

from admin.services.central_database_service import CentralDatabaseService


def _banner() -> None:
    print("\n" + "=" * 78)
    print("RUN THIS SCRIPT FROM POWERSHELL (PS ...>), NOT FROM PYTHON REPL (>>>).")
    print("If you see >>>, type: exit()  then re-run from PS with: python admin\\tools\\...")
    print("=" * 78 + "\n")


def main() -> int:
    _banner()

    ap = argparse.ArgumentParser(
        description="Recompute Phase 32-42 (currently Phase 37-42) derived features for an ingested drummer and store them into song_performance_analysis."
    )
    ap.add_argument("--drummer", dest="drummer_slug", required=True, help="Drummer slug (drummers.drummer_id)")
    args = ap.parse_args()

    db = CentralDatabaseService.get_instance()
    if not getattr(db, "_initialized", False):
        db.initialize()

    res = db.run_phase32_42_features_for_drummer(drummer_slug=str(args.drummer_slug))
    analyses = int((res or {}).get("analyses") or 0)
    updated = int((res or {}).get("updated") or 0)
    print(f"Processed {analyses} analysis(es). Updated {updated} row(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

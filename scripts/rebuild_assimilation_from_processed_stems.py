import argparse
import os
import sys
import json
import time
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Callable

# Ensure repo root on PYTHONPATH
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from admin.services.central_database_service import CentralDatabaseService  # noqa: E402


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def log(level: str, message: str) -> None:
    print(f"[{_now()}] [{level}] {message}", flush=True)


def _result_failure_reason(step_name: str, result: Any) -> str:
    if not isinstance(result, dict):
        return ""
    if result.get("error"):
        return str(result.get("error"))
    analysis_errors = result.get("analysis_errors")
    if isinstance(analysis_errors, int) and analysis_errors > 0:
        return f"{analysis_errors} analysis errors"
    if "Phase 6" in step_name and result.get("preset_saved") is False:
        return "preset_saved=False"
    return ""


def run_step(step_name: str, action: Callable[[], Any]) -> Dict[str, Any]:
    started = time.perf_counter()
    log("STEP", f"{step_name} started")
    try:
        result = action()
        elapsed = round(time.perf_counter() - started, 3)
        failure_reason = _result_failure_reason(step_name, result)
        if failure_reason:
            log("ERROR", f"{step_name} reported failure in {elapsed}s: {failure_reason}")
            return {"ok": False, "duration_sec": elapsed, "error": failure_reason, "result": result}
        log("OK", f"{step_name} completed in {elapsed}s")
        return {"ok": True, "duration_sec": elapsed, "result": result}
    except Exception as exc:
        elapsed = round(time.perf_counter() - started, 3)
        log("ERROR", f"{step_name} failed in {elapsed}s: {exc}")
        return {"ok": False, "duration_sec": elapsed, "error": str(exc)}


def find_song_folders(base_dir: Path) -> Dict[str, List[Path]]:
    """Scan base_dir for processed-stems structure and return {slug: [song_folder_paths...]}

    Expected layout:
      base_dir/<drummer_slug>/<song_folder>/drum_analysis.json
    """
    result: Dict[str, List[Path]] = {}
    if not base_dir.is_dir():
        return result

    for slug_dir in sorted(p for p in base_dir.iterdir() if p.is_dir()):
        song_dirs: List[Path] = []
        try:
            for song_dir in sorted(p for p in slug_dir.iterdir() if p.is_dir()):
                if (song_dir / "drum_analysis.json").exists():
                    song_dirs.append(song_dir)
        except Exception:
            pass
        if song_dirs:
            result[slug_dir.name] = song_dirs
    return result


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Ingest processed stems and rebuild assimilation phases into the main DB")
    p.add_argument("--base-dir", required=True, help="Base folder containing processed_stems/<slug>/<song>/drum_analysis.json")
    p.add_argument("--drummers", default="", help="Comma-separated slugs to process (default: all slugs found under base-dir)")
    p.add_argument("--db-backend", default=os.getenv("DB_BACKEND", "postgres"), help="DB backend (postgres/sqlite)")
    p.add_argument("--database-url", default=os.getenv("DATABASE_URL", ""), help="DATABASE_URL for Postgres; if provided will override env")
    p.add_argument("--max-events-per-stem", type=int, default=5000, help="Max events per stem during Phase 2")
    p.add_argument("--compute-hashes", action="store_true", help="Compute SHA256 on artifacts during ingest (slower)")
    p.add_argument("--hash-max-bytes", type=int, default=0, help="When computing hashes, limit bytes read per file (0=all)")
    p.add_argument("--summary-json", default="", help="Optional path to write machine-readable summary JSON")
    return p.parse_args()


def main() -> None:
    args = parse_args()

    # Configure DB env for CentralDatabaseService.initialize()
    os.environ["DB_BACKEND"] = str(args.db_backend or "postgres").strip()
    if args.database_url:
        os.environ["DATABASE_URL"] = str(args.database_url).strip()
    # Avoid long CREATE INDEX timeouts during bulk rebuilds unless explicitly enabled
    if not os.environ.get("DB_SKIP_INDEXES"):
        os.environ["DB_SKIP_INDEXES"] = "1"

    base_dir = Path(args.base_dir).expanduser().resolve()
    if not base_dir.exists() or not base_dir.is_dir():
        log("ERROR", f"Base dir not found or not a directory: {base_dir}")
        sys.exit(2)

    # Discover song folders
    discovered = find_song_folders(base_dir)
    if not discovered:
        log("ERROR", f"No song folders with drum_analysis.json found under: {base_dir}")
        sys.exit(3)

    total_songs = sum(len(v) for v in discovered.values())
    log("INFO", f"Discovered {len(discovered)} slugs and {total_songs} song folders under {base_dir}")

    target_slugs: List[str]
    if args.drummers.strip():
        target_slugs = [s.strip() for s in args.drummers.split(",") if s.strip()]
    else:
        target_slugs = sorted(discovered.keys())

    # Initialize DB service
    if target_slugs:
        log("INFO", "Target slugs: " + ", ".join(target_slugs))
    log("INFO", f"Initializing database (backend={os.environ.get('DB_BACKEND', '')})")
    db = CentralDatabaseService.get_instance()
    if not db.initialize():
        log("ERROR", "Failed to initialize database; check DB_BACKEND/DATABASE_URL")
        sys.exit(4)
    log("OK", "Database initialized")

    total_ingested = 0
    per_slug_results: Dict[str, Dict[str, Any]] = {}

    for slug in target_slugs:
        slug_started = time.perf_counter()
        song_dirs = discovered.get(slug, [])
        if not song_dirs:
            # Allow processing even if none discovered (maybe user provided a slug not present on disk)
            log("WARN", f"[{slug}] No song folders found on disk")
            per_slug_results[slug] = {"ingested": 0, "ingest_total": 0, "phases": {}, "duration_sec": 0}
            continue

        ingested = 0
        log("INFO", f"[{slug}] Starting ingest for {len(song_dirs)} song folders")
        for sd in song_dirs:
            log("STEP", f"[{slug}] Ingesting song folder: {sd}")
            aid = None
            try:
                aid = db.ingest_processed_stems_song_folder(
                    drummer_id=slug,
                    song_folder=str(sd),
                    compute_hashes=bool(args.compute_hashes),
                    hash_max_bytes=int(args.hash_max_bytes or 0),
                    analysis_version="baseline_v1",
                )
            except Exception as exc:
                log("ERROR", f"[{slug}] Ingest exception for {sd}: {exc}")
            if aid:
                ingested += 1
                log("OK", f"[{slug}] Ingested ({ingested}/{len(song_dirs)}): {sd.name}")
            else:
                log("WARN", f"[{slug}] Ingest failed ({ingested}/{len(song_dirs)}): {sd.name}")
        total_ingested += ingested

        # Run phases 2 → 6
        p2 = run_step(
            f"[{slug}] Phase 2 (hit events)",
            lambda: db.run_phase2_hit_event_extraction_for_drummer(
                drummer_slug=slug,
                max_events_per_stem=int(args.max_events_per_stem),
            ),
        )
        p3 = run_step(f"[{slug}] Phase 3 (fills/techniques)", lambda: db.run_phase3_fills_and_techniques_for_drummer(drummer_slug=slug))
        p4 = run_step(
            f"[{slug}] Phase 4 (microtiming/dynamics)",
            lambda: db.run_phase4_microtiming_and_dynamics_for_drummer(drummer_slug=slug),
        )
        p5 = run_step(f"[{slug}] Phase 5 (profile rollup)", lambda: db.run_phase5_profile_rollup_for_drummer(drummer_slug=slug))
        p6 = run_step(
            f"[{slug}] Phase 6 (persona/preset export)",
            lambda: db.run_phase6_persona_preset_export_for_drummer(drummer_slug=slug),
        )
        p7 = run_step(
            f"[{slug}] Phase 7 (assimilation profiles + embeddings)",
            lambda: db.run_phase7_assimilation_profiles_for_drummer(drummer_slug=slug),
        )
        # Phase 32–42: compute derived features for downstream sentient runtime
        p3242 = run_step(
            f"[{slug}] Phase 32–42 (derived features)",
            lambda: db.run_phase32_42_features_for_drummer(drummer_slug=slug),
        )

        slug_elapsed = round(time.perf_counter() - slug_started, 3)

        per_slug_results[slug] = {
            "ingested": ingested,
            "ingest_total": len(song_dirs),
            "phases": {"p2": p2, "p3": p3, "p4": p4, "p5": p5, "p6": p6, "p7": p7, "p32_42": p3242},
            "duration_sec": slug_elapsed,
        }

        log("INFO", f"=== {slug} summary ===")
        log("INFO", f"[{slug}] Ingest complete: {ingested}/{len(song_dirs)}")
        for phase_name, phase_result in per_slug_results[slug]["phases"].items():
            state = "OK" if phase_result.get("ok") else "FAILED"
            dur = phase_result.get("duration_sec")
            log("INFO", f"[{slug}] {phase_name}: {state} ({dur}s)")
        log("INFO", f"[{slug}] Total duration: {slug_elapsed}s")

    failed_slugs = [
        slug
        for slug, data in per_slug_results.items()
        if any(not phase_data.get("ok", False) for phase_data in data.get("phases", {}).values())
    ]
    log("INFO", f"Done. Total songs ingested: {total_ingested}")
    log("INFO", f"Processed slugs: {len(per_slug_results)}")
    log("WARN", f"Slugs with failed phases: {', '.join(failed_slugs)}" if failed_slugs else "No phase failures detected")

    if args.summary_json:
        summary_path = Path(args.summary_json).expanduser().resolve()
        payload = {
            "generated_at": _now(),
            "db_backend": os.environ.get("DB_BACKEND"),
            "base_dir": str(base_dir),
            "total_ingested": total_ingested,
            "processed_slugs": len(per_slug_results),
            "failed_slugs": failed_slugs,
            "results": per_slug_results,
        }
        summary_path.parent.mkdir(parents=True, exist_ok=True)
        summary_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        log("INFO", f"Wrote summary JSON: {summary_path}")


if __name__ == "__main__":
    main()

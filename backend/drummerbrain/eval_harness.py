import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


@dataclass(frozen=True)
class EvalCase:
    name: str
    tempos: List[float]
    time_signature: Tuple[int, int]
    measure_count: int


def _resolve_db_path(explicit: Optional[str] = None) -> Path:
    if explicit:
        return Path(explicit)
    p = os.getenv("DRUMMERBRAIN_DB_PATH")
    if p:
        return Path(p)
    return Path(__file__).resolve().parents[2] / "admin" / "data" / "drummerbrain_clips.db"


def _resolve_cases_path(explicit: Optional[str] = None) -> Path:
    if explicit:
        return Path(explicit)
    p = os.getenv("DRUMMERBRAIN_EVAL_CASES_PATH")
    if p:
        return Path(p)
    return Path(__file__).resolve().parent / "eval_cases.json"


def _load_cases(path: Path) -> List[EvalCase]:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        raw = None

    out: List[EvalCase] = []
    if isinstance(raw, list):
        for row in raw:
            if not isinstance(row, dict):
                continue
            name = str(row.get("name") or "").strip()
            bpm = row.get("bpm")
            bars = row.get("bars")
            ts = row.get("time_signature")
            if not name:
                continue
            try:
                bpm_f = float(bpm)
                bars_i = int(bars)
                if not (isinstance(ts, list) and len(ts) == 2):
                    continue
                nn = int(ts[0])
                dd = int(ts[1])
                if bpm_f <= 0 or bars_i <= 0 or nn <= 0 or dd <= 0:
                    continue
            except Exception:
                continue
            out.append(EvalCase(name=name, tempos=[float(bpm_f)] * int(bars_i), time_signature=(int(nn), int(dd)), measure_count=int(bars_i)))
    return out


def _build_config_payload(case: EvalCase) -> Dict[str, Any]:
    bars = max(1, int(case.measure_count))
    return {
        "sectionId": f"eval_{case.name}",
        "startMeasure": 0,
        "endMeasure": bars - 1,
        "tempos": list(case.tempos),
        "timeSignature": [int(case.time_signature[0]), int(case.time_signature[1])],
        "style": "rock",
        "drummer": "studio_rock",
        "intensity": 0.7,
        "variation": 0.5,
        "generationMode": "full_ai",
        "humanize": False,
        "fillLocations": [],
        "fillType": "auto",
        "drummerBrainEnabled": True,
        "buildScope": "selected_section",
    }


def run_suite(*, db_path: Optional[str] = None, cases_path: Optional[str] = None, limit_cases: Optional[int] = None) -> Dict[str, Any]:
    import drum_generation_api

    import sqlite3
    import tempfile

    from backend.drummerbrain import db as dtkdb

    resolved = _resolve_db_path(db_path)

    # Ensure the harness can validate written-reference (tempo-adaptive) selection even when the
    # primary DB is missing. We seed a tiny deterministic DB in a temp dir in that case.
    seeded_temp_db: Optional[Path] = None
    if not resolved.exists():
        td = tempfile.TemporaryDirectory()
        seeded_temp_db = Path(td.name) / "drummerbrain_eval_seed.db"
        conn = dtkdb.connect(seeded_temp_db)
        try:
            dtkdb.ensure_schema(conn)
            dtkdb.upsert_dataset(
                conn,
                dataset_id="written_eval",
                label="Written Eval",
                root_path=str(Path(td.name)),
                dataset_type="written_reference",
            )
            asset_id = "written_eval:seed"
            dtkdb.upsert_audio_asset(
                conn,
                asset_id=asset_id,
                dataset_id="written_eval",
                song_key="seed",
                variant="written",
                source_path="eval_seed",
                content_sha256="0" * 64,
                size_bytes=None,
            )
            # 1 bar @ 4/4, subdiv=4: kick on 1, snare on 2/4, hat on 8ths.
            events = [
                {"beat_index": 0, "sub": 0, "subdiv": 4, "lane": "kick", "strength": 0.9},
                {"beat_index": 1, "sub": 0, "subdiv": 4, "lane": "snare_center", "strength": 0.8},
                {"beat_index": 2, "sub": 0, "subdiv": 4, "lane": "kick", "strength": 0.85},
                {"beat_index": 3, "sub": 0, "subdiv": 4, "lane": "snare_center", "strength": 0.8},
            ]
            for bi in range(4):
                events.append({"beat_index": bi, "sub": 0, "subdiv": 2, "lane": "hihat_closed", "strength": 0.6})
                events.append({"beat_index": bi, "sub": 1, "subdiv": 2, "lane": "hihat_closed", "strength": 0.6})

            feats = {"subdiv": 4, "tempo_adaptive": True, "duration_beats": 4.0}
            dtkdb.upsert_transcription_artifact(
                conn,
                asset_id=asset_id,
                transcription_version="written_eval_seed_v1",
                events=events,
                features=feats,
                confidence=0.9,
                provenance={"source_ref": "eval_seed", "clip_id": "seed"},
            )
        finally:
            conn.close()
        resolved = seeded_temp_db
        os.environ["DRUMMERBRAIN_DB_PATH"] = str(resolved)
        # Hold onto the temp dir object so it doesn't get GC'ed early.
        os.environ["DRUMMERBRAIN_EVAL__TEMP_DIR"] = td.name
    else:
        os.environ["DRUMMERBRAIN_DB_PATH"] = str(resolved)

    resolved_cases_path = _resolve_cases_path(cases_path)
    cases = _load_cases(resolved_cases_path)
    if not cases:
        cases = [
            EvalCase(name="bpm70_2bar_44", tempos=[70.0] * 2, time_signature=(4, 4), measure_count=2),
            EvalCase(name="bpm90_4bar_44", tempos=[90.0] * 4, time_signature=(4, 4), measure_count=4),
            EvalCase(name="bpm100_8bar_44", tempos=[100.0] * 8, time_signature=(4, 4), measure_count=8),
            EvalCase(name="bpm120_4bar_44", tempos=[120.0] * 4, time_signature=(4, 4), measure_count=4),
            EvalCase(name="bpm140_8bar_44", tempos=[140.0] * 8, time_signature=(4, 4), measure_count=8),
            EvalCase(name="bpm160_1bar_44", tempos=[160.0], time_signature=(4, 4), measure_count=1),
            EvalCase(name="bpm120_4bar_34", tempos=[120.0] * 4, time_signature=(3, 4), measure_count=4),
            EvalCase(name="bpm120_4bar_68", tempos=[120.0] * 4, time_signature=(6, 8), measure_count=4),
        ]
    if limit_cases is not None:
        cases = cases[: max(0, int(limit_cases))]

    results: List[Dict[str, Any]] = []
    used = 0
    fallback = 0
    dataset_stats: Dict[str, Dict[str, Any]] = {}
    dataset_type_stats: Dict[str, Dict[str, Any]] = {}
    failure_reasons: Dict[str, int] = {}

    dataset_id_to_type: Dict[str, str] = {}
    try:
        if resolved.exists():
            conn = sqlite3.connect(str(resolved))
            try:
                cur = conn.cursor()
                cur.execute("SELECT dataset_id, dataset_type FROM datasets")
                for did, dtyp in cur.fetchall() or []:
                    dataset_id_to_type[str(did)] = str(dtyp)
            finally:
                conn.close()
    except Exception:
        dataset_id_to_type = {}

    for c in cases:
        cfg = drum_generation_api.DrumGenerationConfig(_build_config_payload(c))
        events, prov = drum_generation_api._try_build_internal_events_from_drummerbrain(cfg)
        prov = prov if isinstance(prov, dict) else {"used": False, "reason": "invalid_provenance"}
        dsid = str(prov.get("dataset_id") or "")
        dtype = dataset_id_to_type.get(dsid, "") if dsid else ""
        row = {
            "case": c.name,
            "used": bool(events) and bool(prov.get("used")),
            "reason": prov.get("reason"),
            "asset_id": prov.get("asset_id"),
            "dataset_id": prov.get("dataset_id"),
            "dataset_type": dtype,
            "policy_version": prov.get("policy_version"),
            "candidate_count": prov.get("candidate_count"),
            "best_score": prov.get("best_score"),
            "target_bpm": prov.get("target_bpm"),
            "score_terms": prov.get("score_terms"),
        }
        if row["used"]:
            used += 1
        else:
            fallback += 1
            r = str(row.get("reason") or "")
            failure_reasons[r] = int(failure_reasons.get(r, 0)) + 1

        dsid = str(row.get("dataset_id") or "")
        if dsid:
            st = dataset_stats.get(dsid)
            if not isinstance(st, dict):
                st = {"used": 0, "fallback": 0, "cases": 0}
                dataset_stats[dsid] = st
            st["cases"] = int(st.get("cases", 0)) + 1
            if row["used"]:
                st["used"] = int(st.get("used", 0)) + 1
            else:
                st["fallback"] = int(st.get("fallback", 0)) + 1

        dtype = str(row.get("dataset_type") or "")
        if dtype:
            st2 = dataset_type_stats.get(dtype)
            if not isinstance(st2, dict):
                st2 = {"used": 0, "fallback": 0, "cases": 0}
                dataset_type_stats[dtype] = st2
            st2["cases"] = int(st2.get("cases", 0)) + 1
            if row["used"]:
                st2["used"] = int(st2.get("used", 0)) + 1
            else:
                st2["fallback"] = int(st2.get("fallback", 0)) + 1
        results.append(row)

    # Threshold checks (configurable via env). These are for evaluation reporting only.
    min_used_fraction = None
    try:
        env_min = os.getenv("DRUMMERBRAIN_EVAL_MIN_USED_FRACTION")
        if env_min is not None and str(env_min).strip() != "":
            min_used_fraction = float(env_min)
    except Exception:
        min_used_fraction = None

    allowed_failure_reasons = None
    try:
        afr = os.getenv("DRUMMERBRAIN_EVAL_ALLOWED_FAILURE_REASONS")
        if afr is not None and str(afr).strip() != "":
            allowed_failure_reasons = [s.strip() for s in str(afr).split(",") if s.strip()]
    except Exception:
        allowed_failure_reasons = None

    used_fraction = float(used) / float(max(1, len(cases)))
    checks: Dict[str, Any] = {"used_fraction": used_fraction}
    if min_used_fraction is not None:
        checks["min_used_fraction"] = float(min_used_fraction)
        checks["min_used_fraction_ok"] = bool(used_fraction >= float(min_used_fraction))
    if allowed_failure_reasons is not None:
        checks["allowed_failure_reasons"] = list(allowed_failure_reasons)
        bad = []
        for rr, cnt in sorted(failure_reasons.items(), key=lambda kv: (-int(kv[1]), kv[0])):
            if rr and rr not in allowed_failure_reasons:
                bad.append({"reason": rr, "count": int(cnt)})
        checks["allowed_failure_reasons_ok"] = bool(len(bad) == 0)
        checks["disallowed_failure_reasons"] = bad

    return {
        "ok": True,
        "db_path": str(resolved),
        "cases_path": str(resolved_cases_path),
        "case_count": int(len(cases)),
        "used_count": int(used),
        "fallback_count": int(fallback),
        "used_fraction": used_fraction,
        "dataset_stats": dataset_stats,
        "dataset_type_stats": dataset_type_stats,
        "failure_reasons": failure_reasons,
        "checks": checks,
        "results": results,
    }


def write_report(*, out_path: str, report: Dict[str, Any]) -> None:
    p = Path(out_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")


def compare_to_baseline(*, report: Dict[str, Any], baseline: Dict[str, Any]) -> Dict[str, Any]:
    """Compare current report to a baseline report.

    Deterministic comparison:
    - used_fraction drop tolerance
    - per-case drift counts (used/reason/asset_id)
    """
    tol = 0.0
    try:
        tol = float(os.getenv("DRUMMERBRAIN_EVAL_BASELINE_TOLERANCE", "0") or 0)
    except Exception:
        tol = 0.0
    tol = max(0.0, tol)

    cur_used = float(report.get("used_fraction") or 0.0)
    base_used = float(baseline.get("used_fraction") or 0.0)

    base_results = baseline.get("results")
    cur_results = report.get("results")
    base_by_case = {}
    if isinstance(base_results, list):
        for r in base_results:
            if isinstance(r, dict) and r.get("case"):
                base_by_case[str(r.get("case"))] = r

    drift = {"used": 0, "reason": 0, "asset_id": 0, "dataset_id": 0}
    total_compared = 0
    if isinstance(cur_results, list):
        for r in cur_results:
            if not isinstance(r, dict) or not r.get("case"):
                continue
            key = str(r.get("case"))
            br = base_by_case.get(key)
            if not isinstance(br, dict):
                continue
            total_compared += 1
            if bool(r.get("used")) != bool(br.get("used")):
                drift["used"] += 1
            if str(r.get("reason") or "") != str(br.get("reason") or ""):
                drift["reason"] += 1
            if str(r.get("asset_id") or "") != str(br.get("asset_id") or ""):
                drift["asset_id"] += 1
            if str(r.get("dataset_id") or "") != str(br.get("dataset_id") or ""):
                drift["dataset_id"] += 1

    ok = bool(cur_used + tol >= base_used)
    return {
        "ok": ok,
        "tolerance": float(tol),
        "used_fraction": {"current": cur_used, "baseline": base_used, "delta": cur_used - base_used},
        "case_drift": {"compared": int(total_compared), "counts": drift},
    }


def main(argv: Optional[List[str]] = None) -> int:
    import argparse

    ap = argparse.ArgumentParser()
    ap.add_argument("--db-path")
    ap.add_argument("--cases-path")
    ap.add_argument("--out", required=True)
    ap.add_argument("--limit-cases", type=int)
    ap.add_argument("--baseline")
    ap.add_argument("--fail-on-checks", action="store_true")
    args = ap.parse_args(argv)

    report = run_suite(db_path=args.db_path, cases_path=args.cases_path, limit_cases=args.limit_cases)

    if args.baseline:
        try:
            bp = Path(str(args.baseline))
            baseline = json.loads(bp.read_text(encoding="utf-8"))
        except Exception as e:
            baseline = {"ok": False, "error": f"baseline_read_failed: {type(e).__name__}: {e}"}
        if isinstance(baseline, dict) and isinstance(report, dict):
            try:
                report["baseline"] = compare_to_baseline(report=report, baseline=baseline)
            except Exception as e:
                report["baseline"] = {"ok": False, "error": f"baseline_compare_failed: {type(e).__name__}: {e}"}

    write_report(out_path=str(args.out), report=report)

    if args.fail_on_checks:
        checks = report.get("checks") if isinstance(report, dict) else None
        baseline_cmp = report.get("baseline") if isinstance(report, dict) else None
        failed = False
        if isinstance(checks, dict):
            for k, v in checks.items():
                if str(k).endswith("_ok") and v is False:
                    failed = True
        if isinstance(baseline_cmp, dict) and baseline_cmp.get("ok") is False:
            failed = True
        return 2 if failed else 0

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

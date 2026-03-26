import argparse
import json
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

from . import db as dtkdb
from .features import extract_features_and_confidence
from .manifest import validate_transcription_artifact_record


def _iter_jsonl(p: Path) -> Iterable[Dict[str, Any]]:
    with p.open("r", encoding="utf-8") as f:
        for line in f:
            s = (line or "").strip()
            if not s:
                continue
            yield json.loads(s)


def _load_records(in_path: Path) -> List[Dict[str, Any]]:
    if in_path.suffix.lower() == ".jsonl":
        recs = list(_iter_jsonl(in_path))
    else:
        obj = json.loads(in_path.read_text(encoding="utf-8"))
        if isinstance(obj, list):
            recs = list(obj)
        elif isinstance(obj, dict) and isinstance(obj.get("records"), list):
            recs = list(obj.get("records") or [])
        else:
            raise ValueError("input must be .jsonl or a JSON list or {records:[...]} object")

    out: List[Dict[str, Any]] = []
    for r in recs:
        if not isinstance(r, dict):
            continue
        out.append(r)

    out.sort(key=lambda r: str(r.get("asset_id") or r.get("assetId") or ""))
    return out


def _normalize_record(r: Dict[str, Any]) -> Tuple[str, Optional[List[Dict[str, Any]]], Optional[Dict[str, Any]], Optional[float], Dict[str, Any]]:
    asset_id = str(r.get("asset_id") or r.get("assetId") or "").strip()
    if not asset_id:
        raise ValueError("missing asset_id")

    events = r.get("events")
    if events is not None and not isinstance(events, list):
        raise ValueError("events must be a list")

    features = r.get("features")
    if features is not None and not isinstance(features, dict):
        raise ValueError("features must be an object")

    confidence = r.get("confidence")
    if confidence is not None:
        confidence = float(confidence)

    provenance = r.get("provenance")
    if provenance is None:
        provenance = {}
    if not isinstance(provenance, dict):
        raise ValueError("provenance must be an object")

    return asset_id, events, features, confidence, provenance


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--db-path")
    ap.add_argument("--in", dest="in_path", required=True)
    ap.add_argument("--transcription-version", required=True)
    ap.add_argument("--skip-missing-assets", action="store_true")
    args = ap.parse_args(argv)

    in_path = Path(str(args.in_path))
    if not in_path.exists():
        raise FileNotFoundError(str(in_path))

    conn = dtkdb.connect(Path(str(args.db_path))) if args.db_path else dtkdb.connect()
    try:
        dtkdb.ensure_schema(conn)
        records = _load_records(in_path)

        cur = conn.cursor()
        missing = 0
        inserted = 0
        failed = 0

        for r in records:
            try:
                validate_transcription_artifact_record(r)
                asset_id, events, features, confidence, provenance = _normalize_record(r)

                if events is not None:
                    feats_out, conf_out = extract_features_and_confidence(events=events, features_in=features)
                    if features is None:
                        features = feats_out
                    if confidence is None:
                        confidence = float(conf_out)

                cur.execute("SELECT 1 FROM audio_assets WHERE asset_id = ?", (asset_id,))
                exists = cur.fetchone() is not None
                if not exists:
                    missing += 1
                    if args.skip_missing_assets:
                        continue
                    raise ValueError(f"missing audio_asset for asset_id={asset_id}")

                dtkdb.upsert_transcription_artifact(
                    conn,
                    asset_id=asset_id,
                    transcription_version=str(args.transcription_version),
                    events=events,
                    features=features,
                    confidence=confidence,
                    provenance=provenance,
                )
                inserted += 1
            except Exception:
                failed += 1

        if failed > 0 and not bool(args.skip_missing_assets):
            return 2
        return 0
    finally:
        conn.close()


if __name__ == "__main__":
    raise SystemExit(main())

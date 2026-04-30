import argparse
import hashlib
import json
import math
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

from . import db as dtkdb
from .features import extract_features_and_confidence
from .manifest import validate_written_reference_record


def _sha256_text(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8", errors="ignore")).hexdigest()


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
        if isinstance(r, dict):
            out.append(r)
    out.sort(key=lambda r: (str(r.get("dataset_id") or ""), str(r.get("clip_id") or r.get("id") or "")))
    return out


def _grid_event_to_drummerbrain_event(
    *,
    ev: Dict[str, Any],
    beats_per_bar: int,
    resolution_ppq: int,
    subdiv: int,
) -> Optional[Dict[str, Any]]:
    if not isinstance(ev, dict):
        return None

    try:
        bar = int(ev.get("barIndex"))
        tick = int(ev.get("tickInBar"))
    except Exception:
        return None

    if resolution_ppq <= 0 or beats_per_bar <= 0 or subdiv <= 0:
        return None

    total_beats = float(bar * beats_per_bar) + (float(tick) / float(resolution_ppq))
    if total_beats < 0:
        return None

    beat_index = int(math.floor(total_beats))
    phase = total_beats - float(beat_index)
    sub = int(round(phase * float(subdiv)))
    if sub >= subdiv:
        beat_index += 1
        sub = 0

    vel = ev.get("velocity")
    strength = None
    if vel is not None:
        try:
            vv = float(vel)
            strength = max(0.0, min(1.0, vv / 127.0))
        except Exception:
            strength = None

    out: Dict[str, Any] = {
        "beat_index": int(beat_index),
        "sub": int(sub),
        "subdiv": int(subdiv),
        "lane": str(ev.get("instrument_id") or ev.get("instrumentId") or ev.get("lane") or "hit"),
    }
    if strength is not None:
        out["strength"] = float(strength)
    return out


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--db-path")
    ap.add_argument("--in", dest="in_path", required=True)
    ap.add_argument("--dataset-id", required=True)
    ap.add_argument("--label", required=True)
    ap.add_argument("--dataset-type", default="written_reference")
    ap.add_argument("--transcription-version", required=True)
    ap.add_argument("--root-path", default="")
    ap.add_argument("--default-meter", default="4/4")
    ap.add_argument("--default-resolution-ppq", type=int, default=480)
    ap.add_argument("--default-subdiv", type=int, default=4)
    args = ap.parse_args(argv)

    in_path = Path(str(args.in_path))
    if not in_path.exists():
        raise FileNotFoundError(str(in_path))

    if int(args.default_resolution_ppq) <= 0:
        raise ValueError("--default-resolution-ppq must be > 0")
    if int(args.default_subdiv) <= 0:
        raise ValueError("--default-subdiv must be > 0")

    def _parse_meter(s: str) -> Tuple[int, int]:
        try:
            a, b = (s or "").split("/", 1)
            return max(1, int(a)), max(1, int(b))
        except Exception:
            return 4, 4

    default_beats_per_bar, _ = _parse_meter(str(args.default_meter))

    conn = dtkdb.connect(Path(str(args.db_path))) if args.db_path else dtkdb.connect()
    try:
        dtkdb.ensure_schema(conn)
        dtkdb.upsert_dataset(
            conn,
            dataset_id=str(args.dataset_id),
            label=str(args.label),
            root_path=str(args.root_path or ""),
            dataset_type=str(args.dataset_type or "written_reference"),
        )

        records = _load_records(in_path)
        inserted = 0
        failed = 0

        for r in records:
            try:
                validate_written_reference_record(r)
                clip_id = str(r.get("clip_id") or r.get("id") or "").strip()
                if not clip_id:
                    raise ValueError("missing clip_id")

                meter = str(r.get("meter") or r.get("time_signature") or args.default_meter)
                beats_per_bar, _ = _parse_meter(meter)

                resolution_ppq = int(r.get("resolution_ppq") or r.get("ppq") or args.default_resolution_ppq)
                subdiv = int(r.get("subdiv") or args.default_subdiv)

                grid_events = r.get("events") or r.get("grid_events") or []
                if not isinstance(grid_events, list):
                    raise ValueError("events must be a list")

                events: List[Dict[str, Any]] = []
                for ev in grid_events:
                    out_ev = _grid_event_to_drummerbrain_event(
                        ev=ev,
                        beats_per_bar=int(beats_per_bar),
                        resolution_ppq=int(resolution_ppq),
                        subdiv=int(subdiv),
                    )
                    if out_ev is not None:
                        events.append(out_ev)

                events.sort(key=lambda e: (int(e.get("beat_index") or 0), int(e.get("sub") or 0), int(e.get("subdiv") or 0), str(e.get("lane") or "")))

                source_ref = str(r.get("source_ref") or r.get("source") or clip_id)
                stable_key = json.dumps(
                    {
                        "dataset_id": str(args.dataset_id),
                        "clip_id": str(clip_id),
                        "source_ref": source_ref,
                        "meter": meter,
                        "resolution_ppq": int(resolution_ppq),
                        "subdiv": int(subdiv),
                    },
                    sort_keys=True,
                    ensure_ascii=False,
                )
                sha = _sha256_text(stable_key)

                asset_id = f"{args.dataset_id}:{sha[:16]}"

                dtkdb.upsert_audio_asset(
                    conn,
                    asset_id=asset_id,
                    dataset_id=str(args.dataset_id),
                    song_key=str(clip_id),
                    variant="written",
                    source_path=str(source_ref),
                    content_sha256=str(sha),
                    size_bytes=None,
                )

                features_in = r.get("features") if isinstance(r.get("features"), dict) else {}
                features_in = dict(features_in)
                features_in.setdefault("meter", meter)
                features_in.setdefault("beats_per_bar", int(beats_per_bar))
                features_in.setdefault("resolution_ppq", int(resolution_ppq))
                features_in.setdefault("subdiv", int(subdiv))
                features_in.setdefault("tempo_adaptive", True)

                feats, conf = extract_features_and_confidence(events=events, features_in=features_in)

                confidence = r.get("confidence")
                if confidence is not None:
                    conf = float(confidence)

                prov = r.get("provenance") if isinstance(r.get("provenance"), dict) else {}
                prov = dict(prov)
                prov.setdefault("source_ref", source_ref)
                prov.setdefault("clip_id", clip_id)
                prov.setdefault("meter", meter)
                prov.setdefault("resolution_ppq", int(resolution_ppq))
                prov.setdefault("subdiv", int(subdiv))

                dtkdb.upsert_transcription_artifact(
                    conn,
                    asset_id=asset_id,
                    transcription_version=str(args.transcription_version),
                    events=events,
                    features=feats,
                    confidence=float(conf),
                    provenance=prov,
                )

                inserted += 1
            except Exception:
                failed += 1

        if failed > 0:
            return 2
        return 0
    finally:
        conn.close()


if __name__ == "__main__":
    raise SystemExit(main())

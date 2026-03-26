import json
from typing import Any, Dict, List, Optional, Tuple


class ManifestError(ValueError):
    pass


def _as_dict(x: Any) -> Dict[str, Any]:
    if x is None:
        return {}
    if not isinstance(x, dict):
        raise ManifestError("expected object")
    return x


def _as_list(x: Any) -> List[Any]:
    if x is None:
        return []
    if not isinstance(x, list):
        raise ManifestError("expected list")
    return x


def validate_transcription_artifact_record(r: Dict[str, Any]) -> None:
    r = _as_dict(r)
    asset_id = str(r.get("asset_id") or r.get("assetId") or "").strip()
    if not asset_id:
        raise ManifestError("missing asset_id")

    events = r.get("events")
    if events is not None:
        events = _as_list(events)
        for i, e in enumerate(events):
            if not isinstance(e, dict):
                raise ManifestError(f"events[{i}] must be object")
            if "beat_index" in e:
                try:
                    int(e.get("beat_index"))
                except Exception:
                    raise ManifestError(f"events[{i}].beat_index must be int")
            if "sub" in e:
                try:
                    int(e.get("sub"))
                except Exception:
                    raise ManifestError(f"events[{i}].sub must be int")
            if "subdiv" in e:
                try:
                    sd = int(e.get("subdiv"))
                    if sd <= 0:
                        raise ManifestError(f"events[{i}].subdiv must be > 0")
                except ManifestError:
                    raise
                except Exception:
                    raise ManifestError(f"events[{i}].subdiv must be int")

    features = r.get("features")
    if features is not None and not isinstance(features, dict):
        raise ManifestError("features must be object")

    prov = r.get("provenance")
    if prov is not None and not isinstance(prov, dict):
        raise ManifestError("provenance must be object")

    conf = r.get("confidence")
    if conf is not None:
        try:
            float(conf)
        except Exception:
            raise ManifestError("confidence must be number")


def validate_written_reference_record(r: Dict[str, Any]) -> None:
    r = _as_dict(r)
    clip_id = str(r.get("clip_id") or r.get("id") or "").strip()
    if not clip_id:
        raise ManifestError("missing clip_id")

    meter = r.get("meter") or r.get("time_signature")
    if meter is not None:
        m = str(meter)
        if "/" not in m:
            raise ManifestError("meter must look like '4/4'")

    resolution_ppq = r.get("resolution_ppq") or r.get("ppq")
    if resolution_ppq is not None:
        try:
            if int(resolution_ppq) <= 0:
                raise ManifestError("resolution_ppq must be > 0")
        except ManifestError:
            raise
        except Exception:
            raise ManifestError("resolution_ppq must be int")

    subdiv = r.get("subdiv")
    if subdiv is not None:
        try:
            if int(subdiv) <= 0:
                raise ManifestError("subdiv must be > 0")
        except ManifestError:
            raise
        except Exception:
            raise ManifestError("subdiv must be int")

    events = r.get("events") or r.get("grid_events")
    events = _as_list(events)
    for i, e in enumerate(events):
        if not isinstance(e, dict):
            raise ManifestError(f"events[{i}] must be object")
        if "barIndex" not in e or "tickInBar" not in e:
            raise ManifestError(f"events[{i}] missing barIndex/tickInBar")
        try:
            int(e.get("barIndex"))
            int(e.get("tickInBar"))
        except Exception:
            raise ManifestError(f"events[{i}] barIndex/tickInBar must be int")


def load_manifest_records(text: str) -> List[Dict[str, Any]]:
    obj = json.loads(text)
    if isinstance(obj, list):
        return [r for r in obj if isinstance(r, dict)]
    if isinstance(obj, dict) and isinstance(obj.get("records"), list):
        return [r for r in (obj.get("records") or []) if isinstance(r, dict)]
    raise ManifestError("manifest must be a JSON list or {records:[...]} object")

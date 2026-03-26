import math
from typing import Any, Dict, List, Optional, Tuple


def _safe_float(x: Any, default: float = 0.0) -> float:
    try:
        v = float(x)
        if not math.isfinite(v):
            return float(default)
        return v
    except Exception:
        return float(default)


def extract_features_and_confidence(
    *,
    events: Optional[List[Dict[str, Any]]],
    features_in: Optional[Dict[str, Any]] = None,
) -> Tuple[Dict[str, Any], float]:
    """Deterministic feature extraction from DrummerBrain-style events.

    Supports both:
    - time-based events ("t" in seconds)
    - tempo-adaptive events (beat_index/sub/subdiv)

    Returns (features, confidence).
    """
    base_feats: Dict[str, Any] = dict(features_in or {})
    evs = list(events or [])

    event_count = int(len(evs))
    unique_positions = 0
    mean_strength = 0.0

    strengths: List[float] = []
    pos = set()

    lane_counts: Dict[str, int] = {}
    downbeat_strengths: List[float] = []
    offbeat_strengths: List[float] = []
    backbeat_hits = 0
    backbeat_opportunities = 0

    max_t = 0.0
    max_pos_beats = 0.0
    subdiv_seen: Optional[int] = None

    beats_per_bar = 4
    try:
        bpb = (features_in or {}).get("beats_per_bar") if isinstance(features_in, dict) else None
        if bpb is not None:
            beats_per_bar = max(1, int(bpb))
    except Exception:
        beats_per_bar = 4

    for e in evs:
        if not isinstance(e, dict):
            continue

        lane = str(e.get("lane") or "").strip() or "hit"
        lane_counts[lane] = int(lane_counts.get(lane, 0)) + 1

        if "t" in e:
            max_t = max(max_t, _safe_float(e.get("t"), 0.0))

        bi = e.get("beat_index")
        sub = e.get("sub")
        subdiv = e.get("subdiv")
        if subdiv_seen is None and subdiv is not None:
            try:
                subdiv_seen = int(subdiv)
            except Exception:
                subdiv_seen = None

        try:
            bi_i = int(bi) if bi is not None else 0
        except Exception:
            bi_i = 0
        try:
            sub_i = int(sub) if sub is not None else 0
        except Exception:
            sub_i = 0
        try:
            subdiv_i = int(subdiv) if subdiv is not None else 0
        except Exception:
            subdiv_i = 0

        if subdiv_i > 0:
            pos.add((bi_i, sub_i, subdiv_i))
            max_pos_beats = max(max_pos_beats, float(bi_i) + (float(sub_i) / float(subdiv_i)))
        else:
            pos.add((bi_i, sub_i, 0))
            max_pos_beats = max(max_pos_beats, float(bi_i))

        strengths.append(_safe_float(e.get("strength"), 0.5))

        # Downbeat/offbeat buckets and backbeat proxy.
        is_downbeat = bool(sub_i == 0)
        st = _safe_float(e.get("strength"), 0.5)
        if is_downbeat:
            downbeat_strengths.append(float(st))
        else:
            offbeat_strengths.append(float(st))

        # Backbeat proxy (works for 4/4/3/6 etc as a best-effort):
        # consider beats 2 and 4 positions as (1 and 3) in 0-index beat-in-bar.
        try:
            beat_in_bar = int(bi_i % max(1, beats_per_bar))
        except Exception:
            beat_in_bar = 0
        if is_downbeat and beat_in_bar in {1, 3}:
            backbeat_opportunities += 1
            if "snare" in lane:
                backbeat_hits += 1

    unique_positions = int(len(pos))
    if strengths:
        mean_strength = float(sum(strengths) / float(len(strengths)))

    feats: Dict[str, Any] = dict(base_feats)
    feats.setdefault("event_count", event_count)
    feats.setdefault("unique_positions", unique_positions)
    feats.setdefault("mean_strength", float(mean_strength))

    feats.setdefault("lane_counts", dict(sorted(lane_counts.items(), key=lambda kv: kv[0])))
    feats.setdefault("has_kick", bool(lane_counts.get("kick", 0) > 0 or lane_counts.get("bd", 0) > 0))
    feats.setdefault("has_snare", bool(any(("snare" in k and v > 0) for k, v in lane_counts.items())))
    feats.setdefault("has_hat", bool(any(("hihat" in k and v > 0) for k, v in lane_counts.items())))

    downbeat_mean = float(sum(downbeat_strengths) / float(len(downbeat_strengths))) if downbeat_strengths else 0.0
    offbeat_mean = float(sum(offbeat_strengths) / float(len(offbeat_strengths))) if offbeat_strengths else 0.0
    feats.setdefault("downbeat_strength", downbeat_mean)
    feats.setdefault("offbeat_strength", offbeat_mean)

    # Duration inference.
    dur_s = feats.get("duration_s")
    if dur_s is None and max_t > 0.0:
        # Assume one-beat tail.
        feats["duration_s"] = float(max_t)

    if feats.get("duration_beats") is None and max_pos_beats > 0.0:
        feats["duration_beats"] = float(max_pos_beats)

    try:
        dur_beats2 = _safe_float(feats.get("duration_beats"), 0.0)
        if dur_beats2 > 1e-6:
            feats.setdefault("hits_per_beat", float(event_count) / float(dur_beats2))
            feats.setdefault("hits_per_bar", float(event_count) / float(dur_beats2 / float(max(1, beats_per_bar))))
    except Exception:
        pass

    # Syncopation proxy: fraction of events not on downbeats.
    if event_count > 0:
        feats.setdefault("syncopation_ratio", float(len(offbeat_strengths)) / float(event_count))

    if backbeat_opportunities > 0:
        feats.setdefault("backbeat_ratio", float(backbeat_hits) / float(backbeat_opportunities))
    else:
        feats.setdefault("backbeat_ratio", 0.0)

    if subdiv_seen is not None and subdiv_seen > 0 and feats.get("subdiv") is None:
        feats["subdiv"] = int(subdiv_seen)

    tempo_adaptive = bool(feats.get("tempo_adaptive"))
    if not tempo_adaptive and ("t" not in (evs[0] if evs else {})) and max_pos_beats > 0.0:
        feats["tempo_adaptive"] = True

    # Confidence heuristic: bounded, deterministic.
    u_norm = 0.0
    if unique_positions > 0:
        u_norm = min(1.0, float(unique_positions) / 32.0)

    e_norm = 0.0
    if event_count > 0:
        e_norm = min(1.0, float(event_count) / 64.0)

    conf = 0.20 + 0.45 * max(0.0, min(1.0, mean_strength)) + 0.20 * u_norm + 0.15 * e_norm
    conf = float(max(0.0, min(1.0, conf)))

    return feats, conf

from __future__ import annotations

from dataclasses import asdict, is_dataclass
from typing import Any, Dict, Iterable, List, Mapping, MutableMapping, Optional, Sequence, Tuple


def _norm(value: Any) -> str:
    return str(value or "").strip().lower().replace("-", "_").replace(" ", "_")


def _f(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return float(default)


def _candidate_to_mapping(candidate: Any) -> Dict[str, Any]:
    if isinstance(candidate, Mapping):
        return dict(candidate)
    if is_dataclass(candidate):
        try:
            return asdict(candidate)
        except Exception:
            pass
    out: Dict[str, Any] = {}
    for key in (
        "id",
        "title",
        "source",
        "tags",
        "style_group",
        "style_detail",
        "default_role",
        "complexity_score",
        "offbeat_ratio",
        "snare_backbeat_ratio",
        "kick_share",
        "snare_share",
        "cymbal_share",
        "tom_share",
        "hat_hits_per_bar",
        "ride_tip_hits_per_bar",
        "ride_bell_hits_per_bar",
        "bars",
    ):
        if hasattr(candidate, key):
            out[key] = getattr(candidate, key)
    return out


def _collect_tokens(candidate: Mapping[str, Any]) -> List[str]:
    tokens: List[str] = []
    for field in ("id", "title", "source", "style_group", "style_detail", "default_role"):
        value = candidate.get(field)
        if value:
            tokens.extend(_norm(value).split("_"))
            tokens.append(_norm(value))
    tags = candidate.get("tags") or []
    if isinstance(tags, Sequence) and not isinstance(tags, (str, bytes)):
        for tag in tags:
            if tag:
                tokens.extend(_norm(tag).split("_"))
                tokens.append(_norm(tag))
    return [t for t in tokens if t]


_GROOVE_FAMILY_RULES: Dict[str, Tuple[str, ...]] = {
    "ride_lead": ("ride", "ride_lead", "ridebow", "ride_bow", "ridebell", "ride_bell"),
    "open_hat_lift": ("open_hat", "hihat_open", "open", "lift", "chorus"),
    "pocket_backbeat": ("pocket", "backbeat", "verse", "straight"),
    "syncopated_kick": ("syncopated", "kick", "sync", "broken"),
    "shuffle_pocket": ("shuffle", "swing", "triplet"),
    "linear_support": ("linear",),
    "tom_color": ("tom", "toms"),
    "halftime_space": ("half", "halftime", "space", "sparse"),
}

_FILL_FAMILY_RULES: Dict[str, Tuple[str, ...]] = {
    "snare_pickup": ("snare", "pickup", "lead_in"),
    "snare_roll": ("snare", "roll", "buzz"),
    "tom_lift": ("tom", "lift", "build"),
    "linear_burst": ("linear", "burst"),
    "triplet_turnaround": ("triplet", "turnaround", "shuffle", "swing"),
    "flam_tom": ("flam", "tom"),
    "cymbal_wash": ("cymbal", "wash", "crash"),
    "none": ("none", "empty", "skip"),
}


def _family_match_score(tokens: Sequence[str], family: str, *, groove: bool) -> float:
    rules = _GROOVE_FAMILY_RULES if groove else _FILL_FAMILY_RULES
    wanted = rules.get(_norm(family), ())
    if not wanted:
        return 0.0
    token_set = set(tokens)
    hits = sum(1.0 for item in wanted if item in token_set)
    if hits <= 0:
        return 0.0
    return hits / max(1.0, float(len(wanted)))


def _timekeeper_bonus(candidate: Mapping[str, Any], hints: Mapping[str, Any]) -> float:
    policy = hints.get("retrievalPolicy") or {}
    if not policy.get("preferTimekeeperMatch"):
        return 0.0
    score_inputs = hints.get("scoreInputs") or {}
    timekeeper = _norm(score_inputs.get("timekeeper"))
    if not timekeeper:
        return 0.0
    ride = _f(candidate.get("ride_tip_hits_per_bar")) + _f(candidate.get("ride_bell_hits_per_bar"))
    hats = _f(candidate.get("hat_hits_per_bar"))
    if timekeeper == "ride":
        return 0.2 if ride > hats else -0.05
    if timekeeper in {"hats", "hihat", "hi_hat"}:
        return 0.2 if hats >= max(ride, 0.1) else -0.05
    if timekeeper == "mixed":
        return 0.08 if ride > 0.0 and hats > 0.0 else 0.0
    return 0.0


def _feel_bonus(candidate: Mapping[str, Any], hints: Mapping[str, Any], *, groove: bool) -> float:
    score_inputs = hints.get("scoreInputs") or {}
    time_feel = _norm(score_inputs.get("timeFeel"))
    if not groove or not time_feel:
        return 0.0
    offbeat = _f(candidate.get("offbeat_ratio"))
    backbeat = _f(candidate.get("snare_backbeat_ratio"))
    if time_feel in {"shuffle", "swing"}:
        return 0.25 * offbeat
    if time_feel == "straight":
        return 0.15 * backbeat
    if time_feel == "laid_back":
        return 0.08 * backbeat + 0.05 * (1.0 - offbeat)
    if time_feel == "pushed":
        return 0.08 * offbeat + 0.05 * _f(candidate.get("kick_share"))
    return 0.0


def _complexity_fit_bonus(candidate: Mapping[str, Any], hints: Mapping[str, Any], *, groove: bool) -> float:
    score_inputs = hints.get("scoreInputs") or {}
    energy = _f(score_inputs.get("energy"), 0.5)
    fill_aggr = _f(score_inputs.get("fillAggression"), 0.5)
    complexity = _f(candidate.get("complexity_score"), 0.5)
    target = (energy * 0.6 + fill_aggr * 0.4) if groove else (fill_aggr * 0.7 + energy * 0.3)
    return max(0.0, 0.18 - abs(complexity - target) * 0.3)


def _score_candidate(candidate: Any, hints: Mapping[str, Any], *, groove: bool) -> Dict[str, Any]:
    mapping = _candidate_to_mapping(candidate)
    tokens = _collect_tokens(mapping)
    families = hints.get("preferredGrooveFamilies" if groove else "preferredFillFamilies") or []
    family_weights = hints.get("grooveFamilyWeights" if groove else "fillFamilyWeights") or {}

    family_components: List[Tuple[str, float]] = []
    weighted_family_score = 0.0
    for family in families:
        fam_key = _norm(family)
        match = _family_match_score(tokens, fam_key, groove=groove)
        weight = _f(family_weights.get(family, family_weights.get(fam_key, 0.0)))
        component = match * max(0.05, weight)
        if component > 0.0:
            family_components.append((fam_key, round(component, 4)))
            weighted_family_score += component

    timekeeper_bonus = _timekeeper_bonus(mapping, hints) if groove else 0.0
    feel_bonus = _feel_bonus(mapping, hints, groove=groove)
    complexity_bonus = _complexity_fit_bonus(mapping, hints, groove=groove)

    final_score = weighted_family_score + timekeeper_bonus + feel_bonus + complexity_bonus
    return {
        "candidate": mapping,
        "score": round(final_score, 6),
        "scoreBreakdown": {
            "family": round(weighted_family_score, 6),
            "timekeeper": round(timekeeper_bonus, 6),
            "feel": round(feel_bonus, 6),
            "complexity": round(complexity_bonus, 6),
            "matchedFamilies": family_components,
        },
    }



def rerank_groove_candidates(candidates: Iterable[Any], retrieval_hints: Mapping[str, Any], *, limit: Optional[int] = None) -> List[Dict[str, Any]]:
    scored = [_score_candidate(c, retrieval_hints or {}, groove=True) for c in candidates or []]
    scored.sort(key=lambda item: (item["score"], item["candidate"].get("id") or ""), reverse=True)
    if limit is not None:
        scored = scored[: max(1, int(limit))]
    return scored



def rerank_fill_candidates(candidates: Iterable[Any], retrieval_hints: Mapping[str, Any], *, limit: Optional[int] = None) -> List[Dict[str, Any]]:
    scored = [_score_candidate(c, retrieval_hints or {}, groove=False) for c in candidates or []]
    scored.sort(key=lambda item: (item["score"], item["candidate"].get("id") or ""), reverse=True)
    if limit is not None:
        scored = scored[: max(1, int(limit))]
    return scored


__all__ = [
    "rerank_groove_candidates",
    "rerank_fill_candidates",
]

from __future__ import annotations

from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

SUBDIVISION_ORDER = ["1", "e", "&", "a"] * 4


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return float(default)


def _clamp(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, float(value)))


def normalize_instrument_id(inst_id: str) -> str:
    s = str(inst_id or '').strip().lower()
    if not s:
        return 'unknown'
    if s.startswith('snare'):
        return 'snare'
    if s.startswith('kick') or s == 'bd':
        return 'kick'
    if s.startswith('hihat') or s.startswith('hh') or s == 'hat':
        return 'hihat'
    if s.startswith('ride'):
        return 'ride'
    if s.startswith('crash'):
        return 'crash'
    if s.startswith('tom'):
        return 'tom'
    return s


def _phrase_kind_from_label(label: Any) -> str:
    raw = str(label or '').strip().lower()
    if any(tok in raw for tok in ['fill', 'pickup', 'turnaround']):
        return 'fill'
    return 'groove'


def _role_preferences(inst: str, section_label: str) -> List[str]:
    raw = str(section_label or '').strip().lower()
    if inst == 'snare':
        return ['backbeat', 'accent', 'support', 'ghost']
    if inst == 'kick':
        return ['foundation', 'support', 'accent']
    if inst in {'hihat', 'ride'}:
        if 'chorus' in raw and inst == 'ride':
            return ['timekeeping', 'accent', 'support']
        return ['timekeeping', 'support', 'accent']
    if inst == 'tom':
        return ['fill', 'accent', 'support']
    return ['support', 'accent']


def _iter_profile_rows(container: Any) -> Iterable[Mapping[str, Any]]:
    if isinstance(container, Mapping):
        profiles = container.get('profiles')
        if isinstance(profiles, list):
            for row in profiles:
                if isinstance(row, Mapping):
                    yield row
            return
        for key, value in container.items():
            if not isinstance(value, Mapping):
                continue
            row = dict(value)
            if 'instrument' not in row:
                row['instrument'] = normalize_instrument_id(str(key).split(':', 1)[0])
            if 'role' not in row and ':' in str(key):
                row['role'] = str(key).split(':', 1)[1]
            yield row
    elif isinstance(container, list):
        for row in container:
            if isinstance(row, Mapping):
                yield row


def _best_profile_rows(container: Any, inst: str, roles: Sequence[str]) -> List[Mapping[str, Any]]:
    rows = []
    for row in _iter_profile_rows(container):
        if normalize_instrument_id(str(row.get('instrument') or row.get('instrumentId') or '')) != inst:
            continue
        rows.append(row)
    if not rows:
        return []
    for role in roles:
        subset = [r for r in rows if str(r.get('role') or '').strip().lower() == role]
        if subset:
            return subset
    generic = [r for r in rows if not str(r.get('role') or '').strip()]
    return generic or rows


def _weighted_mean(values: Sequence[Tuple[float, float]], default: float) -> float:
    if not values:
        return float(default)
    total_w = sum(max(0.0, float(w)) for _v, w in values)
    if total_w <= 0:
        return float(sum(v for v, _w in values) / max(len(values), 1))
    return float(sum(float(v) * max(0.0, float(w)) for v, w in values) / total_w)


def build_subdivision_offsets(
    timing_container: Any,
    inst: str,
    section_label: str,
    swing_amount: float,
    laid_back: float,
    global_var_ms: float,
    max_ms: float,
) -> Tuple[List[float], float]:
    roles = _role_preferences(inst, section_label)
    rows = _best_profile_rows(timing_container, inst, roles)
    if not rows:
        out = []
        for i, sub in enumerate(SUBDIVISION_ORDER):
            base = (swing_amount * 8.0 if sub in {'e', 'a'} else 0.0) + laid_back * 4.0
            out.append(_clamp(base, -max_ms, max_ms))
        return out, max(0.0, global_var_ms * 0.7)

    aggregate_mean = _weighted_mean([
        (_safe_float(r.get('mean_offset_ms'), 0.0), _safe_float(r.get('sample_count'), 1.0))
        for r in rows
    ], 0.0)
    aggregate_std = _weighted_mean([
        (_safe_float(r.get('std_offset_ms'), global_var_ms * 0.7), _safe_float(r.get('sample_count'), 1.0))
        for r in rows
    ], global_var_ms * 0.7)

    by_sub: Dict[str, List[Tuple[float, float]]] = {}
    for r in rows:
        sub = str(r.get('subdivision') or '').strip().lower()
        if sub:
            by_sub.setdefault(sub, []).append((_safe_float(r.get('mean_offset_ms'), aggregate_mean), _safe_float(r.get('sample_count'), 1.0)))

    out: List[float] = []
    for idx, sub in enumerate(SUBDIVISION_ORDER):
        if sub in by_sub:
            mean_offset = _weighted_mean(by_sub[sub], aggregate_mean)
        else:
            mean_offset = aggregate_mean
        if sub in {'e', 'a'}:
            mean_offset += swing_amount * 8.0
        mean_offset += laid_back * 4.0
        out.append(_clamp(mean_offset, -max_ms, max_ms))
    return out, max(0.0, aggregate_std)


def _dynamic_row(dynamic_container: Any, inst: str, section_label: str) -> Optional[Mapping[str, Any]]:
    roles = _role_preferences(inst, section_label)
    rows = _best_profile_rows(dynamic_container, inst, roles)
    if not rows:
        return None
    rows = sorted(rows, key=lambda r: (_safe_float(r.get('sample_count'), 0.0), _safe_float(r.get('velocity_std'), 0.0)), reverse=True)
    return rows[0]


def _transition_probability(drummer_profile: Mapping[str, Any], src: str, dst: str, default: float) -> float:
    model = drummer_profile.get('transition_model') or {}
    transitions = []
    if isinstance(model, Mapping):
        if isinstance(model.get('transitions'), list):
            transitions = model.get('transitions') or []
        elif isinstance(model.get(src), Mapping):
            try:
                return _clamp(_safe_float((model.get(src) or {}).get(dst), default), 0.0, 1.0)
            except Exception:
                return default
    for row in transitions:
        if not isinstance(row, Mapping):
            continue
        if str(row.get('from') or '').strip().lower() == src and str(row.get('to') or '').strip().lower() == dst:
            return _clamp(_safe_float(row.get('probability'), default), 0.0, 1.0)
    return default


def derive_phrase_shape(section_label: str, variation: float, drummer_profile: Mapping[str, Any]) -> str:
    raw = str(section_label or '').strip().lower()
    groove_to_fill = _transition_probability(drummer_profile, 'groove', 'fill', 0.25)
    fill_to_groove = _transition_probability(drummer_profile, 'fill', 'groove', 0.8)
    if 'intro' in raw and variation < 0.5:
        return 'flat'
    if 'chorus' in raw or 'bridge' in raw or groove_to_fill >= 0.42:
        return 'swell'
    if fill_to_groove < 0.55:
        return 'push'
    return 'flat' if variation < 0.6 else 'swell'


def build_sentient_instrument_profile(
    instrument_id: str,
    section_label: str,
    local_base_velocity: int,
    humanize_amount: float,
    swing_amount: float,
    laid_back: float,
    global_var_ms: float,
    ghost_density: float,
    drummer_profile: Mapping[str, Any],
    energy_intensity: float,
    variation: float,
) -> Dict[str, Any]:
    inst = normalize_instrument_id(instrument_id)
    timing_container = drummer_profile.get('instrument_timing_profiles') or drummer_profile.get('timing_profiles') or {}
    dynamic_container = drummer_profile.get('instrument_dynamic_profiles') or drummer_profile.get('dynamic_profiles') or {}
    max_ms = 10.0 * _clamp(humanize_amount, 0.0, 1.0)
    offsets, random_std = build_subdivision_offsets(
        timing_container=timing_container,
        inst=inst,
        section_label=section_label,
        swing_amount=swing_amount,
        laid_back=laid_back,
        global_var_ms=global_var_ms,
        max_ms=max_ms,
    )
    drow = _dynamic_row(dynamic_container, inst, section_label)
    vel_mean = _safe_float((drow or {}).get('velocity_mean'), local_base_velocity)
    vel_std = _safe_float((drow or {}).get('velocity_std'), 10.0)
    sample_count = _safe_float((drow or {}).get('sample_count'), 0.0)

    inst_bias = {
        'kick': 8,
        'snare': 0,
        'hihat': -8,
        'ride': -4,
        'tom': 2,
        'crash': 10,
    }.get(inst, 0)
    base = int(round((_clamp(vel_mean, 1.0, 127.0) * 0.65) + ((local_base_velocity + inst_bias) * 0.35)))
    accent_boost = int(round(_clamp(max(8.0, vel_std * 1.15 + energy_intensity * 10.0), 0.0, 40.0)))
    random_range = int(round(_clamp((random_std * max(0.5, humanize_amount)) + (vel_std * 0.35), 0.0, 20.0)))
    phrase_shape = derive_phrase_shape(section_label, variation, drummer_profile)

    actual_instrument_id = instrument_id
    if inst == 'snare' and instrument_id == 'snare':
        actual_instrument_id = 'snare_center'
    if inst == 'hihat' and instrument_id == 'hihat':
        actual_instrument_id = 'hihat_closed'
    if inst == 'ride' and instrument_id == 'ride':
        actual_instrument_id = 'ride_bow'

    return {
        'instrumentId': actual_instrument_id,
        'microTiming': {
            'subdivisionOffsetsMs': offsets,
            'swingAmount': float(_clamp(swing_amount, 0.0, 1.0)),
            'laidBackAmount': float(_clamp(laid_back + (_weighted_mean([(sum(offsets)/len(offsets), 1.0)], 0.0) / 12.0), -1.0, 1.0)),
            'randomStdMs': float(max(0.0, random_std)),
        },
        'velocityProfile': {
            'base': int(_clamp(base, 1, 127)),
            'accentBoost': int(_clamp(accent_boost, 0, 40)),
            'ghostReduction': float(0.45 if inst == 'snare' else 0.7),
            'randomRange': int(_clamp(random_range, 0, 20)),
            'phraseShape': phrase_shape,
        },
        'ghostDensity': float(_clamp(ghost_density if inst == 'snare' else ghost_density * 0.35, 0.0, 1.0)),
        'flamProbability': float(_clamp(0.12 if inst == 'snare' and sample_count >= 4 and humanize_amount > 0.6 else 0.0, 0.0, 1.0)),
        'dragProbability': float(_clamp(0.06 if inst == 'snare' and humanize_amount > 0.7 else 0.0, 0.0, 1.0)),
    }

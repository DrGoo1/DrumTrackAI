from __future__ import annotations

import re
from dataclasses import dataclass, replace
from typing import Iterable, List, Sequence, Tuple

from .beatprompt_presets import (
    DEFAULT_PATTERN_TEMPLATE,
    DEFAULT_PERSONA_ID,
    DEFAULT_STYLE_PACK,
    PROMPT_TEMPLATES,
    PatternHit,
    PatternTemplateDefinition,
    get_pattern,
    get_template_by_token,
)

SECTION_KEYWORDS = (
    "intro",
    "verse",
    "pre-chorus",
    "chorus",
    "hook",
    "bridge",
    "drop",
    "breakdown",
    "outro",
)

MODIFIER_KEYWORDS: Tuple[Tuple[str, Tuple[str, ...]], ...] = (
    ("doubletime hats", ("doubletime", "double-time", "double time")),
    ("triplet hats", ("triplet hat", "triplet hats", "triplet hi-hat")),
    ("ghost notes", ("ghost note", "ghosted")),
    ("brushes", ("brush", "brushes")),
    ("anthemic", ("anthem", "anthemic")),
    ("half-time", ("half time", "half-time")),
    ("four on the floor", ("four on the floor", "4-on-the-floor")),
    ("wide hats", ("wide hat", "open hat")),
    ("808 kicks", ("808", "sub kick")),
)

TEMPO_WORD_PRESETS = {
    "slow": 72,
    "chill": 84,
    "laid": 92,
    "medium": 108,
    "steady": 116,
    "upbeat": 128,
    "fast": 150,
    "frantic": 172,
}

SEGMENT_SPLIT_REGEX = re.compile(r"(?:\?|\.|\n|,|;|->|\band\b|\bthen\b)+", re.IGNORECASE)
METER_REGEX = re.compile(r"(\d+)\s*/\s*(\d+)")


@dataclass
class PromptSection:
    label: str
    bars: int
    tempo: float
    meter: str
    persona_id: str
    style_pack: str
    pattern_template: str
    modifiers: List[str]
    raw_text: str | None = None
    confidence: float = 0.6

    def to_payload(self) -> dict:
        return {
            "label": self.label,
            "bars": self.bars,
            "tempo": self.tempo,
            "meter": self.meter,
            "persona_id": self.persona_id,
            "style_pack": self.style_pack,
            "pattern_template": self.pattern_template,
            "modifiers": self.modifiers,
            "confidence": self.confidence,
            "raw_text": self.raw_text,
        }


def normalize_sections(prompt: str, sections_payload: Sequence[dict] | None) -> Tuple[List[PromptSection], List[str]]:
    if sections_payload:
        return _normalize_from_payload(sections_payload)
    return parse_prompt(prompt)


def parse_prompt(prompt: str) -> Tuple[List[PromptSection], List[str]]:
    trimmed = (prompt or "").strip()
    if not trimmed:
        return [], ["Describe a groove to get started."]

    segments = [seg.strip() for seg in SEGMENT_SPLIT_REGEX.split(trimmed) if seg and seg.strip()]
    sections: List[PromptSection] = []
    warnings: List[str] = []

    for idx, segment in enumerate(segments):
        template = get_template_by_token(segment)
        label = _detect_section_label(segment, template.default_section_label if template else f"Section {idx+1}")
        bars = _detect_bars(segment, template.default_bars if template else 8)
        tempo = _detect_tempo(segment, template.default_tempo if template else 110)
        meter = _detect_meter(segment, template.default_meter if template else "4/4")
        modifiers = _detect_modifiers(segment, list(template.default_modifiers) if template else [])
        persona_id = template.persona_id if template else DEFAULT_PERSONA_ID
        style_pack = template.style_pack if template else DEFAULT_STYLE_PACK
        pattern_template = template.pattern_template if template else DEFAULT_PATTERN_TEMPLATE
        confidence = 0.9 if template else 0.5

        sections.append(
            PromptSection(
                label=label,
                bars=bars,
                tempo=tempo,
                meter=meter,
                persona_id=persona_id,
                style_pack=style_pack,
                pattern_template=pattern_template,
                modifiers=modifiers,
                raw_text=segment,
                confidence=confidence,
            )
        )

    if not sections:
        warnings.append("We could not detect any sections. Try adding words like 'chorus' or 'bridge'.")

    return sections, warnings


def _normalize_from_payload(sections_payload: Sequence[dict]) -> Tuple[List[PromptSection], List[str]]:
    sections: List[PromptSection] = []
    warnings: List[str] = []
    for idx, raw in enumerate(sections_payload):
        if not isinstance(raw, dict):
            warnings.append(f"Section {idx+1} ignored (not an object).")
            continue

        label = str(raw.get("label") or f"Section {idx+1}").strip() or f"Section {idx+1}"
        bars = _safe_int(raw.get("bars"), default=4, minimum=1)
        tempo = _safe_float(raw.get("tempo"), default=110.0, minimum=40.0)
        meter = str(raw.get("meter") or "4/4").strip()
        persona_id = str(raw.get("persona_id") or DEFAULT_PERSONA_ID)
        style_pack = str(raw.get("style_pack") or DEFAULT_STYLE_PACK)
        pattern_template = str(raw.get("pattern_template") or DEFAULT_PATTERN_TEMPLATE)
        modifiers = [str(m).strip() for m in raw.get("modifiers", []) if isinstance(m, str)]

        sections.append(
            PromptSection(
                label=_title_case(label),
                bars=bars,
                tempo=tempo,
                meter=meter,
                persona_id=persona_id,
                style_pack=style_pack,
                pattern_template=pattern_template,
                modifiers=modifiers,
                raw_text=raw.get("rawText"),
                confidence=float(raw.get("confidence", 0.8)),
            )
        )

    if not sections:
        warnings.append("No valid sections were supplied.")
    return sections, warnings


def render_sections_to_hits(sections: Sequence[PromptSection]) -> Tuple[List[dict], float]:
    if not sections:
        return [], 110.0

    hits: List[dict] = []
    beat_cursor = 0.0
    overall_tempo = sections[0].tempo

    for section in sections:
        pattern = get_pattern(section.pattern_template)
        beats_per_bar = _beats_per_bar(section.meter or pattern.meter)
        pattern_hits = _apply_modifiers(pattern, section.modifiers, beats_per_bar)
        for bar_idx in range(section.bars):
            bar_offset = beat_cursor + bar_idx * beats_per_bar
            for hit in pattern_hits:
                hits.append(
                    {
                        "instrument": hit.instrument,
                        "beat_position": round(bar_offset + hit.beat, 4),
                        "velocity": hit.velocity,
                        "confidence": hit.confidence,
                    }
                )
        beat_cursor += beats_per_bar * section.bars

    return hits, overall_tempo


def serialize_sections(sections: Sequence[PromptSection]) -> List[dict]:
    return [section.to_payload() for section in sections]


def _apply_modifiers(
    pattern: PatternTemplateDefinition,
    modifiers: Sequence[str],
    beats_per_bar: float,
) -> List[PatternHit]:
    hits = list(pattern.hits)
    modifier_set = {m.lower() for m in modifiers}

    if "doubletime hats" in modifier_set:
        hits = _ensure_hat_grid(hits, beats_per_bar, step=0.5, velocity=90)
    if "triplet hats" in modifier_set:
        hits = _ensure_hat_grid(hits, beats_per_bar, step=1 / 3, velocity=88)
    if "four on the floor" in modifier_set:
        hits = _ensure_kick_grid(hits, beats_per_bar, step=1.0, velocity=112)
    if "ghost notes" in modifier_set:
        hits = _add_ghost_notes(hits, beats_per_bar)
    if "anthemic" in modifier_set:
        hits = [replace(hit, velocity=min(127, hit.velocity + 6)) for hit in hits]
    if "808 kicks" in modifier_set:
        hits = _add_extra_kicks(hits, beats_per_bar)
    if "wide hats" in modifier_set:
        hits = _add_open_hats(hits, beats_per_bar)
    if "brushes" in modifier_set:
        hits = [replace(hit, velocity=70) if hit.instrument == "hihat" else hit for hit in hits]

    return hits


def _ensure_hat_grid(hits: List[PatternHit], beats_per_bar: float, step: float, velocity: int) -> List[PatternHit]:
    hat_positions = {round(hit.beat, 4) for hit in hits if hit.instrument == "hihat"}
    pos = 0.0
    generated = list(hits)
    while pos < beats_per_bar - 1e-6:
        rounded = round(pos, 4)
        if rounded not in hat_positions:
            generated.append(PatternHit(beat=rounded, instrument="hihat", velocity=velocity))
            hat_positions.add(rounded)
        pos += step
    return generated


def _ensure_kick_grid(hits: List[PatternHit], beats_per_bar: float, step: float, velocity: int) -> List[PatternHit]:
    kick_positions = {round(hit.beat, 4) for hit in hits if hit.instrument == "kick"}
    pos = 0.0
    generated = list(hits)
    while pos < beats_per_bar - 1e-6:
        rounded = round(pos, 4)
        if rounded not in kick_positions:
            generated.append(PatternHit(beat=rounded, instrument="kick", velocity=velocity))
            kick_positions.add(rounded)
        pos += step
    return generated


def _add_ghost_notes(hits: List[PatternHit], beats_per_bar: float) -> List[PatternHit]:
    generated = list(hits)
    for anchor in (1.0, 3.0):
        if anchor < beats_per_bar:
            generated.append(PatternHit(beat=max(0.0, anchor - 0.15), instrument="snare", velocity=72, confidence=0.8))
    return generated


def _add_extra_kicks(hits: List[PatternHit], beats_per_bar: float) -> List[PatternHit]:
    generated = list(hits)
    for beat in (0.0, 1.5, 3.5):
        if beat < beats_per_bar:
            generated.append(PatternHit(beat=round(beat, 4), instrument="kick", velocity=120))
    return generated


def _add_open_hats(hits: List[PatternHit], beats_per_bar: float) -> List[PatternHit]:
    generated = list(hits)
    for beat in (0.0, 2.0):
        if beat < beats_per_bar:
            generated.append(PatternHit(beat=beat + 0.75 if beats_per_bar >= 3 else beat, instrument="hihat", velocity=110))
    return generated


def _detect_section_label(segment: str, fallback: str) -> str:
    lowered = segment.lower()
    for keyword in SECTION_KEYWORDS:
        if keyword in lowered:
            if keyword == "pre-chorus":
                return "Pre-Chorus"
            return " ".join(part.capitalize() for part in keyword.split())
    return _title_case(fallback)


def _detect_bars(segment: str, fallback: int) -> int:
    match = re.search(r"(\d{1,2})\s*(?:bars?|measures?)", segment, re.IGNORECASE)
    if match:
        return max(1, int(match.group(1)))
    return fallback


def _detect_tempo(segment: str, fallback: float) -> float:
    match = re.search(r"(\d{2,3})\s*(?:bpm|beats|tempo)?", segment, re.IGNORECASE)
    if match:
        return float(match.group(1))
    lowered = segment.lower()
    for word, tempo in TEMPO_WORD_PRESETS.items():
        if word in lowered:
            return float(tempo)
    if "half time" in lowered or "half-time" in lowered:
        return max(60.0, fallback / 2)
    if "double time" in lowered or "double-time" in lowered:
        return min(190.0, fallback * 2)
    return fallback


def _detect_meter(segment: str, fallback: str) -> str:
    match = METER_REGEX.search(segment)
    if match:
        return f"{match.group(1)}/{match.group(2)}"
    if "6/8" in segment or "six eight" in segment.lower():
        return "6/8"
    return fallback


def _detect_modifiers(segment: str, defaults: List[str]) -> List[str]:
    lowered = segment.lower()
    modifiers = list(defaults)
    for label, patterns in MODIFIER_KEYWORDS:
        if any(pattern in lowered for pattern in patterns):
            modifiers.append(label)
    seen = set()
    deduped: List[str] = []
    for mod in modifiers:
        key = mod.lower()
        if key not in seen:
            deduped.append(mod)
            seen.add(key)
    return deduped


def _beats_per_bar(meter: str) -> float:
    match = METER_REGEX.match(meter.strip())
    if not match:
        return 4.0
    numerator = int(match.group(1))
    denominator = int(match.group(2)) or 4
    return numerator * (4 / denominator)


def _safe_int(value, default: int, minimum: int) -> int:
    try:
        ivalue = int(value)
        return max(minimum, ivalue)
    except (TypeError, ValueError):
        return default


def _safe_float(value, default: float, minimum: float) -> float:
    try:
        fvalue = float(value)
        return max(minimum, fvalue)
    except (TypeError, ValueError):
        return default


def _title_case(text: str) -> str:
    return " ".join(part.capitalize() for part in text.split())


__all__ = [
    "PromptSection",
    "normalize_sections",
    "parse_prompt",
    "render_sections_to_hits",
    "serialize_sections",
]

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Sequence, Tuple

DEFAULT_PERSONA_ID = "neo_soul_guru"
DEFAULT_STYLE_PACK = "neo_soul_pocket"
DEFAULT_PATTERN_TEMPLATE = "default_pocket"


@dataclass(frozen=True)
class PromptTemplate:
    id: str
    display_name: str
    tokens: Tuple[str, ...]
    default_section_label: str
    default_bars: int
    default_tempo: float
    default_meter: str
    persona_id: str
    style_pack: str
    pattern_template: str
    default_modifiers: Tuple[str, ...] = ()


PROMPT_TEMPLATES: Tuple[PromptTemplate, ...] = (
    PromptTemplate(
        id="pop_punk_chorus",
        display_name="Pop-Punk Anthem",
        tokens=("pop punk", "pop-punk", "punk rock"),
        default_section_label="Chorus",
        default_bars=8,
        default_tempo=170,
        default_meter="4/4",
        persona_id="arena_rock_captain",
        style_pack="pop_punk_energy",
        pattern_template="chorus_pop_punk",
        default_modifiers=("doubletime hats",),
    ),
    PromptTemplate(
        id="pop_punk_verse",
        display_name="Pop-Punk Verse",
        tokens=("punk verse", "emo verse"),
        default_section_label="Verse",
        default_bars=8,
        default_tempo=160,
        default_meter="4/4",
        persona_id="arena_rock_captain",
        style_pack="pop_punk_energy",
        pattern_template="verse_pop_punk",
    ),
    PromptTemplate(
        id="motown_68_ballad",
        display_name="Motown 6/8",
        tokens=("motown", "6/8", "six eight", "soul ballad"),
        default_section_label="Chorus",
        default_bars=8,
        default_tempo=92,
        default_meter="6/8",
        persona_id="neo_soul_guru",
        style_pack="neo_soul_pocket",
        pattern_template="motown_ballad",
        default_modifiers=("brushes",),
    ),
    PromptTemplate(
        id="neo_soul_pocket",
        display_name="Neo-Soul Pocket",
        tokens=("neo soul", "r&b pocket", "dilla"),
        default_section_label="Verse",
        default_bars=8,
        default_tempo=94,
        default_meter="4/4",
        persona_id="neo_soul_guru",
        style_pack="neo_soul_pocket",
        pattern_template="neo_soul_verse",
        default_modifiers=("ghost notes", "laid back"),
    ),
    PromptTemplate(
        id="trap_verse",
        display_name="Trap Verse",
        tokens=("trap", "808", "triplet hats"),
        default_section_label="Verse",
        default_bars=8,
        default_tempo=142,
        default_meter="4/4",
        persona_id="alt_glitch_curator",
        style_pack="alt_glitch_half_time",
        pattern_template="verse_trap",
        default_modifiers=("triplet hats", "808 kicks"),
    ),
    PromptTemplate(
        id="alt_halftime",
        display_name="Alt Halftime",
        tokens=("halftime", "alt bridge", "heavy bridge"),
        default_section_label="Bridge",
        default_bars=4,
        default_tempo=85,
        default_meter="4/4",
        persona_id="alt_glitch_curator",
        style_pack="alt_glitch_half_time",
        pattern_template="bridge_halftime",
        default_modifiers=("wide hats",),
    ),
    PromptTemplate(
        id="disco_floor",
        display_name="Disco Floor",
        tokens=("disco", "four on the floor", "70s dance"),
        default_section_label="Chorus",
        default_bars=8,
        default_tempo=124,
        default_meter="4/4",
        persona_id="arena_rock_captain",
        style_pack="disco_floor",
        pattern_template="chorus_disco",
        default_modifiers=("four on the floor",),
    ),
    PromptTemplate(
        id="dnb_roll",
        display_name="Drum-n-Bass",
        tokens=("drum and bass", "dnb", "jungle"),
        default_section_label="Drop",
        default_bars=8,
        default_tempo=172,
        default_meter="4/4",
        persona_id="alt_glitch_curator",
        style_pack="dnb_rolls",
        pattern_template="drop_dnb",
    ),
)


@dataclass(frozen=True)
class PatternHit:
    beat: float
    instrument: str
    velocity: int = 100
    confidence: float = 0.95


@dataclass(frozen=True)
class PatternTemplateDefinition:
    id: str
    meter: str
    hits: Tuple[PatternHit, ...]


def _make_hits(rows: Sequence[Tuple[float, str, int]]) -> Tuple[PatternHit, ...]:
    return tuple(PatternHit(beat=row[0], instrument=row[1], velocity=row[2]) for row in rows)


PATTERN_LIBRARY: Dict[str, PatternTemplateDefinition] = {
    "default_pocket": PatternTemplateDefinition(
        id="default_pocket",
        meter="4/4",
        hits=_make_hits(
            [
                (0.0, "kick", 108),
                (1.0, "snare", 112),
                (2.0, "kick", 104),
                (3.0, "snare", 112),
                (0.0, "hihat", 86),
                (1.0, "hihat", 84),
                (2.0, "hihat", 86),
                (3.0, "hihat", 84),
            ]
        ),
    ),
    "chorus_pop_punk": PatternTemplateDefinition(
        id="chorus_pop_punk",
        meter="4/4",
        hits=_make_hits(
            [
                (0.0, "kick", 120),
                (0.75, "kick", 115),
                (1.0, "snare", 118),
                (1.75, "kick", 110),
                (2.0, "kick", 115),
                (3.0, "snare", 120),
                (0.0, "hihat", 96),
                (1.0, "hihat", 95),
                (2.0, "hihat", 96),
                (3.0, "hihat", 95),
            ]
        ),
    ),
    "verse_pop_punk": PatternTemplateDefinition(
        id="verse_pop_punk",
        meter="4/4",
        hits=_make_hits(
            [
                (0.0, "kick", 110),
                (1.0, "snare", 112),
                (1.75, "kick", 100),
                (3.0, "snare", 112),
                (0.0, "hihat", 90),
                (1.0, "hihat", 88),
                (2.0, "hihat", 90),
                (3.0, "hihat", 88),
            ]
        ),
    ),
    "motown_ballad": PatternTemplateDefinition(
        id="motown_ballad",
        meter="6/8",
        hits=_make_hits(
            [
                (0.0, "kick", 105),
                (1.5, "snare", 92),
                (3.0, "kick", 102),
                (4.5, "snare", 92),
                (0.0, "hihat", 70),
                (1.0, "hihat", 68),
                (2.0, "hihat", 70),
                (3.0, "hihat", 68),
                (4.0, "hihat", 70),
                (5.0, "hihat", 68),
            ]
        ),
    ),
    "neo_soul_verse": PatternTemplateDefinition(
        id="neo_soul_verse",
        meter="4/4",
        hits=_make_hits(
            [
                (0.0, "kick", 104),
                (1.0, "snare", 108),
                (1.75, "kick", 92),
                (2.5, "kick", 95),
                (3.0, "snare", 110),
                (0.0, "hihat", 82),
                (1.0, "hihat", 80),
                (2.0, "hihat", 82),
                (3.0, "hihat", 80),
            ]
        ),
    ),
    "verse_trap": PatternTemplateDefinition(
        id="verse_trap",
        meter="4/4",
        hits=_make_hits(
            [
                (0.0, "kick", 115),
                (1.0, "snare", 118),
                (1.75, "kick", 105),
                (2.5, "kick", 108),
                (3.0, "snare", 120),
                (0.0, "hihat", 92),
                (0.5, "hihat", 92),
                (1.0, "hihat", 92),
                (1.5, "hihat", 92),
                (2.0, "hihat", 92),
                (2.5, "hihat", 92),
                (3.0, "hihat", 92),
                (3.5, "hihat", 92),
            ]
        ),
    ),
    "bridge_halftime": PatternTemplateDefinition(
        id="bridge_halftime",
        meter="4/4",
        hits=_make_hits(
            [
                (0.0, "kick", 118),
                (2.0, "kick", 110),
                (3.0, "snare", 122),
                (0.0, "hihat", 90),
                (1.0, "hihat", 88),
                (2.0, "hihat", 90),
                (3.0, "hihat", 88),
            ]
        ),
    ),
    "chorus_disco": PatternTemplateDefinition(
        id="chorus_disco",
        meter="4/4",
        hits=_make_hits(
            [
                (0.0, "kick", 118),
                (1.0, "kick", 118),
                (2.0, "kick", 118),
                (3.0, "kick", 118),
                (1.0, "snare", 112),
                (3.0, "snare", 112),
                (0.0, "hihat", 100),
                (0.5, "hihat", 100),
                (1.0, "hihat", 100),
                (1.5, "hihat", 100),
                (2.0, "hihat", 100),
                (2.5, "hihat", 100),
                (3.0, "hihat", 100),
                (3.5, "hihat", 100),
            ]
        ),
    ),
    "drop_dnb": PatternTemplateDefinition(
        id="drop_dnb",
        meter="4/4",
        hits=_make_hits(
            [
                (0.0, "kick", 120),
                (1.0, "snare", 118),
                (1.75, "kick", 110),
                (2.5, "kick", 110),
                (3.0, "snare", 118),
                (0.0, "hihat", 100),
                (0.25, "hihat", 98),
                (0.5, "hihat", 100),
                (0.75, "hihat", 98),
                (1.0, "hihat", 100),
                (1.25, "hihat", 98),
                (1.5, "hihat", 100),
                (1.75, "hihat", 98),
                (2.0, "hihat", 100),
                (2.25, "hihat", 98),
                (2.5, "hihat", 100),
                (2.75, "hihat", 98),
                (3.0, "hihat", 100),
                (3.25, "hihat", 98),
                (3.5, "hihat", 100),
                (3.75, "hihat", 98),
            ]
        ),
    ),
}


def get_template_by_token(text: str) -> PromptTemplate | None:
    lowered = text.lower()
    for template in PROMPT_TEMPLATES:
        if any(token in lowered for token in template.tokens):
            return template
    return None


def get_pattern(pattern_id: str) -> PatternTemplateDefinition:
    return PATTERN_LIBRARY.get(pattern_id) or PATTERN_LIBRARY[DEFAULT_PATTERN_TEMPLATE]


__all__ = [
    "PromptTemplate",
    "PatternHit",
    "PatternTemplateDefinition",
    "PROMPT_TEMPLATES",
    "PATTERN_LIBRARY",
    "DEFAULT_PERSONA_ID",
    "DEFAULT_STYLE_PACK",
    "DEFAULT_PATTERN_TEMPLATE",
    "get_template_by_token",
    "get_pattern",
]

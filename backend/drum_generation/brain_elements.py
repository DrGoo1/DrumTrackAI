"""Jamstix-style brain element registry.

Provides structured metadata for the Drum Builder "brain" panel so the
frontend can render the proper controls and the backend can merge overrides
into performance specs.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional

from .drum_generation_config import BrainElementSetting


@dataclass(frozen=True)
class BrainElementDefinition:
    """Describes a single adjustable brain element."""

    id: str
    label: str
    description: str
    min_value: float = 0.0
    max_value: float = 1.0
    default_value: float = 0.5
    supports_freeze: bool = True
    supports_disable: bool = True
    grouping: str = "core"


# Base registry shared across most styles. Individual drummer/style layers can
# tweak defaults or limit availability by overriding `STYLE_OVERRIDES`.
BASE_BRAIN_ELEMENTS: Dict[str, BrainElementDefinition] = {
    "feel_processor": BrainElementDefinition(
        id="feel_processor",
        label="Feel Processor",
        description="Controls pocket, timing variance, and power variance",
        min_value=-1.0,
        max_value=1.0,
        default_value=0.0,
        grouping="timing",
    ),
    "redirection": BrainElementDefinition(
        id="redirection",
        label="Redirection",
        description="Routes one limb's pattern to an alternate instrument",
        grouping="kit",
    ),
    "power_hand": BrainElementDefinition(
        id="power_hand",
        label="Power Hand",
        description="Switches hats to ride/crash when power exceeds threshold",
        grouping="kit",
    ),
    "reduction": BrainElementDefinition(
        id="reduction",
        label="Reduction",
        description="Drops notes as intensity falls for softer sections",
        grouping="dynamics",
    ),
    "auto_snare": BrainElementDefinition(
        id="auto_snare",
        label="Auto Snare",
        description="Switch between sidestick and center hits based on power",
        grouping="kit",
    ),
    "ghost_density": BrainElementDefinition(
        id="ghost_density",
        label="Ghost Density",
        description="Adds or removes ghost-note articulations",
        grouping="dynamics",
    ),
    "fill_aggression": BrainElementDefinition(
        id="fill_aggression",
        label="Fill Aggression",
        description="Controls how busy Jamstix-style fills are",
        grouping="fills",
    ),
    "hat_openness": BrainElementDefinition(
        id="hat_openness",
        label="Hat Openness",
        description="Bias toward more open or tight hi-hat articulations",
        grouping="kit",
    ),
}


STYLE_OVERRIDES: Dict[str, Dict[str, BrainElementDefinition]] = {
    # Example: funk styles expose deeper ghost control and limit reduction.
    "funk": {
        "ghost_density": BrainElementDefinition(
            id="ghost_density",
            label="Ghost Density",
            description="Funk ghost articulation depth",
            min_value=0.0,
            max_value=1.5,
            default_value=0.9,
            grouping="dynamics",
        ),
    },
    "metal": {
        "power_hand": BrainElementDefinition(
            id="power_hand",
            label="Power Hand",
            description="Aggressive ride/crash toggling for metal choruses",
            default_value=0.8,
            grouping="kit",
        ),
        "ghost_density": BrainElementDefinition(
            id="ghost_density",
            label="Ghost Density",
            description="Metal grooves often suppress ghosts",
            default_value=0.2,
        ),
    },
}


def get_brain_elements(style: Optional[str] = None) -> List[BrainElementDefinition]:
    """Return the list of applicable brain elements for a style."""

    elements = dict(BASE_BRAIN_ELEMENTS)
    if style and style in STYLE_OVERRIDES:
        elements.update(STYLE_OVERRIDES[style])
    return list(elements.values())


def merge_brain_settings(
    defaults: Iterable[BrainElementDefinition],
    overrides: Optional[Iterable[BrainElementSetting]],
) -> Dict[str, float]:
    """Combine default element values with user overrides.

    Returns a {element_id: value} map ready for downstream use.
    """

    definition_map = {elem.id: elem for elem in defaults}
    merged: Dict[str, float] = {elem_id: definition_map[elem_id].default_value for elem_id in definition_map}
    if not overrides:
        return merged

    for setting in overrides:
        if setting.disabled:
            continue
        definition = definition_map.get(setting.elementId)
        min_val = definition.min_value if definition else 0.0
        max_val = definition.max_value if definition else 1.0
        merged[setting.elementId] = max(min(setting.value, max_val), min_val)
    return merged

# backend/drum_generation/part_types_config.py
"""
Jamstix-inspired part type presets for song sections.

Each part type defines default behavior for intensity, variation, fills,
power hand (primary cymbal), and groove profile.
"""

from dataclasses import dataclass
from typing import Dict, Optional

@dataclass
class PartTypePreset:
    """
    Defines default characteristics for a song part type.
    Inspired by Jamstix Song Builder part presets.
    """
    id: str
    label: str
    defaultLengthBars: int
    defaultStyle: Optional[str]
    defaultDrummer: Optional[str]
    defaultIntensity: float           # 0.0 - 1.0
    defaultVariation: float           # 0.0 - 1.0
    defaultFillDensity: float         # 0.0 - 1.0 (how often fills occur)
    defaultPowerHand: Optional[str]   # Primary cymbal: "hihat_closed", "ride_bow", etc.
    defaultGrooveProfile: str         # Groove feel identifier


# Part type presets dictionary
PART_TYPES: Dict[str, PartTypePreset] = {
    "intro": PartTypePreset(
        id="intro",
        label="Intro",
        defaultLengthBars=4,
        defaultStyle=None,
        defaultDrummer=None,
        defaultIntensity=0.4,
        defaultVariation=0.3,
        defaultFillDensity=0.2,
        defaultPowerHand="hihat_closed",
        defaultGrooveProfile="simple_backbeat",
    ),
    "verse": PartTypePreset(
        id="verse",
        label="Verse",
        defaultLengthBars=8,
        defaultStyle=None,
        defaultDrummer=None,
        defaultIntensity=0.6,
        defaultVariation=0.4,
        defaultFillDensity=0.3,
        defaultPowerHand="hihat_closed",
        defaultGrooveProfile="tight_backbeat",
    ),
    "prechorus": PartTypePreset(
        id="prechorus",
        label="Pre-Chorus",
        defaultLengthBars=4,
        defaultStyle=None,
        defaultDrummer=None,
        defaultIntensity=0.7,
        defaultVariation=0.5,
        defaultFillDensity=0.5,
        defaultPowerHand="hihat_open",
        defaultGrooveProfile="build_up",
    ),
    "chorus": PartTypePreset(
        id="chorus",
        label="Chorus",
        defaultLengthBars=8,
        defaultStyle=None,
        defaultDrummer=None,
        defaultIntensity=0.9,
        defaultVariation=0.6,
        defaultFillDensity=0.6,
        defaultPowerHand="ride_bow",
        defaultGrooveProfile="open_crash",
    ),
    "bridge": PartTypePreset(
        id="bridge",
        label="Bridge",
        defaultLengthBars=8,
        defaultStyle=None,
        defaultDrummer=None,
        defaultIntensity=0.7,
        defaultVariation=0.7,
        defaultFillDensity=0.5,
        defaultPowerHand="ride_bow",
        defaultGrooveProfile="exploratory",
    ),
    "solo": PartTypePreset(
        id="solo",
        label="Solo",
        defaultLengthBars=8,
        defaultStyle=None,
        defaultDrummer=None,
        defaultIntensity=0.8,
        defaultVariation=0.8,
        defaultFillDensity=0.7,
        defaultPowerHand="ride_bow",
        defaultGrooveProfile="open_and_varied",
    ),
    "drum_solo": PartTypePreset(
        id="drum_solo",
        label="Drum Solo",
        defaultLengthBars=4,
        defaultStyle=None,
        defaultDrummer=None,
        defaultIntensity=0.95,
        defaultVariation=0.9,
        defaultFillDensity=1.0,
        defaultPowerHand=None,
        defaultGrooveProfile="full_kit_showcase",
    ),
    "breakdown": PartTypePreset(
        id="breakdown",
        label="Breakdown",
        defaultLengthBars=4,
        defaultStyle=None,
        defaultDrummer=None,
        defaultIntensity=0.5,
        defaultVariation=0.6,
        defaultFillDensity=0.3,
        defaultPowerHand="hihat_closed",
        defaultGrooveProfile="sparse_syncopated",
    ),
    "buildup": PartTypePreset(
        id="buildup",
        label="Build-Up",
        defaultLengthBars=2,
        defaultStyle=None,
        defaultDrummer=None,
        defaultIntensity=0.75,
        defaultVariation=0.5,
        defaultFillDensity=0.8,
        defaultPowerHand="crash_1",
        defaultGrooveProfile="crescendo_fill",
    ),
    "outro": PartTypePreset(
        id="outro",
        label="Outro",
        defaultLengthBars=4,
        defaultStyle=None,
        defaultDrummer=None,
        defaultIntensity=0.5,
        defaultVariation=0.3,
        defaultFillDensity=0.2,
        defaultPowerHand="hihat_closed",
        defaultGrooveProfile="fade_out",
    ),
    "stop": PartTypePreset(
        id="stop",
        label="Stop",
        defaultLengthBars=1,
        defaultStyle=None,
        defaultDrummer=None,
        defaultIntensity=0.0,
        defaultVariation=0.0,
        defaultFillDensity=0.0,
        defaultPowerHand=None,
        defaultGrooveProfile="silence",
    ),
    "interlude": PartTypePreset(
        id="interlude",
        label="Interlude",
        defaultLengthBars=4,
        defaultStyle=None,
        defaultDrummer=None,
        defaultIntensity=0.55,
        defaultVariation=0.5,
        defaultFillDensity=0.4,
        defaultPowerHand="ride_bow",
        defaultGrooveProfile="atmospheric",
    ),
}


def get_part_type_preset(part_type_id: str) -> PartTypePreset:
    """
    Get part type preset by ID.
    
    Args:
        part_type_id: Part type identifier (e.g., "verse", "chorus")
        
    Returns:
        PartTypePreset for the given ID, or "verse" preset as default
    """
    # Normalize ID (lowercase, strip whitespace)
    normalized_id = part_type_id.lower().strip()
    
    # Try direct match
    if normalized_id in PART_TYPES:
        return PART_TYPES[normalized_id]
    
    # Try partial match (e.g., "pre-chorus" → "prechorus")
    normalized_id_no_hyphen = normalized_id.replace("-", "").replace("_", "")
    for key, preset in PART_TYPES.items():
        if key.replace("-", "").replace("_", "") == normalized_id_no_hyphen:
            return preset
    
    # Default to verse if no match
    return PART_TYPES["verse"]


def list_part_types() -> list[str]:
    """Get list of all available part type IDs."""
    return list(PART_TYPES.keys())


def get_part_type_label(part_type_id: str) -> str:
    """Get human-readable label for a part type."""
    preset = get_part_type_preset(part_type_id)
    return preset.label


# Convenience function for applying part type defaults to config
def apply_part_type_defaults(config_dict: dict, part_type_id: str) -> dict:
    """
    Apply part type preset defaults to a configuration dictionary.
    Only overwrites fields that are not already set.
    
    Args:
        config_dict: Configuration dictionary to update
        part_type_id: Part type to apply
        
    Returns:
        Updated configuration dictionary
    """
    preset = get_part_type_preset(part_type_id)
    
    # Apply defaults only if not already set
    if "intensity" not in config_dict or config_dict["intensity"] is None:
        config_dict["intensity"] = preset.defaultIntensity
    
    if "variation" not in config_dict or config_dict["variation"] is None:
        config_dict["variation"] = preset.defaultVariation
    
    if "fillDensity" not in config_dict or config_dict.get("fillDensity") is None:
        config_dict["fillDensity"] = preset.defaultFillDensity
    
    if "powerHand" not in config_dict or config_dict.get("powerHand") is None:
        config_dict["powerHand"] = preset.defaultPowerHand
    
    if "grooveProfile" not in config_dict or config_dict.get("grooveProfile") is None:
        config_dict["grooveProfile"] = preset.defaultGrooveProfile
    
    return config_dict

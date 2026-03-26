#!/usr/bin/env python3
"""
Jamstix-Style Performance Spec Generator
=========================================
Generates performanceSpec (microtiming, velocity, feel) 
inspired by Jamstix brain logic
"""
from typing import Dict, Any, List
from dataclasses import dataclass
import json

@dataclass
class PerformanceProfile:
    """Performance characteristics for an instrument"""
    instrument_id: str
    micro_timing_offsets: List[float]  # ms per subdivision
    laid_back_amount: float  # 0.0-1.0
    velocity_base: int  # 1-127
    velocity_accent_boost: int  # added to accents
    velocity_ghost_reduction: float  # multiplier for ghosts
    velocity_random_range: int  # ±range
    phrase_shape: str  # "flat", "swell", "decay"

def generate_performance_spec(
    style: str,
    drummer_profile: str,
    intensity: float,
    variation: float,
    swing: float,
    section_type: str = "verse"
) -> Dict[str, Any]:
    """
    Generate Jamstix-style performance spec
    
    Args:
        style: "rock", "funk", "jazz", "latin"
        drummer_profile: "bonham", "purdie", "gadd", "porcaro"
        intensity: 0.0-1.0 (how hard to hit)
        variation: 0.0-1.0 (humanization amount)
        swing: 0.0-1.0 (swing amount)
        section_type: "intro", "verse", "chorus", "bridge", "outro"
    
    Returns:
        Complete performanceSpec dict
    """
    
    # Determine global feel
    if swing > 0.5:
        global_feel = "swing"
    elif drummer_profile in ("bonham", "porcaro"):
        global_feel = "laid_back"
    elif drummer_profile == "purdie":
        global_feel = "on_the_pocket"
    else:
        global_feel = "on_the_beat"
    
    # Base velocity by style and intensity
    base_velocity = int(80 + (intensity * 35))
    
    # Profiles per instrument
    profiles = []
    
    # Snare profile
    snare_profile = {
        "instrumentId": "snare_center",
        "microTiming": {
            "subdivisionOffsetsMs": _generate_timing_offsets(
                global_feel, swing, variation, "snare"
            ),
            "laidBackAmount": 0.4 if global_feel == "laid_back" else 0.1,
            "swingAmount": swing
        },
        "velocityProfile": {
            "base": base_velocity + 10,  # Snare slightly louder
            "accentBoost": int(15 + (intensity * 10)),
            "ghostReduction": 0.3,
            "randomRange": int(3 + (variation * 8)),
            "phraseShape": _get_phrase_shape(section_type)
        },
        "ghostDensity": 0.6 if style == "funk" else 0.2,
        "flamProbability": 0.15 if drummer_profile == "gadd" else 0.05,
        "dragProbability": 0.05
    }
    profiles.append(snare_profile)
    
    # Kick profile
    kick_profile = {
        "instrumentId": "kick",
        "microTiming": {
            "subdivisionOffsetsMs": _generate_timing_offsets(
                global_feel, swing, variation, "kick"
            ),
            "laidBackAmount": 0.2 if global_feel == "laid_back" else 0.0,
            "swingAmount": swing * 0.5  # Less swing on kick
        },
        "velocityProfile": {
            "base": base_velocity + 15,  # Kick loudest
            "accentBoost": int(12 + (intensity * 8)),
            "ghostReduction": 0.5,
            "randomRange": int(2 + (variation * 6)),
            "phraseShape": "flat"
        }
    }
    profiles.append(kick_profile)
    
    # Hi-hat profile
    hihat_profile = {
        "instrumentId": "hihat_closed",
        "microTiming": {
            "subdivisionOffsetsMs": _generate_timing_offsets(
                global_feel, swing, variation, "hihat"
            ),
            "laidBackAmount": 0.3 if global_feel == "laid_back" else 0.0,
            "swingAmount": swing
        },
        "velocityProfile": {
            "base": base_velocity - 15,  # Hats quieter
            "accentBoost": int(8 + (intensity * 6)),
            "ghostReduction": 0.4,
            "randomRange": int(4 + (variation * 10)),
            "phraseShape": "flat"
        },
        "ghostDensity": 0.3,
        "opennessVariation": variation * 0.5
    }
    profiles.append(hihat_profile)
    
    # Ride profile (for jazz/rock)
    if style in ("jazz", "rock"):
        ride_profile = {
            "instrumentId": "ride_bow",
            "microTiming": {
                "subdivisionOffsetsMs": _generate_timing_offsets(
                    global_feel, swing, variation, "ride"
                ),
                "laidBackAmount": 0.2,
                "swingAmount": swing * 1.2 if style == "jazz" else swing
            },
            "velocityProfile": {
                "base": base_velocity - 10,
                "accentBoost": int(6 + (intensity * 5)),
                "ghostReduction": 0.5,
                "randomRange": int(3 + (variation * 7)),
                "phraseShape": "swell" if style == "jazz" else "flat"
            }
        }
        profiles.append(ride_profile)
    
    # Build complete spec
    spec = {
        "globalFeel": global_feel,
        "quantizationBase": "16th",
        "phrases": [
            {
                "phraseId": f"{section_type}_main",
                "barStart": 0,
                "barEnd": 7,
                "profiles": profiles
            }
        ]
    }
    
    return spec

def _generate_timing_offsets(
    feel: str,
    swing: float,
    variation: float,
    instrument: str
) -> List[float]:
    """Generate microtiming offsets for 16 subdivisions"""
    offsets = [0.0] * 16
    
    if feel == "laid_back":
        # Delay certain subdivisions
        for i in range(16):
            if i % 4 in (2, 3):  # Off-beats
                offsets[i] = 5.0 + (variation * 8.0)
    
    elif feel == "swing":
        # Swing: delay off-beats
        for i in range(16):
            if i % 2 == 1:  # Off-beats
                offsets[i] = 10.0 + (swing * 25.0)
    
    # Add humanization
    for i in range(16):
        offsets[i] += (variation * 5.0) * (0.5 if i % 2 == 0 else -0.5)
    
    return offsets

def _get_phrase_shape(section_type: str) -> str:
    """Get velocity phrase shape for section"""
    if section_type == "intro":
        return "swell"
    elif section_type == "chorus":
        return "flat"  # Consistent loud
    elif section_type == "outro":
        return "decay"
    else:
        return "flat"

# Example usage
if __name__ == "__main__":
    spec = generate_performance_spec(
        style="rock",
        drummer_profile="bonham",
        intensity=0.9,
        variation=0.7,
        swing=0.1,
        section_type="chorus"
    )
    
    print(json.dumps(spec, indent=2))

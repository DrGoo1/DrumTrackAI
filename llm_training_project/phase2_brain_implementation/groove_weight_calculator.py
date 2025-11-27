#!/usr/bin/env python3
"""
Jamstix-Style Groove Weight Calculator
=======================================
Calculates "weight" or emphasis for different parts of the bar,
inspired by Jamstix's groove weight system
"""
from typing import List, Dict
import math

def calculate_groove_weights(
    time_signature: str,
    style: str,
    emphasis_pattern: str = "standard"
) -> List[float]:
    """
    Calculate groove weights for each 16th note subdivision
    
    Args:
        time_signature: "4/4", "3/4", "6/8", etc.
        style: "rock", "funk", "jazz", "latin"
        emphasis_pattern: "standard", "offbeat", "syncopated"
    
    Returns:
        List of weights (0.0-1.0) for each 16th note in a bar
    """
    
    numerator, denominator = map(int, time_signature.split('/'))
    
    # Number of 16th notes per bar
    sixteenths_per_bar = (numerator * 16) // denominator
    
    weights = [0.5] * sixteenths_per_bar  # Start with neutral
    
    if time_signature == "4/4":
        weights = _calculate_4_4_weights(style, emphasis_pattern, sixteenths_per_bar)
    elif time_signature == "3/4":
        weights = _calculate_3_4_weights(style, emphasis_pattern, sixteenths_per_bar)
    elif time_signature == "6/8":
        weights = _calculate_6_8_weights(style, emphasis_pattern, sixteenths_per_bar)
    
    return weights

def _calculate_4_4_weights(style: str, emphasis: str, length: int) -> List[float]:
    """Calculate weights for 4/4 time"""
    weights = [0.5] * length  # 16 subdivisions
    
    if emphasis == "standard":
        # Strong beats: 1, 3
        weights[0] = 1.0   # Beat 1
        weights[8] = 0.8   # Beat 3
        
        # Backbeat: 2, 4
        weights[4] = 0.9   # Beat 2
        weights[12] = 0.9  # Beat 4
        
        # Eighth note upbeats
        weights[2] = 0.6
        weights[6] = 0.6
        weights[10] = 0.6
        weights[14] = 0.6
    
    elif emphasis == "offbeat":
        # Emphasis on off-beats (funk style)
        for i in range(length):
            if i % 4 in (1, 3):  # Off-beat 16ths
                weights[i] = 0.8
            elif i % 4 == 2:  # And of beat
                weights[i] = 0.7
            else:
                weights[i] = 0.5
    
    elif emphasis == "syncopated":
        # Syncopated pattern
        weights[0] = 1.0   # 1
        weights[3] = 0.8   # e&
        weights[6] = 0.7   # &of2
        weights[9] = 0.6   # e&of3
        weights[12] = 0.9  # 4
    
    # Style-specific adjustments
    if style == "funk":
        # Emphasize the "1" more
        weights[0] = 1.0
        weights[4] = 0.7  # De-emphasize beat 2
    
    elif style == "jazz":
        # Swing feel - emphasize beats 2 and 4
        weights[4] = 1.0
        weights[12] = 1.0
    
    elif style == "rock":
        # Strong backbeat
        weights[4] = 1.0
        weights[12] = 1.0
    
    return weights

def _calculate_3_4_weights(style: str, emphasis: str, length: int) -> List[float]:
    """Calculate weights for 3/4 time (waltz)"""
    weights = [0.5] * length  # 12 subdivisions
    
    # Beat 1 is strongest in 3/4
    weights[0] = 1.0
    weights[4] = 0.6  # Beat 2
    weights[8] = 0.6  # Beat 3
    
    return weights

def _calculate_6_8_weights(style: str, emphasis: str, length: int) -> List[float]:
    """Calculate weights for 6/8 time"""
    weights = [0.5] * length
    
    # Two main pulses in 6/8
    weights[0] = 1.0   # Beat 1
    weights[12] = 0.9  # Beat 4 (second pulse)
    
    # Triplet feel
    for i in [4, 8, 16, 20]:
        if i < length:
            weights[i] = 0.7
    
    return weights

def apply_groove_weights_to_velocities(
    hits: List[Dict],
    groove_weights: List[float],
    base_velocity: int = 100,
    weight_influence: float = 0.5
) -> List[Dict]:
    """
    Apply groove weights to hit velocities
    
    Args:
        hits: List of drum hits with beat_position
        groove_weights: Weight for each 16th note
        base_velocity: Base velocity (before weighting)
        weight_influence: 0.0-1.0 how much weights affect velocity
    
    Returns:
        Hits with adjusted velocities
    """
    
    for hit in hits:
        beat_pos = hit.get("beat_position", 0)
        
        # Find closest 16th note
        sixteenth_index = int((beat_pos * 4) % len(groove_weights))
        weight = groove_weights[sixteenth_index]
        
        # Adjust velocity based on weight
        velocity_adjustment = (weight - 0.5) * 2 * weight_influence  # -1 to +1
        adjusted_velocity = base_velocity + int(velocity_adjustment * 30)
        
        # Clamp to valid range
        hit["velocity"] = max(20, min(127, adjusted_velocity))
    
    return hits

def visualize_groove_weights(weights: List[float], time_signature: str):
    """Print ASCII visualization of groove weights"""
    print(f"\nGroove Weights for {time_signature}:")
    print("Beat: ", end="")
    
    numerator = int(time_signature.split('/')[0])
    for beat in range(1, numerator + 1):
        print(f" {beat}   ", end="")
    print()
    
    print("      ", end="")
    for i, weight in enumerate(weights):
        bar_length = int(weight * 10)
        bar = "█" * bar_length + "░" * (10 - bar_length)
        print(bar, end=" ")
        if (i + 1) % 4 == 0:
            print("  ", end="")
    print()

# Example usage
if __name__ == "__main__":
    # Calculate weights for different styles
    rock_weights = calculate_groove_weights("4/4", "rock", "standard")
    funk_weights = calculate_groove_weights("4/4", "funk", "offbeat")
    
    visualize_groove_weights(rock_weights, "4/4")
    visualize_groove_weights(funk_weights, "4/4")
    
    # Example: apply weights to hits
    test_hits = [
        {"instrument_id": "kick", "beat_position": 0.0},
        {"instrument_id": "snare", "beat_position": 1.0},
        {"instrument_id": "kick", "beat_position": 2.0},
        {"instrument_id": "snare", "beat_position": 3.0}
    ]
    
    weighted_hits = apply_groove_weights_to_velocities(
        test_hits, rock_weights, base_velocity=100, weight_influence=0.7
    )
    
    print("\nWeighted Hits:")
    for hit in weighted_hits:
        print(f"  {hit['instrument_id']}: beat {hit['beat_position']}, velocity {hit['velocity']}")

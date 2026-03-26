# backend/drum_generation/power_model.py
"""
Power modeling from guide track analysis.

Computes per-bar power/intensity values by combining guide track RMS
analysis with user intensity controls. Used to drive dynamic drum generation.
"""

from typing import List, Optional
import numpy as np


def compute_power_curve_from_guide(
    rms_values: List[float],
    user_intensity: float,
    smoothing_window: int = 3,
) -> List[float]:
    """
    Compute a per-bar power value (0..1) from guide RMS and user intensity.
    
    The power curve represents the dynamic intensity of the music over time,
    combining the guide track's actual loudness with the user's desired
    intensity level.
    
    Args:
        rms_values: RMS (root mean square) values per bar from guide track
        user_intensity: User's intensity setting (0..1, where 1 is most aggressive)
        smoothing_window: Number of bars to smooth over (default 3)
        
    Returns:
        List of per-bar power values (0..1), same length as rms_values
        
    Example:
        >>> rms = [0.2, 0.3, 0.5, 0.7, 0.6]
        >>> power = compute_power_curve_from_guide(rms, user_intensity=0.7)
        >>> # power will range from ~0.3 to 0.9 based on RMS and intensity
    """
    if not rms_values:
        # No guide data: return constant user intensity
        return [user_intensity]
    
    rms_arr = np.array(rms_values, dtype=np.float32)
    
    # Normalize RMS to 0..1 range
    if rms_arr.max() > 0:
        rms_norm = rms_arr / rms_arr.max()
    else:
        rms_norm = np.zeros_like(rms_arr)
    
    # Apply smoothing to reduce sharp jumps
    if smoothing_window > 1 and len(rms_norm) >= smoothing_window:
        kernel = np.ones(smoothing_window) / smoothing_window
        rms_smooth = np.convolve(rms_norm, kernel, mode='same')
    else:
        rms_smooth = rms_norm
    
    # Combine with user intensity
    # Formula: base_floor + (user_intensity * normalized_rms)
    # This ensures minimum intensity while scaling with guide track
    base_floor = 0.2  # Minimum power level
    intensity_range = 0.8  # Available range above floor
    
    power = base_floor + (intensity_range * user_intensity * rms_smooth)
    
    # Clip to valid range
    power = np.clip(power, 0.0, 1.0)
    
    return power.tolist()


def compute_power_curve_from_sections(
    section_energies: List[float],
    bars_per_section: List[int],
    user_intensity: float,
) -> List[float]:
    """
    Compute power curve from section-level energy estimates.
    
    Useful when you have pre-analyzed sections (intro, verse, chorus, etc.)
    with energy levels, but need per-bar power values.
    
    Args:
        section_energies: Energy level (0..1) for each section
        bars_per_section: Number of bars in each section
        user_intensity: User's intensity setting (0..1)
        
    Returns:
        List of per-bar power values (0..1)
        
    Example:
        >>> energies = [0.4, 0.6, 0.9]  # intro, verse, chorus
        >>> bars = [4, 8, 8]
        >>> power = compute_power_curve_from_sections(energies, bars, 0.7)
        >>> # power will have 20 values (4+8+8), with chorus bars at highest
    """
    if len(section_energies) != len(bars_per_section):
        raise ValueError("section_energies and bars_per_section must have same length")
    
    power = []
    for energy, num_bars in zip(section_energies, bars_per_section):
        # Combine section energy with user intensity
        section_power = 0.2 + (0.8 * user_intensity * energy)
        section_power = np.clip(section_power, 0.0, 1.0)
        
        # Add per-bar values for this section
        power.extend([section_power] * num_bars)
    
    return power


def interpolate_power_curve(
    power_values: List[float],
    target_length: int,
    method: str = "linear",
) -> List[float]:
    """
    Interpolate power curve to match target length.
    
    Useful when you have coarse power estimates (e.g., per 4 bars)
    but need finer resolution (e.g., per bar).
    
    Args:
        power_values: Original power values
        target_length: Desired output length
        method: Interpolation method ("linear", "nearest", "cubic")
        
    Returns:
        Interpolated power values of length target_length
    """
    if len(power_values) == target_length:
        return power_values
    
    if len(power_values) == 0:
        return [0.5] * target_length
    
    x_orig = np.linspace(0, 1, len(power_values))
    x_target = np.linspace(0, 1, target_length)
    
    if method == "nearest":
        # Nearest neighbor
        indices = np.round(x_target * (len(power_values) - 1)).astype(int)
        result = [power_values[i] for i in indices]
    elif method == "cubic" and len(power_values) >= 4:
        # Cubic interpolation (requires at least 4 points)
        from scipy.interpolate import interp1d
        f = interp1d(x_orig, power_values, kind='cubic', fill_value='extrapolate')
        result = np.clip(f(x_target), 0.0, 1.0).tolist()
    else:
        # Linear interpolation (default)
        result = np.interp(x_target, x_orig, power_values).tolist()
    
    return result


def analyze_power_transitions(
    power_values: List[float],
    threshold: float = 0.2,
) -> List[tuple]:
    """
    Detect significant power transitions (builds/drops).
    
    Useful for identifying build-ups, breakdowns, and section changes
    that might need special fill or transition handling.
    
    Args:
        power_values: Per-bar power values
        threshold: Minimum change to consider significant (0..1)
        
    Returns:
        List of (bar_index, change_amount, transition_type) tuples
        transition_type is "build" (positive) or "drop" (negative)
        
    Example:
        >>> power = [0.4, 0.4, 0.5, 0.7, 0.9, 0.5, 0.4]
        >>> transitions = analyze_power_transitions(power, threshold=0.2)
        >>> # Returns: [(3, 0.4, "build"), (5, -0.4, "drop")]
    """
    if len(power_values) < 2:
        return []
    
    transitions = []
    prev_power = power_values[0]
    
    for i, power in enumerate(power_values[1:], start=1):
        change = power - prev_power
        
        if abs(change) >= threshold:
            transition_type = "build" if change > 0 else "drop"
            transitions.append((i, change, transition_type))
        
        prev_power = power
    
    return transitions


def power_to_velocity_scale(power: float) -> float:
    """
    Convert power value to velocity scale factor.
    
    Used to adjust MIDI velocities based on power curve.
    
    Args:
        power: Power value (0..1)
        
    Returns:
        Velocity scale factor (0.5..1.3)
        
    Example:
        >>> scale = power_to_velocity_scale(0.9)  # High power
        >>> adjusted_vel = int(base_velocity * scale)
    """
    # Map power 0..1 to velocity scale 0.5..1.3
    # Low power: reduce velocities
    # High power: boost velocities
    min_scale = 0.5
    max_scale = 1.3
    return min_scale + (max_scale - min_scale) * power


def power_to_fill_probability(power: float, base_probability: float = 0.3) -> float:
    """
    Convert power value to fill probability.
    
    Higher power → more frequent fills.
    
    Args:
        power: Power value (0..1)
        base_probability: Base fill probability (0..1)
        
    Returns:
        Adjusted fill probability (0..1)
    """
    # Higher power increases fill probability
    # Formula: base + (power * additional_probability)
    additional_probability = 0.5
    return np.clip(base_probability + (power * additional_probability), 0.0, 1.0)


def power_to_ghost_note_density(power: float, base_density: float = 0.3) -> float:
    """
    Convert power value to ghost note density.
    
    Medium power tends to have more ghost notes (groove).
    Very high or very low power reduces ghost notes.
    
    Args:
        power: Power value (0..1)
        base_density: Base ghost note density (0..1)
        
    Returns:
        Adjusted ghost note density (0..1)
    """
    # Ghost notes are most prominent in medium-intensity playing
    # Create a curve that peaks around 0.6-0.7 power
    optimal_power = 0.65
    distance_from_optimal = abs(power - optimal_power)
    
    # Gaussian-like curve
    ghost_factor = np.exp(-4 * (distance_from_optimal ** 2))
    
    return base_density + (0.4 * ghost_factor)

"""
Drum Generation API - Integrates all analytics and generation tools
Connects: Rust audio-core, Drummer DB, GrooVAE AI, Humanization
"""

import json
import time
import numpy as np
from typing import List, Dict, Tuple
from pathlib import Path

# Import existing tools
from drummer_mapping_service import get_drummer_service
from ai_pattern_generator import AIPatternGenerator

# Drum generation configuration
class DrumGenerationConfig:
    def __init__(self, data: Dict):
        self.section_id = data['sectionId']
        self.start_measure = data['startMeasure']
        self.end_measure = data['endMeasure']
        self.tempos = data['tempos']  # BPM per measure
        self.time_signature = tuple(data['timeSignature'])
        self.style = data['style']
        self.drummer = data['drummer']
        self.intensity = data['intensity']  # 0.0-1.0
        self.variation = data['variation']  # 0.0-1.0
        self.generation_mode = data['generationMode']  # 'template', 'ai_variation', 'full_ai'
        self.humanize = data['humanize']
        self.fill_locations = data.get('fillLocations', [])
        self.fill_type = data.get('fillType', 'auto')
    
    @property
    def measure_count(self) -> int:
        return self.end_measure - self.start_measure


def generate_drums(config: DrumGenerationConfig) -> Dict:
    """
    Main drum generation function - integrates all tools
    
    Returns:
    {
        'midi_notes': [...],
        'midi_base64': '...',
        'metadata': {...}
    }
    """
    start_time = time.time()
    
    # 1. Get drummer profile from database
    drummer_service = get_drummer_service()
    drummer_profile = drummer_service.get_drummer_by_name(config.drummer)
    
    if not drummer_profile:
        # Fallback to generic style
        drummer_profile = {'style': config.style, 'name': 'Generic'}
    
    # 2. Generate pattern based on mode
    if config.generation_mode == 'template':
        pattern = generate_from_template(config, drummer_profile)
    elif config.generation_mode == 'ai_variation':
        pattern = generate_ai_variation(config, drummer_profile)
    elif config.generation_mode == 'full_ai':
        pattern = generate_full_ai(config, drummer_profile)
    else:
        raise ValueError(f"Unknown generation mode: {config.generation_mode}")
    
    # 3. Adapt to per-measure tempo
    pattern = adapt_to_tempo_changes(pattern, config)
    
    # 4. Add fills at specified locations
    pattern = add_fills(pattern, config)
    
    # 5. Humanize if requested
    if config.humanize:
        pattern = humanize_pattern(pattern, amount=0.7)
    
    # 6. Convert to MIDI format
    midi_notes = pattern_to_midi_notes(pattern)
    midi_base64 = pattern_to_midi_base64(pattern, config)
    
    generation_time_ms = (time.time() - start_time) * 1000
    
    return {
        'midi_notes': midi_notes,
        'midi_base64': midi_base64,
        'metadata': {
            'generation_time_ms': round(generation_time_ms, 1),
            'drummer_used': drummer_profile.get('name', config.drummer),
            'style': config.style,
            'mode': config.generation_mode,
            'humanized': config.humanize,
            'measure_count': config.measure_count,
            'tempo_range': f"{min(config.tempos):.0f}-{max(config.tempos):.0f} BPM"
        }
    }


def generate_from_template(config: DrumGenerationConfig, drummer_profile: Dict) -> np.ndarray:
    """
    Generate from pre-computed template pattern (FAST)
    Uses drummer database patterns
    """
    import subprocess
    
    # Use existing Rust audio-core generation
    avg_tempo = sum(config.tempos) / len(config.tempos)
    
    # Call Rust CLI
    result = subprocess.run([
        'target/release/audio-core.exe',
        'generate-json',
        '--bpm', str(avg_tempo),
        '--bars', str(config.measure_count),
        '--density', str(config.intensity),
        '--style', config.style,
        '--label', config.section_id.split('-')[0] if '-' in config.section_id else 'verse',
        '--swing-preset', 'off',
        '--vel-preset', 'accent24',
        '--fill-preset', 'none'  # We'll add fills separately
    ], capture_output=True, text=True)
    
    if result.returncode != 0:
        raise Exception(f"Rust generation failed: {result.stderr}")
    
    # Parse JSON output
    pattern_data = json.loads(result.stdout)
    
    # Convert to numpy array for processing
    pattern = json_to_pattern_array(pattern_data)
    
    return pattern


def generate_ai_variation(config: DrumGenerationConfig, drummer_profile: Dict) -> np.ndarray:
    """
    Generate AI variation of template (MEDIUM)
    Uses GrooVAE to create variation
    """
    # 1. Get base template
    base_pattern = generate_from_template(config, drummer_profile)
    
    # 2. Apply AI variation using GrooVAE
    try:
        ai_gen = AIPatternGenerator()
        
        # Convert pattern to GrooVAE format
        pattern_tensor = pattern_array_to_groovae_format(base_pattern)
        
        # Generate variation
        varied_pattern = ai_gen.vary_pattern(
            base_pattern=pattern_tensor,
            variation_amount=config.variation
        )
        
        # Convert back
        pattern = groovae_to_pattern_array(varied_pattern)
        
    except Exception as e:
        print(f"⚠️ AI variation failed: {e}, using template")
        pattern = base_pattern
    
    return pattern


def generate_full_ai(config: DrumGenerationConfig, drummer_profile: Dict) -> np.ndarray:
    """
    Generate completely new pattern with AI (SLOW)
    Full GrooVAE generation from scratch
    """
    try:
        ai_gen = AIPatternGenerator()
        
        # Create style embedding
        style_embedding = create_style_embedding(
            style=config.style,
            drummer=drummer_profile,
            intensity=config.intensity
        )
        
        # Generate from scratch
        pattern_tensor = ai_gen.generate_pattern(
            temperature=1.0 + config.variation,
            bars=config.measure_count,
            style_embedding=style_embedding
        )
        
        # Convert to pattern array
        pattern = groovae_to_pattern_array(pattern_tensor)
        
    except Exception as e:
        print(f"⚠️ Full AI generation failed: {e}, using template")
        pattern = generate_from_template(config, drummer_profile)
    
    return pattern


def adapt_to_tempo_changes(pattern: np.ndarray, config: DrumGenerationConfig) -> np.ndarray:
    """
    Adapt pattern to per-measure tempo changes
    Critical for handling tempo variations
    """
    if len(set(config.tempos)) == 1:
        # All same tempo, no adaptation needed
        return pattern
    
    # Pattern format: [time, drum_type, velocity]
    # Each measure should scale to its tempo
    
    avg_tempo = sum(config.tempos) / len(config.tempos)
    notes_per_measure = len(pattern) // config.measure_count
    
    adapted_pattern = []
    time_offset = 0.0
    
    for measure_idx in range(config.measure_count):
        measure_tempo = config.tempos[measure_idx]
        tempo_ratio = avg_tempo / measure_tempo  # Stretch if slower, compress if faster
        
        # Get notes for this measure
        start_idx = measure_idx * notes_per_measure
        end_idx = start_idx + notes_per_measure
        measure_notes = pattern[start_idx:end_idx]
        
        # Scale times for this measure
        for note in measure_notes:
            scaled_time = time_offset + (note[0] - measure_idx) * tempo_ratio
            adapted_pattern.append([scaled_time, note[1], note[2]])
        
        # Update time offset for next measure
        beats_per_measure = config.time_signature[0]
        measure_duration = (beats_per_measure * 60.0) / measure_tempo
        time_offset += measure_duration
    
    return np.array(adapted_pattern)


def add_fills(pattern: np.ndarray, config: DrumGenerationConfig) -> np.ndarray:
    """
    Add fills at specified measure locations
    """
    if not config.fill_locations:
        return pattern
    
    # Load fill library
    fills = load_fill_library()
    
    # Choose fill type
    if config.fill_type == 'auto':
        # Context-aware fill selection
        fill_pattern = choose_fill_for_context(config)
    else:
        fill_pattern = fills.get(config.fill_type, fills['tom_run'])
    
    # Insert fills at specified measures
    for measure_idx in config.fill_locations:
        if measure_idx >= config.measure_count:
            continue
        
        # Replace last beat of measure with fill
        pattern = insert_fill_at_measure(pattern, fill_pattern, measure_idx, config)
    
    return pattern


def humanize_pattern(pattern: np.ndarray, amount: float = 0.7) -> np.ndarray:
    """
    Apply humanization to make drums sound natural
    - Timing variation (groove)
    - Velocity variation (dynamics)
    """
    humanized = pattern.copy()
    
    for i, note in enumerate(humanized):
        time, drum_type, velocity = note
        
        # Timing variation (Gaussian jitter)
        # Downbeats stay tight, other notes can be looser
        is_downbeat = (time % 1.0) < 0.1
        
        if is_downbeat:
            jitter = np.random.normal(0, amount * 5)  # ms
        else:
            jitter = np.random.normal(0, amount * 10)  # ms
        
        humanized[i][0] = time + (jitter / 1000.0)
        
        # Velocity variation
        vel_variation = np.random.normal(0, amount * 15)  # MIDI velocity units
        humanized[i][2] = np.clip(velocity + vel_variation, 20, 127)
    
    return humanized


# Helper functions

def json_to_pattern_array(pattern_json: Dict) -> np.ndarray:
    """Convert JSON pattern to numpy array"""
    notes = []
    for event in pattern_json.get('events', []):
        notes.append([
            event['time'],
            drum_name_to_midi(event['drum']),
            event['velocity']
        ])
    return np.array(notes)


def pattern_array_to_groovae_format(pattern: np.ndarray):
    """Convert pattern to GrooVAE tensor format"""
    # Placeholder - actual implementation depends on GrooVAE model
    return pattern


def groovae_to_pattern_array(tensor) -> np.ndarray:
    """Convert GrooVAE output to pattern array"""
    # Placeholder - actual implementation depends on GrooVAE model
    return tensor


def create_style_embedding(style: str, drummer: Dict, intensity: float) -> np.ndarray:
    """Create embedding vector for AI generation"""
    # Simple embedding based on style characteristics
    style_vectors = {
        'rock': [0.8, 0.6, 0.7, 0.5],
        'funk': [0.6, 0.9, 0.8, 0.7],
        'jazz': [0.5, 0.7, 0.9, 0.8],
        'latin': [0.7, 0.8, 0.6, 0.9],
        'metal': [0.9, 0.5, 0.6, 0.4],
        'pop': [0.6, 0.7, 0.7, 0.6]
    }
    
    base_vector = style_vectors.get(style, [0.6, 0.6, 0.6, 0.6])
    # Scale by intensity
    return np.array(base_vector) * intensity


def load_fill_library() -> Dict:
    """Load fill patterns library"""
    return {
        'tom_run': np.array([
            # [time, drum, velocity]
            [0.0, 48, 100],   # Tom 1
            [0.125, 48, 95],
            [0.25, 45, 100],  # Tom 2
            [0.375, 45, 95],
            [0.5, 43, 105],   # Floor tom
            [0.625, 43, 100],
            [0.75, 36, 110],  # Kick (ending)
            [0.75, 49, 120]   # Crash
        ]),
        'snare_buzz': np.array([
            [0.0, 38, 80],
            [0.05, 38, 75],
            [0.1, 38, 80],
            [0.15, 38, 85],
            [0.2, 38, 90],
            [0.25, 38, 95],
            [0.3, 38, 100]
        ]),
        'crash_buildup': np.array([
            [0.0, 42, 70],   # Closed hihat
            [0.125, 42, 75],
            [0.25, 42, 80],
            [0.375, 42, 85],
            [0.5, 46, 100],  # Open hihat
            [0.625, 46, 105],
            [0.75, 49, 120]  # Crash
        ])
    }


def choose_fill_for_context(config: DrumGenerationConfig) -> np.ndarray:
    """Choose fill based on musical context"""
    fills = load_fill_library()
    
    # High intensity → tom run
    if config.intensity > 0.7:
        return fills['tom_run']
    # Medium → crash buildup
    elif config.intensity > 0.4:
        return fills['crash_buildup']
    # Low → simple snare
    else:
        return fills['snare_buzz']


def insert_fill_at_measure(pattern: np.ndarray, fill: np.ndarray, measure_idx: int, config: DrumGenerationConfig) -> np.ndarray:
    """Insert fill pattern at specific measure"""
    # Calculate time offset for this measure
    beats_per_measure = config.time_signature[0]
    time_offset = measure_idx * beats_per_measure
    
    # Offset fill times
    fill_with_offset = fill.copy()
    fill_with_offset[:, 0] += time_offset
    
    # Remove notes in last beat of measure
    last_beat_start = time_offset + beats_per_measure - 1
    pattern_without_last_beat = pattern[pattern[:, 0] < last_beat_start]
    
    # Add fill
    return np.vstack([pattern_without_last_beat, fill_with_offset])


def drum_name_to_midi(drum_name: str) -> int:
    """Convert drum name to MIDI note number"""
    drum_map = {
        'kick': 36,
        'snare': 38,
        'hihat': 42,
        'open_hihat': 46,
        'crash': 49,
        'ride': 51,
        'tom1': 48,
        'tom2': 45,
        'floor_tom': 43
    }
    return drum_map.get(drum_name, 38)


def pattern_to_midi_notes(pattern: np.ndarray) -> List[Dict]:
    """Convert pattern array to MIDI note objects"""
    midi_notes = []
    for i, note in enumerate(pattern):
        time, drum_midi, velocity = note
        midi_notes.append({
            'id': f'note-{i}',
            'time': float(time),
            'duration': 0.1,  # Default duration
            'note': int(drum_midi),
            'velocity': int(velocity),
            'drum': midi_to_drum_name(int(drum_midi))
        })
    return midi_notes


def pattern_to_midi_base64(pattern: np.ndarray, config: DrumGenerationConfig) -> str:
    """Convert pattern to base64 encoded MIDI file"""
    # Use existing Rust MIDI export if available
    import subprocess
    import base64
    
    # For now, return placeholder
    # TODO: Implement full MIDI file generation
    return base64.b64encode(b"MIDI_FILE_PLACEHOLDER").decode('utf-8')


def midi_to_drum_name(midi_note: int) -> str:
    """Convert MIDI note to drum name"""
    reverse_map = {
        36: 'kick',
        38: 'snare',
        42: 'hihat',
        46: 'open_hihat',
        49: 'crash',
        51: 'ride',
        48: 'tom1',
        45: 'tom2',
        43: 'floor_tom'
    }
    return reverse_map.get(midi_note, 'snare')

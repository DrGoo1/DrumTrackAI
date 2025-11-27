"""
Integration Example - Complete Drum Generation Flow
===================================================
Shows how to integrate the new drum builder into your existing API.
"""

import base64
import logging
from typing import Dict, Any, List

# Import new drum generation components
from drum_generation import DrumGenerationConfig
from drum_generation.llm_performance_spec import get_performance_spec_from_llm
from drum_generation.pattern_layer import (
    generate_grid_pattern_events,
    convert_internal_events_to_grid_events,
)
from dcsmpiano import (
    build_drumtrack_for_dcsm,
    convert_dcsm_track_to_legacy_midi_notes,
)

logger = logging.getLogger(__name__)


# ============================================================================
# EXAMPLE 1: Integrate with existing internal events
# ============================================================================

def generate_drums_with_existing_pattern_generator(
    audio_path: str,
    request: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Use this if you already have a working pattern generator.
    
    This wraps your existing logic and adds the performance layer.
    """
    
    # 1. Parse request to config
    config = DrumGenerationConfig.from_dict(request)
    
    # 2. Analyze audio (your existing function)
    songmap = analyze_audio_file(audio_path)
    
    # 3. Generate pattern using your EXISTING function
    internal_events = your_existing_pattern_generator(
        audio_path=audio_path,
        style=config.style,
        drummer=config.drummer,
        intensity=config.intensity,
        variation=config.variation,
        start_measure=config.startMeasure,
        end_measure=config.endMeasure,
    )
    # internal_events should be list of:
    # {
    #   "time_sec": float,
    #   "length_sec": float,
    #   "instrument_id": str,
    #   "midi_pitch": int,
    #   "velocity": int,
    #   "isGhost": bool,
    #   "isAccent": bool,
    # }
    
    # 4. Get drummer profile (simple version for now)
    drummer_profile = get_drummer_profile_simple(config.drummer)
    
    # 5. Build SongMap summary for LLM
    songmap_summary = build_songmap_summary(songmap)
    
    # 6. Get section label
    section_label = get_section_label(songmap, config.sectionId)
    
    # 7. Get performance spec from LLM (or defaults)
    perf_spec = get_performance_spec_from_llm(
        cfg=config,
        section_label=section_label,
        songmap_summary=songmap_summary,
        drummer_profile=drummer_profile,
    )
    
    # 8. Build high-resolution DCSM track
    dcsm_track = build_drumtrack_for_dcsm(
        songmap=songmap,
        internal_drum_events=internal_events,
        style_id=config.style,
        performance_spec=perf_spec,
        resolution_ppq=960,
    )
    
    # 9. Export to MIDI
    midi_bytes = export_track_to_smf(dcsm_track, songmap)
    midi_b64 = base64.b64encode(midi_bytes).decode('utf-8')
    
    # 10. Return both new and legacy formats
    return {
        "ok": True,
        "status_message": "Generated drum track with LLM performance",
        "midi_smf_base64": midi_b64,
        "drum_track": dcsm_track.to_dict(),  # NEW high-res format
        "midi_notes": convert_dcsm_track_to_legacy_midi_notes(dcsm_track),  # OLD
        "metadata": {
            "style": config.style,
            "drummer": config.drummer,
            "humanized": config.humanize,
            "performance_from_llm": True,
            "resolution_ppq": 960,
        }
    }


# ============================================================================
# EXAMPLE 2: Use new pattern layer
# ============================================================================

def generate_drums_with_new_pattern_layer(
    audio_path: str,
    request: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Use this if you want to use the new pattern layer.
    
    This generates patterns using the new GridEvent system.
    """
    
    # 1-2. Same as above
    config = DrumGenerationConfig.from_dict(request)
    songmap = analyze_audio_file(audio_path)
    
    # 3. Generate grid events (new pattern layer)
    grid_events = generate_grid_pattern_events(
        songmap=songmap,
        config=config,
        pattern_model=None,  # Pass your pattern model here
    )
    
    # 4. Convert grid events to internal format
    internal_events = convert_grid_events_to_internal_format(
        grid_events, songmap, config
    )
    
    # 5-10. Same as Example 1
    drummer_profile = get_drummer_profile_simple(config.drummer)
    songmap_summary = build_songmap_summary(songmap)
    section_label = get_section_label(songmap, config.sectionId)
    
    perf_spec = get_performance_spec_from_llm(
        cfg=config,
        section_label=section_label,
        songmap_summary=songmap_summary,
        drummer_profile=drummer_profile,
    )
    
    dcsm_track = build_drumtrack_for_dcsm(
        songmap=songmap,
        internal_drum_events=internal_events,
        style_id=config.style,
        performance_spec=perf_spec,
        resolution_ppq=960,
    )
    
    midi_bytes = export_track_to_smf(dcsm_track, songmap)
    midi_b64 = base64.b64encode(midi_bytes).decode('utf-8')
    
    return {
        "ok": True,
        "midi_smf_base64": midi_b64,
        "drum_track": dcsm_track.to_dict(),
        "midi_notes": convert_dcsm_track_to_legacy_midi_notes(dcsm_track),
    }


# ============================================================================
# Helper Functions
# ============================================================================

def get_drummer_profile_simple(drummer_name: str) -> Dict[str, Any]:
    """
    Simple drummer profile.
    
    TODO: Replace with database query to drumtrackai.db
    """
    
    # Defaults
    profile = {
        "name": drummer_name,
        "timing_tightness": 0.8,
        "ghost_note_frequency": 0.5,
        "preferred_feel": "straight",
        "style_specialties": ["rock", "funk"],
    }
    
    # Adjust for known drummers
    if "porcaro" in drummer_name.lower():
        profile["timing_tightness"] = 0.85
        profile["ghost_note_frequency"] = 0.7
        profile["preferred_feel"] = "laid_back"
    elif "bonham" in drummer_name.lower():
        profile["timing_tightness"] = 0.75
        profile["ghost_note_frequency"] = 0.3
        profile["preferred_feel"] = "pushed"
    elif "bernard" in drummer_name.lower():
        profile["timing_tightness"] = 0.9
        profile["ghost_note_frequency"] = 0.8
        profile["preferred_feel"] = "straight"
    
    return profile


def build_songmap_summary(songmap: Any) -> Dict[str, Any]:
    """
    Create condensed SongMap summary for LLM prompt.
    
    Keeps prompt size manageable while providing key context.
    """
    
    sections_list = []
    if hasattr(songmap, 'sections'):
        for s in songmap.sections:
            sections_list.append({
                "label": getattr(s, 'label', 'unknown'),
                "startBar": getattr(s, 'start_bar_index', 0),
                "endBar": getattr(s, 'end_bar_index', 0),
                "energy": getattr(s, 'energy', 0.5),
            })
    
    avg_energy = 0.5
    if sections_list:
        avg_energy = sum(s["energy"] for s in sections_list) / len(sections_list)
    
    return {
        "bars": len(songmap.bars) if hasattr(songmap, 'bars') else 0,
        "sections": sections_list,
        "avgEnergy": avg_energy,
        "globalBPM": getattr(songmap, 'global_bpm_estimate', 120.0),
    }


def get_section_label(songmap: Any, section_id: str) -> str:
    """
    Get human-readable section label.
    """
    
    if hasattr(songmap, 'sections'):
        for s in songmap.sections:
            if getattr(s, 'id', None) == section_id:
                return getattr(s, 'label', section_id)
    
    # Fallback: prettify section_id
    return section_id.replace("_", " ").title()


def convert_grid_events_to_internal_format(
    grid_events: List[Any],
    songmap: Any,
    config: DrumGenerationConfig,
) -> List[Dict[str, Any]]:
    """
    Convert GridEvent objects to internal format.
    """
    
    from dcsmpiano.drumtrack_schema import instrument_id_to_midi_pitch
    
    internal_events = []
    
    for ge in grid_events:
        bar = songmap.bars[ge.bar_index]
        bar_len_sec = bar.end_time - bar.start_time
        
        # Calculate time in seconds
        frac = ge.subdivision_index / ge.subdivisions_per_bar
        time_sec = bar.start_time + (frac * bar_len_sec)
        
        # Get MIDI pitch
        midi_pitch = instrument_id_to_midi_pitch(ge.instrument_id)
        
        # Calculate velocity
        velocity = 100
        if ge.is_accent:
            velocity = 110
        if ge.is_ghost:
            velocity = 60
        
        internal_events.append({
            "time_sec": time_sec,
            "length_sec": 0.2,  # Default note length
            "instrument_id": ge.instrument_id,
            "midi_pitch": midi_pitch,
            "velocity": velocity,
            "isGhost": ge.is_ghost,
            "isAccent": ge.is_accent,
            "isFlam": ge.is_flam,
            "isDrag": ge.is_drag,
        })
    
    return internal_events


def export_track_to_smf(dcsm_track: Any, songmap: Any) -> bytes:
    """
    Export DrumTrackForDCSM to Standard MIDI File.
    
    TODO: Replace with your actual MIDI export function.
    """
    
    import mido
    from mido import Message, MidiFile, MidiTrack
    
    mid = MidiFile(type=1)
    track = MidiTrack()
    mid.tracks.append(track)
    
    # Tempo
    tempo = int(60_000_000 / 120)  # 120 BPM default
    track.append(mido.MetaMessage('set_tempo', tempo=tempo, time=0))
    
    # Convert notes
    notes_sorted = sorted(dcsm_track.notes, key=lambda n: (n.barIndex, n.tickInBar))
    
    current_tick = 0
    for note in notes_sorted:
        # Calculate absolute tick
        bar_ticks = dcsm_track.resolution_ppq * 4  # Assume 4/4
        note_tick = (note.barIndex * bar_ticks) + note.tickInBar
        
        # Delta time
        delta = note_tick - current_tick
        
        # Note on
        track.append(Message(
            'note_on',
            channel=9,
            note=note.midiPitch,
            velocity=note.velocity,
            time=delta,
        ))
        
        # Note off
        track.append(Message(
            'note_off',
            channel=9,
            note=note.midiPitch,
            velocity=0,
            time=note.tickLength,
        ))
        
        current_tick = note_tick + note.tickLength
    
    # Save to bytes
    from io import BytesIO
    buffer = BytesIO()
    mid.save(file=buffer)
    return buffer.getvalue()


# ============================================================================
# Placeholder for existing functions (replace with your actual code)
# ============================================================================

def analyze_audio_file(audio_path: str) -> Any:
    """
    PLACEHOLDER: Replace with your actual audio analysis.
    
    Should return SongMap object with:
    - bars (list of bar objects with start_time, end_time, tempo_bpm, meter)
    - sections (list of section objects with label, start_bar_index, end_bar_index, energy)
    - global_bpm_estimate (float)
    """
    raise NotImplementedError("Replace with your actual analyze_audio_file()")


def your_existing_pattern_generator(
    audio_path: str,
    style: str,
    drummer: str,
    intensity: float,
    variation: float,
    start_measure: int,
    end_measure: int,
) -> List[Dict[str, Any]]:
    """
    PLACEHOLDER: Replace with your actual pattern generator.
    
    Should return list of events with:
    - time_sec: float
    - length_sec: float
    - instrument_id: str
    - midi_pitch: int
    - velocity: int
    - isGhost: bool
    - isAccent: bool
    """
    raise NotImplementedError("Replace with your actual pattern generator")


# ============================================================================
# FastAPI endpoint example
# ============================================================================

"""
# Add to your FastAPI app:

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI()

class DrumGenRequest(BaseModel):
    audio_path: str
    sectionId: str
    startMeasure: int
    endMeasure: int
    tempos: List[float]
    timeSignature: tuple
    style: str
    drummer: str
    intensity: float
    variation: float
    generationMode: str
    humanize: bool
    humanizeAmount: float = 0.7
    ghostNoteAmount: float = 0.7
    swingAmount: float = 0.0
    fillLocations: List[int] = []
    fillType: str = "auto"
    buildScope: str = "full_song"
    guideEnabled: bool = False
    guideInstrument: str = "mix"

@app.post("/api/generate-drums")
async def api_generate_drums(req: DrumGenRequest):
    try:
        result = generate_drums_with_existing_pattern_generator(
            audio_path=req.audio_path,
            request=req.dict(),
        )
        return result
    except Exception as e:
        logger.error(f"Drum generation failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
"""

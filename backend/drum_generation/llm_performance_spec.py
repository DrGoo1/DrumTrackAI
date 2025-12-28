"""
LLM Performance Spec Generator
==============================
Generates DrumPerformanceSpec using LLM + analytics.

The LLM designs HOW the drummer plays, not WHAT notes.
"""

import json
import os
from textwrap import dedent
from typing import Dict, Any, Optional
import logging
import math
import urllib.request

logger = logging.getLogger(__name__)

# Optional: Import OpenAI or other LLM client
try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    logger.warning("OpenAI not available")

# Import new Jamstix-style modules
try:
    from .part_types_config import get_part_type_preset
    from .power_model import (
        compute_power_curve_from_guide,
        power_to_velocity_scale,
        power_to_fill_probability,
        power_to_ghost_note_density,
    )
    JAMSTIX_MODULES_AVAILABLE = True
except ImportError:
    JAMSTIX_MODULES_AVAILABLE = False
    logger.warning("Jamstix modules not available")

try:
    from .local_humanization_model import get_local_humanization_model
    LOCAL_HUMANIZATION_AVAILABLE = True
except Exception:
    get_local_humanization_model = None
    LOCAL_HUMANIZATION_AVAILABLE = False


def build_songmap_summary(songmap) -> Dict[str, Any]:
    """
    Build condensed SongMap summary for LLM context.
    
    Includes section information, part types, and energy levels.
    """
    try:
        sections_data = []
        for s in getattr(songmap, 'sections', []):
            section_info = {
                "label": getattr(s, 'label', 'unknown'),
                "startBar": getattr(s, 'start_bar_index', 0),
                "endBar": getattr(s, 'end_bar_index', 0),
                "energy": getattr(s, 'energy', 0.5),
            }
            
            # Add part type if available
            if JAMSTIX_MODULES_AVAILABLE:
                part_type_id = getattr(s, 'part_type', None) or section_info['label'].lower()
                preset = get_part_type_preset(part_type_id)
                section_info['partType'] = preset.id
                section_info['grooveProfile'] = preset.defaultGrooveProfile
            
            sections_data.append(section_info)
        
        total_bars = len(getattr(songmap, 'bars', []))
        avg_energy = sum(s['energy'] for s in sections_data) / max(len(sections_data), 1) if sections_data else 0.5
        
        return {
            "bars": total_bars,
            "sections": sections_data,
            "avgEnergy": float(avg_energy),
        }
    except Exception as e:
        logger.warning(f"Failed to build songmap summary: {e}")
        return {"bars": 0, "sections": [], "avgEnergy": 0.5}


def build_llm_prompt_for_performance(
    cfg: "DrumGenerationConfig",
    section_label: str,
    songmap_summary: Dict[str, Any],
    drummer_profile: Dict[str, Any],
    power_curve: Optional[list] = None,
) -> str:
    """
    Build comprehensive LLM prompt for performance spec generation.
    
    Args:
        cfg: Complete drum generation config
        section_label: Human-readable section name
        songmap_summary: Condensed SongMap data
        drummer_profile: Drummer style characteristics
    
    Returns:
        Detailed prompt string for LLM
    """
    
    # Calculate tempo statistics
    avg_tempo = sum(cfg.tempos) / max(len(cfg.tempos), 1)
    tempo_range = f"{min(cfg.tempos):.1f}-{max(cfg.tempos):.1f} BPM"
    
    # Guide track info
    guide_text = "no dedicated guide track (use full mix)" if not cfg.guideEnabled else \
                 f"a dedicated guide track that is primarily {cfg.guideInstrument}"
    
    # Part type context
    part_type_info = ""
    if JAMSTIX_MODULES_AVAILABLE and section_label:
        try:
            preset = get_part_type_preset(section_label.lower())
            part_type_info = f"""
    Part Type: {preset.label}
    Default Characteristics:
      - Intensity: {preset.defaultIntensity:.2f}
      - Variation: {preset.defaultVariation:.2f}
      - Fill Density: {preset.defaultFillDensity:.2f}
      - Power Hand: {preset.defaultPowerHand}
      - Groove Profile: {preset.defaultGrooveProfile}
"""
        except:
            pass
    
    # Power curve info
    power_info = ""
    if power_curve:
        avg_power = sum(power_curve) / len(power_curve)
        min_power = min(power_curve)
        max_power = max(power_curve)
        power_info = f"""
    Power Curve (from guide track analysis):
      - Average: {avg_power:.2f}
      - Range: {min_power:.2f} - {max_power:.2f}
      - Per-bar values: {[f'{p:.2f}' for p in power_curve[:8]]}{'...' if len(power_curve) > 8 else ''}
"""
    
    # Build comprehensive prompt
    prompt = dedent(f"""
    You are a world-class drum performance designer and musical director.
    You work inside DrumTracKAI, an advanced AI drum composition system.
    
    The system has ALREADY generated the basic drum pattern (kick/snare/hat/ride/toms).
    Your job is to design HOW the drummer PERFORMS those notes:
    - Micro-timing (ahead/behind the beat, swing, laid-back feel)
    - Velocities (dynamics, accents, ghost notes)
    - Articulations (flams, drags, special techniques)
    - Per-instrument feel (snare vs hi-hat vs ride timing differences)
    
    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    MUSICAL CONTEXT
    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    
    Section: {section_label} (ID: {cfg.sectionId})
    Measures: {cfg.startMeasure}-{cfg.endMeasure} ({cfg.endMeasure - cfg.startMeasure + 1} bars)
    Time Signature: {cfg.timeSignature[0]}/{cfg.timeSignature[1]}
    Tempo: {avg_tempo:.1f} BPM (range: {tempo_range})
    
    Style: {cfg.style}
    Drummer: {cfg.drummer}
    Generation Mode: {cfg.generationMode}
    
    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    USER INTENT (How they want it to feel)
    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    
    Intensity: {cfg.intensity:.2f} (0=soft/delicate, 1=aggressive/powerful)
    Variation: {cfg.variation:.2f} (0=consistent groove, 1=lots of changes)
    
    Humanize: {"ENABLED" if cfg.humanize else "DISABLED"}
    Humanize Amount: {cfg.humanizeAmount:.2f} (0=robotic/tight, 1=very loose/human)
    Ghost Notes: {cfg.ghostNoteAmount:.2f} (0=none, 1=very dense/ghosty)
    Swing: {cfg.swingAmount:.2f} (0=straight, 1=heavy swing/shuffle)
    
    Fill Type: {cfg.fillType}
    Fill Locations: {cfg.fillLocations if cfg.fillLocations else "none specified"}
    
    Guide Track: {guide_text}
    {part_type_info}
    {power_info}
    
    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    ANALYTICAL DATA
    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    
    SongMap Summary:
    {json.dumps(songmap_summary, indent=2)[:1500]}
    
    Drummer Profile Summary:
    {json.dumps(drummer_profile, indent=2)[:1500]}
    
    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    OUTPUT REQUIREMENTS
    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    
    Output ONLY valid JSON matching this exact schema (DrumPerformanceSpec):
    
    {{
      "styleId": "<style_id>",
      "globalFeel": "straight" | "swing" | "shuffle" | "laid_back" | "pushed",
      "quantizationBase": "16th" | "8th" | "triplet_8th" | "triplet_16th",
      "phrases": [
        {{
          "phraseId": "<unique_phrase_id>",
          "barStart": <int>,
          "barEnd": <int>,
          "profiles": [
            {{
              "instrumentId": "kick" | "snare_center" | "snare_ghost" | "hihat_closed" | "hihat_open" | "ride_bow" | etc.,
              "microTiming": {{
                "subdivisionOffsetsMs": [<float>, ...],  // Array of 4, 8, or 16 values (ms offsets)
                "swingAmount": <float 0..1>,
                "laidBackAmount": <float -1..1>  // negative=pushed, positive=laid-back
              }},
              "velocityProfile": {{
                "base": <int 1..127>,
                "accentBoost": <int 0..40>,
                "ghostReduction": <float 0..1>,
                "randomRange": <int 0..20>,
                "phraseShape": "flat" | "swell" | "decay" | "wave"
              }},
              "ghostDensity": <float 0..1>,
              "flamProbability": <float 0..1>,
              "dragProbability": <float 0..1>
            }}
          ]
        }}
      ]
    }}
    
    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    CRITICAL RULES
    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    
    1. ALWAYS provide profiles for at least:
       - snare_center (or snare_ghost if ghostNoteAmount > 0.3)
       - hihat_closed (or hihat_open depending on style)
       - kick
       - ride_bow (if ride is used in this style)
    
    2. Micro-timing:
       - Higher humanizeAmount → larger offset values (up to ±10ms)
       - Lower humanizeAmount → tighter offsets (±2ms)
       - Respect swingAmount: more swing → bigger differences between on/off beats
       - Respect drummer profile timing characteristics
    
    3. Velocities:
       - Higher intensity → higher base velocities, bigger accents
       - Lower intensity → softer base, subtle accents
       - Ghost notes should be 30-50% of base velocity
       - Respect drummer profile dynamics
    
    4. Ghost notes:
       - ghostNoteAmount controls ghostDensity in profiles
       - High ghostNoteAmount → ghostDensity 0.6-0.9 for snare
       - Low ghostNoteAmount → ghostDensity 0.0-0.2
    
    5. Musical context:
       - Verse: Often more laid-back, less intense
       - Chorus: Often pushed/ahead, more aggressive
       - Bridge: Can be very different from verse/chorus
       - Respect section energy from SongMap
    
    6. Variation:
       - If variation > 0.7: Create multiple phrases with different feels
       - If variation < 0.3: Single phrase with consistent feel
    
    7. DO NOT invent notes or patterns - you're only describing HOW to play existing notes.
    
    Output ONLY the JSON. No explanations, no markdown, no prose.
    """)
    
    return prompt


def get_performance_spec_from_llm(
    cfg: "DrumGenerationConfig",
    section_label: str,
    songmap_summary: Dict[str, Any],
    drummer_profile: Dict[str, Any],
    power_curve: Optional[list] = None,
    use_cache: bool = True,
) -> Dict[str, Any]:
    """
    Get DrumPerformanceSpec from LLM.
    
    Args:
        cfg: Drum generation config
        section_label: Section name
        songmap_summary: Condensed SongMap
        drummer_profile: Drummer characteristics
        use_cache: Whether to cache results (future enhancement)
    
    Returns:
        DrumPerformanceSpec as dictionary
    """
    
    if not cfg.humanize:
        # If humanize is off, return minimal spec
        logger.info("Humanize disabled, using flat performance spec")
        return build_flat_performance_spec(cfg, songmap_summary)

    provider = str(os.getenv("LLM_PROVIDER", "local")).strip().lower()
    if provider == "local_service":
        return get_performance_spec_from_local_service(
            cfg=cfg,
            songmap_summary=songmap_summary,
            drummer_profile=drummer_profile,
        )
    if provider == "local":
        if not LOCAL_HUMANIZATION_AVAILABLE or get_local_humanization_model is None:
            raise RuntimeError("Local LLM provider selected but local humanization model is not available")
        return build_local_performance_spec(
            cfg=cfg,
            songmap_summary=songmap_summary,
            drummer_profile=drummer_profile,
        )

    if provider != "openai":
        raise RuntimeError(f"Unsupported LLM_PROVIDER: {provider}")

    if not OPENAI_AVAILABLE:
        raise RuntimeError("OpenAI client library is not available; no fallback performance spec is allowed")
    
    try:
        # Build prompt
        prompt = build_llm_prompt_for_performance(
            cfg, section_label, songmap_summary, drummer_profile, power_curve
        )
        
        # Get API key
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY is not set; no fallback performance spec is allowed")
        
        # Call LLM
        client = OpenAI(api_key=api_key)
        
        response = client.chat.completions.create(
            model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            messages=[
                {
                    "role": "system",
                    "content": "You are a professional drum performance designer. Output only valid JSON."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0.7,
            max_tokens=2048,
            response_format={"type": "json_object"}  # Force JSON output
        )
        
        # Parse response
        content = response.choices[0].message.content
        spec = json.loads(content)

        logger.info(f"LLM generated performance spec with {len(spec.get('phrases', []))} phrases")
        return spec
        
    except json.JSONDecodeError as e:
        raise RuntimeError(f"LLM returned invalid JSON: {e}")

    except Exception as e:
        raise RuntimeError(f"LLM call failed: {e}")


def get_performance_spec_from_local_service(
    cfg: "DrumGenerationConfig",
    songmap_summary: Dict[str, Any],
    drummer_profile: Dict[str, Any],
) -> Dict[str, Any]:
    base_url = str(os.getenv("LOCAL_LLM_URL", "")).strip().rstrip("/")
    if not base_url:
        raise RuntimeError("LLM_PROVIDER=local_service but LOCAL_LLM_URL is not set")

    timeout_s = float(os.getenv("LOCAL_LLM_TIMEOUT_S", "15"))
    url = f"{base_url}/v1/performance_spec"

    cfg_payload = {}
    if hasattr(cfg, "to_dict") and callable(getattr(cfg, "to_dict")):
        try:
            cfg_payload = cfg.to_dict()
        except Exception:
            cfg_payload = cfg.__dict__ if hasattr(cfg, "__dict__") else {}
    else:
        cfg_payload = cfg.__dict__ if hasattr(cfg, "__dict__") else {}

    payload = {
        "cfg": cfg_payload,
        "songmap_summary": songmap_summary,
        "drummer_profile": drummer_profile,
    }

    try:
        body = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=timeout_s) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
        try:
            data = json.loads(raw)
        except Exception as e:
            raise RuntimeError(f"Local LLM service returned invalid JSON: {e}")

        if not isinstance(data, dict) or not data.get("ok"):
            raise RuntimeError(f"Local LLM service returned failure: {data}")
        spec = data.get("spec")
        if not isinstance(spec, dict):
            raise RuntimeError(f"Local LLM service response missing 'spec': {data}")
        return spec
    except Exception as e:
        raise RuntimeError(f"Local LLM service call failed: {e}")


def build_local_performance_spec(
    cfg: "DrumGenerationConfig",
    songmap_summary: Dict[str, Any],
    drummer_profile: Dict[str, Any],
) -> Dict[str, Any]:
    model = get_local_humanization_model()
    avg_tempo = sum(cfg.tempos) / max(len(cfg.tempos), 1)
    style = getattr(cfg, "style", None)
    complexity = 0.7
    try:
        complexity = float(getattr(cfg, "complexity", None) or 0.7)
    except Exception:
        complexity = 0.7

    params = model.predict_params(
        tempo_bpm=float(avg_tempo),
        style=style,
        pattern_complexity=float(max(0.0, min(1.0, complexity))),
    )

    swing_from_model = float(params.get("swing_factor", 0.0))
    swing_amount = float(max(0.0, min(1.0, (cfg.swingAmount + swing_from_model) * 0.5)))

    timing_var = float(params.get("timing_variance", 0.0))
    timing_drift = float(params.get("timing_drift", 0.0))
    groove_consistency = float(params.get("groove_consistency", 0.8))

    max_ms = 10.0 * float(max(0.0, min(1.0, cfg.humanizeAmount)))
    var_ms = max(0.0, min(max_ms, timing_var * max_ms))
    drift_ms = max(-max_ms, min(max_ms, (timing_drift - 0.5) * 2.0 * (max_ms * 0.6)))
    tightness = max(0.0, min(1.0, groove_consistency))
    var_ms *= (0.4 + 0.6 * (1.0 - tightness))

    laid_back = 0.0
    feel_map = {
        "rock": "straight",
        "funk": "laid_back",
        "jazz": "swing",
        "shuffle": "shuffle",
        "blues": "shuffle",
    }
    global_feel = feel_map.get(str(cfg.style or "").lower(), "straight")
    if swing_amount > 0.55:
        global_feel = "swing"
    if global_feel == "laid_back":
        laid_back = 0.2
    if global_feel == "pushed":
        laid_back = -0.2

    def _subdivision_offsets(scale: float) -> list:
        out = []
        for i in range(16):
            base = math.sin((i + 1) * 1.7) * var_ms * scale
            if (i % 2) == 1:
                base += swing_amount * 8.0
            base += drift_ms
            out.append(float(max(-max_ms, min(max_ms, base))))
        return out

    base_velocity = int(60 + cfg.intensity * 50)
    base_velocity = max(1, min(127, base_velocity))
    ghost_pref = float(params.get("ghost_note_frequency", 0.15))
    ghost_density = float(max(0.0, min(1.0, cfg.ghostNoteAmount * ghost_pref)))

    def _profile(inst: str, timing_scale: float, vel_bias: int, accent_boost: int, ghost_reduction: float, rr: int):
        return {
            "instrumentId": inst,
            "microTiming": {
                "subdivisionOffsetsMs": _subdivision_offsets(timing_scale),
                "swingAmount": float(swing_amount),
                "laidBackAmount": float(laid_back),
            },
            "velocityProfile": {
                "base": int(max(1, min(127, base_velocity + vel_bias))),
                "accentBoost": int(max(0, min(40, accent_boost))),
                "ghostReduction": float(max(0.0, min(1.0, ghost_reduction))),
                "randomRange": int(max(0, min(20, rr))),
                "phraseShape": "swell" if cfg.variation > 0.6 else "flat",
            },
            "ghostDensity": float(ghost_density if inst.startswith("snare") else ghost_density * 0.4),
            "flamProbability": float(0.1 if cfg.humanizeAmount > 0.6 and inst.startswith("snare") else 0.0),
            "dragProbability": float(0.05 if cfg.humanizeAmount > 0.7 and inst.startswith("snare") else 0.0),
        }

    profiles = [
        _profile("kick", 0.5, 10, int(cfg.intensity * 20), 0.7, int(cfg.humanizeAmount * 8)),
        _profile("snare_center", 1.0, 0, int(15 + cfg.intensity * 25), 0.4, int(cfg.humanizeAmount * 10)),
        _profile("hihat_closed", 0.8, -10, int(8 + cfg.intensity * 12), 0.6, int(cfg.humanizeAmount * 6)),
        _profile("ride_bow", 0.7, -5, int(10 + cfg.intensity * 15), 0.5, int(cfg.humanizeAmount * 7)),
    ]

    return {
        "styleId": cfg.style,
        "globalFeel": global_feel,
        "quantizationBase": "16th",
        "phrases": [
            {
                "phraseId": f"{cfg.sectionId}_local",
                "barStart": cfg.startMeasure,
                "barEnd": cfg.endMeasure,
                "profiles": profiles,
            }
        ],
    }


def build_flat_performance_spec(
    cfg: "DrumGenerationConfig",
    songmap_summary: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Build minimal flat performance spec (no humanization).
    
    Args:
        cfg: Drum generation config
        songmap_summary: SongMap data
    
    Returns:
        Minimal DrumPerformanceSpec
    """
    bar_count = cfg.endMeasure - cfg.startMeasure + 1
    
    return {
        "styleId": cfg.style,
        "globalFeel": "straight",
        "quantizationBase": "16th",
        "phrases": [
            {
                "phraseId": f"{cfg.sectionId}_phrase",
                "barStart": cfg.startMeasure,
                "barEnd": cfg.endMeasure,
                "profiles": [
                    {
                        "instrumentId": inst,
                        "microTiming": {
                            "subdivisionOffsetsMs": [0.0] * 16,
                            "swingAmount": 0.0,
                            "laidBackAmount": 0.0,
                        },
                        "velocityProfile": {
                            "base": 100,
                            "accentBoost": 10,
                            "ghostReduction": 0.5,
                            "randomRange": 0,
                            "phraseShape": "flat",
                        },
                        "ghostDensity": 0.0,
                        "flamProbability": 0.0,
                        "dragProbability": 0.0,
                    }
                    for inst in ["kick", "snare_center", "hihat_closed", "ride_bow"]
                ],
            }
        ],
    }


def build_default_performance_spec(
    cfg: "DrumGenerationConfig",
    songmap_summary: Dict[str, Any],
    drummer_profile: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Build default performance spec using analytics (no LLM).
    
    Uses drummer profile + user controls to create reasonable defaults.
    
    Args:
        cfg: Drum generation config
        songmap_summary: SongMap data
        drummer_profile: Drummer characteristics
    
    Returns:
        DrumPerformanceSpec as dictionary
    """
    
    # Extract drummer timing characteristics
    timing_tightness = drummer_profile.get("timing_tightness", 0.8)
    ghost_preference = drummer_profile.get("ghost_note_frequency", 0.5)
    
    # Calculate micro-timing based on humanize amount and drummer style
    max_offset = cfg.humanizeAmount * 8.0 * (1.0 - timing_tightness)  # 0-8ms range
    
    # Build offset pattern (16 subdivisions)
    import random
    random.seed(hash(cfg.drummer + cfg.sectionId))  # Deterministic but varied
    offsets = [random.uniform(-max_offset, max_offset) for _ in range(16)]
    
    # Adjust for swing
    if cfg.swingAmount > 0.1:
        for i in range(0, 16, 2):
            if i + 1 < 16:
                offsets[i + 1] += cfg.swingAmount * 15.0  # Push off-beats later
    
    # Base velocity from intensity
    base_velocity = int(60 + cfg.intensity * 50)  # 60-110 range
    
    # Ghost density from controls + drummer preference
    ghost_density = cfg.ghostNoteAmount * ghost_preference
    
    # Determine feel from style
    feel_map = {
        "rock": "straight",
        "funk": "laid_back",
        "jazz": "swing",
        "shuffle": "shuffle",
        "blues": "shuffle",
    }
    global_feel = feel_map.get(cfg.style.lower(), "straight")
    if cfg.swingAmount > 0.5:
        global_feel = "swing"
    
    bar_count = cfg.endMeasure - cfg.startMeasure + 1
    
    return {
        "styleId": cfg.style,
        "globalFeel": global_feel,
        "quantizationBase": "16th",
        "phrases": [
            {
                "phraseId": f"{cfg.sectionId}_default",
                "barStart": cfg.startMeasure,
                "barEnd": cfg.endMeasure,
                "profiles": [
                    # Kick
                    {
                        "instrumentId": "kick",
                        "microTiming": {
                            "subdivisionOffsetsMs": [o * 0.5 for o in offsets],  # Kick tighter
                            "swingAmount": cfg.swingAmount * 0.3,
                            "laidBackAmount": 0.0,
                        },
                        "velocityProfile": {
                            "base": base_velocity + 10,
                            "accentBoost": int(cfg.intensity * 20),
                            "ghostReduction": 0.7,
                            "randomRange": int(cfg.humanizeAmount * 8),
                            "phraseShape": "flat",
                        },
                        "ghostDensity": 0.0,
                        "flamProbability": 0.0,
                        "dragProbability": 0.0,
                    },
                    # Snare
                    {
                        "instrumentId": "snare_center",
                        "microTiming": {
                            "subdivisionOffsetsMs": offsets,
                            "swingAmount": cfg.swingAmount,
                            "laidBackAmount": 0.2 if global_feel == "laid_back" else 0.0,
                        },
                        "velocityProfile": {
                            "base": base_velocity,
                            "accentBoost": int(15 + cfg.intensity * 25),
                            "ghostReduction": 0.4,
                            "randomRange": int(cfg.humanizeAmount * 10),
                            "phraseShape": "swell" if cfg.variation > 0.6 else "flat",
                        },
                        "ghostDensity": ghost_density,
                        "flamProbability": 0.1 if cfg.humanizeAmount > 0.5 else 0.0,
                        "dragProbability": 0.05 if cfg.humanizeAmount > 0.7 else 0.0,
                    },
                    # Hi-hat
                    {
                        "instrumentId": "hihat_closed",
                        "microTiming": {
                            "subdivisionOffsetsMs": [o * 0.8 for o in offsets],
                            "swingAmount": cfg.swingAmount * 1.2,  # Hats swing more
                            "laidBackAmount": -0.1 if global_feel == "pushed" else 0.1,
                        },
                        "velocityProfile": {
                            "base": base_velocity - 15,
                            "accentBoost": int(8 + cfg.intensity * 12),
                            "ghostReduction": 0.6,
                            "randomRange": int(cfg.humanizeAmount * 6),
                            "phraseShape": "flat",
                        },
                        "ghostDensity": ghost_density * 0.5,
                        "flamProbability": 0.0,
                        "dragProbability": 0.0,
                    },
                    # Ride
                    {
                        "instrumentId": "ride_bow",
                        "microTiming": {
                            "subdivisionOffsetsMs": [o * 0.7 for o in offsets],
                            "swingAmount": cfg.swingAmount * 1.5,  # Ride swings most
                            "laidBackAmount": 0.3 if global_feel == "laid_back" else 0.0,
                        },
                        "velocityProfile": {
                            "base": base_velocity - 10,
                            "accentBoost": int(10 + cfg.intensity * 15),
                            "ghostReduction": 0.5,
                            "randomRange": int(cfg.humanizeAmount * 7),
                            "phraseShape": "flat",
                        },
                        "ghostDensity": 0.1,
                        "flamProbability": 0.0,
                        "dragProbability": 0.0,
                    },
                ],
            }
        ],
    }

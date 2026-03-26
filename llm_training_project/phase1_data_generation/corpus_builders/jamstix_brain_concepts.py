#!/usr/bin/env python3
"""
Jamstix Brain Concepts Corpus Builder
======================================
Creates training examples from Jamstix-style brain logic and concepts
Based on Phase 2 implementation and drum reasoning
"""
import json
from pathlib import Path
from typing import List, Dict

# Jamstix-inspired brain concepts for LLM training

JAMSTIX_BRAIN_CONCEPTS = [
    {
        "concept": "Priority System",
        "explanation": "Each drum hit has a priority value (0.0-1.0) representing its importance. High priority hits (accents, backbeat snares, crashes on beat 1) override conflicting limb actions. Low priority hits (ghost notes, hi-hat upbeats) can be dropped if limbs are busy. Priority determines which hits to keep when physical constraints arise.",
        "application": "Realistic playability, limb conflict resolution, humanization",
        "examples": [
            "Snare on beats 2 and 4: priority 0.9 (backbeat)",
            "Crash on beat 1: priority 1.0 (section marker)",
            "Ghost note between beats: priority 0.3 (texture)",
            "Hi-hat on upbeat: priority 0.5 (groove)"
        ]
    },
    {
        "concept": "Timing Offset and Feel",
        "explanation": "Microtiming adjustments (-50ms to +50ms) create human feel. Laid-back feel: snare/hats delayed 5-15ms behind beat. Pushed feel: hits 5-10ms ahead. Swing: off-beats delayed to create triplet feel. These subtle timing variations distinguish human from mechanical performance.",
        "application": "Human feel, groove, style characteristics",
        "examples": [
            "Laid-back rock: snare +10ms, hats +7ms",
            "Pushed funk: snare -8ms, creating urgency",
            "Jazz swing: off-beat 8ths delayed +20ms",
            "On-the-pocket: all hits within ±2ms"
        ]
    },
    {
        "concept": "Limb Assignment and Constraints",
        "explanation": "Each hit must be assigned to a limb (LH, RH, LF, RF). Physical constraints limit what's playable: same limb can't hit two instruments simultaneously, minimum time between same-limb hits (~50ms for fast players), cross-sticking takes longer. Respecting limb physics ensures realistic patterns.",
        "application": "Playability validation, pattern feasibility",
        "examples": [
            "Kick (RF) and hi-hat pedal (LF): simultaneous OK",
            "Snare (RH) and crash (RH): <50ms = conflict",
            "Cross-stick from ride to tom: needs extra time",
            "Hi-hat with left hand while riding: possible"
        ]
    },
    {
        "concept": "Groove Weights",
        "explanation": "Each 16th note subdivision has a weight (0.0-1.0) representing its emphasis in the groove. Beat 1 typically has highest weight (1.0), backbeats (2 and 4) high weight (0.9), off-beats medium (0.6), sixteenth notes between low (0.4). Weights affect velocity: high-weight hits played louder.",
        "application": "Velocity control, groove feel, emphasis",
        "examples": [
            "Rock 4/4: weights [1.0, 0.6, 0.6, 0.6, 0.9, 0.6, 0.6, 0.6, 0.8, ...]",
            "Funk offbeat: emphasize 16th note offbeats",
            "Jazz: emphasize beats 2 and 4 for swing",
            "Apply weight × base_velocity for final velocity"
        ]
    },
    {
        "concept": "Ghost Notes",
        "explanation": "Ghost notes are soft hits (velocity 20-45) that add texture without dominating. Common in funk and R&B on snare. They fill space between main hits, create groove, suggest implied rhythm. Placement typically on 16th note subdivisions. Ghost density: 0.0-1.0 controls how many soft hits to add.",
        "application": "Funk grooves, texture, pocket feel",
        "examples": [
            "Funk pattern: ghosts on 'e' and 'a' of each beat",
            "Between kick and snare: ghost note fills gap",
            "Ghost density 0.6: ~60% of possible ghost positions filled",
            "Velocity range: 20-45 (vs normal 80-100)"
        ]
    },
    {
        "concept": "Fill Design",
        "explanation": "Fills are transitions between sections, typically 1-2 beats long. Types: tom runs (ascending/descending across toms), snare rolls (with rudiments), cymbal builds (crashes building intensity), mixed (combination). Fills end with crash on downbeat. Complexity (0.0-1.0) controls density and technical difficulty.",
        "application": "Section transitions, energy builds, musicality",
        "examples": [
            "Tom run: floor→mid→high with accent on high",
            "Snare roll: paradiddle pattern building to crash",
            "Cymbal build: crashes on every 8th note with kick",
            "End of 4-bar phrase: 2-beat fill into next section"
        ]
    },
    {
        "concept": "Velocity Profiles",
        "explanation": "Velocity isn't constant - it varies by context. Base velocity (80-110), accent boost (+15-25), ghost reduction (×0.3), random variation (±3-8 for humanization). Phrase shapes: flat (consistent), swell (build up), decay (fade out). Different instruments have different velocity ranges.",
        "application": "Dynamics, expressiveness, humanization",
        "examples": [
            "Snare: base 100, accents 120, ghosts 30",
            "Kick: base 115 (loudest), accents 125",
            "Hi-hat: base 75 (quieter), accents 90",
            "Chorus swell: start 90, build to 110 over 8 bars"
        ]
    },
    {
        "concept": "Hit Styles",
        "explanation": "How a hit is executed affects sound and playability. Single: one stroke. Double: two quick strokes same hand (used in rolls). Bounce: multiple rebounds from one stroke (buzz rolls). Flam: grace note + primary. Drag: double grace + primary. Each style has different timing and sound characteristics.",
        "application": "Rolls, accents, articulation, rudimental work",
        "examples": [
            "Long roll: double strokes (RR LL RR LL)",
            "Buzz roll: bounce technique for smooth sound",
            "Snare accent: flam for fuller sound",
            "Tom fill: single strokes alternating hands"
        ]
    },
    {
        "concept": "Style-Specific Vocabulary",
        "explanation": "Each style has characteristic patterns. Rock: straight 8ths on ride/hats, backbeat emphasis, simple kick patterns. Funk: 16th note hi-hats, ghost notes, syncopated kicks. Jazz: ride cymbal with swing, cross-stick, brushes. Latin: clave-based patterns, specific tom/cymbal work. Style affects instrument choice, timing feel, density.",
        "application": "Genre awareness, authentic generation",
        "examples": [
            "Rock: [kick beat1, snare beat2, kick 'and of 2', snare beat4]",
            "Funk: dense hi-hat 16ths with ghost notes between",
            "Jazz: ride quarter notes with swing, snare on 2&4",
            "Latin: clave pattern dictates kick/snare placement"
        ]
    },
    {
        "concept": "Section Awareness",
        "explanation": "Drums adapt to song sections. Intro: simpler, building energy. Verse: supportive, restrained. Chorus: fuller, more energy. Bridge: variation, often simplified or different pattern. Outro: wind down or big ending. Fills mark transitions. Intensity increases verse→chorus, decreases chorus→verse.",
        "application": "Arrangement, dynamics, musical structure",
        "examples": [
            "Intro: just hi-hat and kick, building",
            "Verse: basic groove, velocity 80-90",
            "Chorus: add crashes, ride, velocity 100-110",
            "Bridge: half-time or pattern variation",
            "Outro: fade or big ending with cymbal crashes"
        ]
    }
]

LIMB_CONSTRAINT_RULES = [
    {
        "rule": "Same Limb Minimum Time",
        "description": "Same limb cannot hit two instruments within ~50ms. Fast drummers can go down to 40ms, beginners need 70-80ms. This prevents physically impossible patterns.",
        "enforcement": "Check time difference between consecutive same-limb hits. Flag conflicts < 50ms.",
        "example": "Right hand snare at 1.000s and right hand tom at 1.030s = 30ms = TOO FAST"
    },
    {
        "rule": "Cross-Stick Time Penalty",
        "description": "Moving stick across body (e.g., right hand from ride to floor tom) takes extra time. Add 20-30ms to minimum time for cross-stick moves.",
        "enforcement": "Detect cross-stick moves, increase minimum time requirement.",
        "example": "Ride→floor tom cross-stick needs 70ms instead of 50ms"
    },
    {
        "rule": "Simultaneous Different Limbs OK",
        "description": "Different limbs can hit simultaneously without conflict. Kick+snare, kick+hat, snare+crash are all valid.",
        "enforcement": "Only check conflicts for same limb, ignore different limbs.",
        "example": "Kick (RF) and snare (RH) at same time = VALID"
    },
    {
        "rule": "Foot Technique Limitations",
        "description": "Single pedal kick: notes must alternate or have minimum time. Double pedal: can play faster. Hi-hat pedal (LF) limits left foot kick on double bass setups.",
        "enforcement": "For single pedal, check kick note spacing. For double pedal, allow faster.",
        "example": "Single pedal 16th notes at 180 BPM = probably impossible"
    },
    {
        "rule": "Priority-Based Conflict Resolution",
        "description": "When limb conflict detected, keep higher priority hit, drop or delay lower priority hit. Preserve musical essentials (backbeat, crashes) over texture (ghosts).",
        "enforcement": "Compare priority values, resolve in favor of higher priority.",
        "example": "Backbeat snare (priority 0.9) vs ghost note (priority 0.3) = keep snare"
    }
]

DRUMMER_PERSONALITY_PROFILES = [
    {
        "drummer": "John Bonham Style",
        "characteristics": "Heavy hits, laid-back feel (+10-15ms), big dynamics (velocity range 60-127), triplet-based fills, simple but powerful patterns, prominent kick, open hi-hats for accents",
        "velocity_profile": "Base 105, accents 125, ghosts 50",
        "timing": "Laid-back 10-15ms on snare/hats",
        "typical_patterns": "Quarter note kick, backbeat snare, occasional 16th kick doubles, triplet fills"
    },
    {
        "drummer": "Bernard Purdie Style",
        "characteristics": "Deep pocket, ghost notes (funk), precise timing (±3ms), shuffle feel, half-time grooves, signature 'Purdie shuffle', medium-high velocity consistency",
        "velocity_profile": "Base 95, accents 110, ghosts 35 (frequent)",
        "timing": "On the pocket, tight timing",
        "typical_patterns": "Ghost note clusters, shuffle hi-hat, syncopated kick, half-time snare"
    },
    {
        "drummer": "Steve Gadd Style",
        "characteristics": "Technical precision, complex fills with rudiments, dynamic control (wide range), brush work, linear patterns (no simultaneous hits), jazz and fusion vocabulary",
        "velocity_profile": "Base 90, accents 115, excellent dynamic range",
        "timing": "Precise, can play ahead or behind as needed",
        "typical_patterns": "Linear grooves, paradiddle-based fills, brush patterns, metric modulation"
    },
    {
        "drummer": "Jeff Porcaro Style",
        "characteristics": "Studio precision, ghost notes, half-time shuffles, ride cymbal grooves, musical fills (not flashy), consistent velocity, serves the song",
        "velocity_profile": "Base 92, accents 108, moderate dynamics",
        "timing": "Slightly laid-back for pocket, very consistent",
        "typical_patterns": "Rosanna half-time shuffle, ghost note funk, ride bell patterns, orchestral fills"
    }
]

def create_brain_concept_examples() -> List[Dict]:
    """Create training examples from brain concepts"""
    examples = []
    
    for concept in JAMSTIX_BRAIN_CONCEPTS:
        # Explanation
        examples.append({
            "task": "explain_drum_concept",
            "input": {
                "question": f"Explain {concept['concept']} in drum programming"
            },
            "output": {
                "explanation": concept['explanation'],
                "application": concept['application'],
                "examples": concept['examples']
            },
            "meta": {
                "source": "jamstix_brain",
                "category": "brain_concept"
            }
        })
        
        # Application
        examples.append({
            "task": "apply_drum_concept",
            "input": {
                "concept": concept['concept'],
                "scenario": concept['application']
            },
            "output": {
                "guidance": concept['explanation'],
                "examples": concept['examples']
            },
            "meta": {
                "source": "jamstix_brain",
                "category": "concept_application"
            }
        })
    
    return examples

def create_limb_constraint_examples() -> List[Dict]:
    """Create training examples for limb constraints"""
    examples = []
    
    for rule in LIMB_CONSTRAINT_RULES:
        examples.append({
            "task": "explain_limb_constraint",
            "input": {
                "question": f"Explain the rule: {rule['rule']}"
            },
            "output": {
                "rule": rule['rule'],
                "description": rule['description'],
                "enforcement": rule['enforcement'],
                "example": rule['example']
            },
            "meta": {
                "source": "jamstix_brain",
                "category": "limb_constraint"
            }
        })
        
        examples.append({
            "task": "validate_pattern_playability",
            "input": {
                "rule": rule['rule'],
                "example_situation": rule['example']
            },
            "output": {
                "is_playable": "impossible" in rule['example'].lower() or "too fast" in rule['example'].lower(),
                "explanation": rule['description'],
                "resolution": rule['enforcement']
            },
            "meta": {
                "source": "jamstix_brain",
                "category": "playability_check"
            }
        })
    
    return examples

def create_drummer_profile_examples() -> List[Dict]:
    """Create training examples for drummer personalities"""
    examples = []
    
    for profile in DRUMMER_PERSONALITY_PROFILES:
        # Profile explanation
        examples.append({
            "task": "explain_drummer_style",
            "input": {
                "drummer": profile['drummer']
            },
            "output": {
                "characteristics": profile['characteristics'],
                "velocity_profile": profile['velocity_profile'],
                "timing": profile['timing'],
                "typical_patterns": profile['typical_patterns']
            },
            "meta": {
                "source": "jamstix_brain",
                "category": "drummer_profile"
            }
        })
        
        # Style emulation
        examples.append({
            "task": "emulate_drummer_style",
            "input": {
                "target_drummer": profile['drummer'],
                "base_pattern": "basic rock groove"
            },
            "output": {
                "adjustments": {
                    "velocity": profile['velocity_profile'],
                    "timing": profile['timing'],
                    "pattern_modifications": profile['typical_patterns']
                },
                "explanation": f"To emulate {profile['drummer']}: {profile['characteristics']}"
            },
            "meta": {
                "source": "jamstix_brain",
                "category": "style_emulation"
            }
        })
    
    return examples

def build_jamstix_brain_jsonl(output_file: Path):
    """Build complete Jamstix brain training JSONL"""
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    examples = []
    examples.extend(create_brain_concept_examples())
    examples.extend(create_limb_constraint_examples())
    examples.extend(create_drummer_profile_examples())
    
    with output_file.open('w', encoding='utf-8') as f:
        for example in examples:
            f.write(json.dumps(example) + '\n')
    
    print(f"✅ Created {len(examples)} Jamstix brain training examples")
    print(f"   Output: {output_file}")
    
    # Summary
    by_task = {}
    by_category = {}
    for ex in examples:
        task = ex['task']
        category = ex['meta'].get('category', 'unknown')
        by_task[task] = by_task.get(task, 0) + 1
        by_category[category] = by_category.get(category, 0) + 1
    
    print(f"\n📊 By Task Type:")
    for task, count in sorted(by_task.items()):
        print(f"   {task}: {count}")
    
    print(f"\n📊 By Category:")
    for category, count in sorted(by_category.items()):
        print(f"   {category}: {count}")

def main():
    output_file = Path("F:/DrumTracKAI_v1.1.16_Clean/llm_training_project/training_datasets/jamstix_brain_train.jsonl")
    
    print("=" * 70)
    print("Jamstix Brain Concepts Corpus Builder")
    print("=" * 70)
    print()
    
    build_jamstix_brain_jsonl(output_file)

if __name__ == "__main__":
    main()

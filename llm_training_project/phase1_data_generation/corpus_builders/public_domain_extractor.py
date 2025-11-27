#!/usr/bin/env python3
"""
Public Domain Drum Instruction Extractor
=========================================
Extracts drum instruction from public domain sources and converts to LLM training format
"""
import json
from pathlib import Path
from typing import List, Dict

# Public domain drum instruction content
# These are pre-1928 public domain sources

PUBLIC_DOMAIN_RUDIMENTS = {
    "single_stroke_roll": {
        "name": "Single Stroke Roll",
        "sticking": "R L R L R L R L",
        "description": "Alternating single strokes played at high speed. Foundation of all drumming.",
        "application": "Fills, solos, building speed and control",
        "difficulty": "beginner",
        "year": "1869",
        "source": "Bruce & Emmett Drummer's Guide"
    },
    "double_stroke_roll": {
        "name": "Double Stroke Roll",
        "sticking": "RR LL RR LL RR LL",
        "description": "Two strokes per hand in alternation. Creates smooth sustained rolls.",
        "application": "Long rolls, orchestral work, traditional rudimental drumming",
        "difficulty": "beginner",
        "year": "1869",
        "source": "Bruce & Emmett Drummer's Guide"
    },
    "paradiddle": {
        "name": "Paradiddle",
        "sticking": "R L RR L R LL",
        "description": "Single-single-double pattern. Fundamental coordination exercise.",
        "application": "Fills, groove variations, limb independence",
        "difficulty": "intermediate",
        "year": "1869",
        "source": "Bruce & Emmett Drummer's Guide"
    },
    "flam": {
        "name": "Flam",
        "sticking": "lR rL (grace note + primary)",
        "description": "Grace note immediately before primary stroke. Creates 'fuller' sound.",
        "application": "Accents, transitions, orchestral work",
        "difficulty": "beginner",
        "year": "1869",
        "source": "Bruce & Emmett Drummer's Guide"
    },
    "drag": {
        "name": "Drag (Ruff)",
        "sticking": "ll R rr L (double grace + primary)",
        "description": "Two grace notes before primary stroke. More pronounced than flam.",
        "application": "Marching, orchestral, adding weight to accents",
        "difficulty": "intermediate",
        "year": "1869",
        "source": "Bruce & Emmett Drummer's Guide"
    },
    "five_stroke_roll": {
        "name": "Five Stroke Roll",
        "sticking": "RR LL R (or LL RR L)",
        "description": "Two doubles ending with single accent. Measured roll.",
        "application": "Fills, orchestral passages, adding texture",
        "difficulty": "intermediate",
        "year": "1869",
        "source": "Bruce & Emmett Drummer's Guide"
    },
    "seven_stroke_roll": {
        "name": "Seven Stroke Roll",
        "sticking": "RR LL RR L (or LL RR LL R)",
        "description": "Three doubles ending with single accent. Longer measured roll.",
        "application": "Extended fills, orchestral crescendos",
        "difficulty": "intermediate",
        "year": "1869",
        "source": "Bruce & Emmett Drummer's Guide"
    },
    "nine_stroke_roll": {
        "name": "Nine Stroke Roll",
        "sticking": "RR LL RR LL R",
        "description": "Four doubles ending with single accent.",
        "application": "Long fills, building tension",
        "difficulty": "advanced",
        "year": "1869",
        "source": "Bruce & Emmett Drummer's Guide"
    },
    "flam_tap": {
        "name": "Flam Tap",
        "sticking": "lR R rL L",
        "description": "Flam followed by tap with same hand.",
        "application": "Groove embellishments, rudimental solos",
        "difficulty": "intermediate",
        "year": "1869",
        "source": "Bruce & Emmett Drummer's Guide"
    },
    "flamacue": {
        "name": "Flamacue",
        "sticking": "lR L R rL R L",
        "description": "Flam-accent-single pattern. Classic rudimental combination.",
        "application": "Solos, orchestral snare work",
        "difficulty": "advanced",
        "year": "1869",
        "source": "Bruce & Emmett Drummer's Guide"
    }
}

DRUM_TECHNIQUE_CONCEPTS = [
    {
        "concept": "Stick Height and Velocity",
        "explanation": "Higher stick height produces louder volume. Control dynamics by varying stick height: low for soft (ghost notes), medium for normal playing, high for accents. Consistent height at each dynamic level ensures even tone.",
        "application": "Dynamic control, ghost notes, accents",
        "source": "Traditional drumming pedagogy (pre-1928)"
    },
    {
        "concept": "Rebound Control",
        "explanation": "Allow stick to bounce naturally after striking. Control rebound for rolls and fast passages. Tense grip stops rebound; relaxed grip allows natural bounce. Multiple-bounce rolls (buzz rolls) use controlled rebound.",
        "application": "Rolls, speed development, relaxation",
        "source": "Traditional drumming pedagogy (pre-1928)"
    },
    {
        "concept": "Accent Patterns",
        "explanation": "Accents are louder notes that create rhythmic emphasis. Common patterns: every 3rd note, every 4th note, alternating. Practice accents on single strokes, then doubles, then paradiddles to develop control.",
        "application": "Groove, phrasing, musicality",
        "source": "Traditional drumming pedagogy (pre-1928)"
    },
    {
        "concept": "Sticking Patterns",
        "explanation": "Alternating hands (R L R L) is foundational. Sticking affects speed, flow, and phrasing. Same-hand patterns (RR or LL) create different feel. Practice all rudiments with both lead hands.",
        "application": "Fills, coordination, vocabulary",
        "source": "Traditional drumming pedagogy (pre-1928)"
    },
    {
        "concept": "Matched Grip vs Traditional Grip",
        "explanation": "Matched: both hands hold sticks identically. Traditional: left hand underhand (from military drum carrying position). Matched provides equal power both hands. Traditional offers subtle tonal control.",
        "application": "Grip choice, comfort, style",
        "source": "Military drumming tradition (1800s)"
    },
    {
        "concept": "Subdivisions and Time",
        "explanation": "Quarter notes divide into 2 eighths, 4 sixteenths, or 3 triplets. Understanding subdivisions enables accurate time placement. Practice with metronome at various tempos.",
        "application": "Timing, accuracy, groove",
        "source": "Traditional drumming pedagogy (pre-1928)"
    },
    {
        "concept": "Orchestral vs Rudimental Style",
        "explanation": "Orchestral: smooth rolls, clean articulation, blend with ensemble. Rudimental: crisp accents, clear stickings, martial precision. Different contexts require different approaches.",
        "application": "Context awareness, adaptability",
        "source": "Traditional drumming pedagogy (pre-1928)"
    }
]

def create_rudiment_training_examples() -> List[Dict]:
    """Create LLM training examples from rudiment knowledge"""
    examples = []
    
    for rudiment_id, rudiment in PUBLIC_DOMAIN_RUDIMENTS.items():
        # Explanation example
        examples.append({
            "task": "explain_drum_concept",
            "input": {
                "question": f"Explain the {rudiment['name']} rudiment"
            },
            "output": {
                "explanation": f"{rudiment['description']} Sticking: {rudiment['sticking']}. "
                              f"Application: {rudiment['application']}.",
                "difficulty": rudiment['difficulty'],
                "sticking": rudiment['sticking']
            },
            "meta": {
                "source": "public_domain",
                "original_source": rudiment['source'],
                "year": rudiment['year'],
                "category": "rudiment"
            }
        })
        
        # Application example
        examples.append({
            "task": "suggest_rudiment",
            "input": {
                "goal": rudiment['application'],
                "difficulty_level": rudiment['difficulty']
            },
            "output": {
                "rudiment": rudiment['name'],
                "sticking": rudiment['sticking'],
                "explanation": f"Use {rudiment['name']} because: {rudiment['description']}"
            },
            "meta": {
                "source": "public_domain",
                "category": "rudiment_application"
            }
        })
        
        # Sticking recognition
        examples.append({
            "task": "identify_rudiment",
            "input": {
                "sticking": rudiment['sticking']
            },
            "output": {
                "rudiment": rudiment['name'],
                "description": rudiment['description']
            },
            "meta": {
                "source": "public_domain",
                "category": "rudiment_recognition"
            }
        })
    
    return examples

def create_technique_training_examples() -> List[Dict]:
    """Create LLM training examples from technique concepts"""
    examples = []
    
    for concept in DRUM_TECHNIQUE_CONCEPTS:
        # Explanation example
        examples.append({
            "task": "explain_drum_concept",
            "input": {
                "question": f"Explain {concept['concept']}"
            },
            "output": {
                "explanation": concept['explanation'],
                "application": concept['application']
            },
            "meta": {
                "source": "public_domain",
                "original_source": concept['source'],
                "category": "technique"
            }
        })
        
        # Application example
        examples.append({
            "task": "apply_technique",
            "input": {
                "situation": concept['application'],
                "technique": concept['concept']
            },
            "output": {
                "guidance": concept['explanation']
            },
            "meta": {
                "source": "public_domain",
                "category": "technique_application"
            }
        })
    
    return examples

def build_public_domain_jsonl(output_file: Path):
    """Build complete public domain training JSONL"""
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    examples = []
    examples.extend(create_rudiment_training_examples())
    examples.extend(create_technique_training_examples())
    
    with output_file.open('w', encoding='utf-8') as f:
        for example in examples:
            f.write(json.dumps(example) + '\n')
    
    print(f"✅ Created {len(examples)} public domain training examples")
    print(f"   Output: {output_file}")
    
    # Summary
    by_task = {}
    for ex in examples:
        task = ex['task']
        by_task[task] = by_task.get(task, 0) + 1
    
    print(f"\n📊 By Task Type:")
    for task, count in sorted(by_task.items()):
        print(f"   {task}: {count}")

def main():
    output_file = Path("F:/DrumTracKAI_v1.1.16_Clean/llm_training_project/training_datasets/public_domain_train.jsonl")
    
    print("=" * 70)
    print("Public Domain Drum Instruction Extractor")
    print("=" * 70)
    print()
    
    build_public_domain_jsonl(output_file)

if __name__ == "__main__":
    main()

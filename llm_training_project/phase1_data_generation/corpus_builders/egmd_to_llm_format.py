#!/usr/bin/env python3
"""
E-GMD Dataset to LLM Training Format Converter
==============================================
Convert extracted E-GMD features to LLM training JSONL
"""
import json
import sqlite3
import sys
from pathlib import Path
from typing import Dict, Any

def convert_egmd_to_llm_format(db_path: Path, output_file: Path):
    """Convert E-GMD extracted features to LLM training format"""
    
    if not db_path.exists():
        print(f"ERROR: Database not found: {db_path}")
        sys.exit(1)
    
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    
    # Get all extracted features
    cur.execute("""
        SELECT 
            source_file, total_hits, duration, tempo, time_signature,
            drum_counts_json, velocity_stats_json, timing_features_json,
            pattern_density, ghost_notes, accents, sequential_patterns_json,
            hihat_articulations_json, fill_segments_json, velocity_curve_json,
            swing_amount, style_hints_json
        FROM egmd_midi_features
    """)
    
    processed = 0
    
    with output_file.open("w", encoding="utf-8") as f_out:
        for row in cur.fetchall():
            (source_file, total_hits, duration, tempo, time_sig,
             drum_counts_json, velocity_stats_json, timing_json,
             density, ghost_notes, accents, seq_patterns_json,
             hihat_json, fills_json, velocity_curve_json,
             swing, style_hints_json) = row
            
            # Parse JSON fields
            drum_counts = json.loads(drum_counts_json) if drum_counts_json else {}
            velocity_stats = json.loads(velocity_stats_json) if velocity_stats_json else {}
            style_hints = json.loads(style_hints_json) if style_hints_json else []
            seq_patterns = json.loads(seq_patterns_json) if seq_patterns_json else {}
            velocity_curve = json.loads(velocity_curve_json) if velocity_curve_json else []
            fills = json.loads(fills_json) if fills_json else []
            
            # Infer dominant style
            dominant_style = "general"
            if "ride_heavy" in style_hints:
                dominant_style = "jazz"
            elif "ghost_note_heavy" in style_hints:
                dominant_style = "funk"
            elif "kick_heavy" in style_hints:
                dominant_style = "rock"
            
            # Build LLM training example for pattern understanding
            record = {
                "task": "analyze_pattern",
                "input": {
                    "total_hits": total_hits,
                    "duration": duration,
                    "tempo": tempo,
                    "time_signature": time_sig,
                    "drum_ratios": {
                        k: v / max(total_hits, 1) 
                        for k, v in drum_counts.items()
                    }
                },
                "output": {
                    "style": dominant_style,
                    "style_hints": style_hints,
                    "ghost_notes": ghost_notes,
                    "accents": accents,
                    "swing_amount": swing,
                    "pattern_density": density,
                    "has_fills": len(fills) > 0,
                    "sequential_patterns": seq_patterns
                },
                "meta": {
                    "source": "egmd_dataset",
                    "source_file": source_file
                }
            }
            
            f_out.write(json.dumps(record) + "\n")
            processed += 1
            
            if processed % 1000 == 0:
                print(f"Processed {processed:,} E-GMD patterns...")
    
    conn.close()
    
    print(f"\nComplete!")
    print(f"  Processed: {processed:,} E-GMD patterns")
    print(f"  Output: {output_file}")

def main():
    db_path = Path("F:/DrumTracKAI_v1.1.16_Clean/admin/data/drum_training.db")
    output_file = Path("F:/DrumTracKAI_v1.1.16_Clean/llm_training_project/training_datasets/egmd_pattern_train.jsonl")
    
    print("=" * 70)
    print("E-GMD → LLM Training JSONL Converter")
    print("=" * 70)
    print(f"Database: {db_path}")
    print(f"Output:   {output_file}")
    print()
    
    convert_egmd_to_llm_format(db_path, output_file)

if __name__ == "__main__":
    main()

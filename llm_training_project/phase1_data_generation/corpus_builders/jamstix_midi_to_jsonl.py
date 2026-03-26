#!/usr/bin/env python3
"""
Jamstix MIDI to LLM Training JSONL Converter
============================================
Converts Jamstix-generated MIDI + metadata to LLM training format
"""
import json
import sys
from pathlib import Path
from typing import Dict, Any, List

try:
    import mido
    MIDO_AVAILABLE = True
except ImportError:
    MIDO_AVAILABLE = False
    print("WARNING: mido not available. Install with: pip install mido")

# General MIDI drum map
GM_DRUM_MAP = {
    36: "kick",
    35: "kick",
    38: "snare_center",
    40: "snare_center",
    37: "snare_rim",
    42: "hihat_closed",
    44: "hihat_pedal",
    46: "hihat_open",
    49: "crash_1",
    57: "crash_2",
    51: "ride_bow",
    53: "ride_bell",
    59: "ride_edge",
    41: "tom_low",
    43: "tom_low",
    45: "tom_mid",
    47: "tom_mid",
    48: "tom_high",
    50: "tom_high",
}

def midi_to_pattern_events(midi_path: Path) -> Dict[str, Any]:
    """Convert MIDI file to pattern representation"""
    if not MIDO_AVAILABLE:
        return {"error": "mido not available"}
    
    try:
        mid = mido.MidiFile(str(midi_path))
        ticks_per_beat = mid.ticks_per_beat
        
        events = []
        current_time_ticks = 0
        
        for track in mid.tracks:
            current_time_ticks = 0
            for msg in track:
                current_time_ticks += msg.time
                
                if msg.type == "note_on" and msg.velocity > 0:
                    instrument_id = GM_DRUM_MAP.get(msg.note, "other")
                    beat_pos = current_time_ticks / ticks_per_beat
                    
                    events.append({
                        "time_beats": beat_pos,
                        "midi_pitch": msg.note,
                        "velocity": msg.velocity,
                        "instrument_id": instrument_id,
                    })
        
        return {
            "ticks_per_beat": ticks_per_beat,
            "events": events,
            "total_hits": len(events)
        }
    
    except Exception as e:
        return {"error": str(e)}

def build_training_jsonl(input_dir: Path, output_file: Path):
    """Build LLM training JSONL from Jamstix generated data"""
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    processed = 0
    failed = 0
    
    with output_file.open("w", encoding="utf-8") as f_out:
        for combo_dir in input_dir.iterdir():
            if not combo_dir.is_dir():
                continue
            
            midi_path = combo_dir / "drums.mid"
            meta_path = combo_dir / "jamstix_meta.json"
            
            if not midi_path.exists() or not meta_path.exists():
                print(f"Skipping {combo_dir.name} - missing files")
                failed += 1
                continue
            
            # Load metadata
            with meta_path.open("r", encoding="utf-8") as f_meta:
                meta = json.load(f_meta)
            
            # Convert MIDI to pattern
            pattern_info = midi_to_pattern_events(midi_path)
            
            if "error" in pattern_info:
                print(f"Error processing {combo_dir.name}: {pattern_info['error']}")
                failed += 1
                continue
            
            # Build training example for pattern generation
            record = {
                "task": "generate_pattern",
                "input": {
                    "style": meta["style"],
                    "drummer": meta["drummer"],
                    "song_preset": meta["song_preset"],
                    "tempo": meta["tempo"],
                    "bars": meta["bars"]
                },
                "output": {
                    "pattern": pattern_info["events"],
                    "ticks_per_beat": pattern_info["ticks_per_beat"],
                    "total_hits": pattern_info["total_hits"]
                },
                "meta": {
                    "source": "jamstix_reaper_batch",
                    "combo_dir": str(combo_dir.name),
                    "generated_at": meta.get("generated_at", "")
                }
            }
            
            f_out.write(json.dumps(record) + "\n")
            processed += 1
            
            if processed % 10 == 0:
                print(f"Processed {processed} combinations...")
    
    print(f"\nComplete!")
    print(f"  Processed: {processed}")
    print(f"  Failed: {failed}")
    print(f"  Output: {output_file}")

def main():
    input_dir = Path("F:/DrumTracKAI_v1.1.16_Clean/llm_training_project/phase1_data_generation/output/jamstix_generated")
    output_file = Path("F:/DrumTracKAI_v1.1.16_Clean/llm_training_project/training_datasets/jamstix_pattern_train.jsonl")
    
    if not input_dir.exists():
        print(f"ERROR: Input directory not found: {input_dir}")
        print("Run the Reaper Lua script first to generate Jamstix data")
        sys.exit(1)
    
    print("=" * 70)
    print("Jamstix MIDI → LLM Training JSONL Converter")
    print("=" * 70)
    print(f"Input:  {input_dir}")
    print(f"Output: {output_file}")
    print()
    
    build_training_jsonl(input_dir, output_file)

if __name__ == "__main__":
    main()

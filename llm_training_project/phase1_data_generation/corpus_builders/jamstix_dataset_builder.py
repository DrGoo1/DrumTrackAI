#!/usr/bin/env python3
"""
Jamstix Dataset Builder - COMPLETE VERSION
===========================================
Converts Jamstix Reaper batch outputs into LLM training JSONL
with correct paths for your system
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
    print("⚠️  mido not installed. Installing...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "mido"])
    import mido
    MIDO_AVAILABLE = True

# Updated paths
BASE_DIR = Path("F:/DrumTrackAI_Jamstix_Dataset")
OUT_JSONL = Path("F:/DrumTracKAI_v1.1.16_Clean/llm_training_project/training_datasets/jamstix_pattern_train.jsonl")

# General MIDI drum map (expanded)
GM_DRUM_MAP = {
    35: "kick",
    36: "kick",
    37: "snare_rim",
    38: "snare_center",
    40: "snare_center",
    41: "tom_low",
    42: "hihat_closed",
    43: "tom_low",
    44: "hihat_pedal",
    45: "tom_mid",
    46: "hihat_open",
    47: "tom_mid",
    48: "tom_high",
    49: "crash_1",
    50: "tom_high",
    51: "ride_bow",
    52: "crash_china",
    53: "ride_bell",
    55: "splash",
    57: "crash_2",
    59: "ride_edge",
}

def midi_to_step_events(midi_path: Path) -> Dict[str, Any]:
    """
    Convert Jamstix MIDI into step-based pattern representation
    Suitable for LLM training
    """
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

def build_jsonl():
    """Build LLM training JSONL from Jamstix generated data"""
    
    print("=" * 70)
    print("Jamstix Dataset Builder - COMPLETE VERSION")
    print("=" * 70)
    print(f"Input:  {BASE_DIR}")
    print(f"Output: {OUT_JSONL}")
    print()
    
    if not BASE_DIR.exists():
        print(f"❌ ERROR: Input directory not found: {BASE_DIR}")
        print()
        print("Please run JamstixBatchGenerator_COMPLETE.lua in Reaper first!")
        return
    
    OUT_JSONL.parent.mkdir(parents=True, exist_ok=True)

    processed = 0
    failed = 0
    skipped = 0

    with OUT_JSONL.open("w", encoding="utf-8") as f_out:
        for combo_dir in sorted(BASE_DIR.iterdir()):
            if not combo_dir.is_dir():
                continue
            
            midi_path = combo_dir / "drums.mid"
            meta_path = combo_dir / "jamstix_meta.json"
            
            if not midi_path.exists():
                print(f"⚠️  Missing MIDI: {combo_dir.name}")
                skipped += 1
                continue
                
            if not meta_path.exists():
                print(f"⚠️  Missing meta: {combo_dir.name}")
                skipped += 1
                continue

            # Load metadata
            try:
                with meta_path.open("r", encoding="utf-8") as f_meta:
                    meta = json.load(f_meta)
            except Exception as e:
                print(f"❌ Error reading meta {combo_dir.name}: {e}")
                failed += 1
                continue

            # Convert MIDI to pattern
            pattern_info = midi_to_step_events(midi_path)
            
            if "error" in pattern_info:
                print(f"❌ MIDI error {combo_dir.name}: {pattern_info['error']}")
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
                    "generated_at": meta.get("generated_at", ""),
                    "combination_id": meta.get("combination_id", 0)
                }
            }
            
            f_out.write(json.dumps(record) + "\n")
            processed += 1
            
            if processed % 10 == 0:
                print(f"✓ Processed {processed} combinations...")

    print()
    print("=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"✅ Processed: {processed}")
    print(f"⚠️  Skipped:   {skipped}")
    print(f"❌ Failed:    {failed}")
    print(f"📁 Output:    {OUT_JSONL}")
    
    if processed > 0:
        file_size_mb = OUT_JSONL.stat().st_size / (1024 * 1024)
        print(f"📊 Size:      {file_size_mb:.2f} MB")
    
    print("=" * 70)
    
    if processed > 0:
        print()
        print("✅ Success! Jamstix training data ready.")
        print()
        print("Next steps:")
        print("1. Combine with existing training data:")
        print("   python llm_training_project/combine_training_datasets.py")
        print()
        print("2. Or train separately on Jamstix data for pattern generation")
    else:
        print()
        print("⚠️  No data processed. Check:")
        print(f"  - Reaper script generated files in: {BASE_DIR}")
        print(f"  - Each combo directory has drums.mid + jamstix_meta.json")

def main():
    build_jsonl()

if __name__ == "__main__":
    main()

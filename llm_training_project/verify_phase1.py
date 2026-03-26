#!/usr/bin/env python3
"""Verify Phase 1 Training Data"""
import json
from pathlib import Path

print("=" * 70)
print("PHASE 1 VERIFICATION")
print("=" * 70)

# Check E-GMD training file
egmd_file = Path("llm_training_project/training_datasets/egmd_pattern_train.jsonl")

if egmd_file.exists():
    print(f"\n✅ E-GMD Training File Found")
    print(f"   Location: {egmd_file}")
    print(f"   Size: {egmd_file.stat().st_size:,} bytes ({egmd_file.stat().st_size / 1024 / 1024:.1f} MB)")
    
    # Count lines
    with egmd_file.open('r', encoding='utf-8') as f:
        lines = sum(1 for _ in f)
    print(f"   Examples: {lines:,}")
    
    # Show first 3 examples
    print(f"\n📋 Sample Training Examples:")
    with egmd_file.open('r', encoding='utf-8') as f:
        for i, line in enumerate(f):
            if i >= 3:
                break
            example = json.loads(line)
            print(f"\n   Example {i+1}:")
            print(f"   Task: {example['task']}")
            print(f"   Input: tempo={example['input'].get('tempo')}, hits={example['input'].get('total_hits')}")
            print(f"   Output: style={example['output'].get('style')}, ghost_notes={example['output'].get('ghost_notes')}")
    
    # Count by style
    print(f"\n📊 Style Distribution:")
    styles = {}
    with egmd_file.open('r', encoding='utf-8') as f:
        for line in f:
            example = json.loads(line)
            style = example['output'].get('style', 'unknown')
            styles[style] = styles.get(style, 0) + 1
    
    for style, count in sorted(styles.items(), key=lambda x: x[1], reverse=True):
        print(f"   {style}: {count:,} ({count/lines*100:.1f}%)")

else:
    print(f"\n❌ E-GMD Training File Not Found")
    print(f"   Expected: {egmd_file}")

# Check Jamstix data
jamstix_file = Path("llm_training_project/training_datasets/jamstix_pattern_train.jsonl")
if jamstix_file.exists():
    print(f"\n✅ Jamstix Training File Found")
    with jamstix_file.open('r', encoding='utf-8') as f:
        jamstix_lines = sum(1 for _ in f)
    print(f"   Examples: {jamstix_lines:,}")
else:
    print(f"\n⚠️  Jamstix Training File Not Found")
    print(f"   Run Reaper automation to generate")

print("\n" + "=" * 70)
print("SUMMARY")
print("=" * 70)
print(f"\n✅ E-GMD: {lines:,} examples ready")
if jamstix_file.exists():
    print(f"✅ Jamstix: {jamstix_lines:,} examples ready")
else:
    print(f"⚠️  Jamstix: Pending (run Reaper automation)")

print(f"\n🎯 Total Training Examples: {lines + (jamstix_lines if jamstix_file.exists() else 0):,}")
print(f"📁 Ready for LLM training!")

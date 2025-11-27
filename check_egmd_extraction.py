#!/usr/bin/env python3
"""Check E-GMD extraction status"""
import sqlite3
from pathlib import Path
import json

db_path = Path("admin/data/drum_training.db")

if not db_path.exists():
    print("❌ Database not found")
    exit(1)

conn = sqlite3.connect(db_path)
cur = conn.cursor()

print("=" * 70)
print("E-GMD EXTRACTION STATUS")
print("=" * 70)

# Check if table exists
cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='egmd_midi_features'")
if not cur.fetchone():
    print("\n❌ No egmd_midi_features table found")
    print("   Extraction hasn't been run yet")
    conn.close()
    exit(0)

# Get total extracted
cur.execute("SELECT COUNT(*) FROM egmd_midi_features")
total = cur.fetchone()[0]

print(f"\n📊 Total Extracted: {total:,} files")

if total == 0:
    print("\n⚠️  No files extracted yet")
    print("   Run the extractor to begin")
    conn.close()
    exit(0)

# Get statistics
cur.execute("""
    SELECT 
        AVG(total_hits),
        AVG(duration),
        AVG(tempo),
        AVG(ghost_notes),
        AVG(accents),
        AVG(swing_amount),
        AVG(pattern_density)
    FROM egmd_midi_features
""")
avg_hits, avg_duration, avg_tempo, avg_ghost, avg_accents, avg_swing, avg_density = cur.fetchone()

print(f"\n📈 Statistics:")
print(f"   Avg Hits per File: {avg_hits:.1f}")
print(f"   Avg Duration: {avg_duration:.1f} seconds")
print(f"   Avg Tempo: {avg_tempo:.1f} BPM")
print(f"   Avg Ghost Notes: {avg_ghost:.1f}")
print(f"   Avg Accents: {avg_accents:.1f}")
print(f"   Avg Swing: {avg_swing:.2f}")
print(f"   Avg Density: {avg_density:.1f} hits/sec")

# Get time signatures
cur.execute("SELECT time_signature, COUNT(*) FROM egmd_midi_features GROUP BY time_signature ORDER BY COUNT(*) DESC LIMIT 5")
print(f"\n🎵 Time Signatures:")
for sig, count in cur.fetchall():
    print(f"   {sig}: {count:,} files ({count/total*100:.1f}%)")

# Get style distribution
cur.execute("SELECT style_hints_json FROM egmd_midi_features")
all_hints = []
for row in cur.fetchall():
    if row[0]:
        hints = json.loads(row[0])
        all_hints.extend(hints)

from collections import Counter
hint_counts = Counter(all_hints)

print(f"\n🎸 Style Distribution:")
for hint, count in hint_counts.most_common(10):
    print(f"   {hint}: {count:,} files ({count/total*100:.1f}%)")

# Check for fills
cur.execute("SELECT COUNT(*) FROM egmd_midi_features WHERE fill_segments_json != '[]'")
files_with_fills = cur.fetchone()[0]
print(f"\n🥁 Fills Detected: {files_with_fills:,} files have fills ({files_with_fills/total*100:.1f}%)")

conn.close()

print("\n" + "=" * 70)
print("COMPLETION STATUS")
print("=" * 70)

target = 91074
completion = (total / target) * 100

print(f"\n✅ Extracted: {total:,} / {target:,} files ({completion:.1f}%)")

if total >= target * 0.95:  # 95% complete
    print("🎉 EXTRACTION COMPLETE!")
    print("\n📚 Ready for next phase: TRAINING")
    print("\n🚀 Next Steps:")
    print("   1. Run: python build_egmd_training_dataset.py")
    print("   2. Then train models on E-GMD features")
    print("   3. Test trained models on style recognition")
elif total >= 1000:
    print("✅ Good progress! Extraction ongoing...")
    print(f"\n⏱️  Estimated remaining: {(target - total) / 1000:.0f} more minutes")
else:
    print("⚠️  Just getting started...")
    print("\n💡 Extraction speed: ~1,000 files/minute")
    print(f"   Total time: ~{target / 1000:.0f} minutes")

print("\n" + "=" * 70)

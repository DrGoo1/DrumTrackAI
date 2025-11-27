#!/usr/bin/env python3
"""
Reset E-GMD Database and Extract All 91,074 Files
==================================================
Drops old table and re-extracts with enhanced features
"""
import sqlite3
import sys
from pathlib import Path

print("=" * 70)
print("E-GMD DATABASE RESET & FULL EXTRACTION")
print("=" * 70)

db_path = Path("admin/data/drum_training.db")

if not db_path.exists():
    print(f"\n❌ Database not found: {db_path}")
    print("   Creating new database...")
    db_path.parent.mkdir(parents=True, exist_ok=True)

# Connect to database
conn = sqlite3.connect(db_path)
cur = conn.cursor()

# Check if old table exists
cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='egmd_midi_features'")
table_exists = cur.fetchone() is not None

if table_exists:
    # Get current count
    cur.execute("SELECT COUNT(*) FROM egmd_midi_features")
    old_count = cur.fetchone()[0]
    
    print(f"\n⚠️  Found existing table with {old_count:,} files")
    print("\n   This will:")
    print(f"   1. DROP the old table (losing {old_count:,} basic extractions)")
    print("   2. CREATE new enhanced schema")
    print("   3. EXTRACT all 91,074 files with enhanced features")
    print("\n   Enhanced features include:")
    print("      - Time signatures")
    print("      - Ghost notes & accents")
    print("      - Sequential patterns")
    print("      - Hi-hat articulations")
    print("      - Fill detection")
    print("      - Velocity curves")
    print("      - Swing detection")
    
    response = input("\n   Continue? (yes/no): ").strip().lower()
    
    if response != 'yes':
        print("\n❌ Cancelled by user")
        conn.close()
        sys.exit(0)
    
    # Drop old table
    print("\n🗑️  Dropping old table...")
    cur.execute("DROP TABLE IF EXISTS egmd_midi_features")
    conn.commit()
    print("   ✅ Old table dropped")
else:
    print("\n✅ No existing table found - starting fresh")

conn.close()

print("\n" + "=" * 70)
print("LAUNCHING ENHANCED EXTRACTOR")
print("=" * 70)
print("\n📋 Configuration:")
print("   E-GMD Path: E:\\E-GMD Dataset")
print("   Max Files: ALL (91,074 MIDI files)")
print("   Enhanced Features: ENABLED")
print("\n⏱️  Estimated Time: ~90 minutes")
print("   (at ~1,000 files/minute)")
print("\n🚀 Starting extraction in 3 seconds...")

import time
time.sleep(3)

# Launch the extractor
print("\n" + "=" * 70)
print("EXTRACTION STARTING...")
print("=" * 70 + "\n")

# Import and run extractor
from admin.training.egmd_midi_extractor import EGMDMIDIExtractor
from pathlib import Path

egmd_path = Path("E:\\E-GMD Dataset")

if not egmd_path.exists():
    print(f"❌ E-GMD path not found: {egmd_path}")
    print("   Please update the path in this script")
    sys.exit(1)

extractor = EGMDMIDIExtractor()

print(f"✅ Extractor initialized")
print(f"   Database: {extractor.db_path}")
print(f"   E-GMD Path: {egmd_path}")
print()

def progress_callback(current, total, stats):
    """Print progress every 100 files"""
    if current % 100 == 0 or current == total:
        elapsed = stats.get('elapsed_time', 0)
        files_per_sec = stats.get('files_per_second', 0)
        remaining = (total - current) / files_per_sec if files_per_sec > 0 else 0
        
        print(f"[{current:6,}/{total:,}] "
              f"Success: {stats['successful']:6,} | "
              f"Failed: {stats['failed']:4} | "
              f"Skipped: {stats['skipped']:4} | "
              f"Speed: {files_per_sec:5.1f} files/sec | "
              f"ETA: {remaining/60:.0f}m")
    
    return True

print("Starting batch extraction...")
print()

results = extractor.batch_extract(
    egmd_path=egmd_path,
    max_files=None,  # Extract ALL files
    progress_callback=progress_callback
)

print("\n" + "=" * 70)
print("EXTRACTION COMPLETE!")
print("=" * 70)

print(f"\n📊 Results:")
print(f"   Total Processed: {results['processed']:,} files")
print(f"   Successful: {results['successful']:,} files")
print(f"   Failed: {results['failed']:,} files")
print(f"   Skipped: {results['skipped']:,} files")
print(f"\n⏱️  Time: {results['elapsed_time']/60:.1f} minutes")
print(f"   Speed: {results['files_per_second']:.1f} files/second")

# Get final stats
print("\n" + "=" * 70)
print("FINAL DATABASE STATS")
print("=" * 70)

stats = extractor.get_extraction_stats()

print(f"\n✅ Total Extracted: {stats['total_extracted']:,} files")
print(f"📊 Avg Hits per File: {stats['avg_hits_per_file']:.1f}")
print(f"⏱️  Avg Duration: {stats['avg_duration']:.1f} seconds")
print(f"🎵 Avg Tempo: {stats['avg_tempo']:.1f} BPM")

if stats['style_distribution']:
    print(f"\n🎸 Style Distribution (top 10):")
    sorted_styles = sorted(stats['style_distribution'].items(), key=lambda x: x[1], reverse=True)[:10]
    for style, count in sorted_styles:
        pct = (count / stats['total_extracted']) * 100 if stats['total_extracted'] > 0 else 0
        print(f"   {style:20s}: {count:6,} ({pct:5.1f}%)")

print("\n" + "=" * 70)
print("🎉 READY FOR TRAINING!")
print("=" * 70)

print("\n📚 Next Steps:")
print("   1. Build training dataset: python build_egmd_training_dataset.py")
print("   2. Train style classifier: python train_style_classifier.py")
print("   3. Train humanization model: python train_humanization_model.py")
print("   4. Train pattern generator: python train_pattern_generator.py")

print(f"\n✅ You now have {stats['total_extracted']:,} professional drummer patterns")
print("   with complete enhanced features ready for training!")
print("\n🚀 This is foundational training from E-GMD!")

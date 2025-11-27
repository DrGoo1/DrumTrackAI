#!/usr/bin/env python3
"""
Auto-Extract All E-GMD Files (No Confirmation)
================================================
"""
import sqlite3
import sys
from pathlib import Path

print("=" * 70)
print("E-GMD FULL EXTRACTION - AUTO MODE")
print("=" * 70)

db_path = Path("admin/data/drum_training.db")

# Connect and drop old table
conn = sqlite3.connect(db_path)
cur = conn.cursor()

print("\n🗑️  Dropping old table...")
cur.execute("DROP TABLE IF EXISTS egmd_midi_features")
conn.commit()
conn.close()
print("   ✅ Old table dropped")

print("\n🚀 Starting extraction of all 91,074 files...")
print("   This will take ~90 minutes\n")

# Import and run extractor
from admin.training.egmd_midi_extractor import EGMDMIDIExtractor

egmd_path = Path("E:\\E-GMD Dataset")
extractor = EGMDMIDIExtractor()

def progress_callback(current, total, stats):
    if current % 100 == 0 or current == total:
        elapsed = stats.get('elapsed_time', 0)
        files_per_sec = stats.get('files_per_second', 0)
        remaining = (total - current) / files_per_sec if files_per_sec > 0 else 0
        
        print(f"[{current:6,}/{total:,}] "
              f"Success: {stats['successful']:6,} | "
              f"Failed: {stats['failed']:4} | "
              f"Speed: {files_per_sec:5.1f}/sec | "
              f"ETA: {remaining/60:.0f}m")
    return True

results = extractor.batch_extract(
    egmd_path=egmd_path,
    max_files=None,
    progress_callback=progress_callback
)

print("\n" + "=" * 70)
print("✅ COMPLETE!")
print("=" * 70)
print(f"\nExtracted: {results['successful']:,} files")
print(f"Time: {results['elapsed_time']/60:.1f} minutes")

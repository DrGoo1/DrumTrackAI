#!/usr/bin/env python3
"""Check what training databases are available"""
from pathlib import Path
import os

print("=" * 70)
print("TRAINING DATABASE INVENTORY")
print("=" * 70)

# Databases mentioned in comprehensive_training_widget.py
potential_databases = [
    ("E-GMD Dataset", "E:\\E-GMD Dataset"),
    ("SoundTracksLoops Dataset", "E:\\SoundTracksLoops Dataset"),
    ("Drum Loops 60-125 BPM", "E:\\Drum Loops 60-125 BPM"),
    ("Drum Loops 130-180 BPM", "E:\\Drum Loops 130-180 BPM"),
    ("Drum Samples", "database/drum_samples"),
    ("Snare Rudiments", "database/snare_rudiments"),
    ("SD3 Extracted Samples", "database/sd3_samples"),
]

found_databases = []
missing_databases = []

for name, path in potential_databases:
    p = Path(path)
    if p.exists():
        print(f"\n✅ {name}")
        print(f"   Path: {path}")
        
        # Count files
        try:
            if p.is_dir():
                all_files = list(p.rglob("*"))
                audio_files = [f for f in all_files if f.suffix.lower() in ['.wav', '.mp3', '.flac', '.mid', '.midi']]
                print(f"   Total items: {len(all_files)}")
                print(f"   Audio/MIDI files: {len(audio_files)}")
                
                if audio_files:
                    # Sample file types
                    extensions = {}
                    for f in audio_files:
                        ext = f.suffix.lower()
                        extensions[ext] = extensions.get(ext, 0) + 1
                    print(f"   File types: {extensions}")
        except Exception as e:
            print(f"   Error scanning: {e}")
        
        found_databases.append((name, path, len(audio_files) if 'audio_files' in locals() else 0))
    else:
        missing_databases.append((name, path))
        print(f"\n❌ {name}")
        print(f"   Path: {path}")
        print(f"   Status: NOT FOUND")

print("\n" + "=" * 70)
print("SUMMARY")
print("=" * 70)

print(f"\n✅ Found: {len(found_databases)} databases")
for name, path, count in found_databases:
    print(f"   - {name}: {count} files")

print(f"\n❌ Missing: {len(missing_databases)} databases")
for name, path in missing_databases:
    print(f"   - {name}")

print("\n" + "=" * 70)
print("CURRENT TRAINING DATA")
print("=" * 70)

# Check current training database
db_path = Path("admin/data/drum_training.db")
if db_path.exists():
    import sqlite3
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    
    cur.execute("SELECT COUNT(*) FROM humanization_features")
    feature_count = cur.fetchone()[0]
    
    cur.execute("SELECT COUNT(*) FROM sd_samples")
    sample_count = cur.fetchone()[0]
    
    print(f"\n📊 Current Database: {feature_count} humanization features")
    print(f"📊 Current Database: {sample_count} SD samples")
    
    conn.close()

print("\n" + "=" * 70)
print("RECOMMENDATION")
print("=" * 70)

if found_databases:
    print("\n✅ You have external databases available!")
    print("\nTo train on these databases, you need to:")
    print("   1. Extract features from audio/MIDI files")
    print("   2. Store features in admin/data/drum_training.db")
    print("   3. Then run neural network training")
    print("\n   The current training only uses the 50 pre-extracted features.")
    print("   To learn from E-GMD, SoundTracks, etc., you need feature extraction first!")
else:
    print("\n❌ No external databases found on E:\\ drive")
    print("\nThe comprehensive training widget references databases that don't exist yet.")
    print("You would need to:")
    print("   1. Obtain E-GMD dataset")
    print("   2. Obtain SoundTracksLoops dataset")
    print("   3. Set up feature extraction pipeline")
    print("   4. Then train on extracted features")

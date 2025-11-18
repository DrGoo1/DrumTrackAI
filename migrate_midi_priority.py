"""
Priority MIDI Migration - Get AI training started FAST
Migrates only the 91,074 MIDI files first (most important for AI)
"""

import os
import shutil
from pathlib import Path
import json
from datetime import datetime
from tqdm import tqdm

class MIDIPriorityMigrator:
    def __init__(self):
        self.stats = {'copied': 0, 'skipped': 0, 'errors': 0}
        self.log = []
        
    def migrate_midi_only(self):
        """Migrate ONLY MIDI files for fast AI training start"""
        print("🎵 MIDI Priority Migration")
        print("="*60)
        print("Migrating 91,074 MIDI patterns")
        print("Estimated time: 2-3 hours")
        print("="*60)
        
        # Only migrate E-GMD (has all the MIDI)
        source = "E:/E-GMD Dataset"
        dest = "E:/DrumTracKAI_Master/01_MIDI_Patterns/Datasets/E-GMD"
        
        if not os.path.exists(source):
            print(f"❌ Source not found: {source}")
            return
        
        os.makedirs(dest, exist_ok=True)
        
        # Count MIDI files first
        print("\n📊 Counting MIDI files...")
        midi_files = []
        for root, dirs, files in os.walk(source):
            for file in files:
                if file.lower().endswith(('.mid', '.midi')):
                    midi_files.append(os.path.join(root, file))
        
        total = len(midi_files)
        print(f"Found {total:,} MIDI files\n")
        
        # Migrate with progress bar
        print("🚀 Migrating MIDI files...")
        
        with tqdm(total=total, desc="MIDI Files", unit="file") as pbar:
            for source_path in midi_files:
                try:
                    # Preserve folder structure
                    rel_path = os.path.relpath(source_path, source)
                    dest_path = os.path.join(dest, rel_path)
                    
                    # Create destination folder
                    os.makedirs(os.path.dirname(dest_path), exist_ok=True)
                    
                    # Copy file (preserve metadata)
                    if not os.path.exists(dest_path):
                        shutil.copy2(source_path, dest_path)
                        self.stats['copied'] += 1
                        
                        self.log.append({
                            'source': source_path,
                            'dest': dest_path,
                            'timestamp': datetime.now().isoformat()
                        })
                    else:
                        self.stats['skipped'] += 1
                    
                except Exception as e:
                    self.stats['errors'] += 1
                    if self.stats['errors'] < 10:
                        print(f"\n❌ Error: {Path(source_path).name}: {e}")
                
                pbar.update(1)
        
        # Save log
        log_file = f'midi_migration_log_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
        with open(log_file, 'w') as f:
            json.dump({
                'stats': self.stats,
                'log': self.log[:1000]  # First 1000 for space
            }, f, indent=2)
        
        print("\n" + "="*60)
        print("📊 MIDI MIGRATION COMPLETE")
        print("="*60)
        print(f"✓ Copied: {self.stats['copied']:,} files")
        print(f"⏭ Skipped: {self.stats['skipped']:,} (already existed)")
        if self.stats['errors'] > 0:
            print(f"❌ Errors: {self.stats['errors']}")
        print(f"\n✓ Log saved: {log_file}")
        
        print("\n🎯 NEXT STEPS:")
        print("1. Run: python ultimate_scanner.py --midi-only")
        print("2. Start AI training data preparation")
        print("3. Audio samples can migrate overnight")

if __name__ == "__main__":
    migrator = MIDIPriorityMigrator()
    migrator.migrate_midi_only()

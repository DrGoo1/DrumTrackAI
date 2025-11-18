"""
Complete E Drive Migration Plan
Ensures ALL drum-related folders are properly organized
"""

import os
import shutil
from pathlib import Path
import json
from datetime import datetime
import hashlib

class CompleteMigrator:
    def __init__(self, dry_run=True):
        self.dry_run = dry_run
        self.log = []
        self.stats = {'moved': 0, 'copied': 0, 'skipped': 0, 'errors': 0}
        
        # COMPLETE folder mapping
        self.folder_mappings = {
            # ============================================
            # MIDI PATTERNS - All pattern datasets
            # ============================================
            'E:/E-GMD Dataset': {
                'dest': 'E:/DrumTracKAI_Master/01_MIDI_Patterns/Datasets/E-GMD',
                'type': 'midi_patterns',
                'description': 'Extended Groove MIDI Dataset',
                'organize_by': 'style'  # rock, jazz, funk, etc.
            },
            
            'E:/SoundTracksLoops Dataset': {
                'dest': 'E:/DrumTracKAI_Master/01_MIDI_Patterns/Datasets/SoundTracksLoops',
                'type': 'midi_patterns',
                'description': 'Production loops and patterns',
                'organize_by': 'section'  # verse, chorus, fill
            },
            
            'E:/Snare Rudiments': {
                'dest': 'E:/DrumTracKAI_Master/01_MIDI_Patterns/Datasets/Rudiments',
                'type': 'midi_patterns',
                'description': 'Snare rudiments library',
                'organize_by': 'rudiment_type'  # single_stroke, paradiddles, etc.
            },
            
            # ============================================
            # AUDIO SAMPLES - Individual drum hits
            # ============================================
            'E:/Kick Database': {
                'dest': 'E:/DrumTracKAI_Master/02_Audio_Samples/Acoustic_Drums/Kick',
                'type': 'audio_samples',
                'description': 'Kick drum samples',
                'organize_by': 'manufacturer'  # Ludwig, DW, Pearl, etc.
            },
            
            'E:/Snare Database': {
                'dest': 'E:/DrumTracKAI_Master/02_Audio_Samples/Acoustic_Drums/Snare',
                'type': 'audio_samples',
                'description': 'Snare drum samples',
                'organize_by': 'manufacturer'
            },
            
            'E:/Tom Database': {
                'dest': 'E:/DrumTracKAI_Master/02_Audio_Samples/Acoustic_Drums/Toms',
                'type': 'audio_samples',
                'description': 'Tom drum samples',
                'organize_by': 'size'  # 10", 12", 14", 16", etc.
            },
            
            'E:/Cymbal Database': {
                'dest': 'E:/DrumTracKAI_Master/02_Audio_Samples/Acoustic_Drums',
                'type': 'audio_samples',
                'description': 'Cymbal samples (ride, crash, hi-hat)',
                'organize_by': 'cymbal_type'  # Ride, Crash, Hi-Hat subfolders
            },
            
            'E:/Drum Samples': {
                'dest': 'E:/DrumTracKAI_Master/02_Audio_Samples/Acoustic_Drums',
                'type': 'audio_samples',
                'description': 'Mixed drum samples',
                'organize_by': 'drum_type'  # Auto-detect kick/snare/etc.
            },
            
            # ============================================
            # SAMPLE LIBRARIES - Commercial libraries
            # ============================================
            'E:/MDLib2.2': {
                'dest': 'E:/DrumTracKAI_Master/02_Audio_Samples/Sample_Libraries/MDLib2.2',
                'type': 'sample_library',
                'description': 'MDLib sample library',
                'organize_by': 'kit'
            },
            
            'E:/MindSt Samples': {
                'dest': 'E:/DrumTracKAI_Master/02_Audio_Samples/Sample_Libraries/MindSt',
                'type': 'sample_library',
                'description': 'MindSt sample collection',
                'organize_by': 'kit'
            },
            
            'E:/Samples': {
                'dest': 'E:/DrumTracKAI_Master/02_Audio_Samples/Sample_Libraries/General',
                'type': 'sample_library',
                'description': 'General samples folder',
                'organize_by': 'auto_detect'
            },
            
            # ============================================
            # EXISTING DRUMTRACKAI DATA
            # ============================================
            'E:/DrumTracKAI_Database': {
                'dest': 'E:/DrumTracKAI_Master/06_Database/Legacy',
                'type': 'database',
                'description': 'Legacy DrumTracKAI database files',
                'organize_by': 'none'
            },
            
            'E:/DrumTrackAI_Data': {
                'dest': 'E:/DrumTracKAI_Master/05_Analysis_Results/Legacy',
                'type': 'analysis_data',
                'description': 'Legacy analysis data',
                'organize_by': 'none'
            },
            
            'E:/DrumTracksAI': {
                'dest': 'E:/DrumTracKAI_Master/05_Analysis_Results/Legacy',
                'type': 'analysis_data',
                'description': 'Legacy DrumTracksAI data',
                'organize_by': 'none'
            },
            
            'E:/DrumAnalyzer': {
                'dest': 'E:/DrumTracKAI_Master/05_Analysis_Results/Legacy',
                'type': 'analysis_data',
                'description': 'DrumAnalyzer results',
                'organize_by': 'none'
            },
        }
    
    def scan_and_plan(self):
        """Scan all folders and create migration plan"""
        print("\n" + "="*70)
        print("📋 COMPLETE MIGRATION PLAN")
        print("="*70)
        
        plan = {
            'total_folders': 0,
            'total_files': 0,
            'total_size_gb': 0.0,
            'folders': {}
        }
        
        for source, config in self.folder_mappings.items():
            if os.path.exists(source):
                print(f"\n📁 {source}")
                print(f"   → {config['dest']}")
                print(f"   Type: {config['type']}")
                print(f"   Description: {config['description']}")
                
                # Count files
                file_count = 0
                midi_count = 0
                audio_count = 0
                total_size = 0
                
                for root, dirs, files in os.walk(source):
                    for file in files:
                        file_path = os.path.join(root, file)
                        try:
                            size = os.path.getsize(file_path)
                            total_size += size
                            file_count += 1
                            
                            ext = Path(file).suffix.lower()
                            if ext in ['.mid', '.midi']:
                                midi_count += 1
                            elif ext in ['.wav', '.mp3', '.flac', '.aiff', '.ogg']:
                                audio_count += 1
                        except:
                            pass
                
                size_gb = total_size / (1024**3)
                
                print(f"   Files: {file_count:,}")
                if midi_count > 0:
                    print(f"   MIDI: {midi_count:,}")
                if audio_count > 0:
                    print(f"   Audio: {audio_count:,}")
                print(f"   Size: {size_gb:.2f} GB")
                
                plan['folders'][source] = {
                    'destination': config['dest'],
                    'file_count': file_count,
                    'midi_count': midi_count,
                    'audio_count': audio_count,
                    'size_gb': size_gb,
                    'type': config['type']
                }
                
                plan['total_folders'] += 1
                plan['total_files'] += file_count
                plan['total_size_gb'] += size_gb
                
            else:
                print(f"\n⚠ NOT FOUND: {source}")
        
        # Print summary
        print("\n" + "="*70)
        print("📊 MIGRATION SUMMARY")
        print("="*70)
        print(f"Folders to migrate: {plan['total_folders']}")
        print(f"Total files: {plan['total_files']:,}")
        print(f"Total size: {plan['total_size_gb']:.2f} GB")
        
        # Save plan
        plan_file = 'migration_plan.json'
        with open(plan_file, 'w') as f:
            json.dump(plan, f, indent=2)
        
        print(f"\n✓ Plan saved to: {plan_file}")
        
        # Show breakdown by type
        print("\n📦 By Type:")
        type_stats = {}
        for folder_info in plan['folders'].values():
            ftype = folder_info['type']
            if ftype not in type_stats:
                type_stats[ftype] = {'files': 0, 'size': 0}
            type_stats[ftype]['files'] += folder_info['file_count']
            type_stats[ftype]['size'] += folder_info['size_gb']
        
        for ftype, stats in sorted(type_stats.items()):
            print(f"  {ftype:20s}: {stats['files']:6,} files, {stats['size']:6.2f} GB")
        
        return plan
    
    def execute_migration(self, use_copy=True):
        """Execute the migration (copy or move)"""
        if self.dry_run:
            print("\n⚠ This is a DRY RUN - no files will be moved")
            return
        
        action = "Copying" if use_copy else "Moving"
        print(f"\n🚚 {action} files...")
        print("="*70)
        
        for source, config in self.folder_mappings.items():
            if not os.path.exists(source):
                continue
            
            dest = config['dest']
            print(f"\n📁 {Path(source).name}")
            
            # Create destination
            os.makedirs(dest, exist_ok=True)
            
            # Process files
            file_count = 0
            for root, dirs, files in os.walk(source):
                for file in files:
                    source_path = os.path.join(root, file)
                    
                    # Determine subfolder based on organize_by
                    subfolder = self._determine_subfolder(
                        source_path, 
                        config['organize_by']
                    )
                    
                    dest_path = os.path.join(dest, subfolder, file)
                    os.makedirs(os.path.dirname(dest_path), exist_ok=True)
                    
                    try:
                        if use_copy:
                            shutil.copy2(source_path, dest_path)
                            self.stats['copied'] += 1
                        else:
                            shutil.move(source_path, dest_path)
                            self.stats['moved'] += 1
                        
                        file_count += 1
                        if file_count % 100 == 0:
                            print(f"  Processed {file_count} files...")
                        
                        # Log
                        self.log.append({
                            'source': source_path,
                            'dest': dest_path,
                            'action': 'copy' if use_copy else 'move',
                            'timestamp': datetime.now().isoformat()
                        })
                        
                    except Exception as e:
                        self.stats['errors'] += 1
                        print(f"  ✗ Error: {file}: {e}")
            
            print(f"  ✓ {file_count} files processed")
        
        # Save log
        log_file = f'migration_log_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
        with open(log_file, 'w') as f:
            json.dump({
                'stats': self.stats,
                'log': self.log
            }, f, indent=2)
        
        print(f"\n✓ Migration log saved: {log_file}")
        print(f"\n📊 Final Stats:")
        print(f"  Copied: {self.stats['copied']}")
        print(f"  Moved: {self.stats['moved']}")
        print(f"  Errors: {self.stats['errors']}")
    
    def _determine_subfolder(self, file_path, organize_by):
        """Determine subfolder based on organization method"""
        if organize_by == 'none':
            return ''
        
        path_str = file_path.lower()
        file_name = Path(file_path).name.lower()
        
        if organize_by == 'style':
            # Music style detection
            if 'rock' in path_str or 'rock' in file_name:
                return 'rock'
            elif 'jazz' in path_str or 'jazz' in file_name:
                return 'jazz'
            elif 'funk' in path_str or 'funk' in file_name:
                return 'funk'
            elif 'metal' in path_str:
                return 'metal'
            elif 'latin' in path_str:
                return 'latin'
            return 'uncategorized'
        
        elif organize_by == 'section':
            if 'verse' in path_str:
                return 'verse_patterns'
            elif 'chorus' in path_str:
                return 'chorus_patterns'
            elif 'fill' in path_str:
                return 'fills'
            elif 'loop' in path_str:
                return 'loops'
            return 'uncategorized'
        
        elif organize_by == 'manufacturer':
            manufacturers = ['ludwig', 'dw', 'pearl', 'yamaha', 'tama', 'gretsch']
            for mfr in manufacturers:
                if mfr in path_str or mfr in file_name:
                    return mfr.capitalize()
            return 'Other'
        
        elif organize_by == 'cymbal_type':
            if 'ride' in path_str or 'ride' in file_name:
                return 'Ride'
            elif 'crash' in path_str or 'crash' in file_name:
                return 'Crash'
            elif 'hihat' in path_str or 'hi-hat' in path_str or 'hh' in file_name:
                return 'Hi-Hat'
            return 'Other_Cymbals'
        
        elif organize_by == 'drum_type':
            if 'kick' in path_str or 'bass drum' in path_str:
                return 'Kick'
            elif 'snare' in path_str:
                return 'Snare'
            elif 'tom' in path_str:
                return 'Toms'
            elif 'hihat' in path_str or 'hi-hat' in path_str:
                return 'Hi-Hat'
            return 'Mixed'
        
        return ''

def main():
    import sys
    
    dry_run = '--execute' not in sys.argv
    
    print("🎵 DrumTracKAI Complete Migration Tool")
    print("="*70)
    
    migrator = CompleteMigrator(dry_run=dry_run)
    
    # Step 1: Scan and create plan
    plan = migrator.scan_and_plan()
    
    if dry_run:
        print("\n" + "="*70)
        print("📋 NEXT STEPS:")
        print("="*70)
        print("1. Review migration_plan.json")
        print("2. Run: python create_optimal_structure.py")
        print("3. Run: python complete_migration_plan.py --execute")
    else:
        print("\n⚠ Ready to migrate files!")
        response = input("Use COPY (safer) or MOVE? (copy/move): ")
        use_copy = response.lower() != 'move'
        migrator.execute_migration(use_copy=use_copy)

if __name__ == "__main__":
    main()

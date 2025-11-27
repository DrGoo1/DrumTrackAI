"""
Analyze Current E Drive Structure
Generates report of what exists and where it should go
"""

import os
from pathlib import Path
from collections import defaultdict
import json

class StructureAnalyzer:
    def __init__(self):
        self.stats = defaultdict(int)
        self.file_catalog = []
        
    def analyze_e_drive(self):
        """Analyze all drum-related folders on E drive"""
        print("🔍 Analyzing E Drive Structure...")
        print("="*60)
        
        folders_to_analyze = [
            "E:/E-GMD Dataset",
            "E:/SoundTracksLoops Dataset",
            "E:/Snare Rudiments",
            "E:/Kick Database",
            "E:/Snare Database",
            "E:/Tom Database",
            "E:/Cymbal Database",
            "E:/Drum Samples",
            "E:/Samples",
            "E:/MDLib2.2",
            "E:/MindSt Samples",
        ]
        
        for folder in folders_to_analyze:
            if os.path.exists(folder):
                print(f"\n📁 {folder}")
                self.analyze_folder(folder)
            else:
                print(f"\n⚠ Not found: {folder}")
        
        self.generate_report()
    
    def analyze_folder(self, folder_path):
        """Analyze a single folder"""
        midi_count = 0
        wav_count = 0
        mp3_count = 0
        other_count = 0
        total_size = 0
        
        for root, dirs, files in os.walk(folder_path):
            for file in files:
                file_path = os.path.join(root, file)
                ext = Path(file).suffix.lower()
                
                try:
                    size = os.path.getsize(file_path)
                    total_size += size
                    
                    # Categorize
                    file_info = {
                        'path': file_path,
                        'name': file,
                        'size': size,
                        'extension': ext,
                        'folder': folder_path
                    }
                    self.file_catalog.append(file_info)
                    
                    if ext in ['.mid', '.midi']:
                        midi_count += 1
                        self.stats['total_midi'] += 1
                    elif ext == '.wav':
                        wav_count += 1
                        self.stats['total_wav'] += 1
                    elif ext == '.mp3':
                        mp3_count += 1
                        self.stats['total_mp3'] += 1
                    elif ext in ['.flac', '.aiff', '.ogg']:
                        other_count += 1
                        self.stats['total_other_audio'] += 1
                    
                except Exception as e:
                    pass
        
        # Print folder stats
        print(f"  MIDI: {midi_count}")
        print(f"  WAV: {wav_count}")
        print(f"  MP3: {mp3_count}")
        print(f"  Other: {other_count}")
        print(f"  Total size: {total_size / (1024**3):.2f} GB")
    
    def generate_report(self):
        """Generate analysis report"""
        print("\n" + "="*60)
        print("📊 ANALYSIS REPORT")
        print("="*60)
        
        print(f"\nTotal Files Found: {len(self.file_catalog)}")
        print(f"  MIDI files: {self.stats['total_midi']}")
        print(f"  WAV files: {self.stats['total_wav']}")
        print(f"  MP3 files: {self.stats['total_mp3']}")
        print(f"  Other audio: {self.stats['total_other_audio']}")
        
        # Group by destination
        print("\n📦 Recommended Migration:")
        
        patterns_dest = [f for f in self.file_catalog if f['extension'] in ['.mid', '.midi']]
        samples_dest = [f for f in self.file_catalog if f['extension'] in ['.wav', '.mp3', '.flac', '.aiff']]
        
        print(f"\n  → 01_MIDI_Patterns/: {len(patterns_dest)} files")
        print(f"  → 02_Audio_Samples/: {len(samples_dest)} files")
        
        # Identify duplicates
        print("\n🔍 Checking for duplicates...")
        name_counts = defaultdict(int)
        for f in self.file_catalog:
            name_counts[f['name']] += 1
        
        duplicates = {name: count for name, count in name_counts.items() if count > 1}
        if duplicates:
            print(f"  Found {len(duplicates)} duplicate filenames:")
            for name, count in list(duplicates.items())[:10]:
                print(f"    {name}: {count} copies")
        else:
            print("  No duplicates found ✓")
        
        # Save detailed report
        report = {
            'total_files': len(self.file_catalog),
            'statistics': dict(self.stats),
            'duplicates': duplicates,
            'files_by_folder': {}
        }
        
        # Group files by current folder
        for file in self.file_catalog:
            folder = file['folder']
            if folder not in report['files_by_folder']:
                report['files_by_folder'][folder] = []
            report['files_by_folder'][folder].append({
                'name': file['name'],
                'size': file['size'],
                'extension': file['extension']
            })
        
        with open('e_drive_analysis_report.json', 'w') as f:
            json.dump(report, f, indent=2)
        
        print("\n✓ Detailed report saved to: e_drive_analysis_report.json")
        print("\n📋 Next Steps:")
        print("  1. Review the report")
        print("  2. Run: python create_optimal_structure.py")
        print("  3. Run: python migrate_files.py --dry-run")

if __name__ == "__main__":
    analyzer = StructureAnalyzer()
    analyzer.analyze_e_drive()

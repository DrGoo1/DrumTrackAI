"""
Ultimate DrumTracKAI Scanner
Scans all E drive folders recursively and intelligently indexes everything
"""

import os
import sqlite3
import json
import mido
from pathlib import Path
from typing import Dict, List, Optional
import hashlib
import wave
import struct
from dataclasses import dataclass
import re

class UnifiedDatabaseManager:
    """Manages the unified DrumTracKAI database"""
    
    def __init__(self, db_path: str = "f:/DrumTracKAI_v1.1.16_Clean/admin/drumtrackai.db"):
        self.db_path = db_path
        self.conn = None
        self.init_database()
    
    def init_database(self):
        """Initialize database with unified schema"""
        self.conn = sqlite3.connect(self.db_path)
        
        # Check if tables exist
        cursor = self.conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='drum_patterns'")
        exists = cursor.fetchone() is not None
        
        if not exists:
            # Execute schema only if tables don't exist
            with open('unified_database_schema.sql', 'r') as f:
                self.conn.executescript(f.read())
            self.conn.commit()
            print(f"✓ Database initialized: {self.db_path}")
        else:
            print(f"✓ Using existing database: {self.db_path}")
    
    def close(self):
        if self.conn:
            self.conn.close()


class UltimateScanner:
    """Scans and indexes all drum-related files"""
    
    def __init__(self, db: UnifiedDatabaseManager):
        self.db = db
        self.stats = {
            'patterns_found': 0,
            'samples_found': 0,
            'midi_files': 0,
            'audio_files': 0,
            'errors': 0
        }
    
    def scan_all_e_drive(self):
        """Scan all relevant folders on E drive"""
        print("\n" + "="*60)
        print("🔍 ULTIMATE E DRIVE SCANNER")
        print("="*60)
        
        folders_to_scan = [
            ("E:/E-GMD Dataset", "egmd", "patterns"),
            ("E:/SoundTracksLoops Dataset", "soundtracks", "patterns"),
            ("E:/Snare Rudiments", "rudiments", "patterns"),
            ("E:/Kick Database", "kick_samples", "samples"),
            ("E:/Snare Database", "snare_samples", "samples"),
            ("E:/Tom Database", "tom_samples", "samples"),
            ("E:/Cymbal Database", "cymbal_samples", "samples"),
            ("E:/Drum Samples", "general_samples", "samples"),
            ("E:/Samples", "samples", "samples"),
            ("E:/MDLib2.2", "mdlib", "samples"),
            ("E:/MindSt Samples", "mindst", "samples"),
        ]
        
        for folder_path, source_name, scan_type in folders_to_scan:
            if os.path.exists(folder_path):
                print(f"\n📁 Scanning: {folder_path}")
                if scan_type == "patterns":
                    self.scan_pattern_folder(folder_path, source_name)
                else:
                    self.scan_sample_folder(folder_path, source_name)
            else:
                print(f"⚠ Folder not found: {folder_path}")
        
        self.print_statistics()
    
    def scan_pattern_folder(self, folder_path: str, source: str):
        """Scan folder for MIDI patterns"""
        print(f"  Looking for MIDI patterns...")
        
        midi_files = []
        for root, dirs, files in os.walk(folder_path):
            for file in files:
                if file.lower().endswith(('.mid', '.midi')):
                    midi_files.append(os.path.join(root, file))
        
        print(f"  Found {len(midi_files)} MIDI files")
        
        for idx, midi_path in enumerate(midi_files):
            if idx % 100 == 0 and idx > 0:
                print(f"    Processed {idx}/{len(midi_files)}...")
            
            try:
                self.index_midi_pattern(midi_path, source)
                self.stats['patterns_found'] += 1
                self.stats['midi_files'] += 1
            except Exception as e:
                self.stats['errors'] += 1
                if self.stats['errors'] < 10:  # Only print first 10 errors
                    print(f"    ✗ Error: {Path(midi_path).name}: {e}")
        
        print(f"  ✓ Indexed {self.stats['patterns_found']} patterns")
    
    def scan_sample_folder(self, folder_path: str, source: str):
        """Scan folder for audio samples"""
        print(f"  Looking for audio samples...")
        
        audio_extensions = {'.wav', '.mp3', '.flac', '.aiff', '.ogg'}
        audio_files = []
        
        for root, dirs, files in os.walk(folder_path):
            for file in files:
                if Path(file).suffix.lower() in audio_extensions:
                    audio_files.append(os.path.join(root, file))
        
        print(f"  Found {len(audio_files)} audio files")
        
        for idx, audio_path in enumerate(audio_files):
            if idx % 100 == 0 and idx > 0:
                print(f"    Processed {idx}/{len(audio_files)}...")
            
            try:
                self.index_audio_sample(audio_path, source)
                self.stats['samples_found'] += 1
                self.stats['audio_files'] += 1
            except Exception as e:
                self.stats['errors'] += 1
        
        print(f"  ✓ Indexed {self.stats['samples_found']} samples")
    
    def index_midi_pattern(self, file_path: str, source: str):
        """Extract and index MIDI pattern"""
        mid = mido.MidiFile(file_path)
        
        # Extract tempo
        tempo_bpm = 120.0
        time_sig = "4/4"
        
        for track in mid.tracks:
            for msg in track:
                if msg.type == 'set_tempo':
                    tempo_bpm = mido.tempo2bpm(msg.tempo)
                    break
                elif msg.type == 'time_signature':
                    time_sig = f"{msg.numerator}/{msg.denominator}"
            if tempo_bpm != 120.0:
                break
        
        # Count hits by drum type
        drum_hits = {
            'kick': 0, 'snare': 0, 'hihat': 0,
            'ride': 0, 'tom': 0, 'crash': 0
        }
        
        kick_times = []
        snare_times = []
        hihat_times = []
        
        time = 0.0
        for track in mid.tracks:
            for msg in track:
                time += msg.time
                if msg.type == 'note_on' and msg.velocity > 0:
                    # GM drum mapping
                    if msg.note == 36:
                        drum_hits['kick'] += 1
                        kick_times.append(time)
                    elif msg.note == 38:
                        drum_hits['snare'] += 1
                        snare_times.append(time)
                    elif msg.note in [42, 44, 46]:
                        drum_hits['hihat'] += 1
                        hihat_times.append(time)
                    elif msg.note == 51:
                        drum_hits['ride'] += 1
                    elif msg.note in [41, 43, 45, 47, 48, 50]:
                        drum_hits['tom'] += 1
                    elif msg.note in [49, 55, 57]:
                        drum_hits['crash'] += 1
        
        duration_seconds = mid.length
        duration_bars = max(1, int((duration_seconds / 60.0) * tempo_bpm / 4.0))
        
        # Normalize timing patterns
        if duration_seconds > 0:
            kick_pattern = json.dumps([t / duration_seconds for t in kick_times[:32]])
            snare_pattern = json.dumps([t / duration_seconds for t in snare_times[:32]])
            hihat_pattern = json.dumps([t / duration_seconds for t in hihat_times[:32]])
        else:
            kick_pattern = snare_pattern = hihat_pattern = "[]"
        
        # Calculate metrics
        total_notes = sum(drum_hits.values())
        density = total_notes / max(duration_bars * 4, 1)
        complexity = min(1.0, density / 8.0)
        
        # Infer style and section from path/filename
        path_str = file_path.lower()
        style = self._infer_style(path_str)
        section_type = self._infer_section(path_str)
        
        # Insert into database
        cursor = self.db.conn.cursor()
        cursor.execute('''
            INSERT OR REPLACE INTO drum_patterns (
                file_path, dataset_source, tempo_bpm, time_signature,
                duration_bars, duration_seconds, style, section_type,
                complexity, density, kick_count, snare_count, hihat_count,
                ride_count, tom_count, crash_count,
                kick_pattern, snare_pattern, hihat_pattern
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        ''', (
            file_path, source, tempo_bpm, time_sig,
            duration_bars, duration_seconds, style, section_type,
            complexity, density,
            drum_hits['kick'], drum_hits['snare'], drum_hits['hihat'],
            drum_hits['ride'], drum_hits['tom'], drum_hits['crash'],
            kick_pattern, snare_pattern, hihat_pattern
        ))
        
        self.db.conn.commit()
    
    def index_audio_sample(self, file_path: str, source: str):
        """Extract and index audio sample"""
        file_name = Path(file_path).name
        file_size = os.path.getsize(file_path)
        
        # Infer drum type from path/filename
        drum_type = self._infer_drum_type(file_path)
        variation = self._infer_variation(file_path)
        category = self._infer_category(file_path)
        
        # Get audio properties
        format = Path(file_path).suffix[1:].lower()
        sample_rate = 44100  # default
        bit_depth = 16
        duration_ms = 0
        
        if format == 'wav':
            try:
                with wave.open(file_path, 'rb') as wav:
                    sample_rate = wav.getframerate()
                    bit_depth = wav.getsampwidth() * 8
                    duration_ms = int((wav.getnframes() / sample_rate) * 1000)
            except:
                pass
        
        # Extract manufacturer and kit name from path
        path_parts = Path(file_path).parts
        manufacturer = self._extract_manufacturer(path_parts)
        kit_name = self._extract_kit_name(path_parts)
        
        # Insert into database
        cursor = self.db.conn.cursor()
        cursor.execute('''
            INSERT OR REPLACE INTO drum_samples (
                file_path, file_name, file_size, drum_type, variation,
                sample_rate, bit_depth, duration_ms, format,
                category, manufacturer, kit_name
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
        ''', (
            file_path, file_name, file_size, drum_type, variation,
            sample_rate, bit_depth, duration_ms, format,
            category, manufacturer, kit_name
        ))
        
        self.db.conn.commit()
    
    def _infer_style(self, path_str: str) -> str:
        """Infer musical style from path"""
        if 'rock' in path_str:
            return 'rock'
        elif 'jazz' in path_str:
            return 'jazz'
        elif 'funk' in path_str:
            return 'funk'
        elif 'latin' in path_str:
            return 'latin'
        elif 'edm' in path_str or 'electronic' in path_str:
            return 'edm'
        elif 'metal' in path_str:
            return 'metal'
        elif 'pop' in path_str:
            return 'pop'
        return 'unknown'
    
    def _infer_section(self, path_str: str) -> str:
        """Infer section type from path"""
        if 'fill' in path_str or 'rudiment' in path_str:
            return 'fill'
        elif 'verse' in path_str:
            return 'verse'
        elif 'chorus' in path_str:
            return 'chorus'
        elif 'intro' in path_str:
            return 'intro'
        elif 'outro' in path_str:
            return 'outro'
        return 'groove'
    
    def _infer_drum_type(self, path_str: str) -> str:
        """Infer drum type from path"""
        path_lower = path_str.lower()
        if 'kick' in path_lower or 'bass drum' in path_lower or 'bd' in path_lower:
            return 'kick'
        elif 'snare' in path_lower or 'sd' in path_lower:
            return 'snare'
        elif 'hihat' in path_lower or 'hh' in path_lower or 'hi-hat' in path_lower:
            return 'hihat'
        elif 'ride' in path_lower:
            return 'ride'
        elif 'crash' in path_lower:
            return 'crash'
        elif 'tom' in path_lower:
            return 'tom'
        elif 'cymbal' in path_lower:
            return 'cymbal'
        return 'unknown'
    
    def _infer_variation(self, path_str: str) -> str:
        """Infer sample variation"""
        path_lower = path_str.lower()
        if 'center' in path_lower:
            return 'center'
        elif 'edge' in path_lower:
            return 'edge'
        elif 'rim' in path_lower:
            return 'rim'
        elif 'open' in path_lower:
            return 'open'
        elif 'closed' in path_lower:
            return 'closed'
        return 'default'
    
    def _infer_category(self, path_str: str) -> str:
        """Infer sample category"""
        path_lower = path_str.lower()
        if 'acoustic' in path_lower:
            return 'acoustic'
        elif 'electronic' in path_lower or '808' in path_lower or '909' in path_lower:
            return 'electronic'
        elif 'processed' in path_lower:
            return 'processed'
        return 'acoustic'
    
    def _extract_manufacturer(self, path_parts: tuple) -> str:
        """Extract manufacturer from path"""
        manufacturers = [
            'Ludwig', 'DW', 'Pearl', 'Yamaha', 'Tama', 'Gretsch',
            'Roland', 'Alesis', 'Simmons', 'Superior Drummer', 'SD3',
            'Addictive Drums', 'BFD', 'EZ Drummer', 'Steven Slate'
        ]
        
        for part in path_parts:
            for mfr in manufacturers:
                if mfr.lower() in part.lower():
                    return mfr
        return 'Unknown'
    
    def _extract_kit_name(self, path_parts: tuple) -> str:
        """Extract kit name from path"""
        # Usually the folder name before the sample file
        if len(path_parts) >= 2:
            return path_parts[-2]
        return 'Unknown'
    
    def print_statistics(self):
        """Print scanning statistics"""
        print("\n" + "="*60)
        print("📊 SCAN STATISTICS")
        print("="*60)
        print(f"✓ Patterns indexed: {self.stats['patterns_found']}")
        print(f"✓ Samples indexed: {self.stats['samples_found']}")
        print(f"  MIDI files: {self.stats['midi_files']}")
        print(f"  Audio files: {self.stats['audio_files']}")
        if self.stats['errors'] > 0:
            print(f"⚠ Errors: {self.stats['errors']}")
        print("="*60)
        
        # Query database for totals
        cursor = self.db.conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM drum_patterns")
        total_patterns = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM drum_samples")
        total_samples = cursor.fetchone()[0]
        
        print(f"\n📦 DATABASE TOTALS:")
        print(f"  Total patterns in DB: {total_patterns}")
        print(f"  Total samples in DB: {total_samples}")


if __name__ == "__main__":
    import sys
    
    midi_only = '--midi-only' in sys.argv
    
    print("🎵 DrumTracKAI Ultimate Scanner v2.0")
    if midi_only:
        print("Mode: MIDI Patterns ONLY (fast mode)")
    else:
        print("Mode: Full scan (patterns + samples)")
    print("="*60)
    
    # Initialize database
    db = UnifiedDatabaseManager()
    
    # Scan
    scanner = UltimateScanner(db)
    
    if midi_only:
        # Only scan MIDI patterns
        print("\n📁 Scanning MIDI patterns from new location...")
        scanner.scan_pattern_folder(
            "E:/DrumTracKAI_Master/01_MIDI_Patterns/Datasets/E-GMD",
            "egmd"
        )
    else:
        # Full scan
        scanner.scan_all_e_drive()
    
    # Close database
    db.close()
    
    print("\n✅ Scanning complete!")
    if midi_only:
        print("✓ MIDI patterns indexed")
        print("\n🎯 Next: Audio samples can be scanned later")
    else:
        print("Database ready for AI training and admin interface")

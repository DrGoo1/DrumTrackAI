"""
Dataset Scanner for DrumTracKAI
Scans E-GMD, SoundTracksLoops, and Snare Rudiments datasets
Extracts features, patterns, and metadata for AI training
"""

import os
import json
import numpy as np
from pathlib import Path
from typing import Dict, List, Tuple
import mido
from dataclasses import dataclass, asdict
import sqlite3

@dataclass
class DrumPattern:
    """Represents a single drum pattern from dataset"""
    file_path: str
    dataset_source: str  # 'egmd', 'soundtracks', 'rudiments'
    
    # Timing info
    tempo_bpm: float
    time_signature: str
    duration_bars: int
    duration_seconds: float
    
    # Pattern characteristics
    style: str  # rock, jazz, funk, etc.
    complexity: float  # 0.0-1.0
    density: float  # notes per beat
    
    # Drum hit counts
    kick_count: int
    snare_count: int
    hihat_count: int
    ride_count: int
    tom_count: int
    crash_count: int
    
    # Pattern features (for ML)
    kick_pattern: List[float]  # Timing of kicks (normalized 0-1)
    snare_pattern: List[float]
    hihat_pattern: List[float]
    
    # Metadata
    drummer_name: str = ""
    genre: str = ""
    section_type: str = ""  # verse, chorus, fill, etc.
    
    def to_dict(self):
        return asdict(self)


class DatasetScanner:
    """Scans drum datasets and extracts patterns"""
    
    def __init__(self, db_path: str = "drum_patterns.db"):
        self.db_path = db_path
        self.init_database()
        
    def init_database(self):
        """Create SQLite database for pattern storage"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        c.execute('''CREATE TABLE IF NOT EXISTS patterns
                     (id INTEGER PRIMARY KEY,
                      file_path TEXT,
                      dataset_source TEXT,
                      tempo_bpm REAL,
                      time_signature TEXT,
                      duration_bars INTEGER,
                      duration_seconds REAL,
                      style TEXT,
                      complexity REAL,
                      density REAL,
                      kick_count INTEGER,
                      snare_count INTEGER,
                      hihat_count INTEGER,
                      ride_count INTEGER,
                      tom_count INTEGER,
                      crash_count INTEGER,
                      kick_pattern TEXT,
                      snare_pattern TEXT,
                      hihat_pattern TEXT,
                      drummer_name TEXT,
                      genre TEXT,
                      section_type TEXT)''')
        
        conn.commit()
        conn.close()
        print(f"✓ Database initialized: {self.db_path}")
    
    def scan_egmd(self, path: str = "E:/E-GMD Dataset"):
        """Scan E-GMD (Extended Groove MIDI Dataset)"""
        print(f"\n📁 Scanning E-GMD Dataset: {path}")
        
        if not os.path.exists(path):
            print(f"⚠ Path not found: {path}")
            return []
        
        patterns = []
        midi_files = list(Path(path).rglob("*.mid")) + list(Path(path).rglob("*.midi"))
        
        print(f"Found {len(midi_files)} MIDI files")
        
        for idx, midi_file in enumerate(midi_files):
            if idx % 100 == 0:
                print(f"  Processing {idx}/{len(midi_files)}...")
            
            try:
                pattern = self.extract_pattern_from_midi(
                    str(midi_file), 
                    dataset_source="egmd"
                )
                if pattern:
                    patterns.append(pattern)
                    self.save_pattern(pattern)
            except Exception as e:
                print(f"  ✗ Error processing {midi_file.name}: {e}")
        
        print(f"✓ Extracted {len(patterns)} patterns from E-GMD")
        return patterns
    
    def scan_soundtracks(self, path: str = "E:/SoundTracksLoops Dataset"):
        """Scan SoundTracksLoops Dataset"""
        print(f"\n📁 Scanning SoundTracksLoops: {path}")
        
        if not os.path.exists(path):
            print(f"⚠ Path not found: {path}")
            return []
        
        patterns = []
        # Scan for audio files (WAV, MP3) and MIDI
        audio_files = (list(Path(path).rglob("*.wav")) + 
                      list(Path(path).rglob("*.mp3")) +
                      list(Path(path).rglob("*.mid")))
        
        print(f"Found {len(audio_files)} files")
        
        for idx, file in enumerate(audio_files):
            if idx % 100 == 0:
                print(f"  Processing {idx}/{len(audio_files)}...")
            
            try:
                if file.suffix.lower() in ['.mid', '.midi']:
                    pattern = self.extract_pattern_from_midi(
                        str(file),
                        dataset_source="soundtracks"
                    )
                else:
                    pattern = self.extract_pattern_from_audio(
                        str(file),
                        dataset_source="soundtracks"
                    )
                
                if pattern:
                    patterns.append(pattern)
                    self.save_pattern(pattern)
            except Exception as e:
                print(f"  ✗ Error: {e}")
        
        print(f"✓ Extracted {len(patterns)} patterns from SoundTracksLoops")
        return patterns
    
    def scan_rudiments(self, path: str = "E:/Snare Rudiments"):
        """Scan Snare Rudiments"""
        print(f"\n📁 Scanning Snare Rudiments: {path}")
        
        if not os.path.exists(path):
            print(f"⚠ Path not found: {path}")
            return []
        
        patterns = []
        files = list(Path(path).rglob("*.mid")) + list(Path(path).rglob("*.wav"))
        
        print(f"Found {len(files)} rudiment files")
        
        for file in files:
            try:
                if file.suffix.lower() in ['.mid', '.midi']:
                    pattern = self.extract_pattern_from_midi(
                        str(file),
                        dataset_source="rudiments"
                    )
                    if pattern:
                        pattern.section_type = "fill"  # Rudiments are fills
                        patterns.append(pattern)
                        self.save_pattern(pattern)
            except Exception as e:
                print(f"  ✗ Error: {e}")
        
        print(f"✓ Extracted {len(patterns)} rudiment patterns")
        return patterns
    
    def extract_pattern_from_midi(self, file_path: str, dataset_source: str) -> DrumPattern:
        """Extract pattern features from MIDI file"""
        mid = mido.MidiFile(file_path)
        
        # Get tempo and time signature
        tempo_bpm = 120.0  # default
        time_sig = "4/4"
        
        for track in mid.tracks:
            for msg in track:
                if msg.type == 'set_tempo':
                    tempo_bpm = mido.tempo2bpm(msg.tempo)
                elif msg.type == 'time_signature':
                    time_sig = f"{msg.numerator}/{msg.denominator}"
                if tempo_bpm != 120.0 and time_sig != "4/4":
                    break
        
        # Count drum hits by type (GM mapping)
        kick_count = snare_count = hihat_count = 0
        ride_count = tom_count = crash_count = 0
        
        kick_times = []
        snare_times = []
        hihat_times = []
        
        time = 0.0
        for track in mid.tracks:
            for msg in track:
                time += msg.time
                if msg.type == 'note_on' and msg.velocity > 0:
                    # GM drum mapping
                    if msg.note == 36:  # Kick
                        kick_count += 1
                        kick_times.append(time)
                    elif msg.note == 38:  # Snare
                        snare_count += 1
                        snare_times.append(time)
                    elif msg.note in [42, 44, 46]:  # Hi-hats
                        hihat_count += 1
                        hihat_times.append(time)
                    elif msg.note == 51:  # Ride
                        ride_count += 1
                    elif msg.note in [41, 43, 45, 47, 48, 50]:  # Toms
                        tom_count += 1
                    elif msg.note in [49, 55, 57]:  # Crashes
                        crash_count += 1
        
        duration_seconds = mid.length
        duration_bars = int((duration_seconds / 60.0) * tempo_bpm / 4.0)
        
        # Normalize timing patterns to 0-1
        if duration_seconds > 0:
            kick_pattern = [t / duration_seconds for t in kick_times[:32]]  # Max 32
            snare_pattern = [t / duration_seconds for t in snare_times[:32]]
            hihat_pattern = [t / duration_seconds for t in hihat_times[:32]]
        else:
            kick_pattern = snare_pattern = hihat_pattern = []
        
        # Calculate density and complexity
        total_notes = kick_count + snare_count + hihat_count + ride_count + tom_count + crash_count
        density = total_notes / max(duration_bars * 4, 1)  # Notes per beat
        complexity = min(1.0, density / 8.0)  # Normalize to 0-1
        
        # Extract style/genre from path
        path_parts = Path(file_path).parts
        style = self._infer_style(path_parts)
        genre = self._infer_genre(path_parts)
        
        return DrumPattern(
            file_path=file_path,
            dataset_source=dataset_source,
            tempo_bpm=tempo_bpm,
            time_signature=time_sig,
            duration_bars=duration_bars,
            duration_seconds=duration_seconds,
            style=style,
            complexity=complexity,
            density=density,
            kick_count=kick_count,
            snare_count=snare_count,
            hihat_count=hihat_count,
            ride_count=ride_count,
            tom_count=tom_count,
            crash_count=crash_count,
            kick_pattern=kick_pattern,
            snare_pattern=snare_pattern,
            hihat_pattern=hihat_pattern,
            genre=genre
        )
    
    def extract_pattern_from_audio(self, file_path: str, dataset_source: str) -> DrumPattern:
        """Extract pattern from audio using onset detection"""
        # TODO: Use librosa or Rust audio-core for onset detection
        # For now, return None - we'll use MIDI primarily
        return None
    
    def _infer_style(self, path_parts: tuple) -> str:
        """Infer style from file path"""
        path_str = " ".join(path_parts).lower()
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
        return 'unknown'
    
    def _infer_genre(self, path_parts: tuple) -> str:
        """Infer genre from file path"""
        return self._infer_style(path_parts)  # Same for now
    
    def save_pattern(self, pattern: DrumPattern):
        """Save pattern to database"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        c.execute('''INSERT INTO patterns VALUES (NULL,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)''',
                  (pattern.file_path, pattern.dataset_source, pattern.tempo_bpm,
                   pattern.time_signature, pattern.duration_bars, pattern.duration_seconds,
                   pattern.style, pattern.complexity, pattern.density,
                   pattern.kick_count, pattern.snare_count, pattern.hihat_count,
                   pattern.ride_count, pattern.tom_count, pattern.crash_count,
                   json.dumps(pattern.kick_pattern),
                   json.dumps(pattern.snare_pattern),
                   json.dumps(pattern.hihat_pattern),
                   pattern.drummer_name, pattern.genre, pattern.section_type))
        
        conn.commit()
        conn.close()
    
    def get_statistics(self):
        """Print dataset statistics"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        print("\n📊 Dataset Statistics:")
        print("=" * 60)
        
        # Total patterns
        c.execute("SELECT COUNT(*) FROM patterns")
        total = c.fetchone()[0]
        print(f"Total patterns: {total}")
        
        # By dataset
        c.execute("SELECT dataset_source, COUNT(*) FROM patterns GROUP BY dataset_source")
        for source, count in c.fetchall():
            print(f"  {source}: {count}")
        
        # By style
        c.execute("SELECT style, COUNT(*) FROM patterns GROUP BY style")
        print("\nBy style:")
        for style, count in c.fetchall():
            print(f"  {style}: {count}")
        
        # Tempo range
        c.execute("SELECT MIN(tempo_bpm), MAX(tempo_bpm), AVG(tempo_bpm) FROM patterns")
        min_t, max_t, avg_t = c.fetchone()
        print(f"\nTempo range: {min_t:.0f} - {max_t:.0f} BPM (avg: {avg_t:.0f})")
        
        # Complexity
        c.execute("SELECT AVG(complexity), AVG(density) FROM patterns")
        avg_comp, avg_dens = c.fetchone()
        print(f"Avg complexity: {avg_comp:.2f}")
        print(f"Avg density: {avg_dens:.2f} notes/beat")
        
        conn.close()


if __name__ == "__main__":
    scanner = DatasetScanner("f:/DrumTracKAI_v1.1.16_Clean/drum_patterns.db")
    
    print("🎵 DrumTracKAI Dataset Scanner")
    print("=" * 60)
    
    # Scan all datasets
    scanner.scan_egmd()
    scanner.scan_soundtracks()
    scanner.scan_rudiments()
    
    # Show statistics
    scanner.get_statistics()
    
    print("\n✓ Scanning complete!")
    print("  Database: drum_patterns.db")
    print("  Next step: Train AI model on extracted patterns")

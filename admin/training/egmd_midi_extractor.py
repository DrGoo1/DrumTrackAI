"""
E-GMD MIDI Feature Extractor
============================
Extracts drum pattern features from E-GMD MIDI dataset for training
"""
import logging
import sqlite3
import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import time
from collections import defaultdict

logger = logging.getLogger(__name__)

try:
    import mido
    MIDO_AVAILABLE = True
except ImportError:
    MIDO_AVAILABLE = False
    logger.warning("mido not available - install with: pip install mido")

# General MIDI Drum Map
GM_DRUM_MAP = {
    35: 'kick',      # Acoustic Bass Drum
    36: 'kick',      # Bass Drum 1
    38: 'snare',     # Acoustic Snare
    40: 'snare',     # Electric Snare
    37: 'snare',     # Side Stick
    42: 'hihat_closed',  # Closed Hi-Hat
    44: 'hihat_pedal',   # Pedal Hi-Hat
    46: 'hihat_open',    # Open Hi-Hat
    41: 'tom_low',       # Low Floor Tom
    43: 'tom_low',       # High Floor Tom
    45: 'tom_mid',       # Low Tom
    47: 'tom_mid',       # Low-Mid Tom
    48: 'tom_high',      # Hi-Mid Tom
    50: 'tom_high',      # High Tom
    49: 'crash',         # Crash Cymbal 1
    57: 'crash',         # Crash Cymbal 2
    51: 'ride',          # Ride Cymbal 1
    59: 'ride',          # Ride Cymbal 2
    53: 'ride',          # Ride Bell
    55: 'crash',         # Splash Cymbal
    52: 'crash',         # Chinese Cymbal
}

@dataclass
class DrumHit:
    """Single drum hit event"""
    time: float  # In seconds
    note: int    # MIDI note number
    velocity: int  # 0-127
    drum_type: str  # mapped drum type

@dataclass
class MIDIFeatures:
    """Extracted features from MIDI file"""
    source_file: str
    total_hits: int
    duration: float  # seconds
    tempo: float  # BPM
    time_signature: str  # e.g. "4/4", "3/4", "7/8"
    drum_counts: Dict[str, int]  # hits per drum type
    velocity_stats: Dict[str, Dict]  # mean, min, max, std per drum
    timing_features: Dict  # swing, groove, etc.
    pattern_density: float  # hits per second
    ghost_notes: int  # velocity < 30
    accents: int  # velocity > 100
    sequential_patterns: Dict  # drum transition probabilities
    hihat_articulations: Dict  # open/closed patterns
    fill_segments: List[Dict]  # detected fills
    velocity_curve: List[float]  # dynamics over time
    swing_amount: float  # detected swing percentage
    style_hints: List[str]  # inferred style characteristics

class EGMDMIDIExtractor:
    """Extract features from E-GMD MIDI files"""
    
    def __init__(self, db_path: str = None):
        if db_path is None:
            module_dir = Path(__file__).parent.parent
            db_path = module_dir / "data" / "drum_training.db"
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_database()
        logger.info(f"E-GMD MIDI Extractor initialized: {self.db_path}")
    
    def _init_database(self):
        """Initialize database schema"""
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        
        # Create table for MIDI features
        cur.execute('''
            CREATE TABLE IF NOT EXISTS egmd_midi_features (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_file TEXT UNIQUE NOT NULL,
                dataset TEXT DEFAULT 'E-GMD',
                total_hits INTEGER,
                duration REAL,
                tempo REAL,
                time_signature TEXT,
                drum_counts_json TEXT,
                velocity_stats_json TEXT,
                timing_features_json TEXT,
                pattern_density REAL,
                ghost_notes INTEGER,
                accents INTEGER,
                sequential_patterns_json TEXT,
                hihat_articulations_json TEXT,
                fill_segments_json TEXT,
                velocity_curve_json TEXT,
                swing_amount REAL,
                style_hints_json TEXT,
                extracted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.commit()
        conn.close()
        logger.info("Database schema initialized")
    
    def extract_from_file(self, midi_path: Path) -> Optional[MIDIFeatures]:
        """Extract features from a single MIDI file"""
        if not MIDO_AVAILABLE:
            logger.error("mido not available")
            return None
        
        try:
            midi = mido.MidiFile(midi_path)
            
            # Extract drum hits
            hits = []
            tempo_us = 500000  # Default 120 BPM in microseconds per beat
            tempo_bpm = float(mido.tempo2bpm(tempo_us))
            
            # Process all tracks
            for track in midi.tracks:
                track_time = 0.0
                for msg in track:
                    track_time += mido.tick2second(msg.time, midi.ticks_per_beat, tempo_us)
                    
                    if msg.type == 'set_tempo':
                        tempo_us = int(msg.tempo)
                        tempo_bpm = float(mido.tempo2bpm(tempo_us))
                    
                    elif msg.type == 'note_on' and msg.velocity > 0:
                        # Check if it's a drum note (channel 10 in MIDI = channel 9 in 0-indexed)
                        if msg.channel == 9:  # Drum channel
                            drum_type = GM_DRUM_MAP.get(msg.note, 'unknown')
                            hits.append(DrumHit(
                                time=track_time,
                                note=msg.note,
                                velocity=msg.velocity,
                                drum_type=drum_type
                            ))
            
            if not hits:
                logger.debug(f"No drum hits found in {midi_path.name}")
                return None
            
            # Calculate features
            duration = max(hit.time for hit in hits) if hits else 0
            
            # Count hits per drum type
            drum_counts = defaultdict(int)
            for hit in hits:
                drum_counts[hit.drum_type] += 1
            
            # Velocity statistics per drum type
            velocity_stats = {}
            drum_velocities = defaultdict(list)
            for hit in hits:
                drum_velocities[hit.drum_type].append(hit.velocity)
            
            for drum, velocities in drum_velocities.items():
                if velocities:
                    velocity_stats[drum] = {
                        'mean': sum(velocities) / len(velocities),
                        'min': min(velocities),
                        'max': max(velocities),
                        'std': (sum((v - sum(velocities)/len(velocities))**2 for v in velocities) / len(velocities))**0.5
                    }
            
            # Time signature detection (look for time_signature event)
            time_signature = "4/4"  # Default
            for track in midi.tracks:
                for msg in track:
                    if msg.type == 'time_signature':
                        time_signature = f"{msg.numerator}/{msg.denominator}"
                        break
            
            # Ghost notes and accents
            ghost_notes = sum(1 for hit in hits if hit.velocity < 30)
            accents = sum(1 for hit in hits if hit.velocity > 100)
            
            # Sequential patterns (what drum follows what)
            sequential_patterns = self._extract_sequential_patterns(hits)
            
            # Hi-hat articulations
            hihat_articulations = self._extract_hihat_articulations(hits)
            
            # Fill detection
            fill_segments = self._detect_fills(hits)
            
            # Velocity curve (dynamics over time)
            velocity_curve = self._extract_velocity_curve(hits, duration)
            
            # Timing features with swing detection
            if len(hits) > 1:
                intervals = [hits[i+1].time - hits[i].time for i in range(len(hits)-1)]
                avg_interval = sum(intervals) / len(intervals) if intervals else 0
                swing_amount = self._detect_swing(hits)
            else:
                avg_interval = 0
                swing_amount = 0
            
            timing_features = {
                'avg_interval': avg_interval,
                'total_hits': len(hits),
                'duration': duration,
                'swing_detected': swing_amount > 0.1
            }
            
            # Pattern density
            pattern_density = len(hits) / duration if duration > 0 else 0
            
            # Infer style hints based on patterns
            style_hints = self._infer_style_hints(hits, drum_counts, velocity_stats, ghost_notes, accents)
            
            return MIDIFeatures(
                source_file=str(midi_path),
                total_hits=len(hits),
                duration=duration,
                tempo=tempo_bpm,
                time_signature=time_signature,
                drum_counts=dict(drum_counts),
                velocity_stats=velocity_stats,
                timing_features=timing_features,
                pattern_density=pattern_density,
                ghost_notes=ghost_notes,
                accents=accents,
                sequential_patterns=sequential_patterns,
                hihat_articulations=hihat_articulations,
                fill_segments=fill_segments,
                velocity_curve=velocity_curve,
                swing_amount=swing_amount,
                style_hints=style_hints
            )
            
        except Exception as e:
            logger.error(f"Error extracting from {midi_path.name}: {e}")
            return None
    
    def _extract_sequential_patterns(self, hits: List[DrumHit]) -> Dict:
        """Extract drum transition probabilities"""
        transitions = defaultdict(lambda: defaultdict(int))
        
        for i in range(len(hits) - 1):
            from_drum = hits[i].drum_type
            to_drum = hits[i+1].drum_type
            transitions[from_drum][to_drum] += 1
        
        # Convert to probabilities
        patterns = {}
        for from_drum, to_drums in transitions.items():
            total = sum(to_drums.values())
            if total > 0:
                patterns[from_drum] = {k: v/total for k, v in to_drums.items()}
        
        return dict(patterns)
    
    def _extract_hihat_articulations(self, hits: List[DrumHit]) -> Dict:
        """Extract hi-hat open/closed patterns"""
        hihat_sequence = [h for h in hits if 'hihat' in h.drum_type]
        
        open_to_closed = 0
        closed_to_open = 0
        
        for i in range(len(hihat_sequence) - 1):
            current = hihat_sequence[i].drum_type
            next_hit = hihat_sequence[i+1].drum_type
            
            if current == 'hihat_open' and next_hit == 'hihat_closed':
                open_to_closed += 1
            elif current == 'hihat_closed' and next_hit == 'hihat_open':
                closed_to_open += 1
        
        return {
            'open_to_closed': open_to_closed,
            'closed_to_open': closed_to_open,
            'total_hihat_hits': len(hihat_sequence)
        }
    
    def _detect_fills(self, hits: List[DrumHit]) -> List[Dict]:
        """Detect drum fills (rapid tom patterns)"""
        fills = []
        window_size = 1.0  # 1 second window
        
        i = 0
        while i < len(hits):
            # Check for rapid hits
            window_hits = []
            start_time = hits[i].time
            j = i
            
            while j < len(hits) and hits[j].time < start_time + window_size:
                window_hits.append(hits[j])
                j += 1
            
            # Fill criteria: >8 hits in 1 second with tom presence
            if len(window_hits) > 8:
                tom_hits = sum(1 for h in window_hits if 'tom' in h.drum_type)
                if tom_hits > 0:
                    fills.append({
                        'start_time': start_time,
                        'duration': window_hits[-1].time - start_time if len(window_hits) > 1 else 0,
                        'hit_count': len(window_hits),
                        'tom_hits': tom_hits
                    })
                    i = j  # Skip past this fill
                    continue
            
            i += 1
        
        return fills
    
    def _extract_velocity_curve(self, hits: List[DrumHit], duration: float) -> List[float]:
        """Extract velocity changes over time"""
        if duration == 0 or not hits:
            return []
        
        # Divide into 10 segments
        num_segments = min(10, len(hits))
        segment_duration = duration / num_segments
        
        velocity_curve = []
        for i in range(num_segments):
            segment_start = i * segment_duration
            segment_end = (i + 1) * segment_duration
            
            segment_hits = [h for h in hits if segment_start <= h.time < segment_end]
            if segment_hits:
                avg_velocity = sum(h.velocity for h in segment_hits) / len(segment_hits)
                velocity_curve.append(avg_velocity)
            else:
                velocity_curve.append(0)
        
        return velocity_curve
    
    def _detect_swing(self, hits: List[DrumHit]) -> float:
        """Detect swing amount (ratio of long/short in triplet feel)"""
        if len(hits) < 8:
            return 0
        
        # Look for alternating long-short patterns in timing
        intervals = [hits[i+1].time - hits[i].time for i in range(len(hits)-1)]
        
        # Check pairs of intervals for swing ratio
        swing_ratios = []
        for i in range(0, len(intervals)-1, 2):
            if intervals[i] > 0 and intervals[i+1] > 0:
                ratio = intervals[i] / intervals[i+1]
                # Swing typically has ratio between 1.5 and 3.0
                if 1.5 <= ratio <= 3.0:
                    swing_ratios.append(ratio)
        
        if len(swing_ratios) > 3:
            avg_ratio = sum(swing_ratios) / len(swing_ratios)
            # Convert to swing percentage (0 = straight, 1 = full triplet swing)
            swing_amount = min(1.0, (avg_ratio - 1.0) / 2.0)
            return swing_amount
        
        return 0
    
    def _infer_style_hints(self, hits: List[DrumHit], drum_counts: Dict, velocity_stats: Dict, ghost_notes: int, accents: int) -> List[str]:
        """Infer playing style characteristics"""
        hints = []
        
        # High hi-hat density = potentially jazz or funk
        hihat_hits = drum_counts.get('hihat_closed', 0) + drum_counts.get('hihat_open', 0)
        total_hits = sum(drum_counts.values())
        
        if total_hits > 0:
            hihat_ratio = hihat_hits / total_hits
            if hihat_ratio > 0.5:
                hints.append('hihat_heavy')
            
            # Ride heavy = potentially jazz
            ride_hits = drum_counts.get('ride', 0)
            ride_ratio = ride_hits / total_hits
            if ride_ratio > 0.4:
                hints.append('ride_heavy')
            
            # Kick density
            kick_hits = drum_counts.get('kick', 0)
            kick_ratio = kick_hits / total_hits
            if kick_ratio > 0.3:
                hints.append('kick_heavy')
            
            # Ghost notes (funk characteristic)
            ghost_ratio = ghost_notes / total_hits
            if ghost_ratio > 0.15:
                hints.append('ghost_note_heavy')
            
            # Accents
            accent_ratio = accents / total_hits
            if accent_ratio > 0.2:
                hints.append('accent_heavy')
        
        # Velocity variation = dynamic playing
        if velocity_stats:
            avg_std = sum(stats.get('std', 0) for stats in velocity_stats.values()) / len(velocity_stats)
            if avg_std > 20:
                hints.append('high_dynamics')
            elif avg_std < 10:
                hints.append('low_dynamics')
        
        return hints
    
    def save_features(self, features: MIDIFeatures):
        """Save extracted features to database"""
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        
        try:
            cur.execute('''
                INSERT OR REPLACE INTO egmd_midi_features 
                (source_file, total_hits, duration, tempo, time_signature, drum_counts_json, 
                 velocity_stats_json, timing_features_json, pattern_density, ghost_notes,
                 accents, sequential_patterns_json, hihat_articulations_json, fill_segments_json,
                 velocity_curve_json, swing_amount, style_hints_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                features.source_file,
                features.total_hits,
                features.duration,
                features.tempo,
                features.time_signature,
                json.dumps(features.drum_counts),
                json.dumps(features.velocity_stats),
                json.dumps(features.timing_features),
                features.pattern_density,
                features.ghost_notes,
                features.accents,
                json.dumps(features.sequential_patterns),
                json.dumps(features.hihat_articulations),
                json.dumps(features.fill_segments),
                json.dumps(features.velocity_curve),
                features.swing_amount,
                json.dumps(features.style_hints)
            ))
            
            conn.commit()
        except Exception as e:
            logger.error(f"Error saving features: {e}")
        finally:
            conn.close()
    
    def batch_extract(self, egmd_path: Path, max_files: Optional[int] = None, 
                     progress_callback=None) -> Dict:
        """Extract features from multiple MIDI files"""
        if not MIDO_AVAILABLE:
            return {'error': 'mido not available'}
        
        # Find all MIDI files
        midi_files = list(egmd_path.rglob("*.midi")) + list(egmd_path.rglob("*.mid"))
        
        if max_files:
            midi_files = midi_files[:max_files]
        
        total_files = len(midi_files)
        logger.info(f"Found {total_files} MIDI files to process")
        
        results = {
            'total_files': total_files,
            'processed': 0,
            'successful': 0,
            'failed': 0,
            'skipped': 0,
            'start_time': time.time()
        }
        
        for i, midi_path in enumerate(midi_files):
            try:
                # Extract features
                features = self.extract_from_file(midi_path)
                
                if features:
                    self.save_features(features)
                    results['successful'] += 1
                else:
                    results['skipped'] += 1
                
                results['processed'] += 1
                
                # Progress callback
                if progress_callback and (i + 1) % 10 == 0:
                    progress_callback(i + 1, total_files, results)
                
            except Exception as e:
                logger.error(f"Error processing {midi_path.name}: {e}")
                results['failed'] += 1
                results['processed'] += 1
        
        results['elapsed_time'] = time.time() - results['start_time']
        results['files_per_second'] = results['processed'] / results['elapsed_time'] if results['elapsed_time'] > 0 else 0
        
        return results
    
    def get_extraction_stats(self) -> Dict:
        """Get statistics on extracted features"""
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        
        cur.execute("SELECT COUNT(*) FROM egmd_midi_features")
        total_extracted = cur.fetchone()[0]
        
        cur.execute("SELECT AVG(total_hits), AVG(duration), AVG(tempo) FROM egmd_midi_features")
        avg_hits, avg_duration, avg_tempo = cur.fetchone()
        
        cur.execute("SELECT style_hints_json FROM egmd_midi_features")
        all_hints = []
        for row in cur.fetchall():
            hints = json.loads(row[0])
            all_hints.extend(hints)
        
        hint_counts = defaultdict(int)
        for hint in all_hints:
            hint_counts[hint] += 1
        
        conn.close()
        
        return {
            'total_extracted': total_extracted,
            'avg_hits_per_file': avg_hits or 0,
            'avg_duration': avg_duration or 0,
            'avg_tempo': avg_tempo or 0,
            'style_distribution': dict(hint_counts)
        }


if __name__ == "__main__":
    # Quick test
    logging.basicConfig(level=logging.INFO)
    
    extractor = EGMDMIDIExtractor()
    print(f"✅ Extractor initialized")
    print(f"   Database: {extractor.db_path}")
    
    # Check stats
    stats = extractor.get_extraction_stats()
    print(f"\n📊 Current extraction stats:")
    print(f"   Total extracted: {stats['total_extracted']}")

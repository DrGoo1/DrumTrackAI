"""
Data Extraction Module for LLM Training
Extracts humanization features from:
1. Commercial songs (using existing Rust audio-core)
2. Superior Drummer samples
3. Live drum sensor data
4. YouTube drum performances (via youtube_downloader.py)
"""

import os
import json
import sqlite3
import numpy as np
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass, asdict
import logging

logger = logging.getLogger(__name__)

try:
    import librosa
    import soundfile as sf
    AUDIO_LIBS_AVAILABLE = True
except ImportError:
    logger.warning("librosa/soundfile not available - audio analysis limited")
    AUDIO_LIBS_AVAILABLE = False


@dataclass
class HumanizationFeatures:
    """Features that make drums sound human"""
    # Timing features
    timing_variance: float  # Std dev of timing deviations from grid
    timing_drift: float  # Systematic early/late tendency
    groove_consistency: float  # How consistent the groove feel is
    swing_factor: float  # Amount of swing/shuffle
    
    # Velocity features
    velocity_variance: float  # Dynamic range variation
    accent_pattern: List[float]  # Which beats get emphasized
    ghost_note_frequency: float  # How often ghost notes appear
    velocity_humanization: float  # Natural velocity micro-variations
    
    # Pattern features
    pattern_complexity: float  # How complex the pattern is
    fill_frequency: float  # How often fills appear
    transition_smoothness: float  # How smooth transitions are
    
    # Stylistic features
    hihat_variation: float  # Variation in hihat patterns
    kick_snare_relationship: float  # Relationship between kick and snare
    ride_vs_hihat_ratio: float  # When to use ride vs hihat
    
    # Context features
    section_awareness: float  # How patterns change between sections
    energy_curve: List[float]  # Energy progression through song
    
    # Metadata
    drummer_name: Optional[str] = None
    style: Optional[str] = None
    tempo: Optional[float] = None
    time_signature: Optional[Tuple[int, int]] = None


class SDSampleExtractor:
    """Extract features from Superior Drummer samples"""
    
    def __init__(self, sd_path: str = "H:/Superior_Drummer"):
        self.sd_path = Path(sd_path)
        self.db_path = Path("admin/data/drum_training.db")
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_database()
        logger.info(f"SD Sample Extractor initialized: {self.sd_path}")
    
    def _init_database(self):
        """Initialize SQLite database for training data"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Samples table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS sd_samples (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                path TEXT NOT NULL,
                drum_type TEXT,
                articulation TEXT,
                velocity_layer INTEGER,
                duration REAL,
                rms_energy REAL,
                spectral_centroid REAL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Features table for extracted features
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS humanization_features (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source TEXT NOT NULL,
                drummer_name TEXT,
                style TEXT,
                tempo REAL,
                features_json TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.commit()
        conn.close()
        logger.info("Database initialized")
    
    def extract_sample_features(self, sample_path: Path) -> Optional[Dict]:
        """Extract features from a single SD sample"""
        if not AUDIO_LIBS_AVAILABLE:
            logger.warning("Audio libraries not available")
            return None
        
        try:
            # Load audio
            y, sr = librosa.load(str(sample_path), sr=44100, mono=True)
            
            # Extract features
            features = {
                'path': str(sample_path),
                'drum_type': self._identify_drum_type(sample_path),
                'articulation': self._identify_articulation(sample_path),
                'duration': len(y) / sr,
                'rms_energy': float(np.sqrt(np.mean(y**2))),
                'spectral_centroid': float(np.mean(librosa.feature.spectral_centroid(y=y, sr=sr))),
            }
            
            return features
            
        except Exception as e:
            logger.error(f"Error extracting from {sample_path}: {e}")
            return None
    
    def _identify_drum_type(self, path: Path) -> str:
        """Identify drum type from filename"""
        name = path.stem.lower()
        if any(k in name for k in ['kick', 'bd', 'bassdrum']):
            return 'kick'
        elif any(s in name for s in ['snare', 'sd']):
            return 'snare'
        elif any(h in name for h in ['hihat', 'hh', 'hat']):
            return 'hihat'
        elif 'ride' in name:
            return 'ride'
        elif any(c in name for c in ['crash', 'splash']):
            return 'crash'
        elif any(t in name for t in ['tom', 'rack', 'floor']):
            return 'tom'
        else:
            return 'unknown'
    
    def _identify_articulation(self, path: Path) -> str:
        """Identify articulation from filename"""
        name = path.stem.lower()
        if 'rim' in name:
            return 'rim'
        elif 'center' in name or 'mid' in name:
            return 'center'
        elif 'edge' in name:
            return 'edge'
        elif 'ghost' in name:
            return 'ghost'
        elif 'accent' in name or 'hard' in name:
            return 'accent'
        else:
            return 'normal'
    
    def batch_extract(self, limit: int = None) -> int:
        """Extract features from all SD samples"""
        sample_dirs = self._find_sample_directories()
        if not sample_dirs:
            logger.error("No SD sample directories found")
            return 0
        
        count = 0
        for sample_dir in sample_dirs:
            audio_files = list(sample_dir.rglob('*.wav'))
            if limit and count >= limit:
                break
            
            for audio_file in audio_files[:limit] if limit else audio_files:
                features = self.extract_sample_features(audio_file)
                if features:
                    self._save_sample_features(features)
                    count += 1
                    if count % 100 == 0:
                        logger.info(f"Extracted {count} samples...")
        
        logger.info(f"Batch extraction complete: {count} samples")
        return count
    
    def _find_sample_directories(self) -> List[Path]:
        """Find SD sample directories"""
        locations = [
            self.sd_path / "Samples",
            self.sd_path / "Data" / "Samples",
            self.sd_path / "Libraries",
            self.sd_path / "Content",
        ]
        found = [loc for loc in locations if loc.exists()]
        
        # Search for SDX libraries
        if self.sd_path.exists():
            for item in self.sd_path.iterdir():
                if item.is_dir() and "SDX" in item.name:
                    sdx_samples = item / "Contents"
                    if sdx_samples.exists():
                        found.append(sdx_samples)
        
        return found
    
    def _save_sample_features(self, features: Dict):
        """Save sample features to database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO sd_samples (path, drum_type, articulation, duration, rms_energy, spectral_centroid)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            features['path'],
            features['drum_type'],
            features['articulation'],
            features['duration'],
            features['rms_energy'],
            features['spectral_centroid']
        ))
        
        conn.commit()
        conn.close()


class CommercialSongAnalyzer:
    """Analyze commercial songs to extract humanization patterns"""
    
    def __init__(self, rust_audio_core_path: str = "audio-core/target/release/audio-core.exe"):
        self.rust_audio_core = Path(rust_audio_core_path)
        self.db_path = Path("admin/data/drum_training.db")
        logger.info("Commercial Song Analyzer initialized")
    
    def analyze_song(self, audio_path: Path, drummer_name: str = None, style: str = None) -> Optional[HumanizationFeatures]:
        """
        Analyze a commercial song to extract humanization features
        Uses existing Rust audio-core for analysis
        """
        try:
            # Use Rust audio-core for analysis
            import subprocess
            import json
            
            result = subprocess.run(
                [str(self.rust_audio_core), 'analyze', str(audio_path)],
                capture_output=True,
                text=True,
                timeout=300
            )
            
            if result.returncode != 0:
                logger.error(f"Rust analysis failed: {result.stderr}")
                return None
            
            analysis_data = json.loads(result.stdout)
            
            # Extract humanization features from analysis
            features = self._extract_humanization_from_analysis(analysis_data, drummer_name, style)
            
            # Save to database
            self._save_features(features, source=str(audio_path))
            
            return features
            
        except Exception as e:
            logger.error(f"Error analyzing song {audio_path}: {e}")
            return None
    
    def _extract_humanization_from_analysis(self, analysis_data: Dict, drummer: str, style: str) -> HumanizationFeatures:
        """Extract humanization features from Rust analysis data"""
        
        # Calculate timing variance from onset times
        onsets = np.array(analysis_data.get('onsets', []))
        timing_variance = 0.0
        timing_drift = 0.0
        
        if len(onsets) > 1:
            # Calculate inter-onset intervals
            intervals = np.diff(onsets)
            timing_variance = float(np.std(intervals))
            
            # Calculate drift (systematic early/late tendency)
            expected_interval = 60.0 / analysis_data.get('tempo', 120.0)
            timing_drift = float(np.mean(intervals - expected_interval))
        
        # Extract tempo and beats
        tempo = analysis_data.get('tempo', 120.0)
        beats = analysis_data.get('beats', [])
        
        # Calculate groove consistency from beat regularity
        groove_consistency = 0.8 if len(beats) > 4 else 0.5
        
        return HumanizationFeatures(
            timing_variance=timing_variance,
            timing_drift=timing_drift,
            groove_consistency=groove_consistency,
            swing_factor=0.0,  # TODO: Calculate from analysis
            velocity_variance=0.15,  # Default human-like variance
            accent_pattern=[1.0, 0.7, 0.9, 0.7] * 4,  # Default 4/4 pattern
            ghost_note_frequency=0.15,
            velocity_humanization=0.12,
            pattern_complexity=0.7,
            fill_frequency=0.25,
            transition_smoothness=0.85,
            hihat_variation=0.3,
            kick_snare_relationship=0.75,
            ride_vs_hihat_ratio=0.2,
            section_awareness=0.8,
            energy_curve=[0.6, 0.7, 0.9, 0.85, 0.7],
            drummer_name=drummer,
            style=style,
            tempo=tempo,
            time_signature=(4, 4)
        )
    
    def _save_features(self, features: HumanizationFeatures, source: str):
        """Save extracted features to database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO humanization_features (source, drummer_name, style, tempo, features_json)
            VALUES (?, ?, ?, ?, ?)
        ''', (
            source,
            features.drummer_name,
            features.style,
            features.tempo,
            json.dumps(asdict(features))
        ))
        
        conn.commit()
        conn.close()
        logger.info(f"Saved features from {source}")
    
    def batch_analyze(self, audio_dir: Path, metadata_file: Path = None) -> int:
        """Batch analyze multiple songs"""
        count = 0
        audio_files = list(audio_dir.glob('*.wav')) + list(audio_dir.glob('*.mp3'))
        
        # Load metadata if provided
        metadata = {}
        if metadata_file and metadata_file.exists():
            with open(metadata_file) as f:
                metadata = json.load(f)
        
        for audio_file in audio_files:
            file_meta = metadata.get(audio_file.stem, {})
            drummer = file_meta.get('drummer')
            style = file_meta.get('style')
            
            features = self.analyze_song(audio_file, drummer, style)
            if features:
                count += 1
                logger.info(f"Analyzed {count}/{len(audio_files)}: {audio_file.name}")
        
        return count


class SensorDataCollector:
    """
    Collect real-time data from drum sensors
    Captures timing, velocity, and articulation from live performance
    """
    
    def __init__(self, sensor_port: str = "COM3", baud_rate: int = 115200):
        self.sensor_port = sensor_port
        self.baud_rate = baud_rate
        self.recording = False
        self.buffer = []
        self.db_path = Path("admin/data/drum_training.db")
        logger.info(f"Sensor Data Collector initialized on {sensor_port}")
    
    def start_recording(self):
        """Start recording sensor data"""
        self.recording = True
        self.buffer = []
        logger.info("Started sensor recording")
    
    def stop_recording(self) -> List[Dict]:
        """Stop recording and return captured data"""
        self.recording = False
        data = self.buffer.copy()
        self.buffer = []
        logger.info(f"Stopped sensor recording: {len(data)} events")
        return data
    
    def process_sensor_event(self, event: Dict):
        """Process a sensor event (called by sensor interface)"""
        if self.recording:
            self.buffer.append({
                'timestamp': event.get('timestamp'),
                'drum': event.get('drum'),  # kick, snare, hihat, etc.
                'velocity': event.get('velocity'),
                'articulation': event.get('articulation'),  # center, rim, edge
                'position': event.get('position')  # X/Y position on drum head
            })
    
    def extract_features_from_recording(self, events: List[Dict], drummer_name: str) -> HumanizationFeatures:
        """Extract humanization features from recorded sensor data"""
        
        if not events:
            logger.warning("No events to extract features from")
            return None
        
        # Convert to numpy arrays for analysis
        timestamps = np.array([e['timestamp'] for e in events])
        velocities = np.array([e['velocity'] for e in events])
        
        # Calculate timing features
        intervals = np.diff(timestamps)
        timing_variance = float(np.std(intervals)) if len(intervals) > 0 else 0.0
        timing_drift = float(np.mean(intervals - np.median(intervals))) if len(intervals) > 0 else 0.0
        
        # Calculate velocity features
        velocity_variance = float(np.std(velocities)) if len(velocities) > 0 else 0.0
        
        # Count ghost notes (low velocity hits)
        ghost_notes = np.sum(velocities < 40)
        ghost_note_frequency = float(ghost_notes / len(velocities)) if len(velocities) > 0 else 0.0
        
        features = HumanizationFeatures(
            timing_variance=timing_variance,
            timing_drift=timing_drift,
            groove_consistency=0.85,  # TODO: Calculate from pattern regularity
            swing_factor=0.0,  # TODO: Detect swing from timing
            velocity_variance=velocity_variance,
            accent_pattern=self._extract_accent_pattern(velocities),
            ghost_note_frequency=ghost_note_frequency,
            velocity_humanization=velocity_variance / 127.0,
            pattern_complexity=0.7,
            fill_frequency=0.2,
            transition_smoothness=0.8,
            hihat_variation=0.3,
            kick_snare_relationship=0.75,
            ride_vs_hihat_ratio=0.2,
            section_awareness=0.7,
            energy_curve=[0.7, 0.8, 0.9, 0.85, 0.7],
            drummer_name=drummer_name,
            style="live_recording",
            tempo=self._estimate_tempo_from_events(events),
            time_signature=(4, 4)
        )
        
        # Save to database
        self._save_sensor_features(features, events)
        
        return features
    
    def _extract_accent_pattern(self, velocities: np.ndarray) -> List[float]:
        """Extract accent pattern from velocity data"""
        # Normalize velocities to 0-1 range
        if len(velocities) == 0:
            return [1.0, 0.7, 0.9, 0.7]
        
        normalized = velocities / 127.0
        # Group into measures (assume 4/4 for now)
        beats_per_measure = 16  # 16th notes
        num_measures = len(normalized) // beats_per_measure
        
        if num_measures == 0:
            return list(normalized[:4]) if len(normalized) >= 4 else [1.0, 0.7, 0.9, 0.7]
        
        # Average accent pattern across measures
        measures = normalized[:num_measures * beats_per_measure].reshape(-1, beats_per_measure)
        avg_pattern = np.mean(measures, axis=0)
        
        return list(avg_pattern)
    
    def _estimate_tempo_from_events(self, events: List[Dict]) -> float:
        """Estimate tempo from sensor events"""
        if len(events) < 4:
            return 120.0
        
        timestamps = np.array([e['timestamp'] for e in events])
        intervals = np.diff(timestamps)
        median_interval = np.median(intervals)
        
        # Assume intervals are 16th notes for now
        beats_per_minute = 60.0 / (median_interval * 4)
        return float(np.clip(beats_per_minute, 60, 200))
    
    def _save_sensor_features(self, features: HumanizationFeatures, events: List[Dict]):
        """Save sensor-captured features to database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        source = f"sensor_recording_{len(events)}_events"
        
        cursor.execute('''
            INSERT INTO humanization_features (source, drummer_name, style, tempo, features_json)
            VALUES (?, ?, ?, ?, ?)
        ''', (
            source,
            features.drummer_name,
            features.style,
            features.tempo,
            json.dumps(asdict(features))
        ))
        
        conn.commit()
        conn.close()
        logger.info(f"Saved sensor features: {source}")


def test_extraction():
    """Test the extraction modules"""
    print("🧪 Testing Data Extraction Modules")
    print("=" * 60)
    
    # Test SD Sample Extractor
    print("\n1. SD Sample Extractor")
    sd_extractor = SDSampleExtractor()
    print(f"   Database: {sd_extractor.db_path}")
    
    # Test Commercial Song Analyzer
    print("\n2. Commercial Song Analyzer")
    song_analyzer = CommercialSongAnalyzer()
    print(f"   Rust audio-core: {song_analyzer.rust_audio_core}")
    
    # Test Sensor Data Collector
    print("\n3. Sensor Data Collector")
    sensor_collector = SensorDataCollector()
    print(f"   Port: {sensor_collector.sensor_port}")
    
    print("\n✅ All extraction modules initialized")


if __name__ == "__main__":
    test_extraction()

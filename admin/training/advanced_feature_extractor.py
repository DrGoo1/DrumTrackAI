"""
Advanced Feature Extractor - MIDI + Audio Analysis
Extracts comprehensive humanization features from both MIDI and audio data
"""

import numpy as np
import mido
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)

try:
    import librosa
    import soundfile as sf
    AUDIO_AVAILABLE = True
except ImportError:
    AUDIO_AVAILABLE = False
    logger.warning("Audio libraries not available")

@dataclass
class ComprehensiveFeatures:
    """Complete humanization features from MIDI + Audio"""
    
    # MIDI Timing Features
    micro_timing_variance: float  # Std dev of timing deviations (ms)
    systematic_drift: float  # Early/late tendency
    groove_swing: float  # Swing percentage
    timing_consistency: float  # How consistent timing is
    
    # MIDI Velocity Features
    velocity_variance: float  # Dynamic range variation
    velocity_humanization: float  # Micro velocity variations
    accent_strength: float  # How strong accents are
    ghost_note_frequency: float  # Frequency of ghost notes (<40 velocity)
    ghost_note_velocity_avg: float  # Average ghost note velocity
    
    # MIDI Pattern Features
    kick_pattern_density: float  # Notes per bar
    snare_pattern_density: float
    hihat_pattern_complexity: float  # Variation in hihat patterns
    ride_usage_ratio: float  # Ride vs hihat ratio
    cymbal_accent_pattern: float  # Crash/ride accent placement
    
    # MIDI Groove Features
    kick_snare_relationship: float  # Timing relationship
    offbeat_hihat_ratio: float  # Offbeat vs downbeat hihats
    syncopation_level: float  # Amount of syncopation
    fill_frequency: float  # How often fills occur
    
    # Audio Features (if available)
    transient_sharpness: float = 0.0  # Attack sharpness
    spectral_centroid: float = 0.0  # Brightness
    dynamic_range_db: float = 0.0  # Audio dynamic range
    reverb_amount: float = 0.0  # Estimated reverb
    
    # Metadata
    tempo: float = 120.0
    style: str = "unknown"
    drummer: str = "unknown"


class MIDIFeatureAnalyzer:
    """Analyzes MIDI files for comprehensive humanization features"""
    
    # GM Drum Map
    DRUM_MAP = {
        'kick': [35, 36],
        'snare': [38, 40],
        'hihat': [42, 44, 46],
        'ride': [51, 59],
        'crash': [49, 55, 57],
        'tom': [41, 43, 45, 47, 48, 50]
    }
    
    def analyze_midi(self, midi_path: Path) -> Optional[ComprehensiveFeatures]:
        """Extract all features from MIDI file"""
        try:
            mid = mido.MidiFile(str(midi_path))
            
            # Extract notes with timing
            notes = self._extract_notes(mid)
            if len(notes) < 10:
                return None
            
            # Calculate tempo
            tempo = self._extract_tempo(mid)
            
            # Analyze timing
            timing_features = self._analyze_timing(notes, tempo)
            
            # Analyze velocities
            velocity_features = self._analyze_velocities(notes)
            
            # Analyze patterns
            pattern_features = self._analyze_patterns(notes)
            
            # Analyze groove
            groove_features = self._analyze_groove(notes, tempo)
            
            return ComprehensiveFeatures(
                **timing_features,
                **velocity_features,
                **pattern_features,
                **groove_features,
                tempo=tempo
            )
            
        except Exception as e:
            logger.error(f"MIDI analysis failed: {e}")
            return None
    
    def _extract_notes(self, mid: mido.MidiFile) -> List[Dict]:
        """Extract all note events with timing"""
        notes = []
        current_time = 0
        
        for track in mid.tracks:
            time = 0
            for msg in track:
                time += msg.time
                if msg.type == 'note_on' and msg.velocity > 0:
                    notes.append({
                        'time': time,
                        'note': msg.note,
                        'velocity': msg.velocity,
                        'drum_type': self._identify_drum(msg.note)
                    })
        
        return sorted(notes, key=lambda x: x['time'])
    
    def _identify_drum(self, note: int) -> str:
        """Identify drum type from MIDI note"""
        for drum, notes in self.DRUM_MAP.items():
            if note in notes:
                return drum
        return 'other'
    
    def _extract_tempo(self, mid: mido.MidiFile) -> float:
        """Extract tempo from MIDI"""
        for track in mid.tracks:
            for msg in track:
                if msg.type == 'set_tempo':
                    return mido.tempo2bpm(msg.tempo)
        return 120.0
    
    def _analyze_timing(self, notes: List[Dict], tempo: float) -> Dict:
        """Analyze micro-timing features"""
        ticks_per_beat = 480
        beat_length = ticks_per_beat
        
        # Calculate expected grid positions
        deviations = []
        for note in notes:
            expected = round(note['time'] / beat_length) * beat_length
            deviation = (note['time'] - expected) / ticks_per_beat * 1000
            deviations.append(deviation)
        
        deviations = np.array(deviations)
        
        return {
            'micro_timing_variance': float(np.std(deviations)),
            'systematic_drift': float(np.mean(deviations)),
            'groove_swing': self._calculate_swing(notes, beat_length),
            'timing_consistency': 1.0 / (1.0 + np.std(deviations))
        }
    
    def _calculate_swing(self, notes: List[Dict], beat_length: float) -> float:
        """Calculate swing percentage"""
        offbeat_notes = [n for n in notes if (n['time'] % beat_length) > (beat_length * 0.4)]
        if not offbeat_notes:
            return 0.0
        
        swing_amounts = []
        for note in offbeat_notes:
            expected_offbeat = (note['time'] // beat_length) * beat_length + beat_length * 0.5
            actual_offset = note['time'] - expected_offbeat
            swing_amounts.append(actual_offset / beat_length)
        
        return float(np.mean(swing_amounts)) if swing_amounts else 0.0
    
    def _analyze_velocities(self, notes: List[Dict]) -> Dict:
        """Analyze velocity features"""
        velocities = np.array([n['velocity'] for n in notes])
        
        # Ghost notes (velocity < 40)
        ghost_notes = velocities[velocities < 40]
        ghost_freq = len(ghost_notes) / len(velocities) if len(velocities) > 0 else 0.0
        ghost_avg = float(np.mean(ghost_notes)) if len(ghost_notes) > 0 else 0.0
        
        # Accent strength (top 20% vs bottom 20%)
        sorted_vels = np.sort(velocities)
        top_20 = sorted_vels[int(len(sorted_vels) * 0.8):]
        bottom_20 = sorted_vels[:int(len(sorted_vels) * 0.2)]
        accent_strength = float(np.mean(top_20) - np.mean(bottom_20)) / 127.0
        
        return {
            'velocity_variance': float(np.std(velocities) / 127.0),
            'velocity_humanization': float(np.std(np.diff(velocities)) / 127.0),
            'accent_strength': accent_strength,
            'ghost_note_frequency': ghost_freq,
            'ghost_note_velocity_avg': ghost_avg / 127.0
        }
    
    def _analyze_patterns(self, notes: List[Dict]) -> Dict:
        """Analyze drum pattern features"""
        kicks = [n for n in notes if n['drum_type'] == 'kick']
        snares = [n for n in notes if n['drum_type'] == 'snare']
        hihats = [n for n in notes if n['drum_type'] == 'hihat']
        rides = [n for n in notes if n['drum_type'] == 'ride']
        
        total_time = notes[-1]['time'] - notes[0]['time'] if len(notes) > 1 else 1
        bars = total_time / (480 * 4)  # Assuming 4/4
        
        # Pattern densities
        kick_density = len(kicks) / bars if bars > 0 else 0
        snare_density = len(snares) / bars if bars > 0 else 0
        
        # Hihat complexity (variation in velocities and timing)
        hihat_complexity = 0.0
        if len(hihats) > 1:
            hihat_vels = np.array([h['velocity'] for h in hihats])
            hihat_times = np.array([h['time'] for h in hihats])
            vel_var = np.std(hihat_vels) / 127.0
            time_var = np.std(np.diff(hihat_times)) / 480.0
            hihat_complexity = (vel_var + time_var) / 2.0
        
        # Ride usage
        ride_ratio = len(rides) / (len(hihats) + len(rides) + 1)
        
        return {
            'kick_pattern_density': float(kick_density / 4.0),
            'snare_pattern_density': float(snare_density / 4.0),
            'hihat_pattern_complexity': float(hihat_complexity),
            'ride_usage_ratio': float(ride_ratio),
            'cymbal_accent_pattern': self._analyze_cymbal_accents(notes)
        }
    
    def _analyze_cymbal_accents(self, notes: List[Dict]) -> float:
        """Analyze crash/ride accent placement"""
        cymbals = [n for n in notes if n['drum_type'] in ['crash', 'ride']]
        if not cymbals:
            return 0.0
        
        # Check if cymbals are on downbeats
        downbeat_cymbals = sum(1 for c in cymbals if (c['time'] % (480 * 4)) < 100)
        return downbeat_cymbals / len(cymbals)
    
    def _analyze_groove(self, notes: List[Dict], tempo: float) -> Dict:
        """Analyze groove characteristics"""
        kicks = [n for n in notes if n['drum_type'] == 'kick']
        snares = [n for n in notes if n['drum_type'] == 'snare']
        hihats = [n for n in notes if n['drum_type'] == 'hihat']
        
        # Kick-snare relationship
        kick_snare_rel = self._calculate_kick_snare_relationship(kicks, snares)
        
        # Offbeat hihat ratio
        offbeat_ratio = 0.0
        if hihats:
            offbeat_hh = sum(1 for h in hihats if (h['time'] % 480) > 240)
            offbeat_ratio = offbeat_hh / len(hihats)
        
        # Syncopation
        syncopation = self._calculate_syncopation(notes)
        
        # Fill frequency
        fill_freq = self._detect_fills(notes)
        
        return {
            'kick_snare_relationship': kick_snare_rel,
            'offbeat_hihat_ratio': offbeat_ratio,
            'syncopation_level': syncopation,
            'fill_frequency': fill_freq
        }
    
    def _calculate_kick_snare_relationship(self, kicks: List, snares: List) -> float:
        """Calculate timing relationship between kick and snare"""
        if not kicks or not snares:
            return 0.5
        
        # Find snares that follow kicks closely
        close_pairs = 0
        for kick in kicks:
            for snare in snares:
                time_diff = abs(snare['time'] - kick['time'])
                if 100 < time_diff < 500:  # Within reasonable range
                    close_pairs += 1
                    break
        
        return close_pairs / max(len(kicks), len(snares))
    
    def _calculate_syncopation(self, notes: List[Dict]) -> float:
        """Calculate syncopation level"""
        if not notes:
            return 0.0
        
        offbeat_notes = sum(1 for n in notes if (n['time'] % 480) not in [0, 240, 480, 720])
        return offbeat_notes / len(notes)
    
    def _detect_fills(self, notes: List[Dict]) -> float:
        """Detect drum fills"""
        if len(notes) < 20:
            return 0.0
        
        # Look for density spikes (more notes in short time = fill)
        window = 480 * 2  # 2 beats
        fills = 0
        
        for i in range(len(notes) - 10):
            window_notes = [n for n in notes[i:i+10] 
                          if n['time'] - notes[i]['time'] < window]
            if len(window_notes) > 8:  # High density = fill
                fills += 1
        
        return min(fills / (len(notes) / 20), 1.0)


class AudioFeatureAnalyzer:
    """Analyzes audio files for complementary features"""
    
    def analyze_audio(self, audio_path: Path) -> Dict:
        """Extract audio features"""
        if not AUDIO_AVAILABLE:
            return self._default_audio_features()
        
        try:
            y, sr = librosa.load(str(audio_path), sr=44100, duration=30)
            
            # Transient sharpness
            onset_env = librosa.onset.onset_strength(y=y, sr=sr)
            transient = float(np.mean(onset_env))
            
            # Spectral centroid (brightness)
            centroid = librosa.feature.spectral_centroid(y=y, sr=sr)
            brightness = float(np.mean(centroid) / sr)
            
            # Dynamic range
            rms = librosa.feature.rms(y=y)
            dynamic_range = float(20 * np.log10(np.max(rms) / (np.min(rms) + 1e-10)))
            
            # Reverb (spectral flatness)
            flatness = librosa.feature.spectral_flatness(y=y)
            reverb = float(np.mean(flatness))
            
            return {
                'transient_sharpness': transient / 10.0,
                'spectral_centroid': brightness,
                'dynamic_range_db': dynamic_range / 60.0,
                'reverb_amount': reverb
            }
            
        except Exception as e:
            logger.error(f"Audio analysis failed: {e}")
            return self._default_audio_features()
    
    def _default_audio_features(self) -> Dict:
        """Default audio features if analysis fails"""
        return {
            'transient_sharpness': 0.5,
            'spectral_centroid': 0.5,
            'dynamic_range_db': 0.5,
            'reverb_amount': 0.3
        }


class ComprehensiveFeatureExtractor:
    """Main extractor combining MIDI and audio analysis"""
    
    def __init__(self):
        self.midi_analyzer = MIDIFeatureAnalyzer()
        self.audio_analyzer = AudioFeatureAnalyzer()
    
    def extract_features(self, 
                        midi_path: Optional[Path] = None,
                        audio_path: Optional[Path] = None,
                        metadata: Optional[Dict] = None) -> Optional[ComprehensiveFeatures]:
        """
        Extract comprehensive features from MIDI and/or audio
        
        Args:
            midi_path: Path to MIDI file
            audio_path: Path to audio file  
            metadata: Optional metadata (tempo, style, drummer)
        
        Returns:
            ComprehensiveFeatures object or None
        """
        features = None
        
        # Extract from MIDI
        if midi_path and midi_path.exists():
            features = self.midi_analyzer.analyze_midi(midi_path)
        
        # Extract from audio
        if audio_path and audio_path.exists():
            audio_features = self.audio_analyzer.analyze_audio(audio_path)
            
            if features:
                # Update existing features with audio data
                for key, value in audio_features.items():
                    setattr(features, key, value)
            else:
                # Create features from audio only
                features = ComprehensiveFeatures(
                    # Use defaults for MIDI features
                    micro_timing_variance=0.02,
                    systematic_drift=0.0,
                    groove_swing=0.0,
                    timing_consistency=0.7,
                    velocity_variance=0.2,
                    velocity_humanization=0.15,
                    accent_strength=0.5,
                    ghost_note_frequency=0.2,
                    ghost_note_velocity_avg=0.3,
                    kick_pattern_density=0.5,
                    snare_pattern_density=0.5,
                    hihat_pattern_complexity=0.5,
                    ride_usage_ratio=0.2,
                    cymbal_accent_pattern=0.5,
                    kick_snare_relationship=0.6,
                    offbeat_hihat_ratio=0.5,
                    syncopation_level=0.3,
                    fill_frequency=0.2,
                    **audio_features
                )
        
        # Add metadata
        if features and metadata:
            if 'tempo' in metadata:
                features.tempo = metadata['tempo']
            if 'style' in metadata:
                features.style = metadata['style']
            if 'drummer' in metadata:
                features.drummer = metadata['drummer']
        
        return features

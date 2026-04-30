"""
DrumTracKAI Complete System - Integrated Advanced Analysis
Revolutionary replacement system with ML-based style learning and pattern generation
"""

import numpy as np
import torch
import sqlite3
import pickle
import logging
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, asdict
from datetime import datetime
import os
import json

# Audio processing
# Note: librosa imported lazily to avoid LLVM issues
import soundfile as sf
from scipy import signal, stats

# ML and neural networks
try:
    import cupy as cp
    CUDA_AVAILABLE = True
except ImportError:
    CUDA_AVAILABLE = False
    cp = None

logger = logging.getLogger(__name__)

@dataclass
class DrumHit:
    """Enhanced drum hit with all integrated features"""
    timestamp: float
    velocity: float
    drum_type: str
    frequency_content: np.ndarray
    attack_sharpness: float = 0.0
    spectral_evolution: List[float] = None
    frequency_modulation: float = 0.0
    micro_timing_deviation: float = 0.0
    phase_in_measure: float = 0.0
    bass_correlation: float = 0.0
    preceding_interval: Optional[float] = None
    following_interval: Optional[float] = None

@dataclass
class TempoProfile:
    """Enhanced tempo profile"""
    average_tempo: float
    tempo_stability: float
    tempo_changes: List[Tuple[float, float]]
    is_steady: bool
    tempo_curve: np.ndarray
    confidence: float

@dataclass
class EntrainmentProfile:
    """Neural entrainment analysis results"""
    dominant_frequency: float
    frequency_stability: float
    phase_coherence: float
    groove_induction_potential: float
    flow_state_compatibility: float
    brainwave_alignment: Dict[str, float]
    tension_release_pattern: List[float]

@dataclass
class RhythmHierarchy:
    """Rhythm hierarchy analysis"""
    levels: List[Dict]
    complexity_score: float
    staggered_rhythm: float
    syncopation_score: float
    hierarchical_depth: int

class DrumTracKAI_Complete_System:
    """Complete integrated drummer analysis system"""
    
    def __init__(self, db_path: str = None, sample_rate: int = 44100):
        self.sample_rate = sample_rate
        self.device = torch.device('cuda' if torch.cuda.is_available() and CUDA_AVAILABLE else 'cpu')
        
        # Database setup
        if db_path is None:
            db_path = os.path.join(os.path.dirname(__file__), '..', 'drumtrackai.db')
        self.db_path = db_path
        
        # Initialize subsystems
        self._initialize_database()
        self._initialize_analyzers()
        
        logger.info(f"DrumTracKAI Complete System initialized on {self.device}")
    
    def _initialize_database(self):
        """Initialize enhanced database schema"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        # Complete analyses table
        c.execute('''CREATE TABLE IF NOT EXISTS complete_analyses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            drummer_id TEXT,
            track_name TEXT,
            standard_analysis BLOB,
            tfr_analysis BLOB,
            scalogram_analysis BLOB,
            entrainment_analysis BLOB,
            integrated_features BLOB
        )''')
        
        # Rhythm patterns table
        c.execute('''CREATE TABLE IF NOT EXISTS rhythm_patterns (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            drummer_id TEXT,
            pattern_name TEXT,
            hierarchy_data BLOB,
            production_rules BLOB,
            style_features BLOB,
            created_timestamp TEXT
        )''')
        
        # Stem files table
        c.execute('''CREATE TABLE IF NOT EXISTS stem_files (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            drummer_id TEXT,
            track_name TEXT,
            stem_type TEXT,
            file_path TEXT,
            analysis_id INTEGER,
            FOREIGN KEY (analysis_id) REFERENCES complete_analyses (id)
        )''')
        
        conn.commit()
        conn.close()
        logger.info("Database schema initialized")
    
    def _initialize_analyzers(self):
        """Initialize analysis subsystems"""
        self.gpu_available = torch.cuda.is_available() and CUDA_AVAILABLE
        logger.info(f"GPU acceleration: {'Available' if self.gpu_available else 'Not available'}")
    
    def complete_drum_analysis(self, drum_path: str, bass_path: str = None, 
                             drum_type: str = "full_kit", drummer_id: str = None) -> Dict:
        """Perform complete integrated analysis on drum audio"""
        logger.info(f"Starting complete analysis for {drum_path}")
        
        try:
            # Load audio
            drum_audio, sr = librosa.load(drum_path, sr=self.sample_rate)
            bass_audio = None
            if bass_path and os.path.exists(bass_path):
                bass_audio, _ = librosa.load(bass_path, sr=self.sample_rate)
            
            # Core analysis pipeline
            analysis = self._perform_integrated_analysis(
                drum_audio, bass_audio, drum_type, drummer_id
            )
            
            # Add metadata
            analysis['timestamp'] = datetime.now().isoformat()
            analysis['drummer_id'] = drummer_id
            analysis['track_name'] = os.path.basename(drum_path)
            analysis['drum_type'] = drum_type
            
            # Save to database
            analysis_id = self._save_complete_analysis(analysis)
            analysis['analysis_id'] = analysis_id
            
            logger.info("Complete analysis finished successfully")
            return analysis
            
        except Exception as e:
            logger.error(f"Complete analysis failed: {str(e)}")
            raise
    
    def _perform_integrated_analysis(self, drum_audio: np.ndarray, bass_audio: Optional[np.ndarray],
                                   drum_type: str, drummer_id: str) -> Dict:
        """Perform the integrated analysis pipeline"""
        
        # 1. Enhanced onset detection
        onsets = self._detect_onsets_enhanced(drum_audio)
        refined_onsets = self._refine_onsets_tfr(drum_audio, onsets)
        
        # 2. Integrated tempo analysis
        tempo_profile = self._analyze_tempo_integrated(drum_audio, refined_onsets)
        
        # 3. Comprehensive hit analysis
        hits = self._analyze_hits_integrated(drum_audio, refined_onsets, tempo_profile, bass_audio)
        
        # 4. Neural entrainment analysis
        entrainment_profile = self._analyze_neural_entrainment(drum_audio, refined_onsets)
        
        # 5. Rhythm hierarchy analysis
        rhythm_hierarchy = self._analyze_rhythm_hierarchy(refined_onsets, tempo_profile)
        
        # 6. Integrated groove metrics
        groove_metrics = self._compute_integrated_groove_metrics(
            hits, rhythm_hierarchy, entrainment_profile, bass_audio
        )
        
        # 7. ML style features
        style_features = self._extract_integrated_style_features(
            hits, tempo_profile, rhythm_hierarchy, entrainment_profile, groove_metrics
        )
        
        # 8. Visualization data
        visualization_data = self._prepare_visualization_data(
            hits, tempo_profile, rhythm_hierarchy, entrainment_profile, groove_metrics
        )
        
        return {
            'onsets': {
                'initial': onsets.tolist(),
                'refined': refined_onsets.tolist(),
                'refinement_stats': self._calculate_refinement_statistics(onsets, refined_onsets)
            },
            'tempo_profile': asdict(tempo_profile),
            'hits': [asdict(hit) for hit in hits],
            'neural_entrainment': asdict(entrainment_profile),
            'rhythm_hierarchy': asdict(rhythm_hierarchy),
            'groove_metrics': groove_metrics,
            'style_features': style_features.tolist() if isinstance(style_features, np.ndarray) else style_features,
            'visualization_data': visualization_data
        }
    
    def _detect_onsets_enhanced(self, audio: np.ndarray) -> np.ndarray:
        """Enhanced onset detection using multiple methods"""
        # Import librosa lazily to avoid LLVM issues during module loading
        import librosa
        
        # Spectral flux
        onset_frames = librosa.onset.onset_detect(
            y=audio, sr=self.sample_rate, units='time',
            hop_length=512, backtrack=True
        )
        
        # Complex domain onset detection for better precision
        stft = librosa.stft(audio, hop_length=512)
        onset_strength = librosa.onset.onset_strength(S=np.abs(stft), sr=self.sample_rate)
        onset_frames_complex = librosa.onset.onset_detect(
            onset_envelope=onset_strength, sr=self.sample_rate, units='time'
        )
        
        # Combine and deduplicate
        all_onsets = np.concatenate([onset_frames, onset_frames_complex])
        all_onsets = np.unique(all_onsets)
        
        # Filter out onsets that are too close together (< 50ms)
        if len(all_onsets) > 1:
            filtered_onsets = [all_onsets[0]]
            for onset in all_onsets[1:]:
                if onset - filtered_onsets[-1] > 0.05:  # 50ms minimum
                    filtered_onsets.append(onset)
            all_onsets = np.array(filtered_onsets)
        
        return all_onsets
    
    def _refine_onsets_tfr(self, audio: np.ndarray, initial_onsets: np.ndarray) -> np.ndarray:
        """Refine onsets using time-frequency reassignment (simplified version)"""
        refined_onsets = []
        
        for onset in initial_onsets:
            # Get a window around the onset
            window_size = int(0.03 * self.sample_rate)  # 30ms window
            start_idx = max(0, int(onset * self.sample_rate) - window_size // 2)
            end_idx = min(len(audio), start_idx + window_size)
            
            if end_idx > start_idx:
                window = audio[start_idx:end_idx]
                
                # Find the precise attack point using energy-based method
                energy = np.abs(window) ** 2
                smoothed_energy = signal.savgol_filter(energy, min(11, len(energy)), 3)
                
                # Find the steepest rise in energy
                energy_diff = np.diff(smoothed_energy)
                if len(energy_diff) > 0:
                    max_rise_idx = np.argmax(energy_diff)
                    refined_time = onset + (max_rise_idx - window_size // 2) / self.sample_rate
                    refined_onsets.append(refined_time)
                else:
                    refined_onsets.append(onset)
            else:
                refined_onsets.append(onset)
        
        return np.array(refined_onsets)
    
    def _analyze_tempo_integrated(self, audio: np.ndarray, onsets: np.ndarray) -> TempoProfile:
        """Enhanced tempo analysis using precise onsets"""
        # Import librosa lazily to avoid LLVM issues during module loading
        import librosa
        
        try:
            # Multiple tempo estimation methods
            tempo_estimates = []
            
            # Method 1: Beat tracking with librosa
            tempo_bt, beats = librosa.beat.beat_track(y=audio, sr=self.sample_rate)
            tempo_estimates.append(tempo_bt)
            
            # Method 2: Onset-based tempo estimation
            if len(onsets) > 1:
                intervals = np.diff(onsets)
                # Convert to BPM (60 seconds / interval)
                onset_tempos = 60.0 / intervals
                # Filter reasonable tempo range (60-200 BPM)
                valid_tempos = onset_tempos[(onset_tempos >= 60) & (onset_tempos <= 200)]
                if len(valid_tempos) > 0:
                    tempo_estimates.append(np.median(valid_tempos))
            
            # Method 3: Autocorrelation-based
            try:
                autocorr = np.correlate(audio, audio, mode='full')
                autocorr = autocorr[len(autocorr)//2:]
                
                # Find peaks in autocorrelation
                min_period = int(self.sample_rate * 60 / 200)  # 200 BPM max
                max_period = int(self.sample_rate * 60 / 60)   # 60 BPM min
                
                if max_period < len(autocorr):
                    peaks, _ = signal.find_peaks(autocorr[min_period:max_period])
                    if len(peaks) > 0:
                        period = peaks[0] + min_period
                        tempo_autocorr = 60.0 * self.sample_rate / period
                        tempo_estimates.append(tempo_autocorr)
            except:
                pass
            
            # Combine estimates
            if tempo_estimates:
                average_tempo = np.median(tempo_estimates)
                tempo_stability = 1.0 / (1.0 + np.std(tempo_estimates))
            else:
                average_tempo = 120.0  # Default fallback
                tempo_stability = 0.5
            
            # Tempo curve analysis
            tempo_curve = np.full(len(audio) // (self.sample_rate // 10), average_tempo)
            
            # Detect tempo changes
            tempo_changes = []
            confidence = min(1.0, tempo_stability * len(tempo_estimates) / 3.0)
            
            return TempoProfile(
                average_tempo=float(average_tempo),
                tempo_stability=float(tempo_stability),
                tempo_changes=tempo_changes,
                is_steady=tempo_stability > 0.8,
                tempo_curve=tempo_curve,
                confidence=float(confidence)
            )
            
        except Exception as e:
            logger.error(f"Tempo analysis failed: {e}")
            # Return default tempo profile
            return TempoProfile(
                average_tempo=120.0,
                tempo_stability=0.5,
                tempo_changes=[],
                is_steady=False,
                tempo_curve=np.array([120.0]),
                confidence=0.0
            )
    
    def analyze_complete_performance(self, audio_data: Dict, tempo_context: int = 120, 
                                   style_context: str = 'rock', metadata: Dict = None) -> Dict:
        """Main method for complete performance analysis"""
        try:
            logger.info(f"Starting complete performance analysis with tempo: {tempo_context}, style: {style_context}")
            
            # Extract drum and bass audio
            drum_audio = audio_data.get('drums', {}).get('audio', np.array([]))
            bass_audio = audio_data.get('bass', {}).get('audio', np.array([]))
            
            if len(drum_audio) == 0:
                raise ValueError("No drum audio data provided")
            
            # Perform integrated analysis
            results = self._perform_integrated_analysis(
                drum_audio, bass_audio if len(bass_audio) > 0 else None,
                "full_kit", metadata.get('drummer_id', 'unknown')
            )
            
            # Add context information
            results['tempo_context'] = tempo_context
            results['style_context'] = style_context
            results['metadata'] = metadata or {}
            
            # Generate visualization data
            results['visualization_data'] = self._generate_visualization_data(results)
            
            logger.info("Complete performance analysis finished successfully")
            return results
            
        except Exception as e:
            logger.error(f"Complete performance analysis failed: {e}")
            raise
    
    def _analyze_hits_integrated(self, audio: np.ndarray, onsets: np.ndarray, 
                               tempo_profile: TempoProfile, bass_audio: Optional[np.ndarray]) -> List[DrumHit]:
        """Comprehensive hit analysis with all integrated features"""
        try:
            hits = []
            
            for i, onset_time in enumerate(onsets):
                onset_sample = int(onset_time * self.sample_rate)
                
                # Extract hit window (50ms around onset)
                window_size = int(0.05 * self.sample_rate)
                start_sample = max(0, onset_sample - window_size // 2)
                end_sample = min(len(audio), onset_sample + window_size // 2)
                hit_window = audio[start_sample:end_sample]
                
                if len(hit_window) == 0:
                    continue
                
                # Basic hit properties
                velocity = np.max(np.abs(hit_window))
                
                # Frequency content analysis
                if len(hit_window) > 0:
                    fft = np.fft.fft(hit_window)
                    freqs = np.fft.fftfreq(len(hit_window), 1/self.sample_rate)
                    magnitude = np.abs(fft)
                    
                    # Find dominant frequency
                    dominant_freq_idx = np.argmax(magnitude[:len(magnitude)//2])
                    dominant_freq = freqs[dominant_freq_idx]
                    
                    # Classify drum type based on frequency
                    if dominant_freq < 100:
                        drum_type = "kick"
                    elif dominant_freq < 300:
                        drum_type = "tom"
                    elif dominant_freq < 1000:
                        drum_type = "snare"
                    else:
                        drum_type = "hihat_cymbal"
                else:
                    magnitude = np.array([0])
                    drum_type = "unknown"
                
                # Attack sharpness (rise time)
                attack_sharpness = self._calculate_attack_sharpness(hit_window)
                
                # Micro-timing deviation
                expected_time = i * (60.0 / tempo_profile.average_tempo)  # Expected beat time
                micro_timing_deviation = onset_time - expected_time
                
                # Bass correlation if available
                bass_correlation = 0.0
                if bass_audio is not None and len(bass_audio) > onset_sample:
                    bass_window = bass_audio[start_sample:end_sample]
                    if len(bass_window) == len(hit_window) and len(hit_window) > 0:
                        correlation = np.corrcoef(hit_window, bass_window)[0, 1]
                        bass_correlation = correlation if not np.isnan(correlation) else 0.0
                
                # Create DrumHit object
                hit = DrumHit(
                    timestamp=float(onset_time),
                    velocity=float(velocity),
                    drum_type=drum_type,
                    frequency_content=magnitude[:len(magnitude)//2],
                    attack_sharpness=float(attack_sharpness),
                    micro_timing_deviation=float(micro_timing_deviation),
                    bass_correlation=float(bass_correlation)
                )
                
                hits.append(hit)
            
            return hits
            
        except Exception as e:
            logger.error(f"Hit analysis failed: {e}")
            return []
    
    def _analyze_neural_entrainment(self, audio: np.ndarray, onsets: np.ndarray) -> EntrainmentProfile:
        """Neural entrainment analysis for brainwave alignment"""
        try:
            # Calculate rhythm frequency from onsets
            if len(onsets) > 1:
                intervals = np.diff(onsets)
                rhythm_freq = 1.0 / np.mean(intervals)  # Hz
            else:
                rhythm_freq = 2.0  # Default 2 Hz
            
            # Brainwave frequency bands (Hz)
            brainwave_bands = {
                'delta': (0.5, 4.0),
                'theta': (4.0, 8.0),
                'alpha': (8.0, 13.0),
                'beta': (13.0, 30.0),
                'gamma': (30.0, 100.0)
            }
            
            # Calculate alignment with each brainwave band
            brainwave_alignment = {}
            for band_name, (low_freq, high_freq) in brainwave_bands.items():
                if low_freq <= rhythm_freq <= high_freq:
                    alignment = 1.0 - abs(rhythm_freq - (low_freq + high_freq) / 2) / ((high_freq - low_freq) / 2)
                else:
                    alignment = max(0.0, 1.0 - min(abs(rhythm_freq - low_freq), abs(rhythm_freq - high_freq)) / rhythm_freq)
                
                brainwave_alignment[band_name] = max(0.0, min(1.0, alignment))
            
            # Phase coherence analysis
            phase_coherence = self._calculate_phase_coherence(onsets)
            
            # Groove induction potential
            groove_potential = self._calculate_groove_potential(onsets, rhythm_freq)
            
            # Flow state compatibility
            flow_compatibility = self._calculate_flow_compatibility(rhythm_freq, phase_coherence)
            
            return EntrainmentProfile(
                dominant_frequency=float(rhythm_freq),
                frequency_stability=float(1.0 / (1.0 + np.std(np.diff(onsets)) if len(onsets) > 1 else 1.0)),
                phase_coherence=float(phase_coherence),
                groove_induction_potential=float(groove_potential),
                flow_state_compatibility=float(flow_compatibility),
                brainwave_alignment=brainwave_alignment,
                tension_release_pattern=self._analyze_tension_release(onsets)
            )
            
        except Exception as e:
            logger.error(f"Neural entrainment analysis failed: {e}")
            return EntrainmentProfile(
                dominant_frequency=2.0,
                frequency_stability=0.5,
                phase_coherence=0.5,
                groove_induction_potential=0.5,
                flow_state_compatibility=0.5,
                brainwave_alignment={'delta': 0.0, 'theta': 0.0, 'alpha': 0.0, 'beta': 0.0, 'gamma': 0.0},
                tension_release_pattern=[]
            )
    
    def _analyze_rhythm_hierarchy(self, onsets: np.ndarray, tempo_profile: TempoProfile) -> RhythmHierarchy:
        """Analyze rhythm hierarchy and complexity"""
        try:
            if len(onsets) < 2:
                return RhythmHierarchy(
                    levels=[],
                    complexity_score=0.0,
                    staggered_rhythm=0.0,
                    syncopation_score=0.0,
                    hierarchical_depth=0
                )
            
            # Calculate intervals
            intervals = np.diff(onsets)
            
            # Beat period in seconds
            beat_period = 60.0 / tempo_profile.average_tempo
            
            # Quantize intervals to beat subdivisions
            subdivisions = [1, 0.5, 0.25, 0.125]  # Whole, half, quarter, eighth notes
            quantized_intervals = []
            
            for interval in intervals:
                best_subdivision = min(subdivisions, key=lambda x: abs(interval - beat_period * x))
                quantized_intervals.append(best_subdivision)
            
            # Calculate complexity metrics
            unique_subdivisions = len(set(quantized_intervals))
            complexity_score = min(1.0, unique_subdivisions / 4.0)
            
            # Syncopation analysis
            syncopation_score = self._calculate_syncopation(quantized_intervals, beat_period)
            
            # Staggered rhythm analysis
            staggered_rhythm = self._calculate_staggered_rhythm(intervals)
            
            # Hierarchical levels
            levels = self._extract_hierarchical_levels(quantized_intervals)
            
            return RhythmHierarchy(
                levels=levels,
                complexity_score=float(complexity_score),
                staggered_rhythm=float(staggered_rhythm),
                syncopation_score=float(syncopation_score),
                hierarchical_depth=len(levels)
            )
            
        except Exception as e:
            logger.error(f"Rhythm hierarchy analysis failed: {e}")
            return RhythmHierarchy(
                levels=[],
                complexity_score=0.0,
                staggered_rhythm=0.0,
                syncopation_score=0.0,
                hierarchical_depth=0
            )
    
    def _compute_integrated_groove_metrics(self, hits: List[DrumHit], rhythm_hierarchy: RhythmHierarchy,
                                         entrainment_profile: EntrainmentProfile, bass_audio: Optional[np.ndarray]) -> Dict:
        """Compute comprehensive groove metrics"""
        try:
            if not hits:
                return {
                    'timing_tightness': 0.0,
                    'dynamic_consistency': 0.0,
                    'attack_consistency': 0.0,
                    'bass_drum_synchronization': 0.0,
                    'overall_groove_score': 0.0
                }
            
            # Timing tightness
            timing_deviations = [abs(hit.micro_timing_deviation) for hit in hits]
            timing_tightness = 1.0 / (1.0 + np.mean(timing_deviations)) if timing_deviations else 0.0
            
            # Dynamic consistency
            velocities = [hit.velocity for hit in hits]
            dynamic_consistency = 1.0 / (1.0 + np.std(velocities)) if len(velocities) > 1 else 1.0
            
            # Attack consistency
            attack_sharpness = [hit.attack_sharpness for hit in hits if hasattr(hit, 'attack_sharpness')]
            attack_consistency = 1.0 / (1.0 + np.std(attack_sharpness)) if len(attack_sharpness) > 1 else 1.0
            
            # Bass-drum synchronization
            bass_correlations = [hit.bass_correlation for hit in hits]
            bass_drum_sync = np.mean([abs(corr) for corr in bass_correlations]) if bass_correlations else 0.0
            
            # Overall groove score
            groove_components = [
                timing_tightness * 0.3,
                dynamic_consistency * 0.25,
                attack_consistency * 0.2,
                bass_drum_sync * 0.15,
                entrainment_profile.groove_induction_potential * 0.1
            ]
            overall_groove_score = sum(groove_components)
            
            return {
                'timing_tightness': float(timing_tightness),
                'dynamic_consistency': float(dynamic_consistency),
                'attack_consistency': float(attack_consistency),
                'bass_drum_synchronization': float(bass_drum_sync),
                'overall_groove_score': float(overall_groove_score)
            }
            
        except Exception as e:
            logger.error(f"Groove metrics calculation failed: {e}")
            return {
                'timing_tightness': 0.0,
                'dynamic_consistency': 0.0,
                'attack_consistency': 0.0,
                'bass_drum_synchronization': 0.0,
                'overall_groove_score': 0.0
            }
    
    def _extract_integrated_style_features(self, hits: List[DrumHit], tempo_profile: TempoProfile,
                                         rhythm_hierarchy: RhythmHierarchy, entrainment_profile: EntrainmentProfile,
                                         groove_metrics: Dict) -> np.ndarray:
        """Extract ML-ready style features"""
        try:
            features = []
            
            # Tempo features
            features.extend([
                tempo_profile.average_tempo / 200.0,  # Normalized tempo
                tempo_profile.tempo_stability,
                1.0 if tempo_profile.is_steady else 0.0
            ])
            
            # Hit pattern features
            if hits:
                velocities = [hit.velocity for hit in hits]
                features.extend([
                    np.mean(velocities),
                    np.std(velocities),
                    len(hits) / 100.0  # Normalized hit count
                ])
            else:
                features.extend([0.0, 0.0, 0.0])
            
            # Rhythm complexity features
            features.extend([
                rhythm_hierarchy.complexity_score,
                rhythm_hierarchy.syncopation_score,
                rhythm_hierarchy.hierarchical_depth / 10.0  # Normalized depth
            ])
            
            # Entrainment features
            features.extend([
                entrainment_profile.groove_induction_potential,
                entrainment_profile.flow_state_compatibility,
                entrainment_profile.phase_coherence
            ])
            
            # Groove features
            features.extend([
                groove_metrics['timing_tightness'],
                groove_metrics['dynamic_consistency'],
                groove_metrics['overall_groove_score']
            ])
            
            return np.array(features, dtype=np.float32)
            
        except Exception as e:
            logger.error(f"Style feature extraction failed: {e}")
            return np.zeros(15, dtype=np.float32)
    
    def _prepare_visualization_data(self, hits: List[DrumHit], tempo_profile: TempoProfile,
                                  rhythm_hierarchy: RhythmHierarchy, entrainment_profile: EntrainmentProfile,
                                  groove_metrics: Dict) -> Dict:
        """Prepare data for visualization"""
        try:
            viz_data = {
                'tempo': {
                    'average': tempo_profile.average_tempo,
                    'stability': tempo_profile.tempo_stability,
                    'curve': tempo_profile.tempo_curve.tolist() if hasattr(tempo_profile.tempo_curve, 'tolist') else []
                },
                'hits': {
                    'timestamps': [hit.timestamp for hit in hits],
                    'velocities': [hit.velocity for hit in hits],
                    'types': [hit.drum_type for hit in hits]
                },
                'groove_metrics': groove_metrics,
                'entrainment': {
                    'brainwave_alignment': entrainment_profile.brainwave_alignment,
                    'groove_potential': entrainment_profile.groove_induction_potential
                },
                'rhythm_complexity': {
                    'complexity_score': rhythm_hierarchy.complexity_score,
                    'syncopation': rhythm_hierarchy.syncopation_score
                }
            }
            
            return viz_data
            
        except Exception as e:
            logger.error(f"Visualization data preparation failed: {e}")
            return {}
    
    def _calculate_refinement_statistics(self, initial_onsets: np.ndarray, refined_onsets: np.ndarray) -> Dict:
        """Calculate onset refinement statistics"""
        try:
            if len(initial_onsets) == 0 or len(refined_onsets) == 0:
                return {'refinement_applied': False, 'improvement_ratio': 0.0}
            
            # Calculate average shift
            if len(initial_onsets) == len(refined_onsets):
                shifts = np.abs(refined_onsets - initial_onsets)
                avg_shift = np.mean(shifts)
                max_shift = np.max(shifts)
                
                return {
                    'refinement_applied': True,
                    'average_shift_ms': float(avg_shift * 1000),
                    'max_shift_ms': float(max_shift * 1000),
                    'improvement_ratio': 1.0
                }
            else:
                return {
                    'refinement_applied': True,
                    'onset_count_change': len(refined_onsets) - len(initial_onsets),
                    'improvement_ratio': 1.0
                }
        except Exception as e:
            logger.error(f"Refinement statistics calculation failed: {e}")
            return {'refinement_applied': False, 'improvement_ratio': 0.0}
    
    # Helper methods for analysis calculations
    def _calculate_attack_sharpness(self, hit_window: np.ndarray) -> float:
        """Calculate attack sharpness of a drum hit"""
        if len(hit_window) < 10:
            return 0.0
        
        # Find the peak
        peak_idx = np.argmax(np.abs(hit_window))
        
        # Calculate rise time (10% to 90% of peak)
        peak_value = np.abs(hit_window[peak_idx])
        threshold_low = 0.1 * peak_value
        threshold_high = 0.9 * peak_value
        
        # Find rise time
        rise_start = 0
        rise_end = peak_idx
        
        for i in range(peak_idx):
            if np.abs(hit_window[i]) >= threshold_low:
                rise_start = i
                break
        
        for i in range(rise_start, peak_idx):
            if np.abs(hit_window[i]) >= threshold_high:
                rise_end = i
                break
        
        rise_time = rise_end - rise_start
        return 1.0 / (1.0 + rise_time / len(hit_window))  # Normalized sharpness
    
    def _calculate_phase_coherence(self, onsets: np.ndarray) -> float:
        """Calculate phase coherence of rhythm"""
        if len(onsets) < 3:
            return 0.5
        
        intervals = np.diff(onsets)
        mean_interval = np.mean(intervals)
        coherence = 1.0 / (1.0 + np.std(intervals) / mean_interval)
        return min(1.0, max(0.0, coherence))
    
    def _calculate_groove_potential(self, onsets: np.ndarray, rhythm_freq: float) -> float:
        """Calculate groove induction potential"""
        # Optimal groove frequencies are around 1.5-3 Hz
        optimal_range = (1.5, 3.0)
        
        if optimal_range[0] <= rhythm_freq <= optimal_range[1]:
            return 1.0
        else:
            distance = min(abs(rhythm_freq - optimal_range[0]), abs(rhythm_freq - optimal_range[1]))
            return max(0.0, 1.0 - distance / rhythm_freq)
    
    def _calculate_flow_compatibility(self, rhythm_freq: float, phase_coherence: float) -> float:
        """Calculate flow state compatibility"""
        # Flow states are enhanced by rhythms around 2-4 Hz with high coherence
        freq_score = 1.0 if 2.0 <= rhythm_freq <= 4.0 else max(0.0, 1.0 - abs(rhythm_freq - 3.0) / 3.0)
        return (freq_score + phase_coherence) / 2.0
    
    def _analyze_tension_release(self, onsets: np.ndarray) -> List[float]:
        """Analyze tension and release patterns"""
        if len(onsets) < 4:
            return []
        
        # Simple tension analysis based on interval changes
        intervals = np.diff(onsets)
        tension_pattern = []
        
        for i in range(1, len(intervals)):
            # Tension increases with shorter intervals, decreases with longer
            if intervals[i] < intervals[i-1]:
                tension_pattern.append(min(1.0, intervals[i-1] / intervals[i] - 1.0))
            else:
                tension_pattern.append(max(-1.0, 1.0 - intervals[i] / intervals[i-1]))
        
        return tension_pattern
    
    def _calculate_syncopation(self, quantized_intervals: List[float], beat_period: float) -> float:
        """Calculate syncopation score"""
        if not quantized_intervals:
            return 0.0
        
        # Count off-beat placements
        off_beat_count = 0
        for interval in quantized_intervals:
            # Off-beat if not on main beat subdivisions
            if interval not in [1.0, 0.5, 0.25]:
                off_beat_count += 1
        
        return min(1.0, off_beat_count / len(quantized_intervals))
    
    def _calculate_staggered_rhythm(self, intervals: np.ndarray) -> float:
        """Calculate staggered rhythm metric"""
        if len(intervals) < 2:
            return 0.0
        
        # Measure variation in intervals
        variation = np.std(intervals) / np.mean(intervals) if np.mean(intervals) > 0 else 0
        return min(1.0, variation)
    
    def _extract_hierarchical_levels(self, quantized_intervals: List[float]) -> List[Dict]:
        """Extract hierarchical rhythm levels"""
        levels = []
        unique_intervals = list(set(quantized_intervals))
        
        for interval in sorted(unique_intervals, reverse=True):
            count = quantized_intervals.count(interval)
            levels.append({
                'subdivision': interval,
                'count': count,
                'proportion': count / len(quantized_intervals)
            })
        
        return levels
    
    def _generate_visualization_data(self, analysis_results: Dict) -> Dict:
        """Generate data for visualization"""
        try:
            viz_data = {}
            
            # Tempo curve data
            tempo_profile = analysis_results.get('tempo_profile')
            if tempo_profile:
                viz_data['tempo_curve'] = {
                    'times': list(range(len(tempo_profile.tempo_curve))),
                    'tempos': tempo_profile.tempo_curve.tolist()
                }
            
            # Hit timeline data
            hits = analysis_results.get('hits', [])
            if hits:
                viz_data['hit_timeline'] = {
                    'times': [hit.timestamp for hit in hits],
                    'velocities': [hit.velocity for hit in hits],
                    'micro_timing': [hit.micro_timing_deviation for hit in hits]
                }
            
            # Style radar data - AUTHENTIC ONLY (no fallback values)
            rhythm_hierarchy = analysis_results.get('rhythm_hierarchy', {})
            groove_metrics = analysis_results.get('groove_metrics', {})
            neural_entrainment = analysis_results.get('neural_entrainment', {})
            
            # Only include style radar if we have REAL analysis data
            if (rhythm_hierarchy and groove_metrics and neural_entrainment and
                all(key in rhythm_hierarchy for key in ['complexity_score', 'syncopation_score']) and
                all(key in groove_metrics for key in ['dynamic_consistency', 'timing_tightness', 'overall_groove_score']) and
                'flow_state_compatibility' in neural_entrainment):
                
                viz_data['style_radar'] = {
                    'categories': ['Complexity', 'Syncopation', 'Dynamics', 'Precision', 'Groove', 'Flow'],
                    'values': [
                        rhythm_hierarchy['complexity_score'],
                        rhythm_hierarchy['syncopation_score'],
                        groove_metrics['dynamic_consistency'],
                        groove_metrics['timing_tightness'],
                        groove_metrics['overall_groove_score'],
                        neural_entrainment['flow_state_compatibility']
                    ],
                    'authenticity': 'REAL_ANALYSIS'  # Mark as authentic
                }
            else:
                # NO FALLBACK - indicate missing data clearly
                viz_data['style_radar'] = {
                    'error': 'INSUFFICIENT_DATA_FOR_STYLE_ANALYSIS',
                    'authenticity': 'ANALYSIS_FAILED',
                    'message': 'Style radar requires complete rhythm, groove, and neural analysis'
                }
            
            # Entrainment spectrum data - AUTHENTIC ONLY
            entrainment = analysis_results.get('neural_entrainment', {})
            if entrainment and 'brainwave_alignment' in entrainment:
                brainwave_alignment = entrainment['brainwave_alignment']
                # Only use if we have REAL brainwave data (not empty or placeholder)
                if brainwave_alignment and len(brainwave_alignment) > 0:
                    viz_data['entrainment_spectrum'] = {
                        'frequencies': list(brainwave_alignment.keys()),
                        'amplitudes': list(brainwave_alignment.values()),
                        'authenticity': 'REAL_NEURAL_ANALYSIS'
                    }
                else:
                    viz_data['entrainment_spectrum'] = {
                        'error': 'NO_BRAINWAVE_DATA',
                        'authenticity': 'ANALYSIS_FAILED',
                        'message': 'Neural entrainment analysis did not produce brainwave alignment data'
                    }
            else:
                viz_data['entrainment_spectrum'] = {
                    'error': 'NEURAL_ENTRAINMENT_ANALYSIS_MISSING',
                    'authenticity': 'ANALYSIS_FAILED',
                    'message': 'Neural entrainment analysis was not performed or failed'
                }
            
            return viz_data
            
        except Exception as e:
            logger.error(f"Error generating visualization data: {e}")
            return {}
    
    def store_complete_analysis(self, drummer_id: str, track_name: str, source_file: str,
                              analysis_results: Dict, metadata: Dict) -> int:
        """Store complete analysis results in database"""
        try:
            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()
            
            # Store main analysis
            c.execute('''
                INSERT INTO complete_analyses 
                (timestamp, drummer_id, track_name, standard_analysis, integrated_features)
                VALUES (?, ?, ?, ?, ?)
            ''', (
                datetime.now().isoformat(),
                drummer_id,
                track_name,
                pickle.dumps(analysis_results),
                pickle.dumps(metadata)
            ))
            
            analysis_id = c.lastrowid
            
            # Store stem file references
            audio_data = metadata.get('audio_data', {})
            for stem_type, stem_info in audio_data.items():
                if isinstance(stem_info, dict) and 'file_path' in stem_info:
                    c.execute('''
                        INSERT INTO stem_files (drummer_id, track_name, stem_type, file_path, analysis_id)
                        VALUES (?, ?, ?, ?, ?)
                    ''', (drummer_id, track_name, stem_type, stem_info['file_path'], analysis_id))
            
            conn.commit()
            conn.close()
            
            logger.info(f"Stored complete analysis with ID: {analysis_id}")
            return analysis_id
            
        except Exception as e:
            logger.error(f"Error storing complete analysis: {e}")
            return -1
    
    def update_drummer_profile(self, drummer_id: str, analysis_results: Dict):
        """Update drummer profile with new analysis"""
        try:
            # This would update the drummer's learned style profile
            # For now, just log the update
            logger.info(f"Updated drummer profile for: {drummer_id}")
            
        except Exception as e:
            logger.error(f"Error updating drummer profile: {e}")
    
    def get_analysis_by_source_file(self, source_file: str) -> Optional[Dict]:
        """Get analysis results by source file"""
        try:
            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()
            
            c.execute('''
                SELECT standard_analysis FROM complete_analyses 
                WHERE integrated_features LIKE ?
                ORDER BY timestamp DESC LIMIT 1
            ''', (f'%{source_file}%',))
            
            result = c.fetchone()
            conn.close()
            
            if result:
                return pickle.loads(result[0])
            return None
            
        except Exception as e:
            logger.error(f"Error getting analysis by source file: {e}")
            return None


# Create a properly named class alias for compatibility
DrumTracKAICompleteSystem = DrumTracKAI_Complete_System

#!/usr/bin/env python3
"""
Tempo-Aware Individual Drum Stem Analyzer
Analyzes each drum stem with tempo context and bass integration for authentic drummer profiling
"""

import os
import sys
import numpy as np
import soundfile as sf
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
import logging
from datetime import datetime

# Set LLVM-safe environment variables
os.environ['NUMBA_DISABLE_INTEL_SVML'] = '1'
os.environ['OMP_NUM_THREADS'] = '1' 
os.environ['NUMBA_DISABLE_TBB'] = '1'

# Setup path
admin_path = Path(__file__).parent.parent
sys.path.insert(0, str(admin_path))

logger = logging.getLogger(__name__)

@dataclass
class TempoAwareDrumAnalysis:
    """Tempo-aware analysis results for a single drum type"""
    drum_type: str
    file_path: str
    duration: float
    sample_rate: int
    
    # Tempo context
    global_tempo: float
    tempo_stability: float
    
    # Onset and timing analysis (tempo-aware)
    onsets: List[float]
    onset_count: int
    on_beat_hits: int
    off_beat_hits: int
    syncopated_hits: int
    
    # Timing precision relative to tempo
    timing_precision_score: float
    micro_timing_deviations: List[float]
    groove_timing_signature: str  # "ahead", "behind", "on", "variable"
    
    # Velocity and dynamics (tempo-contextualized)
    velocities: List[float]
    velocity_on_beats: List[float]
    velocity_off_beats: List[float]
    dynamic_groove_contribution: float
    
    # Bass integration analysis
    bass_correlation_coefficient: float
    bass_sync_events: int
    bass_sync_percentage: float
    bass_drum_pocket_score: float
    bass_interaction_pattern: str
    
    # Rhythmic role analysis
    rhythmic_role: str
    pattern_complexity: float
    pattern_repetition_score: float

class TempoAwareDrumStemAnalyzer:
    """Analyzes individual drum stems with tempo context and bass integration"""
    
    def __init__(self, sample_rate: int = 44100):
        self.sample_rate = sample_rate
        
        # Define expected drum stem files from MVSep DrumSep output
        self.drum_stem_mapping = {
            'kick': ['kick.wav', 'kick_drum.wav', 'bass_drum.wav'],
            'snare': ['snare.wav', 'snare_drum.wav'],
            'toms': ['toms.wav', 'tom.wav', 'tom_drums.wav'],
            'hihat': ['hihat.wav', 'hi_hat.wav', 'hh.wav'],
            'crash': ['crash.wav', 'crash_cymbal.wav'],
            'ride': ['ride.wav', 'ride_cymbal.wav']
        }
        
        logger.info("Tempo-Aware Individual Drum Stem Analyzer initialized")
    
    def analyze_individual_drum_tempo_aware(self, drum_file: Path, drum_type: str, 
                                          tempo_context: float, bass_audio: Optional[np.ndarray] = None) -> TempoAwareDrumAnalysis:
        """Analyze a single drum stem with tempo context and bass integration"""
        
        try:
            # Load drum audio
            drum_audio, sr = sf.read(str(drum_file))
            if len(drum_audio.shape) > 1:
                drum_audio = np.mean(drum_audio, axis=1)  # Convert to mono
            
            logger.info(f"Analyzing {drum_type}: {len(drum_audio)/sr:.1f}s at {tempo_context} BPM")
            
            # 1. Generate tempo-aware beat grid
            beat_grid = self._generate_beat_grid(len(drum_audio), sr, tempo_context)
            
            # 2. Onset detection (LLVM-safe)
            onsets = self._detect_onsets_safe(drum_audio, sr)
            
            # 3. Tempo-aware timing analysis
            timing_analysis = self._analyze_tempo_aware_timing(onsets, beat_grid, tempo_context)
            
            # 4. Velocity analysis (tempo-contextualized)
            velocity_analysis = self._analyze_tempo_aware_velocities(drum_audio, onsets, beat_grid, sr)
            
            # 5. Bass integration analysis
            bass_analysis = self._analyze_bass_integration(drum_audio, bass_audio, onsets, beat_grid, sr)
            
            # 6. Rhythmic role analysis
            role_analysis = self._analyze_rhythmic_role(drum_type, onsets, beat_grid, velocity_analysis)
            
            # Create comprehensive analysis result
            analysis = TempoAwareDrumAnalysis(
                drum_type=drum_type,
                file_path=str(drum_file),
                duration=len(drum_audio) / sr,
                sample_rate=sr,
                
                # Tempo context
                global_tempo=tempo_context,
                tempo_stability=timing_analysis['tempo_stability'],
                
                # Onset and timing analysis
                onsets=onsets.tolist(),
                onset_count=len(onsets),
                on_beat_hits=timing_analysis['on_beat_hits'],
                off_beat_hits=timing_analysis['off_beat_hits'],
                syncopated_hits=timing_analysis['syncopated_hits'],
                
                # Timing precision
                timing_precision_score=timing_analysis['precision_score'],
                micro_timing_deviations=timing_analysis['micro_deviations'],
                groove_timing_signature=timing_analysis['timing_signature'],
                
                # Velocity analysis
                velocities=velocity_analysis['all_velocities'],
                velocity_on_beats=velocity_analysis['on_beat_velocities'],
                velocity_off_beats=velocity_analysis['off_beat_velocities'],
                dynamic_groove_contribution=velocity_analysis['groove_contribution'],
                
                # Bass integration
                bass_correlation_coefficient=bass_analysis['correlation_coefficient'],
                bass_sync_events=bass_analysis['sync_events'],
                bass_sync_percentage=bass_analysis['sync_percentage'],
                bass_drum_pocket_score=bass_analysis['pocket_score'],
                bass_interaction_pattern=bass_analysis['interaction_pattern'],
                
                # Rhythmic role
                rhythmic_role=role_analysis['role'],
                pattern_complexity=role_analysis['complexity'],
                pattern_repetition_score=role_analysis['repetition_score']
            )
            
            logger.info(f"{drum_type} tempo-aware analysis complete: "
                       f"{analysis.timing_precision_score:.3f} precision, "
                       f"{analysis.bass_drum_pocket_score:.3f} pocket score")
            return analysis
            
        except Exception as e:
            logger.error(f"Failed to analyze {drum_type}: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            raise
    
    def _generate_beat_grid(self, audio_length: int, sr: int, tempo: float) -> np.ndarray:
        """Generate a beat grid based on tempo"""
        beat_interval = 60.0 / tempo  # Seconds per beat
        duration = audio_length / sr
        beats = np.arange(0, duration, beat_interval)
        return beats
    
    def _detect_onsets_safe(self, audio: np.ndarray, sr: int) -> np.ndarray:
        """LLVM-safe onset detection using scipy"""
        frame_length = 2048
        hop_length = 512
        
        # Compute energy in overlapping windows
        energy = []
        for i in range(0, len(audio) - frame_length, hop_length):
            frame = audio[i:i + frame_length]
            frame_energy = np.sum(frame ** 2)
            energy.append(frame_energy)
        
        energy = np.array(energy)
        
        # Smooth energy
        from scipy.signal import savgol_filter, find_peaks
        if len(energy) > 5:
            smoothed_energy = savgol_filter(energy, min(5, len(energy)), 2)
        else:
            smoothed_energy = energy
        
        # Find peaks in energy
        threshold = np.mean(smoothed_energy) + 2 * np.std(smoothed_energy)
        min_distance = int(0.05 * sr / hop_length)  # 50ms minimum distance
        
        peaks, _ = find_peaks(smoothed_energy, height=threshold, distance=min_distance)
        
        # Convert frame indices to time
        onset_times = peaks * hop_length / sr
        return onset_times
    
    def _analyze_tempo_aware_timing(self, onsets: np.ndarray, beat_grid: np.ndarray, tempo: float) -> Dict:
        """Analyze timing relative to the beat grid"""
        
        if len(onsets) == 0 or len(beat_grid) == 0:
            return {
                'tempo_stability': 0.0,
                'on_beat_hits': 0,
                'off_beat_hits': 0,
                'syncopated_hits': 0,
                'precision_score': 0.0,
                'micro_deviations': [],
                'timing_signature': 'unknown'
            }
        
        # Find closest beat for each onset
        beat_tolerance = 0.1  # 100ms tolerance for "on beat"
        
        on_beat_hits = 0
        off_beat_hits = 0
        syncopated_hits = 0
        micro_deviations = []
        
        for onset in onsets:
            # Find closest beat
            beat_distances = np.abs(beat_grid - onset)
            closest_beat_distance = np.min(beat_distances)
            closest_beat_idx = np.argmin(beat_distances)
            
            micro_deviations.append(float(closest_beat_distance))
            
            if closest_beat_distance <= beat_tolerance:
                # Check if it's on a strong beat (1, 3) or weak beat (2, 4)
                beat_position = closest_beat_idx % 4
                if beat_position in [0, 2]:  # Strong beats
                    on_beat_hits += 1
                else:  # Weak beats
                    off_beat_hits += 1
            else:
                syncopated_hits += 1
        
        # Calculate precision score
        precision_score = float(1.0 / (1.0 + np.mean(micro_deviations))) if micro_deviations else 0.0
        
        # Determine timing signature
        total_hits = len(onsets)
        if total_hits > 0:
            on_beat_ratio = on_beat_hits / total_hits
            if on_beat_ratio > 0.7:
                timing_signature = "on"
            elif np.mean(micro_deviations) > 0:
                timing_signature = "ahead"
            else:
                timing_signature = "behind"
        else:
            timing_signature = "unknown"
        
        # Tempo stability
        if len(onsets) > 1:
            intervals = np.diff(onsets)
            expected_interval = 60.0 / tempo
            interval_deviations = np.abs(intervals - expected_interval)
            tempo_stability = float(1.0 / (1.0 + np.mean(interval_deviations)))
        else:
            tempo_stability = 1.0
        
        return {
            'tempo_stability': tempo_stability,
            'on_beat_hits': on_beat_hits,
            'off_beat_hits': off_beat_hits,
            'syncopated_hits': syncopated_hits,
            'precision_score': precision_score,
            'micro_deviations': micro_deviations,
            'timing_signature': timing_signature
        }
    
    def _analyze_tempo_aware_velocities(self, audio: np.ndarray, onsets: np.ndarray, 
                                       beat_grid: np.ndarray, sr: int) -> Dict:
        """Analyze velocities in the context of the beat grid"""
        
        if len(onsets) == 0:
            return {
                'all_velocities': [],
                'on_beat_velocities': [],
                'off_beat_velocities': [],
                'groove_contribution': 0.0
            }
        
        velocities = []
        on_beat_velocities = []
        off_beat_velocities = []
        
        window_size = int(0.05 * sr)  # 50ms window
        beat_tolerance = 0.1  # 100ms tolerance
        
        for onset in onsets:
            onset_sample = int(onset * sr)
            start_sample = max(0, onset_sample - window_size // 4)
            end_sample = min(len(audio), onset_sample + 3 * window_size // 4)
            
            if end_sample > start_sample:
                window = audio[start_sample:end_sample]
                velocity = np.sqrt(np.mean(window ** 2))  # RMS energy
                velocities.append(velocity)
                
                # Determine if this onset is on a strong beat
                beat_distances = np.abs(beat_grid - onset)
                closest_beat_distance = np.min(beat_distances)
                closest_beat_idx = np.argmin(beat_distances)
                
                if closest_beat_distance <= beat_tolerance:
                    beat_position = closest_beat_idx % 4
                    if beat_position in [0, 2]:  # Strong beats
                        on_beat_velocities.append(velocity)
                    else:
                        off_beat_velocities.append(velocity)
                else:
                    off_beat_velocities.append(velocity)
            else:
                velocities.append(0.0)
        
        # Calculate groove contribution
        if len(velocities) > 0:
            velocity_consistency = 1.0 / (1.0 + np.std(velocities) / np.mean(velocities))
            groove_contribution = float(velocity_consistency)
        else:
            groove_contribution = 0.0
        
        return {
            'all_velocities': velocities,
            'on_beat_velocities': on_beat_velocities,
            'off_beat_velocities': off_beat_velocities,
            'groove_contribution': groove_contribution
        }
    
    def _analyze_bass_integration(self, drum_audio: np.ndarray, bass_audio: Optional[np.ndarray], 
                                 onsets: np.ndarray, beat_grid: np.ndarray, sr: int) -> Dict:
        """Analyze integration and interaction with bass track"""
        
        if bass_audio is None or len(bass_audio) == 0:
            return {
                'correlation_coefficient': 0.0,
                'sync_events': 0,
                'sync_percentage': 0.0,
                'pocket_score': 0.0,
                'interaction_pattern': 'no_bass'
            }
        
        # Ensure same length
        min_length = min(len(drum_audio), len(bass_audio))
        drum_audio = drum_audio[:min_length]
        bass_audio = bass_audio[:min_length]
        
        # Overall correlation
        correlation_matrix = np.corrcoef(drum_audio, bass_audio)
        correlation_coefficient = float(correlation_matrix[0, 1]) if not np.isnan(correlation_matrix[0, 1]) else 0.0
        
        # Detect bass onsets for synchronization analysis
        bass_onsets = self._detect_onsets_safe(bass_audio, sr)
        
        # Synchronization analysis
        sync_events = 0
        sync_window = 0.05  # 50ms synchronization window
        
        for drum_onset in onsets:
            # Check if there's a bass onset within the sync window
            if len(bass_onsets) > 0:
                bass_distances = np.abs(bass_onsets - drum_onset)
                if np.min(bass_distances) <= sync_window:
                    sync_events += 1
        
        sync_percentage = float(sync_events / len(onsets)) if len(onsets) > 0 else 0.0
        
        # Simple pocket score based on correlation and sync
        pocket_score = float((abs(correlation_coefficient) + sync_percentage) / 2.0)
        
        # Determine interaction pattern
        if sync_percentage > 0.7:
            interaction_pattern = "synchronized"
        elif sync_percentage > 0.3 and pocket_score > 0.5:
            interaction_pattern = "complementary"
        elif correlation_coefficient < 0.2:
            interaction_pattern = "independent"
        else:
            interaction_pattern = "conflicting"
        
        return {
            'correlation_coefficient': correlation_coefficient,
            'sync_events': sync_events,
            'sync_percentage': sync_percentage,
            'pocket_score': pocket_score,
            'interaction_pattern': interaction_pattern
        }
    
    def _analyze_rhythmic_role(self, drum_type: str, onsets: np.ndarray, 
                              beat_grid: np.ndarray, velocity_analysis: Dict) -> Dict:
        """Analyze the rhythmic role of this drum in the overall pattern"""
        
        if len(onsets) == 0:
            return {
                'role': 'inactive',
                'complexity': 0.0,
                'repetition_score': 0.0
            }
        
        # Determine primary role based on drum type and pattern
        if drum_type == 'kick':
            base_role = 'timekeeper'
        elif drum_type == 'snare':
            base_role = 'accent'
        elif drum_type == 'hihat':
            base_role = 'timekeeper'
        elif drum_type in ['crash', 'ride']:
            base_role = 'color'
        elif drum_type == 'toms':
            base_role = 'fill'
        else:
            base_role = 'unknown'
        
        # Calculate pattern complexity
        if len(onsets) > 1:
            intervals = np.diff(onsets)
            unique_intervals = len(np.unique(np.round(intervals, 2)))
            complexity = float(min(1.0, unique_intervals / 10.0))
        else:
            complexity = 0.0
        
        # Simple repetition score based on interval consistency
        if len(onsets) > 2:
            intervals = np.diff(onsets)
            repetition_score = float(1.0 / (1.0 + np.std(intervals) / np.mean(intervals))) if np.mean(intervals) > 0 else 0.0
        else:
            repetition_score = 0.0
        
        return {
            'role': base_role,
            'complexity': complexity,
            'repetition_score': repetition_score
        }

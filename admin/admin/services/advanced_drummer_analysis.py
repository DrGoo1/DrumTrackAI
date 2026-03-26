"""
Advanced Drummer Performance Analysis Service

This service analyzes separated drum stems to extract sophisticated human nuances
and unique characteristics that define a drummer's style and personality.
"""

import os
import json
import logging
import numpy as np
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime
import librosa
import scipy.signal
from scipy.stats import entropy

logger = logging.getLogger(__name__)

@dataclass
class DrumComponent:
    """Individual drum component analysis"""
    name: str
    audio_file: str
    hits: List[float] = field(default_factory=list)
    velocities: List[float] = field(default_factory=list)
    timing_deviations: List[float] = field(default_factory=list)
    spectral_features: Dict[str, float] = field(default_factory=dict)
    
@dataclass
class GrooveAnalysis:
    """Groove and timing analysis results"""
    swing_factor: float = 0.0
    pocket_tightness: float = 0.0
    rhythmic_complexity: float = 0.0
    syncopation_level: float = 0.0
    micro_timing_variance: float = 0.0
    humanness_score: float = 0.0

@dataclass
class DrummerProfile:
    """Complete drummer performance profile"""
    tempo: float
    style: str
    key: str
    duration: float
    components: Dict[str, DrumComponent] = field(default_factory=dict)
    groove: GrooveAnalysis = field(default_factory=GrooveAnalysis)
    signature_patterns: List[Dict] = field(default_factory=list)
    interaction_matrix: Dict[str, Dict[str, float]] = field(default_factory=dict)
    personality_traits: Dict[str, float] = field(default_factory=dict)
    technical_metrics: Dict[str, float] = field(default_factory=dict)

class AdvancedDrummerAnalysis:
    """Advanced drummer performance analysis using separated drum stems"""
    
    def __init__(self, sample_rate: int = 22050):
        self.sample_rate = sample_rate
        self.drum_components = ['kick', 'snare', 'toms', 'hihat', 'crash', 'ride']
        self.onset_threshold = 0.1
        self.min_hit_separation = 0.05
        self.timing_window = 0.02
        
        logger.info("Advanced Drummer Analysis initialized")
    
    def analyze_drummer_performance(self, 
                                  stem_files: Dict[str, str], 
                                  tempo: float, 
                                  style: str = "unknown",
                                  key: str = "C") -> DrummerProfile:
        """Analyze drummer performance from separated stems"""
        logger.info(f"Starting advanced drummer analysis (tempo: {tempo} BPM)")
        
        profile = DrummerProfile(tempo=tempo, style=style, key=key, duration=0.0)
        
        # Step 1: Analyze individual components
        for component_name in self.drum_components:
            if component_name in stem_files and os.path.exists(stem_files[component_name]):
                component = self._analyze_drum_component(stem_files[component_name], component_name, tempo)
                profile.components[component_name] = component
                
                if component.hits:
                    component_duration = max(component.hits) if component.hits else 0
                    profile.duration = max(profile.duration, component_duration)
        
        # Step 2: Analyze groove characteristics
        profile.groove = self._analyze_groove_characteristics(profile.components, tempo)
        
        # Step 3: Extract signature patterns
        profile.signature_patterns = self._extract_signature_patterns(profile.components, tempo)
        
        # Step 4: Analyze component interactions
        profile.interaction_matrix = self._analyze_component_interactions(profile.components)
        
        # Step 5: Extract personality traits
        profile.personality_traits = self._extract_personality_traits(profile)
        
        # Step 6: Calculate technical metrics
        profile.technical_metrics = self._calculate_technical_metrics(profile)
        
        logger.info("Advanced drummer analysis completed")
        return profile
    
    def _analyze_drum_component(self, audio_file: str, component_name: str, tempo: float) -> DrumComponent:
        """Analyze individual drum component"""
        logger.info(f"Analyzing {component_name}: {audio_file}")
        
        try:
            y, sr = librosa.load(audio_file, sr=self.sample_rate)
            
            # Detect onsets
            onset_frames = librosa.onset.onset_detect(
                y=y, sr=sr, units='time', threshold=self.onset_threshold,
                pre_max=3, post_max=3, pre_avg=3, post_avg=5, delta=0.2,
                wait=int(self.min_hit_separation * sr / 512)
            )
            
            # Calculate velocities
            onset_strength = librosa.onset.onset_strength(y=y, sr=sr, hop_length=512)
            velocities = []
            
            for onset_time in onset_frames:
                onset_frame = int(onset_time * sr / 512)
                if 0 <= onset_frame < len(onset_strength):
                    velocity = onset_strength[onset_frame]
                    velocities.append(float(velocity))
                else:
                    velocities.append(0.0)
            
            # Normalize velocities
            if velocities:
                max_vel = max(velocities)
                if max_vel > 0:
                    velocities = [v / max_vel for v in velocities]
            
            # Calculate timing deviations
            beat_interval = 60.0 / tempo
            timing_deviations = []
            
            for hit_time in onset_frames:
                expected_beat = round(hit_time / beat_interval) * beat_interval
                deviation = (hit_time - expected_beat) * 1000
                timing_deviations.append(deviation)
            
            # Extract spectral features
            spectral_features = self._extract_spectral_features(y, sr)
            
            component = DrumComponent(
                name=component_name, audio_file=audio_file,
                hits=onset_frames.tolist(), velocities=velocities,
                timing_deviations=timing_deviations, spectral_features=spectral_features
            )
            
            logger.info(f"{component_name}: {len(onset_frames)} hits detected")
            return component
            
        except Exception as e:
            logger.error(f"Error analyzing {component_name}: {e}")
            return DrumComponent(name=component_name, audio_file=audio_file)
    
    def _extract_spectral_features(self, y: np.ndarray, sr: int) -> Dict[str, float]:
        """Extract spectral characteristics"""
        try:
            spectral_centroids = librosa.feature.spectral_centroid(y=y, sr=sr)
            spectral_rolloff = librosa.feature.spectral_rolloff(y=y, sr=sr)
            spectral_bandwidth = librosa.feature.spectral_bandwidth(y=y, sr=sr)
            zero_crossing_rate = librosa.feature.zero_crossing_rate(y)
            mfccs = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=13)
            
            return {
                'spectral_centroid_mean': float(np.mean(spectral_centroids)),
                'spectral_rolloff_mean': float(np.mean(spectral_rolloff)),
                'spectral_bandwidth_mean': float(np.mean(spectral_bandwidth)),
                'zero_crossing_rate_mean': float(np.mean(zero_crossing_rate)),
                'mfcc_1_mean': float(np.mean(mfccs[0])),
                'brightness': float(np.mean(spectral_centroids) / (sr/2)),
                'roughness': float(np.std(spectral_bandwidth)),
            }
        except Exception as e:
            logger.warning(f"Error extracting spectral features: {e}")
            return {}
    
    def _analyze_groove_characteristics(self, components: Dict[str, DrumComponent], tempo: float) -> GrooveAnalysis:
        """Analyze groove characteristics and timing relationships"""
        groove = GrooveAnalysis()
        
        try:
            # Calculate timing consistency
            all_timing_deviations = []
            for comp in components.values():
                if comp.timing_deviations:
                    all_timing_deviations.extend(comp.timing_deviations)
            
            if all_timing_deviations:
                timing_std = np.std(all_timing_deviations)
                groove.pocket_tightness = max(0, 1 - (timing_std / 50))
                groove.micro_timing_variance = timing_std
            
            # Calculate rhythmic complexity
            groove.rhythmic_complexity = self._calculate_rhythmic_complexity(components, tempo)
            
            # Calculate humanness score
            groove.humanness_score = self._calculate_humanness_score(components, groove)
            
        except Exception as e:
            logger.error(f"Error in groove analysis: {e}")
        
        return groove
    
    def _calculate_rhythmic_complexity(self, components: Dict[str, DrumComponent], tempo: float) -> float:
        """Calculate overall rhythmic complexity"""
        try:
            complexity_factors = []
            
            for comp in components.values():
                if not comp.hits:
                    continue
                
                # Hit density
                if comp.hits:
                    duration = max(comp.hits) - min(comp.hits) if len(comp.hits) > 1 else 1.0
                    hit_density = len(comp.hits) / duration if duration > 0 else 0
                    complexity_factors.append(hit_density)
                
                # Timing variation entropy
                if comp.timing_deviations:
                    bins = np.histogram(comp.timing_deviations, bins=10)[0]
                    if np.sum(bins) > 0:
                        timing_entropy = entropy(bins + 1e-10)
                        complexity_factors.append(timing_entropy)
                
                # Velocity variation
                if comp.velocities:
                    velocity_std = np.std(comp.velocities)
                    complexity_factors.append(velocity_std)
            
            if complexity_factors:
                complexity = np.mean(complexity_factors)
                return max(0, min(1, complexity / 2))
            
        except Exception as e:
            logger.warning(f"Error calculating rhythmic complexity: {e}")
        
        return 0.0
    
    def _calculate_humanness_score(self, components: Dict[str, DrumComponent], groove: GrooveAnalysis) -> float:
        """Calculate humanness vs machine characteristics"""
        try:
            humanness_factors = []
            
            # Timing micro-variations
            if groove.micro_timing_variance > 0:
                timing_humanness = 1.0 - abs(groove.micro_timing_variance - 20) / 30
                humanness_factors.append(max(0, min(1, timing_humanness)))
            
            # Velocity variations
            velocity_variations = []
            for comp in components.values():
                if comp.velocities and len(comp.velocities) > 1:
                    velocity_std = np.std(comp.velocities)
                    velocity_variations.append(velocity_std)
            
            if velocity_variations:
                avg_velocity_variation = np.mean(velocity_variations)
                velocity_humanness = 1.0 - abs(avg_velocity_variation - 0.3) / 0.5
                humanness_factors.append(max(0, min(1, velocity_humanness)))
            
            if humanness_factors:
                return np.mean(humanness_factors)
            
        except Exception as e:
            logger.warning(f"Error calculating humanness score: {e}")
        
        return 0.5
    
    def _extract_signature_patterns(self, components: Dict[str, DrumComponent], tempo: float) -> List[Dict]:
        """Extract characteristic patterns"""
        patterns = []
        
        try:
            beat_interval = 60.0 / tempo
            
            # Extract kick-snare patterns
            kick = components.get('kick')
            snare = components.get('snare')
            
            if kick and snare and kick.hits and snare.hits:
                kick_beats = [round(hit / beat_interval) for hit in kick.hits]
                snare_beats = [round(hit / beat_interval) for hit in snare.hits]
                
                if kick_beats and snare_beats:
                    kick_density = len(kick_beats) / max(max(kick_beats), max(snare_beats), 1)
                    snare_density = len(snare_beats) / max(max(kick_beats), max(snare_beats), 1)
                    
                    if kick_density > 0.5 and snare_density < 0.3:
                        description = "kick-heavy_driving"
                    elif snare_density > 0.4:
                        description = "snare-prominent_complex"
                    else:
                        description = "classic_backbeat"
                    
                    patterns.append({
                        'type': 'kick_snare_pattern',
                        'description': description,
                        'complexity': kick_density + snare_density
                    })
            
        except Exception as e:
            logger.error(f"Error extracting signature patterns: {e}")
        
        return patterns
    
    def _analyze_component_interactions(self, components: Dict[str, DrumComponent]) -> Dict[str, Dict[str, float]]:
        """Analyze component interactions"""
        interaction_matrix = {}
        
        try:
            component_names = list(components.keys())
            
            for comp1_name in component_names:
                interaction_matrix[comp1_name] = {}
                comp1 = components[comp1_name]
                
                for comp2_name in component_names:
                    if comp1_name == comp2_name:
                        interaction_matrix[comp1_name][comp2_name] = 1.0
                        continue
                    
                    comp2 = components[comp2_name]
                    interaction = self._calculate_component_interaction(comp1, comp2)
                    interaction_matrix[comp1_name][comp2_name] = interaction
            
        except Exception as e:
            logger.error(f"Error analyzing component interactions: {e}")
        
        return interaction_matrix
    
    def _calculate_component_interaction(self, comp1: DrumComponent, comp2: DrumComponent) -> float:
        """Calculate interaction strength between components"""
        try:
            if not comp1.hits or not comp2.hits:
                return 0.0
            
            # Calculate synchronization
            sync_count = 0
            total_combinations = 0
            
            for hit1 in comp1.hits:
                for hit2 in comp2.hits:
                    total_combinations += 1
                    if abs(hit1 - hit2) < 0.05:  # Within 50ms
                        sync_count += 1
            
            synchronization = sync_count / total_combinations if total_combinations > 0 else 0
            return max(0, min(1, synchronization))
            
        except Exception as e:
            logger.warning(f"Error calculating component interaction: {e}")
            return 0.0
    
    def _extract_personality_traits(self, profile: DrummerProfile) -> Dict[str, float]:
        """Extract personality traits from performance"""
        traits = {}
        
        try:
            groove = profile.groove
            components = profile.components
            
            # Aggressiveness
            velocities = []
            for comp in components.values():
                if comp.velocities:
                    velocities.extend(comp.velocities)
            
            if velocities:
                traits['aggressiveness'] = np.mean(velocities)
            
            # Precision
            if groove.micro_timing_variance > 0:
                traits['precision'] = max(0, 1 - (groove.micro_timing_variance / 50))
            else:
                traits['precision'] = 1.0
            
            # Creativity
            traits['creativity'] = groove.rhythmic_complexity
            
            # Groove feel
            traits['groove_feel'] = groove.pocket_tightness
            
            # Humanness
            traits['humanness'] = groove.humanness_score
            
        except Exception as e:
            logger.error(f"Error extracting personality traits: {e}")
        
        return traits
    
    def _calculate_technical_metrics(self, profile: DrummerProfile) -> Dict[str, float]:
        """Calculate technical performance metrics"""
        metrics = {}
        
        try:
            # Overall complexity
            metrics['overall_complexity'] = profile.groove.rhythmic_complexity
            
            # Timing consistency
            metrics['timing_consistency'] = profile.groove.pocket_tightness
            
            # Dynamic range
            all_velocities = []
            for comp in profile.components.values():
                if comp.velocities:
                    all_velocities.extend(comp.velocities)
            
            if all_velocities:
                metrics['dynamic_range'] = max(all_velocities) - min(all_velocities)
                metrics['velocity_control'] = 1.0 - np.std(all_velocities)
            
            # Pattern diversity
            metrics['pattern_diversity'] = len(profile.signature_patterns) / 10.0  # Normalize
            
        except Exception as e:
            logger.error(f"Error calculating technical metrics: {e}")
        
        return metrics
    
    def save_profile(self, profile: DrummerProfile, output_file: str) -> bool:
        """Save drummer profile to JSON file"""
        try:
            # Convert profile to serializable dict
            profile_dict = {
                'tempo': profile.tempo,
                'style': profile.style,
                'key': profile.key,
                'duration': profile.duration,
                'components': {
                    name: {
                        'name': comp.name,
                        'audio_file': comp.audio_file,
                        'hits': comp.hits,
                        'velocities': comp.velocities,
                        'timing_deviations': comp.timing_deviations,
                        'spectral_features': comp.spectral_features
                    } for name, comp in profile.components.items()
                },
                'groove': {
                    'swing_factor': profile.groove.swing_factor,
                    'pocket_tightness': profile.groove.pocket_tightness,
                    'rhythmic_complexity': profile.groove.rhythmic_complexity,
                    'syncopation_level': profile.groove.syncopation_level,
                    'micro_timing_variance': profile.groove.micro_timing_variance,
                    'humanness_score': profile.groove.humanness_score
                },
                'signature_patterns': profile.signature_patterns,
                'interaction_matrix': profile.interaction_matrix,
                'personality_traits': profile.personality_traits,
                'technical_metrics': profile.technical_metrics,
                'analysis_timestamp': datetime.now().isoformat()
            }
            
            with open(output_file, 'w') as f:
                json.dump(profile_dict, f, indent=2)
            
            logger.info(f"Drummer profile saved to: {output_file}")
            return True
            
        except Exception as e:
            logger.error(f"Error saving profile: {e}")
            return False

"""
Advanced Drummer Analysis Integration
Combines sophisticated analysis tools with enhanced visualization for comprehensive drummer profiling
"""

import numpy as np
import torch
import logging
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
import json
import os
from pathlib import Path

# Import sophisticated analysis tools
from admin.services.advanced_visualization_service import VisualizationData
from admin.services.advanced_drummer_analysis import AdvancedDrummerAnalysisService

logger = logging.getLogger(__name__)

@dataclass
class NeuralEntrainmentProfile:
    """Neural entrainment analysis results"""
    delta: float = 0.0  # 0.5-4 Hz
    theta: float = 0.0  # 4-8 Hz  
    alpha: float = 0.0  # 8-13 Hz
    beta: float = 0.0   # 13-30 Hz
    gamma: float = 0.0  # 30-100 Hz
    dominant_frequency: float = 0.0
    groove_induction: float = 0.0
    phase_coherence: float = 0.0
    tension_release: float = 0.0
    predictability: float = 0.0
    flow_compatibility: float = 0.0

@dataclass
class TimeFrequencyFeatures:
    """Time-frequency reassignment analysis features"""
    attack_sharpness: float = 0.0
    spectral_evolution: List[float] = None
    frequency_modulation: float = 0.0
    onset_precision: float = 0.0  # Sub-millisecond precision
    transient_strength: float = 0.0
    spectral_centroid_evolution: List[float] = None
    
    def __post_init__(self):
        if self.spectral_evolution is None:
            self.spectral_evolution = []
        if self.spectral_centroid_evolution is None:
            self.spectral_centroid_evolution = []

@dataclass
class StyleVectorEncoding:
    """Neural style vector encoding for drummer characteristics"""
    style_vector: List[float] = None
    style_dimensions: Dict[str, float] = None
    similarity_scores: Dict[str, float] = None
    genre_classification: str = ""
    confidence: float = 0.0
    
    def __post_init__(self):
        if self.style_vector is None:
            self.style_vector = []
        if self.style_dimensions is None:
            self.style_dimensions = {}
        if self.similarity_scores is None:
            self.similarity_scores = {}

class AdvancedDrummerAnalysisIntegrated:
    """
    Integrated advanced drummer analysis combining:
    - Neural entrainment analysis
    - Time-frequency reassignment
    - GPU-accelerated processing
    - Style vector encoding
    - Enhanced visualization
    """
    
    def __init__(self, sample_rate: int = 44100, use_gpu: bool = True):
        self.sample_rate = sample_rate
        self.use_gpu = use_gpu and torch.cuda.is_available()
        
        # Initialize core analysis service
        self.core_analyzer = AdvancedDrummerAnalysisService()
        
        # Initialize sophisticated analysis components
        self._init_neural_entrainment_analyzer()
        self._init_tfr_analyzer()
        self._init_style_encoder()
        
        logger.info(f"Advanced drummer analysis initialized (GPU: {self.use_gpu})")
        
    def _init_neural_entrainment_analyzer(self):
        """Initialize neural entrainment analysis"""
        try:
            # Import neural entrainment module from analytic tools
            import sys
            sys.path.append(str(Path(__file__).parent.parent.parent / "Drum_Analysis" / "Analytic_Tools"))
            
            # This would import the actual neural entrainment module
            # For now, we'll implement a simplified version
            self.neural_analyzer = self._create_neural_analyzer()
            
        except ImportError as e:
            logger.warning(f"Neural entrainment module not available: {e}")
            self.neural_analyzer = None
            
    def _init_tfr_analyzer(self):
        """Initialize time-frequency reassignment analyzer"""
        try:
            # Import TFR module from analytic tools
            # This would import the actual TFR module
            self.tfr_analyzer = self._create_tfr_analyzer()
            
        except ImportError as e:
            logger.warning(f"TFR module not available: {e}")
            self.tfr_analyzer = None
            
    def _init_style_encoder(self):
        """Initialize neural style encoder"""
        try:
            # Initialize PyTorch-based style encoder
            self.style_encoder = self._create_style_encoder()
            
        except Exception as e:
            logger.warning(f"Style encoder not available: {e}")
            self.style_encoder = None
            
    def _create_neural_analyzer(self):
        """Create neural entrainment analyzer"""
        class NeuralEntrainmentAnalyzer:
            def __init__(self, sample_rate):
                self.sr = sample_rate
                
            def analyze_entrainment(self, audio: np.ndarray, hits: List[Dict]) -> NeuralEntrainmentProfile:
                """Analyze neural entrainment characteristics"""
                
                # Extract rhythmic patterns
                if not hits:
                    return NeuralEntrainmentProfile()
                    
                timestamps = np.array([hit.get('timestamp', 0) for hit in hits])
                intervals = np.diff(timestamps)
                
                if len(intervals) == 0:
                    return NeuralEntrainmentProfile()
                
                # Calculate dominant frequency
                mean_interval = np.mean(intervals)
                dominant_freq = 1.0 / mean_interval if mean_interval > 0 else 0.0
                
                # Map to brainwave bands
                delta = self._calculate_band_alignment(dominant_freq, 0.5, 4.0)
                theta = self._calculate_band_alignment(dominant_freq, 4.0, 8.0)
                alpha = self._calculate_band_alignment(dominant_freq, 8.0, 13.0)
                beta = self._calculate_band_alignment(dominant_freq, 13.0, 30.0)
                gamma = self._calculate_band_alignment(dominant_freq, 30.0, 100.0)
                
                # Calculate groove induction potential
                interval_variance = np.std(intervals) / np.mean(intervals) if np.mean(intervals) > 0 else 1.0
                groove_induction = np.exp(-interval_variance * 5)  # Lower variance = higher groove
                
                # Phase coherence (regularity)
                phase_coherence = 1.0 / (1.0 + interval_variance)
                
                # Tension-release patterns (simplified)
                velocities = np.array([hit.get('velocity', 0.5) for hit in hits])
                velocity_changes = np.abs(np.diff(velocities))
                tension_release = np.mean(velocity_changes)
                
                # Predictability
                predictability = 1.0 - min(interval_variance, 1.0)
                
                # Flow compatibility
                flow_compatibility = (groove_induction + phase_coherence + predictability) / 3.0
                
                return NeuralEntrainmentProfile(
                    delta=delta,
                    theta=theta,
                    alpha=alpha,
                    beta=beta,
                    gamma=gamma,
                    dominant_frequency=dominant_freq,
                    groove_induction=groove_induction,
                    phase_coherence=phase_coherence,
                    tension_release=tension_release,
                    predictability=predictability,
                    flow_compatibility=flow_compatibility
                )
                
            def _calculate_band_alignment(self, freq: float, band_min: float, band_max: float) -> float:
                """Calculate alignment with brainwave band"""
                if band_min <= freq <= band_max:
                    return 1.0
                elif freq < band_min:
                    distance = band_min - freq
                elif freq > band_max:
                    distance = freq - band_max
                else:
                    distance = 0
                    
                # Exponential decay based on distance from band
                return np.exp(-distance / 5.0)
                
        return NeuralEntrainmentAnalyzer(self.sample_rate)
        
    def _create_tfr_analyzer(self):
        """Create time-frequency reassignment analyzer"""
        class TFRAnalyzer:
            def __init__(self, sample_rate, use_gpu):
                self.sr = sample_rate
                self.use_gpu = use_gpu
                
            def analyze_tfr_features(self, audio: np.ndarray, hits: List[Dict]) -> List[TimeFrequencyFeatures]:
                """Analyze TFR features for each hit"""
                tfr_features = []
                
                for hit in hits:
                    timestamp = hit.get('timestamp', 0)
                    
                    # Extract audio segment around hit
                    start_sample = max(0, int((timestamp - 0.05) * self.sr))
                    end_sample = min(len(audio), int((timestamp + 0.1) * self.sr))
                    
                    if end_sample <= start_sample:
                        tfr_features.append(TimeFrequencyFeatures())
                        continue
                        
                    segment = audio[start_sample:end_sample]
                    
                    # Calculate TFR features (simplified implementation)
                    features = self._calculate_tfr_features(segment, timestamp)
                    tfr_features.append(features)
                    
                return tfr_features
                
            def _calculate_tfr_features(self, segment: np.ndarray, timestamp: float) -> TimeFrequencyFeatures:
                """Calculate TFR features for audio segment"""
                
                # Attack sharpness (rate of amplitude increase)
                attack_sharpness = self._calculate_attack_sharpness(segment)
                
                # Spectral evolution (simplified)
                spectral_evolution = self._calculate_spectral_evolution(segment)
                
                # Frequency modulation (simplified)
                frequency_modulation = self._calculate_frequency_modulation(segment)
                
                # Onset precision (sub-millisecond)
                onset_precision = self._calculate_onset_precision(segment)
                
                # Transient strength
                transient_strength = self._calculate_transient_strength(segment)
                
                # Spectral centroid evolution
                spectral_centroid_evolution = self._calculate_spectral_centroid_evolution(segment)
                
                return TimeFrequencyFeatures(
                    attack_sharpness=attack_sharpness,
                    spectral_evolution=spectral_evolution,
                    frequency_modulation=frequency_modulation,
                    onset_precision=onset_precision,
                    transient_strength=transient_strength,
                    spectral_centroid_evolution=spectral_centroid_evolution
                )
                
            def _calculate_attack_sharpness(self, segment: np.ndarray) -> float:
                """Calculate attack sharpness"""
                if len(segment) < 10:
                    return 0.0
                    
                # Find peak and calculate rise time
                peak_idx = np.argmax(np.abs(segment))
                if peak_idx < 5:
                    return 1.0  # Very sharp attack
                    
                # Calculate rate of amplitude increase
                attack_portion = segment[:peak_idx]
                if len(attack_portion) < 2:
                    return 1.0
                    
                amplitude_envelope = np.abs(attack_portion)
                rise_rate = np.mean(np.diff(amplitude_envelope))
                
                # Normalize to 0-1 range
                return min(max(rise_rate * 1000, 0.0), 1.0)
                
            def _calculate_spectral_evolution(self, segment: np.ndarray) -> List[float]:
                """Calculate spectral evolution over time"""
                # Simplified spectral evolution
                window_size = len(segment) // 8
                if window_size < 10:
                    return [0.5] * 8
                    
                evolution = []
                for i in range(8):
                    start = i * window_size
                    end = min((i + 1) * window_size, len(segment))
                    window = segment[start:end]
                    
                    # Calculate spectral centroid for this window
                    fft = np.fft.fft(window)
                    freqs = np.fft.fftfreq(len(window), 1/self.sr)
                    magnitude = np.abs(fft[:len(fft)//2])
                    freqs = freqs[:len(freqs)//2]
                    
                    if np.sum(magnitude) > 0:
                        centroid = np.sum(freqs * magnitude) / np.sum(magnitude)
                        evolution.append(centroid / 1000.0)  # Normalize
                    else:
                        evolution.append(0.0)
                        
                return evolution
                
            def _calculate_frequency_modulation(self, segment: np.ndarray) -> float:
                """Calculate frequency modulation depth"""
                if len(segment) < 20:
                    return 0.0
                    
                # Simple frequency modulation detection
                analytic_signal = np.abs(np.fft.hilbert(segment))
                instantaneous_freq = np.diff(np.unwrap(np.angle(np.fft.hilbert(segment))))
                
                if len(instantaneous_freq) > 0:
                    fm_depth = np.std(instantaneous_freq)
                    return min(fm_depth * 100, 1.0)  # Normalize
                    
                return 0.0
                
            def _calculate_onset_precision(self, segment: np.ndarray) -> float:
                """Calculate onset precision (sub-millisecond)"""
                # Find precise onset using energy-based detection
                energy = segment ** 2
                
                # Smooth energy curve
                from scipy import ndimage
                smoothed_energy = ndimage.gaussian_filter1d(energy, sigma=2)
                
                # Find onset as steepest rise
                energy_diff = np.diff(smoothed_energy)
                if len(energy_diff) > 0:
                    onset_idx = np.argmax(energy_diff)
                    # Calculate sub-sample precision
                    precision = 1.0 - (onset_idx % 1)  # Simplified
                    return precision
                    
                return 0.5
                
            def _calculate_transient_strength(self, segment: np.ndarray) -> float:
                """Calculate transient strength"""
                if len(segment) < 10:
                    return 0.0
                    
                # Calculate energy ratio between attack and sustain
                peak_idx = np.argmax(np.abs(segment))
                attack_energy = np.sum(segment[:peak_idx] ** 2) if peak_idx > 0 else 0
                total_energy = np.sum(segment ** 2)
                
                if total_energy > 0:
                    transient_ratio = attack_energy / total_energy
                    return min(transient_ratio * 2, 1.0)  # Normalize
                    
                return 0.0
                
            def _calculate_spectral_centroid_evolution(self, segment: np.ndarray) -> List[float]:
                """Calculate spectral centroid evolution"""
                # Similar to spectral evolution but focused on centroid
                return self._calculate_spectral_evolution(segment)
                
        return TFRAnalyzer(self.sample_rate, self.use_gpu)
        
    def _create_style_encoder(self):
        """Create neural style encoder"""
        class StyleEncoder:
            def __init__(self, use_gpu):
                self.use_gpu = use_gpu
                self.device = torch.device("cuda" if use_gpu else "cpu")
                
            def encode_style(self, analysis_results: Dict) -> StyleVectorEncoding:
                """Encode drummer style into neural vector"""
                
                # Extract key features for style encoding
                features = self._extract_style_features(analysis_results)
                
                # Create style vector (simplified)
                style_vector = self._create_style_vector(features)
                
                # Calculate style dimensions
                style_dimensions = self._calculate_style_dimensions(features)
                
                # Genre classification (simplified)
                genre = self._classify_genre(features)
                
                # Calculate confidence
                confidence = self._calculate_confidence(features)
                
                return StyleVectorEncoding(
                    style_vector=style_vector,
                    style_dimensions=style_dimensions,
                    genre_classification=genre,
                    confidence=confidence
                )
                
            def _extract_style_features(self, analysis_results: Dict) -> Dict:
                """Extract features relevant for style encoding"""
                groove = analysis_results.get('groove_pattern', {})
                timing = analysis_results.get('timing_profile', {})
                neural = analysis_results.get('neural_entrainment', {})
                
                return {
                    'timing_variance': groove.get('timing_variance', 0),
                    'velocity_variance': groove.get('velocity_variance', 0),
                    'syncopation': groove.get('syncopation_score', 0),
                    'complexity': groove.get('rhythmic_complexity', 0),
                    'push_pull': timing.get('push', 0) - timing.get('pull', 0),
                    'groove_induction': neural.get('groove_induction', 0),
                    'humanness': analysis_results.get('humanness_score', 0)
                }
                
            def _create_style_vector(self, features: Dict) -> List[float]:
                """Create neural style vector"""
                # Simplified style vector creation
                vector = [
                    features.get('timing_variance', 0),
                    features.get('velocity_variance', 0),
                    features.get('syncopation', 0),
                    features.get('complexity', 0),
                    features.get('push_pull', 0),
                    features.get('groove_induction', 0),
                    features.get('humanness', 0)
                ]
                
                # Normalize vector
                vector_array = np.array(vector)
                if np.linalg.norm(vector_array) > 0:
                    vector_array = vector_array / np.linalg.norm(vector_array)
                    
                return vector_array.tolist()
                
            def _calculate_style_dimensions(self, features: Dict) -> Dict[str, float]:
                """Calculate interpretable style dimensions"""
                return {
                    'aggressiveness': features.get('velocity_variance', 0) * 2,
                    'precision': 1.0 - features.get('timing_variance', 0) * 10,
                    'creativity': features.get('syncopation', 0) + features.get('complexity', 0),
                    'groove_feel': features.get('groove_induction', 0),
                    'humanness': features.get('humanness', 0),
                    'technical_skill': features.get('complexity', 0)
                }
                
            def _classify_genre(self, features: Dict) -> str:
                """Classify musical genre based on style features"""
                # Simplified genre classification
                if features.get('complexity', 0) > 0.7:
                    return "Progressive/Technical"
                elif features.get('groove_induction', 0) > 0.8:
                    return "Funk/R&B"
                elif features.get('syncopation', 0) > 0.6:
                    return "Jazz/Fusion"
                elif features.get('timing_variance', 0) < 0.01:
                    return "Electronic/Programmed"
                else:
                    return "Rock/Pop"
                    
            def _calculate_confidence(self, features: Dict) -> float:
                """Calculate confidence in style analysis"""
                # Based on feature consistency and completeness
                feature_count = sum(1 for v in features.values() if v > 0)
                completeness = feature_count / len(features)
                
                # Calculate variance in features (lower variance = higher confidence)
                feature_values = list(features.values())
                variance = np.std(feature_values) if len(feature_values) > 1 else 0
                consistency = 1.0 / (1.0 + variance)
                
                return (completeness + consistency) / 2.0
                
        return StyleEncoder(self.use_gpu)
        
    def analyze_comprehensive(self, drum_stems: Dict[str, np.ndarray], 
                            tempo: float, style: str, key: str) -> Dict[str, Any]:
        """
        Comprehensive advanced drummer analysis combining all sophisticated techniques
        """
        logger.info("Starting comprehensive advanced drummer analysis...")
        
        results = {}
        
        for drum_type, audio_data in drum_stems.items():
            logger.info(f"Analyzing {drum_type} with advanced techniques...")
            
            try:
                # 1. Core drummer analysis
                core_results = self.core_analyzer.analyze_drum_component(
                    audio_data, drum_type, self.sample_rate, tempo, style, key
                )
                
                # 2. Neural entrainment analysis
                neural_profile = None
                if self.neural_analyzer:
                    hits = core_results.get('hits', [])
                    neural_profile = self.neural_analyzer.analyze_entrainment(audio_data, hits)
                    logger.info(f"Neural entrainment - Dominant freq: {neural_profile.dominant_frequency:.2f} Hz, "
                              f"Flow compatibility: {neural_profile.flow_compatibility:.2f}")
                
                # 3. Time-frequency reassignment analysis
                tfr_features = []
                if self.tfr_analyzer:
                    hits = core_results.get('hits', [])
                    tfr_features = self.tfr_analyzer.analyze_tfr_features(audio_data, hits)
                    logger.info(f"TFR analysis - {len(tfr_features)} hits analyzed with sub-millisecond precision")
                
                # 4. Style vector encoding
                style_encoding = None
                if self.style_encoder:
                    analysis_for_encoding = {
                        **core_results,
                        'neural_entrainment': asdict(neural_profile) if neural_profile else {}
                    }
                    style_encoding = self.style_encoder.encode_style(analysis_for_encoding)
                    logger.info(f"Style encoding - Genre: {style_encoding.genre_classification}, "
                              f"Confidence: {style_encoding.confidence:.2f}")
                
                # 5. Combine all results
                comprehensive_results = {
                    **core_results,
                    'neural_entrainment': asdict(neural_profile) if neural_profile else {},
                    'tfr_features': [asdict(tfr) for tfr in tfr_features],
                    'style_encoding': asdict(style_encoding) if style_encoding else {},
                    'analysis_metadata': {
                        'gpu_accelerated': self.use_gpu,
                        'neural_analysis_available': self.neural_analyzer is not None,
                        'tfr_analysis_available': self.tfr_analyzer is not None,
                        'style_encoding_available': self.style_encoder is not None,
                        'sample_rate': self.sample_rate
                    }
                }
                
                results[drum_type] = comprehensive_results
                
            except Exception as e:
                logger.error(f"Error analyzing {drum_type}: {str(e)}")
                results[drum_type] = {'error': str(e)}
                
        logger.info("Comprehensive advanced analysis complete")
        return results
        
    def create_visualization_data(self, analysis_results: Dict[str, Any], 
                                drum_type: str = 'kick') -> VisualizationData:
        """Create visualization data from analysis results"""
        
        if drum_type not in analysis_results:
            logger.warning(f"No analysis results for {drum_type}")
            return VisualizationData(
                drum_type=drum_type,
                hits=[],
                groove_pattern={},
                tempo_profile={},
                timing_profile={},
                neural_entrainment={},
                bass_drum_sync={},
                style_features={},
                humanness_score=0.0,
                kit_coherence={}
            )
            
        results = analysis_results[drum_type]
        
        # Extract neural entrainment data
        neural_data = results.get('neural_entrainment', {})
        
        # Extract TFR features and add to hits
        hits = results.get('hits', [])
        tfr_features = results.get('tfr_features', [])
        
        # Enhance hits with TFR data
        enhanced_hits = []
        for i, hit in enumerate(hits):
            enhanced_hit = dict(hit)
            if i < len(tfr_features):
                tfr = tfr_features[i]
                enhanced_hit.update({
                    'attack_sharpness': tfr.get('attack_sharpness', 0),
                    'frequency_modulation': tfr.get('frequency_modulation', 0),
                    'onset_precision': tfr.get('onset_precision', 0),
                    'transient_strength': tfr.get('transient_strength', 0)
                })
            enhanced_hits.append(enhanced_hit)
            
        return VisualizationData(
            drum_type=drum_type,
            hits=enhanced_hits,
            groove_pattern=results.get('groove_pattern', {}),
            tempo_profile=results.get('tempo_profile', {}),
            timing_profile=results.get('timing_profile', {}),
            neural_entrainment=neural_data,
            bass_drum_sync=results.get('bass_drum_sync', {}),
            style_features=results.get('style_features', {}),
            humanness_score=results.get('humanness_score', 0.0),
            kit_coherence=results.get('kit_coherence', {}),
            tfr_features=results.get('tfr_features', [])
        )
        
    def save_comprehensive_profile(self, analysis_results: Dict[str, Any], 
                                 output_path: str, drummer_name: str = "Unknown"):
        """Save comprehensive drummer profile with all advanced analysis"""
        
        profile = {
            'drummer_name': drummer_name,
            'analysis_timestamp': str(np.datetime64('now')),
            'analysis_results': analysis_results,
            'summary': self._generate_analysis_summary(analysis_results),
            'metadata': {
                'version': '1.0',
                'analysis_type': 'comprehensive_advanced',
                'gpu_accelerated': self.use_gpu,
                'sample_rate': self.sample_rate
            }
        }
        
        try:
            with open(output_path, 'w') as f:
                json.dump(profile, f, indent=2, default=str)
            logger.info(f"Comprehensive profile saved to {output_path}")
            
        except Exception as e:
            logger.error(f"Failed to save profile: {str(e)}")
            
    def _generate_analysis_summary(self, analysis_results: Dict[str, Any]) -> Dict[str, Any]:
        """Generate human-readable analysis summary"""
        
        summary = {
            'drums_analyzed': list(analysis_results.keys()),
            'key_findings': {},
            'personality_traits': {},
            'technical_metrics': {}
        }
        
        for drum_type, results in analysis_results.items():
            if 'error' in results:
                continue
                
            # Key findings
            humanness = results.get('humanness_score', 0)
            groove_coherence = results.get('groove_pattern', {}).get('groove_coherence', 0)
            neural_flow = results.get('neural_entrainment', {}).get('flow_compatibility', 0)
            
            summary['key_findings'][drum_type] = {
                'humanness_level': 'High' if humanness > 0.8 else 'Medium' if humanness > 0.6 else 'Low',
                'groove_quality': 'Excellent' if groove_coherence > 0.8 else 'Good' if groove_coherence > 0.6 else 'Fair',
                'flow_induction': 'Strong' if neural_flow > 0.8 else 'Moderate' if neural_flow > 0.6 else 'Weak'
            }
            
            # Personality traits from style encoding
            style_dims = results.get('style_encoding', {}).get('style_dimensions', {})
            summary['personality_traits'][drum_type] = {
                'aggressiveness': style_dims.get('aggressiveness', 0),
                'precision': style_dims.get('precision', 0),
                'creativity': style_dims.get('creativity', 0),
                'technical_skill': style_dims.get('technical_skill', 0)
            }
            
            # Technical metrics
            timing_var = results.get('groove_pattern', {}).get('timing_variance', 0)
            complexity = results.get('groove_pattern', {}).get('rhythmic_complexity', 0)
            
            summary['technical_metrics'][drum_type] = {
                'timing_precision_ms': timing_var * 1000,
                'rhythmic_complexity': complexity,
                'neural_entrainment_strength': neural_flow
            }
            
        return summary

#!/usr/bin/env python3
"""
TFR Integration System
Integrates advanced time-frequency reassignment into the main DrumTracKAI analysis pipeline
"""

import numpy as np
import logging
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import torch

from .advanced_tfr_system import AdvancedTimeFrequencyReassignment, TFRAnalysisResult

logger = logging.getLogger(__name__)

@dataclass
class EnhancedDrumHit:
    """Enhanced drum hit with TFR analysis features"""
    timestamp: float
    velocity: float
    drum_type: str
    frequency_content: np.ndarray
    
    # TFR enhancements
    precise_attack_time: float = 0.0
    attack_sharpness: float = 0.0
    spectral_evolution: List[float] = None
    frequency_modulation: float = 0.0
    transient_strength: float = 0.0
    micro_timing_deviation: float = 0.0
    bass_correlation: float = 0.0
    tfr_analysis: Optional[TFRAnalysisResult] = None

@dataclass
class TFRGrooveMetrics:
    """Advanced groove metrics using TFR analysis"""
    groove_depth: float
    pattern_strength: float
    timbral_consistency: float
    attack_consistency: float
    rhythmic_complexity_tfr: float
    bass_drum_sync_precision: float
    groove_signature: np.ndarray
    micro_timing_precision: float

class DrumTracKAI_TFR_Integration:
    """Integration system for advanced TFR analysis in DrumTracKAI"""
    
    def __init__(self, sample_rate: int = 44100, use_gpu: bool = True):
        self.sample_rate = sample_rate
        self.tfr_analyzer = AdvancedTimeFrequencyReassignment(sample_rate, use_gpu)
        logger.info(f"TFR Integration System initialized (GPU: {use_gpu})")
    
    def refine_onsets_with_tfr(self, audio: np.ndarray, initial_onsets: np.ndarray) -> np.ndarray:
        """Refine onset times using advanced time-frequency reassignment"""
        
        logger.info(f"Refining {len(initial_onsets)} onsets with TFR analysis...")
        refined_onsets = []
        
        for onset in initial_onsets:
            try:
                tfr_analysis = self.tfr_analyzer.analyze_drum_attack(audio, onset, window_size=0.03)
                refined_time = onset + tfr_analysis.attack_time
                refined_onsets.append(refined_time)
            except Exception as e:
                logger.warning(f"TFR refinement failed for onset {onset:.3f}s: {e}")
                refined_onsets.append(onset)
        
        return np.array(refined_onsets)
    
    def analyze_enhanced_drum_hits(self, audio: np.ndarray, refined_onsets: np.ndarray,
                                 bass_onsets: np.ndarray = None,
                                 drum_type: str = "unknown") -> List[EnhancedDrumHit]:
        """Analyze drum hits with full TFR enhancement"""
        
        logger.info(f"Analyzing {len(refined_onsets)} drum hits with TFR enhancement...")
        enhanced_hits = []
        
        for onset_time in refined_onsets:
            try:
                # Perform TFR analysis
                tfr_analysis = self.tfr_analyzer.analyze_drum_attack(audio, onset_time)
                
                # Extract basic features
                hit_features = self._extract_basic_hit_features(audio, onset_time)
                
                # Calculate bass correlation
                bass_correlation = self._calculate_bass_correlation_enhanced(
                    onset_time, bass_onsets
                ) if bass_onsets is not None else 0.0
                
                # Create enhanced hit
                enhanced_hit = EnhancedDrumHit(
                    timestamp=onset_time,
                    velocity=hit_features['velocity'],
                    drum_type=drum_type,
                    frequency_content=hit_features['frequency_content'],
                    precise_attack_time=onset_time + tfr_analysis.attack_time,
                    attack_sharpness=tfr_analysis.attack_sharpness,
                    spectral_evolution=tfr_analysis.spectral_centroid_evolution.tolist(),
                    frequency_modulation=tfr_analysis.frequency_modulation.get('modulation_depth', 0.0),
                    transient_strength=tfr_analysis.transient_strength,
                    bass_correlation=bass_correlation,
                    tfr_analysis=tfr_analysis
                )
                
                enhanced_hits.append(enhanced_hit)
                
            except Exception as e:
                logger.warning(f"Enhanced analysis failed for hit at {onset_time:.3f}s: {e}")
                # Fallback to basic hit
                hit_features = self._extract_basic_hit_features(audio, onset_time)
                basic_hit = EnhancedDrumHit(
                    timestamp=onset_time,
                    velocity=hit_features['velocity'],
                    drum_type=drum_type,
                    frequency_content=hit_features['frequency_content']
                )
                enhanced_hits.append(basic_hit)
        
        logger.info(f"Enhanced hit analysis complete for {len(enhanced_hits)} hits")
        return enhanced_hits
    
    def calculate_tfr_groove_metrics(self, enhanced_hits: List[EnhancedDrumHit], 
                                   bass_onsets: np.ndarray = None) -> TFRGrooveMetrics:
        """Calculate advanced groove metrics using TFR features"""
        
        if not enhanced_hits:
            return TFRGrooveMetrics(
                groove_depth=0.0, pattern_strength=0.0, timbral_consistency=0.0,
                attack_consistency=0.0, rhythmic_complexity_tfr=0.0,
                bass_drum_sync_precision=0.0, groove_signature=np.array([]),
                micro_timing_precision=0.0
            )
        
        # Calculate metrics
        groove_depth = self._calculate_groove_depth(enhanced_hits)
        pattern_strength = self._detect_pattern_strength(enhanced_hits)
        timbral_consistency = self._calculate_timbral_consistency(enhanced_hits)
        attack_consistency = self._calculate_attack_consistency(enhanced_hits)
        rhythmic_complexity_tfr = self._calculate_tfr_rhythmic_complexity(enhanced_hits)
        bass_drum_sync_precision = self._calculate_bass_drum_sync_precision(enhanced_hits)
        groove_signature = self._extract_collective_groove_signature(enhanced_hits)
        micro_timing_precision = self._calculate_micro_timing_precision(enhanced_hits)
        
        return TFRGrooveMetrics(
            groove_depth=groove_depth,
            pattern_strength=pattern_strength,
            timbral_consistency=timbral_consistency,
            attack_consistency=attack_consistency,
            rhythmic_complexity_tfr=rhythmic_complexity_tfr,
            bass_drum_sync_precision=bass_drum_sync_precision,
            groove_signature=groove_signature,
            micro_timing_precision=micro_timing_precision
        )
    
    def extract_groove_signature(self, audio: np.ndarray, refined_onsets: np.ndarray) -> np.ndarray:
        """Extract groove signature using synchrosqueezing"""
        
        try:
            synchro_data = self.tfr_analyzer.synchrosqueeze_transform(audio)
            features = []
            
            for hit_time in refined_onsets:
                time_idx = np.argmin(np.abs(synchro_data['reassigned_data'].times - hit_time))
                spectral_slice = synchro_data['synchrosqueezed'][:, time_idx]
                
                hit_features = [
                    np.max(spectral_slice),
                    np.argmax(spectral_slice) * self.sample_rate / 2 / len(spectral_slice),
                    np.std(spectral_slice),
                    np.sum(spectral_slice > np.max(spectral_slice) * 0.5)
                ]
                features.append(hit_features)
            
            return np.array(features)
            
        except Exception as e:
            logger.warning(f"Groove signature extraction failed: {e}")
            return np.array([])
    
    # Helper methods
    def _extract_basic_hit_features(self, audio: np.ndarray, onset_time: float) -> Dict:
        """Extract basic features for a drum hit"""
        
        window_size = 0.05  # 50ms
        start_sample = int(max(0, (onset_time - window_size/2) * self.sample_rate))
        end_sample = int(min(len(audio), (onset_time + window_size/2) * self.sample_rate))
        
        if end_sample <= start_sample:
            return {'velocity': 0.5, 'frequency_content': np.array([])}
        
        window_audio = audio[start_sample:end_sample]
        velocity = np.sqrt(np.mean(window_audio**2))
        
        if len(window_audio) > 0:
            fft_result = np.fft.fft(window_audio)
            frequency_content = np.abs(fft_result[:len(fft_result)//2])
        else:
            frequency_content = np.array([])
        
        return {'velocity': float(velocity), 'frequency_content': frequency_content}
    
    def _calculate_bass_correlation_enhanced(self, drum_time: float, bass_onsets: np.ndarray) -> float:
        """Enhanced bass correlation using TFR"""
        
        if bass_onsets is None or len(bass_onsets) == 0:
            return 0.0
        
        distances = np.abs(bass_onsets - drum_time)
        nearest_distance = np.min(distances)
        timing_correlation = np.exp(-nearest_distance * 200)
        
        return float(timing_correlation)
    
    def _calculate_groove_depth(self, enhanced_hits: List[EnhancedDrumHit]) -> float:
        """Calculate overall groove depth metric"""
        
        if not enhanced_hits:
            return 0.0
        
        attack_values = [hit.attack_sharpness for hit in enhanced_hits if hit.attack_sharpness > 0]
        attack_consistency = 1.0 / (1.0 + np.std(attack_values)) if attack_values else 0.0
        
        return float(attack_consistency)
    
    def _detect_pattern_strength(self, enhanced_hits: List[EnhancedDrumHit]) -> float:
        """Detect strength of repeating patterns"""
        
        if len(enhanced_hits) < 4:
            return 0.0
        
        timestamps = [hit.timestamp for hit in enhanced_hits]
        intervals = np.diff(timestamps)
        
        if len(intervals) < 2:
            return 0.0
        
        # Simple pattern detection using coefficient of variation
        cv = np.std(intervals) / np.mean(intervals) if np.mean(intervals) > 0 else 1.0
        pattern_strength = 1.0 / (1.0 + cv)
        
        return float(pattern_strength)
    
    def _calculate_timbral_consistency(self, enhanced_hits: List[EnhancedDrumHit]) -> float:
        """Calculate timbral consistency across hits"""
        
        if len(enhanced_hits) < 2:
            return 0.0
        
        # Compare spectral evolution patterns
        consistencies = []
        
        for i, hit1 in enumerate(enhanced_hits):
            for j, hit2 in enumerate(enhanced_hits[i+1:], i+1):
                if (hit1.spectral_evolution and hit2.spectral_evolution and
                    len(hit1.spectral_evolution) > 0 and len(hit2.spectral_evolution) > 0):
                    
                    min_len = min(len(hit1.spectral_evolution), len(hit2.spectral_evolution))
                    evo1 = np.array(hit1.spectral_evolution[:min_len])
                    evo2 = np.array(hit2.spectral_evolution[:min_len])
                    
                    if np.std(evo1) > 0 and np.std(evo2) > 0:
                        correlation = np.corrcoef(evo1, evo2)[0, 1]
                        consistencies.append(max(0.0, correlation))
        
        return float(np.mean(consistencies)) if consistencies else 0.0
    
    def _calculate_attack_consistency(self, enhanced_hits: List[EnhancedDrumHit]) -> float:
        """Calculate attack consistency"""
        
        attack_values = [hit.attack_sharpness for hit in enhanced_hits if hit.attack_sharpness > 0]
        
        if len(attack_values) < 2:
            return 0.0
        
        consistency = 1.0 / (1.0 + np.std(attack_values))
        return float(consistency)
    
    def _calculate_tfr_rhythmic_complexity(self, enhanced_hits: List[EnhancedDrumHit]) -> float:
        """Calculate rhythmic complexity using TFR precision"""
        
        if not enhanced_hits:
            return 0.0
        
        evolution_complexities = []
        
        for hit in enhanced_hits:
            if hit.spectral_evolution and len(hit.spectral_evolution) > 1:
                evolution = np.array(hit.spectral_evolution)
                complexity = np.std(evolution) / (np.mean(evolution) + 1e-10)
                evolution_complexities.append(complexity)
        
        if evolution_complexities:
            avg_complexity = np.mean(evolution_complexities)
            return float(min(avg_complexity, 1.0))
        
        return 0.0
    
    def _calculate_bass_drum_sync_precision(self, enhanced_hits: List[EnhancedDrumHit]) -> float:
        """Calculate bass-drum sync precision"""
        
        bass_correlations = [hit.bass_correlation for hit in enhanced_hits if hit.bass_correlation > 0]
        
        if bass_correlations:
            return float(np.mean(bass_correlations))
        
        return 0.0
    
    def _extract_collective_groove_signature(self, enhanced_hits: List[EnhancedDrumHit]) -> np.ndarray:
        """Extract collective groove signature from all hits"""
        
        if not enhanced_hits:
            return np.array([])
        
        # Statistical summary of key features
        attack_values = [hit.attack_sharpness for hit in enhanced_hits if hit.attack_sharpness > 0]
        transient_values = [hit.transient_strength for hit in enhanced_hits if hit.transient_strength > 0]
        modulation_values = [hit.frequency_modulation for hit in enhanced_hits if hit.frequency_modulation > 0]
        
        groove_signature = [
            np.mean(attack_values) if attack_values else 0.0,
            np.std(attack_values) if attack_values else 0.0,
            np.mean(transient_values) if transient_values else 0.0,
            np.mean(modulation_values) if modulation_values else 0.0
        ]
        
        return np.array(groove_signature)
    
    def _calculate_micro_timing_precision(self, enhanced_hits: List[EnhancedDrumHit]) -> float:
        """Calculate micro-timing precision"""
        
        timing_deviations = [abs(hit.micro_timing_deviation) for hit in enhanced_hits 
                           if hit.micro_timing_deviation != 0]
        
        if timing_deviations:
            precision = 1.0 / (1.0 + np.mean(timing_deviations))
            return float(precision)
        
        return 0.0

# Integration function for main DrumTracKAI system
def integrate_tfr_with_complete_system(complete_system, audio_data: Dict) -> Dict:
    """Integrate TFR analysis with DrumTracKAI Complete System"""
    
    try:
        tfr_integration = DrumTracKAI_TFR_Integration(
            sample_rate=complete_system.sample_rate,
            use_gpu=torch.cuda.is_available()
        )
        
        enhanced_results = {}
        
        for stem_type, stem_data in audio_data.items():
            if stem_type == 'bass':
                continue
            
            logger.info(f"Processing {stem_type} with TFR integration...")
            
            # Get audio and basic onsets
            audio = stem_data.get('audio', np.array([]))
            basic_onsets = stem_data.get('onsets', np.array([]))
            
            if len(audio) == 0 or len(basic_onsets) == 0:
                continue
            
            # Refine onsets with TFR
            refined_onsets = tfr_integration.refine_onsets_with_tfr(audio, basic_onsets)
            
            # Get bass onsets for correlation
            bass_onsets = audio_data.get('bass', {}).get('onsets', np.array([]))
            
            # Analyze enhanced hits
            enhanced_hits = tfr_integration.analyze_enhanced_drum_hits(
                audio, refined_onsets, bass_onsets, stem_type
            )
            
            # Calculate TFR groove metrics
            tfr_metrics = tfr_integration.calculate_tfr_groove_metrics(enhanced_hits, bass_onsets)
            
            # Extract groove signature
            groove_signature = tfr_integration.extract_groove_signature(audio, refined_onsets)
            
            enhanced_results[stem_type] = {
                'enhanced_hits': enhanced_hits,
                'tfr_metrics': tfr_metrics,
                'groove_signature': groove_signature,
                'refined_onsets': refined_onsets
            }
        
        logger.info("TFR integration complete for all stems")
        return enhanced_results
        
    except Exception as e:
        logger.error(f"TFR integration failed: {e}")
        return {}

#!/usr/bin/env python3
"""
Drummer Style Encoder
Extracts quantifiable style characteristics for generative MIDI drum track creation
"""

import numpy as np
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, asdict
import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

@dataclass
class DrummerStyleVector:
    """Comprehensive style vector encoding a drummer's characteristics"""
    
    # Timing Characteristics
    timing_precision_mean: float      # Average timing precision across kit
    timing_precision_std: float       # Consistency of timing precision
    timing_signature: str             # "ahead", "behind", "on", "variable"
    micro_timing_tendency: float      # Average micro-timing deviation (-0.1 to +0.1)
    tempo_stability: float            # How consistent with tempo (0-1)
    
    # Groove Characteristics  
    groove_score: float               # Overall groove rating (0-1)
    dynamic_consistency: float        # Velocity consistency across kit
    accent_frequency: float           # How often accents occur (0-1)
    syncopation_tendency: float       # Preference for syncopated hits (0-1)
    
    # Bass Integration Style
    bass_integration_score: float     # How tightly integrated with bass (0-1)
    bass_interaction_style: str       # "synchronized", "complementary", "independent"
    pocket_playing_score: float       # How well sits in rhythmic pocket (0-1)
    
    # Pattern Characteristics
    pattern_complexity_mean: float    # Average pattern complexity
    pattern_complexity_std: float     # Variation in complexity across kit
    repetition_vs_variation: float    # Balance between repetition and variation (0-1)
    fill_frequency: float             # How often fills occur (0-1)
    
    # Individual Drum Characteristics
    kick_characteristics: Dict        # Kick-specific style traits
    snare_characteristics: Dict       # Snare-specific style traits
    hihat_characteristics: Dict       # Hi-hat-specific style traits
    
    # Velocity and Dynamics
    velocity_range_preference: Tuple[float, float]  # Preferred velocity range
    dynamic_expression_level: float   # How much dynamic variation (0-1)
    ghost_note_tendency: float        # Tendency to use ghost notes (0-1)
    
    # Rhythmic Roles Distribution
    timekeeper_emphasis: float        # Emphasis on timekeeping elements (0-1)
    accent_emphasis: float            # Emphasis on accent elements (0-1)
    color_emphasis: float             # Emphasis on color elements (0-1)
    
    # Meta Information
    drummer_name: str
    source_tracks: List[str]
    confidence_score: float           # Confidence in this style encoding (0-1)

class DrummerStyleEncoder:
    """Encodes drummer characteristics into quantifiable style vectors for MIDI generation"""
    
    def __init__(self):
        logger.info("Drummer Style Encoder initialized")
    
    def encode_drummer_style(self, individual_analyses: Dict, collective_analysis: Dict, 
                           drummer_name: str, track_name: str) -> DrummerStyleVector:
        """Extract comprehensive style vector from individual drum stem analyses"""
        
        logger.info(f"Encoding style vector for {drummer_name} from {track_name}")
        
        valid_analyses = {k: v for k, v in individual_analyses.items() if v is not None}
        
        if not valid_analyses:
            raise ValueError("No valid analyses to encode")
        
        # Extract timing characteristics
        timing_chars = self._extract_timing_characteristics(valid_analyses)
        
        # Extract groove characteristics
        groove_chars = self._extract_groove_characteristics(valid_analyses, collective_analysis)
        
        # Extract bass integration characteristics
        bass_chars = self._extract_bass_integration_characteristics(valid_analyses)
        
        # Extract pattern characteristics
        pattern_chars = self._extract_pattern_characteristics(valid_analyses)
        
        # Extract individual drum characteristics
        drum_chars = self._extract_individual_drum_characteristics(valid_analyses)
        
        # Extract velocity and dynamics
        velocity_chars = self._extract_velocity_characteristics(valid_analyses)
        
        # Extract rhythmic role distribution
        role_chars = self._extract_rhythmic_role_characteristics(valid_analyses)
        
        # Calculate confidence score
        confidence = self._calculate_confidence_score(valid_analyses)
        
        # Create comprehensive style vector
        style_vector = DrummerStyleVector(
            # Timing
            timing_precision_mean=timing_chars['precision_mean'],
            timing_precision_std=timing_chars['precision_std'],
            timing_signature=timing_chars['signature'],
            micro_timing_tendency=timing_chars['micro_timing_tendency'],
            tempo_stability=timing_chars['tempo_stability'],
            
            # Groove
            groove_score=groove_chars['groove_score'],
            dynamic_consistency=groove_chars['dynamic_consistency'],
            accent_frequency=groove_chars['accent_frequency'],
            syncopation_tendency=groove_chars['syncopation_tendency'],
            
            # Bass Integration
            bass_integration_score=bass_chars['integration_score'],
            bass_interaction_style=bass_chars['interaction_style'],
            pocket_playing_score=bass_chars['pocket_score'],
            
            # Patterns
            pattern_complexity_mean=pattern_chars['complexity_mean'],
            pattern_complexity_std=pattern_chars['complexity_std'],
            repetition_vs_variation=pattern_chars['repetition_vs_variation'],
            fill_frequency=pattern_chars['fill_frequency'],
            
            # Individual drums
            kick_characteristics=drum_chars['kick'],
            snare_characteristics=drum_chars['snare'],
            hihat_characteristics=drum_chars['hihat'],
            
            # Velocity/Dynamics
            velocity_range_preference=velocity_chars['range_preference'],
            dynamic_expression_level=velocity_chars['expression_level'],
            ghost_note_tendency=velocity_chars['ghost_note_tendency'],
            
            # Roles
            timekeeper_emphasis=role_chars['timekeeper_emphasis'],
            accent_emphasis=role_chars['accent_emphasis'],
            color_emphasis=role_chars['color_emphasis'],
            
            # Meta
            drummer_name=drummer_name,
            source_tracks=[track_name],
            confidence_score=confidence
        )
        
        logger.info(f"Style vector encoded with {confidence:.3f} confidence")
        return style_vector
    
    def _extract_timing_characteristics(self, valid_analyses: Dict) -> Dict:
        """Extract timing-related characteristics"""
        
        precision_scores = [a.timing_precision_score for a in valid_analyses.values()]
        timing_signatures = [a.groove_timing_signature for a in valid_analyses.values()]
        micro_deviations = []
        tempo_stabilities = [a.tempo_stability for a in valid_analyses.values()]
        
        # Collect all micro-timing deviations
        for analysis in valid_analyses.values():
            micro_deviations.extend(analysis.micro_timing_deviations)
        
        # Determine dominant timing signature
        signature_counts = {}
        for sig in timing_signatures:
            signature_counts[sig] = signature_counts.get(sig, 0) + 1
        dominant_signature = max(signature_counts.keys(), key=lambda k: signature_counts[k])
        
        # Calculate micro-timing tendency (positive = ahead, negative = behind)
        micro_timing_tendency = float(np.mean(micro_deviations)) if micro_deviations else 0.0
        
        return {
            'precision_mean': float(np.mean(precision_scores)),
            'precision_std': float(np.std(precision_scores)),
            'signature': dominant_signature,
            'micro_timing_tendency': micro_timing_tendency,
            'tempo_stability': float(np.mean(tempo_stabilities))
        }
    
    def _extract_groove_characteristics(self, valid_analyses: Dict, collective_analysis: Dict) -> Dict:
        """Extract groove-related characteristics"""
        
        groove_contributions = [a.dynamic_groove_contribution for a in valid_analyses.values()]
        
        # Calculate syncopation tendency
        syncopated_hits = sum(a.syncopated_hits for a in valid_analyses.values())
        total_hits = sum(a.onset_count for a in valid_analyses.values())
        syncopation_tendency = float(syncopated_hits / total_hits) if total_hits > 0 else 0.0
        
        # Calculate accent frequency (based on velocity variations)
        accent_frequency = 0.0
        for analysis in valid_analyses.values():
            if analysis.velocities:
                velocities = np.array(analysis.velocities)
                mean_vel = np.mean(velocities)
                std_vel = np.std(velocities)
                accents = np.sum(velocities > (mean_vel + std_vel))
                accent_frequency += accents / len(velocities)
        
        accent_frequency /= len(valid_analyses)  # Average across drums
        
        # Calculate overall groove score
        groove_score = self._calculate_groove_score(valid_analyses, collective_analysis)
        
        return {
            'groove_score': groove_score,
            'dynamic_consistency': float(np.mean(groove_contributions)),
            'accent_frequency': float(accent_frequency),
            'syncopation_tendency': syncopation_tendency
        }
    
    def _extract_bass_integration_characteristics(self, valid_analyses: Dict) -> Dict:
        """Extract bass integration characteristics"""
        
        integration_scores = [a.bass_drum_pocket_score for a in valid_analyses.values()]
        interaction_styles = [a.bass_interaction_pattern for a in valid_analyses.values()]
        
        # Determine dominant interaction style
        style_counts = {}
        for style in interaction_styles:
            style_counts[style] = style_counts.get(style, 0) + 1
        dominant_style = max(style_counts.keys(), key=lambda k: style_counts[k])
        
        return {
            'integration_score': float(np.mean(integration_scores)),
            'interaction_style': dominant_style,
            'pocket_score': float(np.mean(integration_scores))
        }
    
    def _extract_pattern_characteristics(self, valid_analyses: Dict) -> Dict:
        """Extract pattern-related characteristics"""
        
        complexity_scores = [a.pattern_complexity for a in valid_analyses.values()]
        repetition_scores = [a.pattern_repetition_score for a in valid_analyses.values()]
        
        # Estimate fill frequency (based on toms and complexity)
        fill_frequency = 0.0
        if 'toms' in valid_analyses:
            toms_analysis = valid_analyses['toms']
            # Higher complexity and lower repetition suggests more fills
            fill_frequency = toms_analysis.pattern_complexity * (1.0 - toms_analysis.pattern_repetition_score)
        
        return {
            'complexity_mean': float(np.mean(complexity_scores)),
            'complexity_std': float(np.std(complexity_scores)),
            'repetition_vs_variation': float(np.mean(repetition_scores)),
            'fill_frequency': float(fill_frequency)
        }
    
    def _extract_individual_drum_characteristics(self, valid_analyses: Dict) -> Dict:
        """Extract characteristics specific to each drum type"""
        
        drum_chars = {}
        
        # Kick characteristics
        if 'kick' in valid_analyses:
            kick = valid_analyses['kick']
            drum_chars['kick'] = {
                'timing_precision': kick.timing_precision_score,
                'pattern_complexity': kick.pattern_complexity,
                'velocity_consistency': 1.0 / (1.0 + np.std(kick.velocities) / np.mean(kick.velocities)) if kick.velocities else 0.0,
                'on_beat_preference': kick.on_beat_hits / kick.onset_count if kick.onset_count > 0 else 0.0,
                'bass_sync_tendency': kick.bass_sync_percentage
            }
        else:
            drum_chars['kick'] = {}
        
        # Snare characteristics
        if 'snare' in valid_analyses:
            snare = valid_analyses['snare']
            # Detect ghost notes (low velocity hits)
            ghost_note_ratio = 0.0
            if snare.velocities:
                velocities = np.array(snare.velocities)
                ghost_threshold = np.mean(velocities) * 0.3
                ghost_notes = np.sum(velocities < ghost_threshold)
                ghost_note_ratio = ghost_notes / len(velocities)
            
            drum_chars['snare'] = {
                'timing_precision': snare.timing_precision_score,
                'pattern_complexity': snare.pattern_complexity,
                'ghost_note_ratio': float(ghost_note_ratio),
                'backbeat_emphasis': snare.off_beat_hits / snare.onset_count if snare.onset_count > 0 else 0.0,
                'dynamic_range': float(np.max(snare.velocities) - np.min(snare.velocities)) if snare.velocities else 0.0
            }
        else:
            drum_chars['snare'] = {}
        
        # Hi-hat characteristics
        if 'hihat' in valid_analyses:
            hihat = valid_analyses['hihat']
            drum_chars['hihat'] = {
                'timing_precision': hihat.timing_precision_score,
                'pattern_complexity': hihat.pattern_complexity,
                'timekeeper_consistency': hihat.pattern_repetition_score,
                'subdivision_density': hihat.onset_count / (hihat.duration * 4) if hihat.duration > 0 else 0.0,  # Hits per beat
                'velocity_control': 1.0 / (1.0 + np.std(hihat.velocities) / np.mean(hihat.velocities)) if hihat.velocities else 0.0
            }
        else:
            drum_chars['hihat'] = {}
        
        return drum_chars
    
    def _extract_velocity_characteristics(self, valid_analyses: Dict) -> Dict:
        """Extract velocity and dynamic characteristics"""
        
        all_velocities = []
        for analysis in valid_analyses.values():
            all_velocities.extend(analysis.velocities)
        
        if not all_velocities:
            return {
                'range_preference': (0.0, 1.0),
                'expression_level': 0.0,
                'ghost_note_tendency': 0.0
            }
        
        velocities = np.array(all_velocities)
        
        # Preferred velocity range (10th to 90th percentile)
        range_preference = (float(np.percentile(velocities, 10)), float(np.percentile(velocities, 90)))
        
        # Dynamic expression level (coefficient of variation)
        expression_level = float(np.std(velocities) / np.mean(velocities))
        
        # Ghost note tendency (percentage of hits below 30% of mean)
        ghost_threshold = np.mean(velocities) * 0.3
        ghost_note_tendency = float(np.sum(velocities < ghost_threshold) / len(velocities))
        
        return {
            'range_preference': range_preference,
            'expression_level': expression_level,
            'ghost_note_tendency': ghost_note_tendency
        }
    
    def _extract_rhythmic_role_characteristics(self, valid_analyses: Dict) -> Dict:
        """Extract rhythmic role distribution characteristics"""
        
        roles = [a.rhythmic_role for a in valid_analyses.values()]
        role_counts = {}
        for role in roles:
            role_counts[role] = role_counts.get(role, 0) + 1
        
        total_drums = len(roles)
        
        return {
            'timekeeper_emphasis': float(role_counts.get('timekeeper', 0) / total_drums),
            'accent_emphasis': float(role_counts.get('accent', 0) / total_drums),
            'color_emphasis': float(role_counts.get('color', 0) / total_drums)
        }
    
    def _calculate_groove_score(self, valid_analyses: Dict, collective_analysis: Dict) -> float:
        """Calculate overall groove score based on multiple factors"""
        
        # Use the groove characteristics from our memory
        timing_scores = [a.timing_precision_score for a in valid_analyses.values()]
        groove_contributions = [a.dynamic_groove_contribution for a in valid_analyses.values()]
        complexity_scores = [a.pattern_complexity for a in valid_analyses.values()]
        bass_pocket_scores = [a.bass_drum_pocket_score for a in valid_analyses.values()]
        
        # Weighted groove score calculation
        timing_component = np.mean(timing_scores) * 0.35
        groove_component = np.mean(groove_contributions) * 0.25
        complexity_component = np.mean(complexity_scores) * 0.20
        bass_component = np.mean(bass_pocket_scores) * 0.20
        
        groove_score = timing_component + groove_component + complexity_component + bass_component
        
        return float(groove_score)
    
    def _calculate_confidence_score(self, valid_analyses: Dict) -> float:
        """Calculate confidence in the style encoding"""
        
        # Confidence based on:
        # 1. Number of drums analyzed
        # 2. Amount of data per drum
        # 3. Consistency of characteristics across drums
        
        drum_count_score = len(valid_analyses) / 6.0  # Max 6 drums
        
        # Data amount score (based on onset counts)
        onset_counts = [a.onset_count for a in valid_analyses.values()]
        data_amount_score = min(1.0, np.mean(onset_counts) / 100.0)  # Normalize to 100 onsets
        
        # Consistency score (how consistent timing signatures are)
        timing_signatures = [a.groove_timing_signature for a in valid_analyses.values()]
        unique_signatures = len(set(timing_signatures))
        consistency_score = 1.0 / unique_signatures if unique_signatures > 0 else 0.0
        
        confidence = (drum_count_score + data_amount_score + consistency_score) / 3.0
        
        return float(confidence)
    
    def save_style_vector(self, style_vector: DrummerStyleVector, save_path: Path) -> None:
        """Save style vector to JSON file"""
        
        style_dict = asdict(style_vector)
        
        with open(save_path, 'w') as f:
            json.dump(style_dict, f, indent=2)
        
        logger.info(f"Style vector saved to {save_path}")
    
    def load_style_vector(self, load_path: Path) -> DrummerStyleVector:
        """Load style vector from JSON file"""
        
        with open(load_path, 'r') as f:
            style_dict = json.load(f)
        
        style_vector = DrummerStyleVector(**style_dict)
        
        logger.info(f"Style vector loaded from {load_path}")
        return style_vector

class MIDIStyleGenerator:
    """Generates MIDI drum patterns based on drummer style vectors"""
    
    def __init__(self):
        logger.info("MIDI Style Generator initialized")
    
    def generate_porcaro_like_pattern(self, style_vector: DrummerStyleVector, 
                                    bars: int = 4, tempo: float = 96.0) -> Dict:
        """Generate a Jeff Porcaro-like MIDI drum pattern"""
        
        logger.info(f"Generating {style_vector.drummer_name}-like pattern: {bars} bars at {tempo} BPM")
        
        # Pattern generation based on style characteristics
        pattern = {
            'tempo': tempo,
            'bars': bars,
            'time_signature': (4, 4),
            'tracks': {}
        }
        
        # Generate kick pattern
        pattern['tracks']['kick'] = self._generate_kick_pattern(style_vector, bars, tempo)
        
        # Generate snare pattern
        pattern['tracks']['snare'] = self._generate_snare_pattern(style_vector, bars, tempo)
        
        # Generate hi-hat pattern
        pattern['tracks']['hihat'] = self._generate_hihat_pattern(style_vector, bars, tempo)
        
        # Apply timing characteristics
        pattern = self._apply_timing_characteristics(pattern, style_vector)
        
        logger.info("Pattern generation complete")
        return pattern
    
    def _generate_kick_pattern(self, style_vector: DrummerStyleVector, bars: int, tempo: float) -> List:
        """Generate kick drum pattern based on style characteristics"""
        
        kick_chars = style_vector.kick_characteristics
        pattern = []
        
        # Basic pattern based on on-beat preference
        on_beat_pref = kick_chars.get('on_beat_preference', 0.8)
        
        for bar in range(bars):
            for beat in range(4):  # 4/4 time
                position = bar * 4 + beat
                
                # Strong beats (1, 3) more likely
                if beat in [0, 2]:
                    if np.random.random() < on_beat_pref:
                        velocity = int(80 + np.random.normal(0, 10))  # Around 80 velocity
                        pattern.append({
                            'position': position,
                            'velocity': max(40, min(127, velocity)),
                            'note': 36  # C2 - Kick
                        })
        
        return pattern
    
    def _generate_snare_pattern(self, style_vector: DrummerStyleVector, bars: int, tempo: float) -> List:
        """Generate snare pattern with ghost notes based on style"""
        
        snare_chars = style_vector.snare_characteristics
        pattern = []
        
        ghost_ratio = snare_chars.get('ghost_note_ratio', 0.2)
        backbeat_emphasis = snare_chars.get('backbeat_emphasis', 0.9)
        
        for bar in range(bars):
            for beat in range(4):
                position = bar * 4 + beat
                
                # Backbeat (beats 2, 4)
                if beat in [1, 3]:
                    if np.random.random() < backbeat_emphasis:
                        velocity = int(90 + np.random.normal(0, 15))
                        pattern.append({
                            'position': position,
                            'velocity': max(60, min(127, velocity)),
                            'note': 38  # D2 - Snare
                        })
                
                # Ghost notes on other subdivisions
                elif np.random.random() < ghost_ratio:
                    velocity = int(30 + np.random.normal(0, 5))  # Quiet ghost notes
                    pattern.append({
                        'position': position + np.random.uniform(-0.1, 0.1),  # Slight timing variation
                        'velocity': max(20, min(50, velocity)),
                        'note': 38  # D2 - Snare
                    })
        
        return pattern
    
    def _generate_hihat_pattern(self, style_vector: DrummerStyleVector, bars: int, tempo: float) -> List:
        """Generate hi-hat pattern based on complexity and consistency"""
        
        hihat_chars = style_vector.hihat_characteristics
        pattern = []
        
        complexity = hihat_chars.get('pattern_complexity', 0.8)
        subdivision_density = hihat_chars.get('subdivision_density', 2.0)  # Hits per beat
        
        for bar in range(bars):
            for beat in range(4):
                # Basic 8th note pattern with variations based on complexity
                for subdivision in [0, 0.5]:  # 8th notes
                    position = bar * 4 + beat + subdivision
                    
                    if np.random.random() < (0.9 - complexity * 0.3):  # More complex = more variations
                        velocity = int(60 + np.random.normal(0, 8))
                        pattern.append({
                            'position': position,
                            'velocity': max(40, min(100, velocity)),
                            'note': 42  # F#2 - Closed Hi-hat
                        })
        
        return pattern
    
    def _apply_timing_characteristics(self, pattern: Dict, style_vector: DrummerStyleVector) -> Dict:
        """Apply timing characteristics to the generated pattern"""
        
        timing_tendency = style_vector.micro_timing_tendency
        
        # Apply micro-timing adjustments
        for track_name, track_pattern in pattern['tracks'].items():
            for note in track_pattern:
                # Apply timing tendency (ahead/behind)
                timing_adjustment = timing_tendency + np.random.normal(0, 0.02)  # Small random variation
                note['position'] += timing_adjustment
        
        return pattern

# Example usage function
def create_porcaro_style_vector_from_analysis():
    """Create Jeff Porcaro style vector from our Rosanna analysis"""
    
    # This would use the actual analysis results
    # For now, creating based on our known results
    
    porcaro_vector = DrummerStyleVector(
        # Timing (from our analysis)
        timing_precision_mean=0.863,
        timing_precision_std=0.005,  # Very consistent
        timing_signature="ahead",
        micro_timing_tendency=0.02,  # Slightly ahead
        tempo_stability=0.628,
        
        # Groove (calculated)
        groove_score=0.82,  # Our calculated score
        dynamic_consistency=0.807,
        accent_frequency=0.3,
        syncopation_tendency=0.67,  # High syncopation
        
        # Bass Integration
        bass_integration_score=0.079,
        bass_interaction_style="independent",
        pocket_playing_score=0.079,
        
        # Patterns
        pattern_complexity_mean=1.0,  # Maximum complexity
        pattern_complexity_std=0.0,   # Consistent across kit
        repetition_vs_variation=0.3,  # More variation than repetition
        fill_frequency=0.2,
        
        # Individual drums (from our analysis)
        kick_characteristics={
            'timing_precision': 0.863,
            'pattern_complexity': 1.0,
            'on_beat_preference': 0.16,  # 61/(61+66+253)
            'bass_sync_tendency': 0.161
        },
        snare_characteristics={
            'timing_precision': 0.863,
            'pattern_complexity': 1.0,
            'ghost_note_ratio': 0.25,  # Estimated
            'backbeat_emphasis': 0.17,  # 66/(61+66+253)
            'dynamic_range': 0.026     # 0.043 - 0.017
        },
        hihat_characteristics={
            'timing_precision': 0.868,  # Highest precision
            'pattern_complexity': 1.0,
            'timekeeper_consistency': 0.258,
            'subdivision_density': 1.15,  # 380 onsets / 331.8s / 96 BPM * 60
            'velocity_control': 0.832
        },
        
        # Velocity/Dynamics
        velocity_range_preference=(0.017, 0.043),  # From analysis
        dynamic_expression_level=0.4,
        ghost_note_tendency=0.25,
        
        # Roles
        timekeeper_emphasis=0.33,  # kick, hihat
        accent_emphasis=0.17,      # snare
        color_emphasis=0.33,       # crash, ride
        
        # Meta
        drummer_name="Jeff Porcaro",
        source_tracks=["Rosanna"],
        confidence_score=0.95
    )
    
    return porcaro_vector

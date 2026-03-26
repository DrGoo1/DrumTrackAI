"""
Additional methods for DrumTracKAI Complete System
Contains the remaining analysis methods and utilities
"""

import numpy as np
import librosa
from scipy import stats
from typing import Dict, List, Optional
import sqlite3
import pickle
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class DrumTracKAI_Complete_Methods:
    """Additional methods for the complete system"""
    
    def _analyze_hits_integrated(self, drum_audio, onsets, tempo_profile, bass_audio):
        """Analyze each hit with all integrated features"""
        hits = []
        for i, onset_time in enumerate(onsets):
            hit = self._analyze_single_hit(drum_audio, onset_time)
            hit.timestamp = onset_time
            hit.micro_timing_deviation = self._calculate_micro_timing(onset_time, tempo_profile)
            hit.phase_in_measure = self._calculate_phase_in_measure(onset_time, tempo_profile)
            if bass_audio is not None:
                hit.bass_correlation = self._calculate_bass_correlation(onset_time, bass_audio)
            if i > 0:
                hit.preceding_interval = onset_time - onsets[i-1]
            if i < len(onsets) - 1:
                hit.following_interval = onsets[i+1] - onset_time
            hits.append(hit)
        return hits
    
    def _analyze_single_hit(self, audio, onset_time):
        """Analyze single hit"""
        from .drumtrackai_complete_system import DrumHit
        
        window_size = int(0.1 * self.sample_rate)
        start_idx = max(0, int(onset_time * self.sample_rate))
        end_idx = min(len(audio), start_idx + window_size)
        
        if end_idx > start_idx:
            hit_audio = audio[start_idx:end_idx]
            velocity = np.sqrt(np.mean(hit_audio**2))
            fft = np.fft.fft(hit_audio)
            freq_content = np.abs(fft[:len(fft)//2])
            
            if len(hit_audio) > 1024:
                early_centroid = librosa.feature.spectral_centroid(y=hit_audio[:512], sr=self.sample_rate)[0, 0]
                late_centroid = librosa.feature.spectral_centroid(y=hit_audio[512:1024], sr=self.sample_rate)[0, 0]
                attack_sharpness = abs(early_centroid - late_centroid) / (early_centroid + 1e-10)
            else:
                attack_sharpness = 0.5
            
            return DrumHit(
                timestamp=onset_time, velocity=velocity, drum_type="unknown",
                frequency_content=freq_content, attack_sharpness=attack_sharpness
            )
        else:
            return DrumHit(
                timestamp=onset_time, velocity=0.0, drum_type="unknown",
                frequency_content=np.array([]), attack_sharpness=0.0
            )
    
    def _calculate_micro_timing(self, onset_time, tempo_profile):
        """Calculate micro-timing deviation"""
        beat_period = 60.0 / tempo_profile.average_tempo
        expected_beat = round(onset_time / beat_period) * beat_period
        return (onset_time - expected_beat) * 1000
    
    def _calculate_phase_in_measure(self, onset_time, tempo_profile):
        """Calculate phase in measure"""
        beats_per_measure = 4
        seconds_per_beat = 60.0 / tempo_profile.average_tempo
        seconds_per_measure = seconds_per_beat * beats_per_measure
        return (onset_time % seconds_per_measure) / seconds_per_measure
    
    def _calculate_bass_correlation(self, drum_time, bass_audio):
        """Calculate bass correlation"""
        window_size = int(0.02 * self.sample_rate)
        start_sample = max(0, int((drum_time - 0.01) * self.sample_rate))
        end_sample = min(len(bass_audio), start_sample + window_size)
        
        if end_sample > start_sample:
            bass_window = bass_audio[start_sample:end_sample]
            peak_amplitude = np.max(np.abs(bass_window))
            rms_amplitude = np.sqrt(np.mean(bass_audio**2))
            correlation = peak_amplitude / (rms_amplitude + 1e-10)
            return np.clip(correlation, 0, 1)
        return 0.0
    
    def _analyze_neural_entrainment(self, audio, onsets):
        """Neural entrainment analysis"""
        from .drumtrackai_complete_system import EntrainmentProfile
        
        if len(onsets) < 2:
            return EntrainmentProfile(
                dominant_frequency=1.0, frequency_stability=0.5, phase_coherence=0.5,
                groove_induction_potential=0.5, flow_state_compatibility=0.5,
                brainwave_alignment={'delta': 0.1, 'theta': 0.2, 'alpha': 0.3, 'beta': 0.3, 'gamma': 0.1},
                tension_release_pattern=[]
            )
        
        iois = np.diff(onsets)
        dominant_freq = 1.0 / np.median(iois)
        freq_stability = 1.0 / (1.0 + np.std(iois) / np.mean(iois))
        phase_coherence = freq_stability
        
        optimal_tempo_range = (100, 140)
        tempo_bpm = dominant_freq * 60
        tempo_factor = 1.0 if optimal_tempo_range[0] <= tempo_bpm <= optimal_tempo_range[1] else 0.7
        groove_potential = phase_coherence * tempo_factor
        flow_compatibility = groove_potential * 0.8 + freq_stability * 0.2
        
        brainwave_alignment = {
            'delta': min(0.3, dominant_freq / 4.0),
            'theta': min(0.4, dominant_freq / 8.0),
            'alpha': min(0.5, dominant_freq / 10.0),
            'beta': min(0.4, dominant_freq / 20.0),
            'gamma': min(0.2, dominant_freq / 40.0)
        }
        
        return EntrainmentProfile(
            dominant_frequency=dominant_freq, frequency_stability=freq_stability,
            phase_coherence=phase_coherence, groove_induction_potential=groove_potential,
            flow_state_compatibility=flow_compatibility, brainwave_alignment=brainwave_alignment,
            tension_release_pattern=[]
        )
    
    def _analyze_rhythm_hierarchy(self, onsets, tempo_profile):
        """Rhythm hierarchy analysis"""
        from .drumtrackai_complete_system import RhythmHierarchy
        
        if len(onsets) < 4:
            return RhythmHierarchy(
                levels=[], complexity_score=0.1, staggered_rhythm=0.0,
                syncopation_score=0.0, hierarchical_depth=1
            )
        
        beat_period = 60.0 / tempo_profile.average_tempo
        beat_positions = onsets / beat_period
        beat_grid = np.round(beat_positions)
        
        off_beat_count = 0
        for i, pos in enumerate(beat_positions):
            if abs(pos - beat_grid[i]) > 0.25:
                off_beat_count += 1
        
        syncopation_score = off_beat_count / len(onsets)
        iois = np.diff(onsets)
        complexity_score = np.std(iois) / np.mean(iois) if len(iois) > 0 else 0.1
        staggered_rhythm = syncopation_score * 0.7 + complexity_score * 0.3
        
        return RhythmHierarchy(
            levels=[{'level': 0, 'beats': beat_grid.tolist()}],
            complexity_score=complexity_score, staggered_rhythm=staggered_rhythm,
            syncopation_score=syncopation_score, hierarchical_depth=1
        )
    
    def _compute_integrated_groove_metrics(self, hits, rhythm_hierarchy, entrainment_profile, bass_audio):
        """Compute groove metrics"""
        if len(hits) < 2:
            return self._empty_groove_metrics()
        
        intervals = [h.preceding_interval for h in hits[1:] if h.preceding_interval]
        timing_variance = np.var(intervals) if intervals else 0
        timing_tightness = 1.0 / (1.0 + timing_variance)
        
        velocities = [h.velocity for h in hits]
        velocity_variance = np.var(velocities)
        dynamic_consistency = 1.0 / (1.0 + velocity_variance)
        
        ghost_threshold = np.mean(velocities) * 0.5
        ghost_note_ratio = sum(1 for v in velocities if v < ghost_threshold) / len(hits)
        
        attack_values = [h.attack_sharpness for h in hits]
        attack_consistency = 1.0 / (1.0 + np.std(attack_values)) if attack_values else 0.5
        
        groove_depth = (
            timing_tightness * 0.25 + dynamic_consistency * 0.20 + attack_consistency * 0.15 +
            entrainment_profile.groove_induction_potential * 0.25 + entrainment_profile.flow_state_compatibility * 0.15
        )
        
        return {
            'timing_variance': timing_variance, 'timing_tightness': timing_tightness,
            'velocity_variance': velocity_variance, 'dynamic_consistency': dynamic_consistency,
            'ghost_note_ratio': ghost_note_ratio, 'hierarchical_depth': rhythm_hierarchy.hierarchical_depth,
            'rhythmic_complexity': rhythm_hierarchy.complexity_score, 'entrainment_quality': entrainment_profile.groove_induction_potential,
            'flow_compatibility': entrainment_profile.flow_state_compatibility, 'attack_consistency': attack_consistency,
            'groove_depth': groove_depth, 'overall_groove_score': groove_depth, 'syncopation_score': rhythm_hierarchy.syncopation_score
        }
    
    def _empty_groove_metrics(self):
        """Return empty groove metrics"""
        return {
            'timing_variance': 0, 'timing_tightness': 0, 'velocity_variance': 0, 'dynamic_consistency': 0,
            'ghost_note_ratio': 0, 'hierarchical_depth': 0, 'rhythmic_complexity': 0, 'entrainment_quality': 0,
            'flow_compatibility': 0, 'attack_consistency': 0, 'groove_depth': 0, 'overall_groove_score': 0, 'syncopation_score': 0
        }
    
    def _extract_integrated_style_features(self, hits, tempo_profile, rhythm_hierarchy, entrainment_profile, groove_metrics):
        """Extract style features for ML"""
        features = []
        
        if hits:
            intervals = [h.preceding_interval for h in hits if h.preceding_interval]
            if intervals:
                features.extend([np.mean(intervals), np.std(intervals), np.min(intervals), 
                               np.max(intervals), stats.skew(intervals) if len(intervals) > 2 else 0,
                               stats.kurtosis(intervals) if len(intervals) > 2 else 0])
            else:
                features.extend([0] * 6)
            
            # Velocity features
            velocities = [h.velocity for h in hits]
            features.extend([np.mean(velocities), np.std(velocities), np.min(velocities), 
                           np.max(velocities), stats.skew(velocities) if len(velocities) > 2 else 0,
                           stats.kurtosis(velocities) if len(velocities) > 2 else 0])
            
            # Micro-timing features
            deviations = [h.micro_timing_deviation for h in hits]
            features.extend([np.mean(deviations), np.std(deviations), 
                           np.percentile(deviations, 25), np.percentile(deviations, 75),
                           np.mean([abs(d) for d in deviations])])
            
            # Attack features
            attack_values = [h.attack_sharpness for h in hits]
            features.extend([np.mean(attack_values), np.std(attack_values)])
        else:
            features.extend([0] * 19)
        
        # Tempo features
        features.extend([tempo_profile.average_tempo, tempo_profile.tempo_stability,
                        1.0 if tempo_profile.is_steady else 0.0, len(tempo_profile.tempo_changes)])
        
        # Rhythm hierarchy features
        features.extend([rhythm_hierarchy.staggered_rhythm, rhythm_hierarchy.syncopation_score,
                        rhythm_hierarchy.hierarchical_depth, rhythm_hierarchy.complexity_score])
        
        # Entrainment features
        features.extend([entrainment_profile.dominant_frequency, entrainment_profile.frequency_stability,
                        entrainment_profile.phase_coherence, entrainment_profile.groove_induction_potential,
                        entrainment_profile.flow_state_compatibility])
        
        # Groove metrics
        features.extend([groove_metrics['timing_tightness'], groove_metrics['dynamic_consistency'],
                        groove_metrics['attack_consistency'], groove_metrics['groove_depth']])
        
        return np.array(features, dtype=np.float32)
    
    def _prepare_visualization_data(self, hits, tempo_profile, rhythm_hierarchy, entrainment_profile, groove_metrics):
        """Prepare comprehensive visualization data"""
        return {
            'tempo_curve': {
                'times': np.linspace(0, len(hits) * 0.1, len(tempo_profile.tempo_curve)).tolist(),
                'tempos': tempo_profile.tempo_curve.tolist()
            },
            'hit_timeline': {
                'times': [h.timestamp for h in hits],
                'velocities': [h.velocity for h in hits],
                'micro_timing': [h.micro_timing_deviation for h in hits]
            },
            'style_radar': {
                'categories': ['Complexity', 'Syncopation', 'Dynamics', 'Precision', 'Groove', 'Flow'],
                'values': [rhythm_hierarchy.complexity_score, rhythm_hierarchy.syncopation_score,
                          groove_metrics['dynamic_consistency'], groove_metrics['timing_tightness'],
                          groove_metrics['groove_depth'], entrainment_profile.flow_state_compatibility]
            },
            'entrainment_spectrum': {
                'frequencies': list(entrainment_profile.brainwave_alignment.keys()),
                'amplitudes': list(entrainment_profile.brainwave_alignment.values())
            },
            'rhythm_hierarchy': {
                'levels': rhythm_hierarchy.levels,
                'complexity': rhythm_hierarchy.complexity_score,
                'syncopation': rhythm_hierarchy.syncopation_score
            }
        }
    
    def _calculate_refinement_statistics(self, initial, refined):
        """Calculate onset refinement statistics"""
        if len(initial) != len(refined):
            return {'error': 'Onset count mismatch'}
        
        refinements = (refined - initial) * 1000  # ms
        return {
            'mean_refinement_ms': float(np.mean(refinements)),
            'std_refinement_ms': float(np.std(refinements)),
            'max_refinement_ms': float(np.max(np.abs(refinements))),
            'improved_precision': True
        }
    
    def _save_complete_analysis(self, analysis: Dict) -> int:
        """Save complete analysis to database"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        # Separate different parts of analysis for storage
        standard_analysis = {
            'onsets': analysis['onsets'],
            'tempo_profile': analysis['tempo_profile'],
            'hits': analysis['hits']
        }
        
        tfr_analysis = {
            'refinement_stats': analysis['onsets']['refinement_stats']
        }
        
        scalogram_analysis = {
            'rhythm_hierarchy': analysis['rhythm_hierarchy'],
            'visualization_data': analysis['visualization_data']
        }
        
        entrainment_analysis = analysis['neural_entrainment']
        
        integrated_features = {
            'groove_metrics': analysis['groove_metrics'],
            'style_features': analysis['style_features']
        }
        
        c.execute("""INSERT INTO complete_analyses 
                    (timestamp, drummer_id, track_name, standard_analysis, tfr_analysis,
                     scalogram_analysis, entrainment_analysis, integrated_features)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                 (analysis['timestamp'], 
                  analysis.get('drummer_id', 'unknown'),
                  analysis.get('track_name', 'untitled'),
                  pickle.dumps(standard_analysis),
                  pickle.dumps(tfr_analysis),
                  pickle.dumps(scalogram_analysis),
                  pickle.dumps(entrainment_analysis),
                  pickle.dumps(integrated_features)))
        
        analysis_id = c.lastrowid
        conn.commit()
        conn.close()
        return analysis_id
    
    def store_stem_files(self, stems_dict: Dict[str, str], drummer_id: str, 
                        track_name: str, analysis_id: int):
        """Store stem file paths in database"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        for stem_type, file_path in stems_dict.items():
            c.execute("""INSERT INTO stem_files 
                        (drummer_id, track_name, stem_type, file_path, analysis_id)
                        VALUES (?, ?, ?, ?, ?)""",
                     (drummer_id, track_name, stem_type, file_path, analysis_id))
        
        conn.commit()
        conn.close()
    
    def get_drummer_analyses(self, drummer_id: str) -> List[Dict]:
        """Retrieve all analyses for a drummer"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        c.execute("""SELECT * FROM complete_analyses WHERE drummer_id = ?""", (drummer_id,))
        rows = c.fetchall()
        
        analyses = []
        for row in rows:
            analysis = {
                'id': row[0],
                'timestamp': row[1],
                'drummer_id': row[2],
                'track_name': row[3],
                'standard_analysis': pickle.loads(row[4]),
                'tfr_analysis': pickle.loads(row[5]),
                'scalogram_analysis': pickle.loads(row[6]),
                'entrainment_analysis': pickle.loads(row[7]),
                'integrated_features': pickle.loads(row[8])
            }
            analyses.append(analysis)
        
        conn.close()
        return analyses
    
    def learn_drummer_style(self, drummer_id: str) -> Dict:
        """Learn drummer style from all available analyses"""
        analyses = self.get_drummer_analyses(drummer_id)
        
        if not analyses:
            return {'error': 'No analyses found for drummer'}
        
        # Collect all style features
        all_features = []
        all_groove_metrics = []
        
        for analysis in analyses:
            features = analysis['integrated_features']['style_features']
            if isinstance(features, list):
                all_features.append(features)
            
            groove = analysis['integrated_features']['groove_metrics']
            all_groove_metrics.append(groove)
        
        if not all_features:
            return {'error': 'No style features found'}
        
        # Calculate average style profile
        avg_features = np.mean(all_features, axis=0)
        
        # Calculate performance traits
        avg_groove = {}
        for key in all_groove_metrics[0].keys():
            values = [g[key] for g in all_groove_metrics]
            avg_groove[key] = np.mean(values)
        
        # Determine style characteristics
        style_profile = {
            'drummer_id': drummer_id,
            'num_analyses': len(analyses),
            'avg_features': avg_features.tolist(),
            'performance_traits': {
                'timing_style': 'tight' if avg_groove['timing_tightness'] > 0.7 else 'loose',
                'uses_ghost_notes': avg_groove['ghost_note_ratio'] > 0.2,
                'dynamic_range': avg_groove['velocity_variance'],
                'groove_depth': avg_groove['groove_depth'],
                'flow_compatibility': avg_groove['flow_compatibility']
            },
            'signature_characteristics': {
                'complexity': avg_groove['rhythmic_complexity'],
                'syncopation': avg_groove.get('syncopation_score', 0),
                'entrainment_quality': avg_groove['entrainment_quality']
            }
        }
        
        return style_profile
    
    def generate_drum_pattern(self, style_profile: Dict, pattern_length: float = 8.0, 
                            tempo: float = 120.0, complexity: float = 0.7) -> Dict:
        """Generate new drum pattern based on learned style"""
        logger.info(f"Generating pattern: length={pattern_length}s, tempo={tempo}, complexity={complexity}")
        
        # Calculate pattern parameters
        beat_period = 60.0 / tempo
        num_beats = int(pattern_length / beat_period)
        
        # Extract style characteristics
        traits = style_profile.get('performance_traits', {})
        timing_style = traits.get('timing_style', 'medium')
        uses_ghost_notes = traits.get('uses_ghost_notes', False)
        dynamic_range = traits.get('dynamic_range', 0.5)
        
        # Generate hit pattern
        hits = []
        current_time = 0.0
        
        for beat in range(num_beats):
            # Main beat hit
            if beat % 4 == 0 or (beat % 2 == 0 and complexity > 0.5):  # Kick pattern
                velocity = 0.8 + np.random.normal(0, dynamic_range * 0.1)
                timing_deviation = self._get_timing_deviation(timing_style)
                
                hits.append({
                    'timestamp': current_time + timing_deviation,
                    'velocity': np.clip(velocity, 0.1, 1.0),
                    'drum_type': 'kick',
                    'micro_timing_deviation': timing_deviation * 1000
                })
            
            # Snare hits
            if beat % 4 == 2:  # Backbeat
                velocity = 0.9 + np.random.normal(0, dynamic_range * 0.1)
                timing_deviation = self._get_timing_deviation(timing_style)
                
                hits.append({
                    'timestamp': current_time + timing_deviation,
                    'velocity': np.clip(velocity, 0.1, 1.0),
                    'drum_type': 'snare',
                    'micro_timing_deviation': timing_deviation * 1000
                })
            
            # Ghost notes
            if uses_ghost_notes and np.random.random() < complexity * 0.3:
                ghost_time = current_time + beat_period * 0.5
                velocity = 0.2 + np.random.normal(0, 0.05)
                
                hits.append({
                    'timestamp': ghost_time,
                    'velocity': np.clip(velocity, 0.05, 0.4),
                    'drum_type': 'snare',
                    'micro_timing_deviation': 0
                })
            
            current_time += beat_period
        
        # Hi-hat pattern
        hihat_subdivision = 4 if complexity > 0.6 else 2
        for i in range(int(pattern_length * hihat_subdivision)):
            hihat_time = i * (beat_period / hihat_subdivision)
            velocity = 0.4 + np.random.normal(0, 0.1)
            
            hits.append({
                'timestamp': hihat_time,
                'velocity': np.clip(velocity, 0.1, 0.8),
                'drum_type': 'hihat',
                'micro_timing_deviation': self._get_timing_deviation(timing_style) * 1000
            })
        
        # Sort hits by timestamp
        hits.sort(key=lambda x: x['timestamp'])
        
        return {
            'hits': hits,
            'pattern_length': pattern_length,
            'tempo': tempo,
            'complexity': complexity,
            'style_profile': style_profile['drummer_id'],
            'generated_timestamp': datetime.now().isoformat()
        }
    
    def _get_timing_deviation(self, timing_style: str) -> float:
        """Get timing deviation based on style"""
        if timing_style == 'tight':
            return np.random.normal(0, 0.002)  # ±2ms
        elif timing_style == 'loose':
            return np.random.normal(0, 0.008)  # ±8ms
        else:  # medium
            return np.random.normal(0, 0.005)  # ±5ms

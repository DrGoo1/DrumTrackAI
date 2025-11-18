#!/usr/bin/env python3
"""
Individual Stem Integration Module
Integrates tempo-aware individual drum stem analysis with DrumTracKAI Complete System
"""

import os
import sys
import numpy as np
import soundfile as sf
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import logging
from datetime import datetime
import json

# Set LLVM-safe environment variables
os.environ['NUMBA_DISABLE_INTEL_SVML'] = '1'
os.environ['OMP_NUM_THREADS'] = '1' 
os.environ['NUMBA_DISABLE_TBB'] = '1'

# Setup path
admin_path = Path(__file__).parent.parent
sys.path.insert(0, str(admin_path))

from services.tempo_aware_drum_analyzer import TempoAwareDrumStemAnalyzer, TempoAwareDrumAnalysis
from services.drumtrackai_complete_system import DrumTracKAICompleteSystem

logger = logging.getLogger(__name__)

class IndividualStemIntegration:
    """Integrates individual drum stem analysis with complete system"""
    
    def __init__(self):
        self.tempo_analyzer = TempoAwareDrumStemAnalyzer()
        self.complete_system = DrumTracKAICompleteSystem()
        
        logger.info("Individual Stem Integration initialized")
    
    def analyze_individual_stems_complete(self, stem_directory: Path, drummer_id: str, 
                                        track_name: str, tempo_context: float,
                                        bass_stem_path: Optional[Path] = None) -> Dict:
        """
        Complete analysis workflow:
        1. Find and analyze individual drum stems with tempo context
        2. Load bass stem for integration analysis
        3. Combine individual analyses into collective drummer profile
        4. Store results in database
        5. Generate comprehensive visualizations
        """
        
        logger.info(f"Starting complete individual stem analysis for {drummer_id} - {track_name}")
        logger.info(f"Stem directory: {stem_directory}")
        logger.info(f"Tempo context: {tempo_context} BPM")
        
        try:
            # 1. Load bass audio if available
            bass_audio = None
            if bass_stem_path and bass_stem_path.exists():
                logger.info(f"Loading bass stem: {bass_stem_path}")
                bass_audio, _ = sf.read(str(bass_stem_path))
                if len(bass_audio.shape) > 1:
                    bass_audio = np.mean(bass_audio, axis=1)  # Convert to mono
                logger.info(f"Bass audio loaded: {len(bass_audio)/44100:.1f}s")
            else:
                logger.warning("No bass stem available for integration analysis")
            
            # 2. Find all available drum stems
            found_stems = self.tempo_analyzer.find_drum_stems(stem_directory)
            available_stems = [k for k, v in found_stems.items() if v is not None]
            logger.info(f"Found drum stems: {available_stems}")
            
            if not available_stems:
                raise ValueError("No drum stems found in directory")
            
            # 3. Analyze each individual drum stem with tempo context and bass integration
            individual_analyses = {}
            
            for drum_type, stem_file in found_stems.items():
                if stem_file is not None:
                    logger.info(f"Analyzing individual {drum_type} stem...")
                    
                    try:
                        analysis = self.tempo_analyzer.analyze_individual_drum_tempo_aware(
                            stem_file, drum_type, tempo_context, bass_audio
                        )
                        individual_analyses[drum_type] = analysis
                        
                        logger.info(f"{drum_type} analysis complete:")
                        logger.info(f"  - {analysis.onset_count} onsets detected")
                        logger.info(f"  - {analysis.timing_precision_score:.3f} timing precision")
                        logger.info(f"  - {analysis.bass_drum_pocket_score:.3f} bass pocket score")
                        logger.info(f"  - {analysis.bass_interaction_pattern} bass interaction")
                        logger.info(f"  - {analysis.rhythmic_role} rhythmic role")
                        
                    except Exception as e:
                        logger.error(f"Failed to analyze {drum_type}: {e}")
                        individual_analyses[drum_type] = None
            
            # 4. Create collective analysis combining all individual analyses
            collective_analysis = self._create_collective_analysis(
                individual_analyses, tempo_context, drummer_id, track_name
            )
            
            # 5. Store individual analyses in database
            analysis_id = self._store_individual_analyses(
                individual_analyses, collective_analysis, stem_directory
            )
            
            # 6. Generate comprehensive visualization data
            visualization_data = self._generate_individual_stem_visualization(
                individual_analyses, collective_analysis
            )
            
            # 7. Prepare complete results
            results = {
                'analysis_id': analysis_id,
                'drummer_id': drummer_id,
                'track_name': track_name,
                'tempo_context': tempo_context,
                'individual_analyses': individual_analyses,
                'collective_analysis': collective_analysis,
                'visualization_data': visualization_data,
                'available_stems': available_stems,
                'bass_integration': bass_audio is not None,
                'timestamp': datetime.now().isoformat()
            }
            
            logger.info(f"Complete individual stem analysis finished:")
            logger.info(f"  - Analyzed {len(available_stems)} drum stems")
            logger.info(f"  - Collective groove score: {collective_analysis['collective_groove_score']:.3f}")
            logger.info(f"  - Bass integration score: {collective_analysis['bass_integration_score']:.3f}")
            logger.info(f"  - Analysis ID: {analysis_id}")
            
            return results
            
        except Exception as e:
            logger.error(f"Individual stem analysis failed: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            raise
    
    def _create_collective_analysis(self, individual_analyses: Dict, tempo_context: float,
                                   drummer_id: str, track_name: str) -> Dict:
        """Create collective analysis from individual drum analyses"""
        
        # Filter out None analyses
        valid_analyses = {k: v for k, v in individual_analyses.items() if v is not None}
        
        if not valid_analyses:
            raise ValueError("No valid individual analyses to combine")
        
        # Calculate collective metrics
        all_timing_precision = [a.timing_precision_score for a in valid_analyses.values()]
        all_bass_pocket_scores = [a.bass_drum_pocket_score for a in valid_analyses.values()]
        all_groove_contributions = [a.dynamic_groove_contribution for a in valid_analyses.values()]
        all_pattern_complexity = [a.pattern_complexity for a in valid_analyses.values()]
        
        # Kit timing cohesion (how well all drums work together rhythmically)
        timing_consistency = np.std(all_timing_precision) if len(all_timing_precision) > 1 else 0.0
        kit_timing_cohesion = float(1.0 / (1.0 + timing_consistency))
        
        # Collective groove score
        collective_groove_score = float(np.mean(all_groove_contributions))
        
        # Bass integration score
        bass_integration_score = float(np.mean(all_bass_pocket_scores))
        
        # Rhythmic complexity score
        rhythmic_complexity_score = float(np.mean(all_pattern_complexity))
        
        # Determine overall groove style based on timing signatures
        timing_signatures = [a.groove_timing_signature for a in valid_analyses.values()]
        if timing_signatures.count('on') > len(timing_signatures) / 2:
            groove_style = 'tight'
        elif timing_signatures.count('ahead') > len(timing_signatures) / 2:
            groove_style = 'pushing'
        elif timing_signatures.count('behind') > len(timing_signatures) / 2:
            groove_style = 'laying_back'
        else:
            groove_style = 'variable'
        
        # Determine playing approach based on precision and complexity
        avg_precision = np.mean(all_timing_precision)
        avg_complexity = np.mean(all_pattern_complexity)
        
        if avg_precision > 0.8 and avg_complexity < 0.3:
            playing_approach = 'metronomic'
        elif avg_precision > 0.6 and avg_complexity > 0.6:
            playing_approach = 'technical'
        elif avg_precision < 0.6 and avg_complexity > 0.4:
            playing_approach = 'expressive'
        else:
            playing_approach = 'balanced'
        
        # Create signature timing patterns
        signature_patterns = []
        for drum_type, analysis in valid_analyses.items():
            if analysis.onset_count > 0:
                pattern = {
                    'drum_type': drum_type,
                    'role': analysis.rhythmic_role,
                    'timing_signature': analysis.groove_timing_signature,
                    'complexity': analysis.pattern_complexity,
                    'bass_interaction': analysis.bass_interaction_pattern,
                    'onset_count': analysis.onset_count,
                    'precision_score': analysis.timing_precision_score
                }
                signature_patterns.append(pattern)
        
        collective_analysis = {
            'drummer_id': drummer_id,
            'track_name': track_name,
            'timestamp': datetime.now().isoformat(),
            'tempo_context': tempo_context,
            
            # Collective metrics
            'kit_timing_cohesion': kit_timing_cohesion,
            'collective_groove_score': collective_groove_score,
            'rhythmic_complexity_score': rhythmic_complexity_score,
            'bass_integration_score': bass_integration_score,
            
            # Style characteristics
            'groove_style': groove_style,
            'playing_approach': playing_approach,
            'signature_timing_patterns': signature_patterns,
            
            # Individual drum summary
            'analyzed_drums': list(valid_analyses.keys()),
            'total_onsets': sum(a.onset_count for a in valid_analyses.values()),
            'average_timing_precision': float(np.mean(all_timing_precision)),
            'timing_precision_range': [float(np.min(all_timing_precision)), float(np.max(all_timing_precision))],
            
            # Bass integration summary
            'bass_sync_events_total': sum(a.bass_sync_events for a in valid_analyses.values()),
            'bass_interaction_patterns': {k: v.bass_interaction_pattern for k, v in valid_analyses.items()}
        }
        
        return collective_analysis
    
    def _store_individual_analyses(self, individual_analyses: Dict, collective_analysis: Dict,
                                  stem_directory: Path) -> str:
        """Store individual analyses and collective results in database"""
        
        try:
            # Prepare data for storage
            analysis_data = {
                'individual_analyses': {},
                'collective_analysis': collective_analysis,
                'stem_directory': str(stem_directory),
                'analysis_type': 'individual_stem_analysis'
            }
            
            # Convert individual analyses to serializable format
            for drum_type, analysis in individual_analyses.items():
                if analysis is not None:
                    analysis_data['individual_analyses'][drum_type] = {
                        'drum_type': analysis.drum_type,
                        'file_path': analysis.file_path,
                        'duration': analysis.duration,
                        'sample_rate': analysis.sample_rate,
                        'global_tempo': analysis.global_tempo,
                        'tempo_stability': analysis.tempo_stability,
                        'onsets': analysis.onsets,
                        'onset_count': analysis.onset_count,
                        'on_beat_hits': analysis.on_beat_hits,
                        'off_beat_hits': analysis.off_beat_hits,
                        'syncopated_hits': analysis.syncopated_hits,
                        'timing_precision_score': analysis.timing_precision_score,
                        'micro_timing_deviations': analysis.micro_timing_deviations,
                        'groove_timing_signature': analysis.groove_timing_signature,
                        'velocities': analysis.velocities,
                        'velocity_on_beats': analysis.velocity_on_beats,
                        'velocity_off_beats': analysis.velocity_off_beats,
                        'dynamic_groove_contribution': analysis.dynamic_groove_contribution,
                        'bass_correlation_coefficient': analysis.bass_correlation_coefficient,
                        'bass_sync_events': analysis.bass_sync_events,
                        'bass_sync_percentage': analysis.bass_sync_percentage,
                        'bass_drum_pocket_score': analysis.bass_drum_pocket_score,
                        'bass_interaction_pattern': analysis.bass_interaction_pattern,
                        'rhythmic_role': analysis.rhythmic_role,
                        'pattern_complexity': analysis.pattern_complexity,
                        'pattern_repetition_score': analysis.pattern_repetition_score
                    }
            
            # Store in DrumTracKAI Complete System database
            analysis_id = self.complete_system.store_complete_analysis(
                collective_analysis['drummer_id'],
                collective_analysis['track_name'],
                analysis_data,
                visualization_data={},  # Will be added separately
                stem_files=[str(stem_directory)]
            )
            
            logger.info(f"Individual stem analyses stored with ID: {analysis_id}")
            return analysis_id
            
        except Exception as e:
            logger.error(f"Failed to store individual analyses: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            raise
    
    def _generate_individual_stem_visualization(self, individual_analyses: Dict, 
                                              collective_analysis: Dict) -> Dict:
        """Generate comprehensive visualization data for individual stem analysis"""
        
        visualization_data = {
            'individual_drum_charts': {},
            'collective_overview': {},
            'bass_integration_chart': {},
            'timing_precision_chart': {},
            'rhythmic_roles_chart': {}
        }
        
        valid_analyses = {k: v for k, v in individual_analyses.items() if v is not None}
        
        # Individual drum charts
        for drum_type, analysis in valid_analyses.items():
            visualization_data['individual_drum_charts'][drum_type] = {
                'onset_timeline': {
                    'times': analysis.onsets,
                    'velocities': analysis.velocities,
                    'timing_deviations': analysis.micro_timing_deviations
                },
                'timing_analysis': {
                    'on_beat_hits': analysis.on_beat_hits,
                    'off_beat_hits': analysis.off_beat_hits,
                    'syncopated_hits': analysis.syncopated_hits,
                    'precision_score': analysis.timing_precision_score
                },
                'bass_integration': {
                    'correlation': analysis.bass_correlation_coefficient,
                    'sync_percentage': analysis.bass_sync_percentage,
                    'pocket_score': analysis.bass_drum_pocket_score,
                    'interaction_pattern': analysis.bass_interaction_pattern
                },
                'characteristics': {
                    'rhythmic_role': analysis.rhythmic_role,
                    'pattern_complexity': analysis.pattern_complexity,
                    'groove_contribution': analysis.dynamic_groove_contribution,
                    'timing_signature': analysis.groove_timing_signature
                }
            }
        
        # Collective overview
        visualization_data['collective_overview'] = {
            'groove_score': collective_analysis['collective_groove_score'],
            'bass_integration_score': collective_analysis['bass_integration_score'],
            'timing_cohesion': collective_analysis['kit_timing_cohesion'],
            'complexity_score': collective_analysis['rhythmic_complexity_score'],
            'groove_style': collective_analysis['groove_style'],
            'playing_approach': collective_analysis['playing_approach'],
            'analyzed_drums': collective_analysis['analyzed_drums']
        }
        
        # Bass integration comparison chart
        visualization_data['bass_integration_chart'] = {
            'drum_types': list(valid_analyses.keys()),
            'pocket_scores': [a.bass_drum_pocket_score for a in valid_analyses.values()],
            'sync_percentages': [a.bass_sync_percentage for a in valid_analyses.values()],
            'interaction_patterns': [a.bass_interaction_pattern for a in valid_analyses.values()]
        }
        
        # Timing precision comparison
        visualization_data['timing_precision_chart'] = {
            'drum_types': list(valid_analyses.keys()),
            'precision_scores': [a.timing_precision_score for a in valid_analyses.values()],
            'timing_signatures': [a.groove_timing_signature for a in valid_analyses.values()],
            'tempo_stabilities': [a.tempo_stability for a in valid_analyses.values()]
        }
        
        # Rhythmic roles chart
        visualization_data['rhythmic_roles_chart'] = {
            'roles': [a.rhythmic_role for a in valid_analyses.values()],
            'complexities': [a.pattern_complexity for a in valid_analyses.values()],
            'drum_types': list(valid_analyses.keys()),
            'onset_counts': [a.onset_count for a in valid_analyses.values()]
        }
        
        return visualization_data
    
    def find_bass_stem(self, stem_directory: Path) -> Optional[Path]:
        """Find bass stem file in the directory"""
        
        possible_bass_names = ['bass.wav', 'bass_guitar.wav', 'bass_track.wav', 'bass_stem.wav']
        
        for name in possible_bass_names:
            bass_file = stem_directory / name
            if bass_file.exists():
                logger.info(f"Found bass stem: {bass_file}")
                return bass_file
        
        logger.warning("No bass stem found in directory")
        return None

"""
MVSep Complete Integration Service
Integrates DrumTracKAI Complete System with MVSep workflow
"""

import os
import logging
from typing import Dict, List, Optional
from pathlib import Path
import asyncio

logger = logging.getLogger(__name__)

class MVSepCompleteIntegration:
    """Integration service for MVSep + DrumTracKAI Complete System"""
    
    def __init__(self):
        self.complete_system = None
        self._initialize_complete_system()
    
    def _initialize_complete_system(self):
        """Initialize the DrumTracKAI Complete System"""
        try:
            from .drumtrackai_complete_system import DrumTracKAI_Complete_System
            self.complete_system = DrumTracKAI_Complete_System()
            logger.info("DrumTracKAI Complete System initialized for MVSep integration")
        except Exception as e:
            logger.error(f"Failed to initialize DrumTracKAI Complete System: {e}")
            self.complete_system = None
    
    async def process_mvsep_output(self, stems_dict: Dict[str, str], drummer_id: str, 
                                 track_name: str, metadata: Dict = None) -> Dict:
        """
        Process MVSep output with DrumTracKAI Complete System
        
        Args:
            stems_dict: Dictionary of stem_type -> file_path
            drummer_id: ID of the drummer
            track_name: Name of the track
            metadata: Additional metadata from arrangement analysis
            
        Returns:
            Complete analysis results dictionary
        """
        if not self.complete_system:
            logger.error("DrumTracKAI Complete System not available")
            return {'error': 'Complete system not initialized'}
        
        logger.info(f"Processing MVSep output for {drummer_id} - {track_name}")
        logger.info(f"Available stems: {list(stems_dict.keys())}")
        
        try:
            # Analyze each drum stem with the complete system
            analysis_results = {}
            
            # Prioritize drum stems for analysis
            drum_stems = ['kick', 'snare', 'toms', 'hihat', 'crash', 'ride']
            bass_path = stems_dict.get('bass')
            
            for stem_type in drum_stems:
                if stem_type in stems_dict:
                    stem_path = stems_dict[stem_type]
                    
                    if os.path.exists(stem_path):
                        logger.info(f"Analyzing {stem_type} stem: {stem_path}")
                        
                        # Perform complete analysis
                        analysis = self.complete_system.complete_drum_analysis(
                            drum_path=stem_path,
                            bass_path=bass_path,
                            drum_type=stem_type,
                            drummer_id=drummer_id
                        )
                        
                        analysis_results[stem_type] = analysis
                        logger.info(f"Completed analysis for {stem_type} stem")
                    else:
                        logger.warning(f"Stem file not found: {stem_path}")
            
            # Store stem files in database
            if analysis_results:
                # Use the first analysis ID for stem file storage
                first_analysis = list(analysis_results.values())[0]
                analysis_id = first_analysis.get('analysis_id')
                
                if analysis_id:
                    self.complete_system.store_stem_files(
                        stems_dict, drummer_id, track_name, analysis_id
                    )
                    logger.info(f"Stored stem files for analysis ID: {analysis_id}")
            
            # Learn/update drummer style if we have multiple analyses
            try:
                style_profile = self.complete_system.learn_drummer_style(drummer_id)
                if 'error' not in style_profile:
                    logger.info(f"Updated style profile for drummer {drummer_id}")
                    analysis_results['learned_style'] = style_profile
            except Exception as e:
                logger.warning(f"Could not update style profile: {e}")
            
            # Prepare comprehensive results
            complete_results = {
                'drummer_id': drummer_id,
                'track_name': track_name,
                'timestamp': analysis_results[list(analysis_results.keys())[0]]['timestamp'] if analysis_results else None,
                'stem_analyses': analysis_results,
                'stems_processed': list(analysis_results.keys()),
                'total_stems': len(stems_dict),
                'metadata': metadata or {},
                'integration_status': 'success'
            }
            
            logger.info(f"Complete integration finished for {drummer_id} - {track_name}")
            logger.info(f"Processed {len(analysis_results)} drum stems")
            
            return complete_results
            
        except Exception as e:
            logger.error(f"Error in MVSep complete integration: {str(e)}")
            return {
                'error': str(e),
                'drummer_id': drummer_id,
                'track_name': track_name,
                'integration_status': 'failed'
            }
    
    def get_drummer_complete_analysis(self, drummer_id: str) -> Dict:
        """Get complete analysis data for a drummer"""
        if not self.complete_system:
            return {'error': 'Complete system not available'}
        
        try:
            # Get all analyses for the drummer
            analyses = self.complete_system.get_drummer_analyses(drummer_id)
            
            # Get learned style profile
            style_profile = self.complete_system.learn_drummer_style(drummer_id)
            
            return {
                'drummer_id': drummer_id,
                'analyses': analyses,
                'style_profile': style_profile,
                'total_analyses': len(analyses)
            }
            
        except Exception as e:
            logger.error(f"Error getting complete analysis for {drummer_id}: {e}")
            return {'error': str(e)}
    
    def generate_drummer_pattern(self, drummer_id: str, pattern_length: float = 8.0,
                               tempo: float = 120.0, complexity: float = 0.7) -> Dict:
        """Generate a new drum pattern based on learned drummer style"""
        if not self.complete_system:
            return {'error': 'Complete system not available'}
        
        try:
            # Get the drummer's style profile
            style_profile = self.complete_system.learn_drummer_style(drummer_id)
            
            if 'error' in style_profile:
                return style_profile
            
            # Generate pattern
            pattern = self.complete_system.generate_drum_pattern(
                style_profile=style_profile,
                pattern_length=pattern_length,
                tempo=tempo,
                complexity=complexity
            )
            
            logger.info(f"Generated pattern for {drummer_id}: {len(pattern['hits'])} hits")
            return pattern
            
        except Exception as e:
            logger.error(f"Error generating pattern for {drummer_id}: {e}")
            return {'error': str(e)}
    
    def create_visualization_data(self, drummer_id: str, track_name: str = None) -> Dict:
        """Create comprehensive visualization data for a drummer"""
        if not self.complete_system:
            return {'error': 'Complete system not available'}
        
        try:
            # Get analyses for the drummer
            analyses = self.complete_system.get_drummer_analyses(drummer_id)
            
            if not analyses:
                return {'error': 'No analyses found for drummer'}
            
            # Use the most recent analysis or specific track
            target_analysis = analyses[-1]  # Most recent
            if track_name:
                for analysis in analyses:
                    if analysis['track_name'] == track_name:
                        target_analysis = analysis
                        break
            
            # Create visualization data from the analysis
            viz_data = self.complete_system.create_visualization_data(target_analysis)
            
            return {
                'drummer_id': drummer_id,
                'track_name': target_analysis['track_name'],
                'visualization_data': viz_data,
                'analysis_timestamp': target_analysis['timestamp']
            }
            
        except Exception as e:
            logger.error(f"Error creating visualization data for {drummer_id}: {e}")
            return {'error': str(e)}

# Global integration service instance
_integration_service = None

def get_mvsep_complete_integration() -> MVSepCompleteIntegration:
    """Get the global MVSep complete integration service"""
    global _integration_service
    if _integration_service is None:
        _integration_service = MVSepCompleteIntegration()
    return _integration_service

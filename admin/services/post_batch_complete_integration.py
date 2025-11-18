#!/usr/bin/env python3
"""
Post-Batch Complete System Integration
Connects MVSep batch completion to DrumTracKAI Complete System analysis and UI display
"""

import os
import sys
import logging
from pathlib import Path
from typing import Dict, Optional
import sqlite3
import json
from datetime import datetime

# Set LLVM-safe environment variables before any imports
os.environ['NUMBA_DISABLE_INTEL_SVML'] = '1'
os.environ['OMP_NUM_THREADS'] = '1' 
os.environ['NUMBA_DISABLE_TBB'] = '1'

# Setup path
admin_path = Path(__file__).parent.parent
sys.path.insert(0, str(admin_path))

logger = logging.getLogger(__name__)

class PostBatchCompleteIntegration:
    """Handles post-batch MVSep completion and complete analysis workflow"""
    
    def __init__(self):
        self.admin_path = admin_path
        self.complete_system = None
        self.authenticity_validator = None
        
    def initialize_services(self):
        """Initialize the complete system and authenticity validator"""
        try:
            # Initialize DrumTracKAI Complete System
            from services.drumtrackai_complete_system import DrumTracKAICompleteSystem
            self.complete_system = DrumTracKAICompleteSystem()
            logger.info("DrumTracKAI Complete System initialized")
            
            # Initialize authenticity validator
            from authenticity_validation_framework import AuthenticityValidator
            self.authenticity_validator = AuthenticityValidator()
            logger.info("Authenticity validator initialized")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize services: {e}")
            return False
    
    def process_batch_completion(self, batch_job_data: Dict) -> Optional[Dict]:
        """Process completed batch job and run complete analysis"""
        
        try:
            logger.info(f"Processing batch completion for: {batch_job_data.get('drummer_id', 'unknown')}")
            
            # Extract job information
            drummer_id = batch_job_data.get('drummer_id', 'unknown')
            track_name = batch_job_data.get('track_name', 'unknown')
            output_directory = batch_job_data.get('output_directory')
            tempo_context = batch_job_data.get('tempo', 120)
            style_context = batch_job_data.get('style', 'rock')
            
            if not output_directory:
                logger.error("No output directory provided in batch job data")
                return None
            
            # Locate stem files
            output_path = Path(output_directory)
            drum_file = output_path / "drums.wav"
            bass_file = output_path / "bass.wav"
            
            if not drum_file.exists():
                logger.error(f"Drum file not found: {drum_file}")
                return None
            
            if not bass_file.exists():
                logger.warning(f"Bass file not found: {bass_file}")
                bass_file = None
            
            logger.info(f"Found stems - Drums: {drum_file}, Bass: {bass_file}")
            
            # Load audio data
            import soundfile as sf
            import numpy as np
            
            # Load drums
            drum_audio, drum_sr = sf.read(str(drum_file))
            if len(drum_audio.shape) > 1:
                drum_audio = np.mean(drum_audio, axis=1)
            
            # Load bass if available
            bass_audio = None
            bass_sr = None
            if bass_file:
                bass_audio, bass_sr = sf.read(str(bass_file))
                if len(bass_audio.shape) > 1:
                    bass_audio = np.mean(bass_audio, axis=1)
            
            logger.info(f"Audio loaded - Drums: {len(drum_audio)/drum_sr:.1f}s, Bass: {len(bass_audio)/bass_sr:.1f}s if bass_audio else 'N/A'}")
            
            # Prepare audio data structure
            audio_data = {
                'drums': {
                    'audio': drum_audio,
                    'sample_rate': drum_sr,
                    'file_path': str(drum_file)
                }
            }
            
            if bass_audio is not None:
                audio_data['bass'] = {
                    'audio': bass_audio,
                    'sample_rate': bass_sr,
                    'file_path': str(bass_file)
                }
            
            # Prepare metadata
            metadata = {
                'drummer_id': drummer_id,
                'track_name': track_name,
                'tempo': tempo_context,
                'style': style_context,
                'source_file': f"{drummer_id}_{track_name}.mp3",
                'analysis_type': 'post_batch_complete_analysis',
                'batch_job_data': batch_job_data,
                'audio_data': audio_data
            }
            
            # Initialize services if not already done
            if not self.complete_system:
                if not self.initialize_services():
                    logger.error("Failed to initialize services")
                    return None
            
            # Run complete analysis
            logger.info("Starting DrumTracKAI Complete System analysis...")
            
            analysis_results = self.complete_system.analyze_complete_performance(
                audio_data=audio_data,
                tempo_context=tempo_context,
                style_context=style_context,
                metadata=metadata
            )
            
            logger.info("Complete analysis finished successfully")
            
            # Store results in database
            analysis_id = self.complete_system.store_complete_analysis(
                drummer_id=drummer_id,
                track_name=track_name,
                source_file=metadata['source_file'],
                analysis_results=analysis_results,
                metadata=metadata
            )
            
            if analysis_id <= 0:
                logger.error("Failed to store analysis results")
                return None
            
            logger.info(f"Analysis stored with ID: {analysis_id}")
            
            # Validate authenticity
            if self.authenticity_validator:
                logger.info("Running authenticity validation...")
                
                validation_report = self.authenticity_validator.validate_analysis_results(
                    analysis_results,
                    f"{drummer_id} - {track_name} (Post-Batch Complete Analysis)"
                )
                
                logger.info(f"Authenticity status: {validation_report['overall_authenticity']}")
                
                # Add validation to results
                analysis_results['authenticity_validation'] = validation_report
            
            # Prepare UI display data
            ui_display_data = {
                'analysis_id': analysis_id,
                'drummer_id': drummer_id,
                'track_name': track_name,
                'analysis_results': analysis_results,
                'authenticity_validation': analysis_results.get('authenticity_validation'),
                'timestamp': datetime.now().isoformat(),
                'status': 'completed'
            }
            
            logger.info("Post-batch complete analysis workflow finished successfully")
            
            return ui_display_data
            
        except Exception as e:
            logger.error(f"Post-batch processing failed: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return None
    
    def get_latest_analysis_for_drummer(self, drummer_id: str) -> Optional[Dict]:
        """Get the latest complete analysis for a drummer"""
        
        try:
            if not self.complete_system:
                if not self.initialize_services():
                    return None
            
            conn = sqlite3.connect(self.complete_system.db_path)
            c = conn.cursor()
            
            c.execute("""
                SELECT id, timestamp, track_name, standard_analysis, integrated_features
                FROM complete_analyses 
                WHERE drummer_id = ?
                ORDER BY timestamp DESC LIMIT 1
            """, (drummer_id,))
            
            result = c.fetchone()
            conn.close()
            
            if result:
                analysis_id, timestamp, track_name, standard_analysis, integrated_features = result
                
                import pickle
                analysis_results = pickle.loads(standard_analysis) if standard_analysis else {}
                metadata = pickle.loads(integrated_features) if integrated_features else {}
                
                return {
                    'analysis_id': analysis_id,
                    'timestamp': timestamp,
                    'drummer_id': drummer_id,
                    'track_name': track_name,
                    'analysis_results': analysis_results,
                    'metadata': metadata
                }
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to get latest analysis: {e}")
            return None
    
    def display_analysis_in_ui(self, ui_display_data: Dict):
        """Display analysis results in the UI (placeholder for UI integration)"""
        
        try:
            logger.info("Displaying analysis results in UI...")
            
            # This would integrate with the main UI to show results
            # For now, just log the key information
            
            drummer_id = ui_display_data.get('drummer_id', 'Unknown')
            track_name = ui_display_data.get('track_name', 'Unknown')
            analysis_id = ui_display_data.get('analysis_id', 'Unknown')
            
            logger.info(f"UI Display: {drummer_id} - {track_name} (Analysis ID: {analysis_id})")
            
            # Check authenticity status
            authenticity = ui_display_data.get('authenticity_validation', {})
            if authenticity:
                overall_status = authenticity.get('overall_authenticity', 'UNKNOWN')
                logger.info(f"Authenticity Status: {overall_status}")
            
            # This is where we would trigger the UI update
            # For example, emit a Qt signal or call a UI update method
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to display analysis in UI: {e}")
            return False

# Global instance for easy access
post_batch_integration = PostBatchCompleteIntegration()

def process_completed_batch(batch_job_data: Dict) -> Optional[Dict]:
    """Main entry point for processing completed batch jobs"""
    return post_batch_integration.process_batch_completion(batch_job_data)

def get_latest_analysis(drummer_id: str) -> Optional[Dict]:
    """Get latest analysis for a drummer"""
    return post_batch_integration.get_latest_analysis_for_drummer(drummer_id)

def display_results(ui_display_data: Dict) -> bool:
    """Display results in UI"""
    return post_batch_integration.display_analysis_in_ui(ui_display_data)

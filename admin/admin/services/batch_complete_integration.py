"""
Batch Processor Integration with DrumTracKAI Complete System
Connects MVSep output to comprehensive drummer analysis
"""

import os
import json
import logging
from typing import Dict, List, Optional, Any
from pathlib import Path
from datetime import datetime

from PySide6.QtCore import QObject, Signal, QThread, QTimer
from PySide6.QtWidgets import QApplication

from .drumtrackai_complete_system import DrumTracKAICompleteSystem
from .enhanced_complete_visualization import get_enhanced_complete_visualization

logger = logging.getLogger(__name__)

class BatchCompleteIntegrationWorker(QThread):
    """Worker thread for processing MVSep output through DrumTracKAI Complete System"""
    
    # Signals
    analysis_started = Signal(str)  # file_path
    analysis_progress = Signal(str, int)  # file_path, progress_percent
    analysis_completed = Signal(str, dict)  # file_path, analysis_results
    analysis_failed = Signal(str, str)  # file_path, error_message
    visualization_ready = Signal(str, object)  # file_path, figure
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.complete_system = None
        self.visualization_service = None
        self.pending_analyses = []
        self.current_analysis = None
        
    def initialize_services(self):
        """Initialize the complete system and visualization service"""
        try:
            self.complete_system = DrumTracKAICompleteSystem()
            self.visualization_service = get_enhanced_complete_visualization()
            logger.info("Batch complete integration services initialized")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize services: {e}")
            return False
    
    def add_analysis_job(self, job_data: Dict):
        """Add analysis job to the queue"""
        self.pending_analyses.append(job_data)
        logger.info(f"Added analysis job for: {job_data.get('source_file', 'Unknown')}")
    
    def run(self):
        """Main worker thread execution"""
        if not self.initialize_services():
            return
            
        while self.pending_analyses:
            job_data = self.pending_analyses.pop(0)
            self.current_analysis = job_data
            
            try:
                self._process_analysis_job(job_data)
            except Exception as e:
                logger.error(f"Analysis job failed: {e}")
                self.analysis_failed.emit(
                    job_data.get('source_file', 'Unknown'), 
                    str(e)
                )
            finally:
                self.current_analysis = None
    
    def _process_analysis_job(self, job_data: Dict):
        """Process a single analysis job"""
        source_file = job_data.get('source_file', '')
        stem_files = job_data.get('stem_files', {})
        metadata = job_data.get('metadata', {})
        
        logger.info(f"Starting complete analysis for: {source_file}")
        self.analysis_started.emit(source_file)
        
        # Progress tracking
        total_steps = 7
        current_step = 0
        
        def update_progress(step_name: str):
            nonlocal current_step
            current_step += 1
            progress = int((current_step / total_steps) * 100)
            logger.info(f"Analysis progress: {step_name} ({progress}%)")
            self.analysis_progress.emit(source_file, progress)
        
        try:
            # Step 1: Validate stem files
            update_progress("Validating stem files")
            if not self._validate_stem_files(stem_files):
                raise ValueError("Invalid or missing stem files")
            
            # Step 2: Load audio data
            update_progress("Loading audio data")
            audio_data = self._load_stem_audio_data(stem_files)
            
            # Step 3: Extract tempo and style context
            update_progress("Extracting tempo and style context")
            tempo_style_context = self._extract_tempo_style_context(metadata, audio_data)
            
            # Step 4: Run complete analysis
            update_progress("Running complete drummer analysis")
            analysis_results = self.complete_system.analyze_complete_performance(
                audio_data=audio_data,
                tempo_context=tempo_style_context.get('tempo', 120),
                style_context=tempo_style_context.get('style', 'rock'),
                metadata=metadata
            )
            
            # Step 5: Store results in database
            update_progress("Storing analysis results")
            self._store_analysis_results(source_file, analysis_results, metadata)
            
            # Step 6: Generate visualization
            update_progress("Generating visualization")
            visualization_figure = self._generate_visualization(analysis_results)
            
            # Step 7: Complete
            update_progress("Analysis complete")
            
            # Emit completion signals
            self.analysis_completed.emit(source_file, analysis_results)
            if visualization_figure:
                self.visualization_ready.emit(source_file, visualization_figure)
            
            logger.info(f"Complete analysis finished for: {source_file}")
            
        except Exception as e:
            logger.error(f"Analysis failed for {source_file}: {e}")
            self.analysis_failed.emit(source_file, str(e))
    
    def _validate_stem_files(self, stem_files: Dict) -> bool:
        """Validate that required stem files exist"""
        try:
            required_stems = ['drums', 'bass']  # Minimum required
            
            for stem_type in required_stems:
                if stem_type not in stem_files:
                    logger.warning(f"Missing required stem: {stem_type}")
                    return False
                
                file_path = stem_files[stem_type]
                if not os.path.exists(file_path):
                    logger.warning(f"Stem file not found: {file_path}")
                    return False
            
            logger.info(f"Validated {len(stem_files)} stem files")
            return True
            
        except Exception as e:
            logger.error(f"Stem validation error: {e}")
            return False
    
    def _load_stem_audio_data(self, stem_files: Dict) -> Dict:
        """Load audio data from stem files"""
        try:
            import librosa
            import numpy as np
            
            audio_data = {}
            
            for stem_type, file_path in stem_files.items():
                try:
                    # Load audio with librosa
                    y, sr = librosa.load(file_path, sr=44100)
                    audio_data[stem_type] = {
                        'audio': y,
                        'sample_rate': sr,
                        'duration': len(y) / sr,
                        'file_path': file_path
                    }
                    logger.debug(f"Loaded {stem_type}: {len(y)} samples at {sr}Hz")
                    
                except Exception as e:
                    logger.warning(f"Failed to load {stem_type} from {file_path}: {e}")
                    continue
            
            if not audio_data:
                raise ValueError("No audio data could be loaded from stem files")
            
            logger.info(f"Loaded audio data for {len(audio_data)} stems")
            return audio_data
            
        except Exception as e:
            logger.error(f"Audio loading error: {e}")
            raise
    
    def _extract_tempo_style_context(self, metadata: Dict, audio_data: Dict) -> Dict:
        """Extract tempo and style context from metadata and audio"""
        try:
            context = {}
            
            # Get tempo from metadata (from arrangement analysis)
            tempo = metadata.get('tempo', None)
            if tempo:
                context['tempo'] = int(round(tempo))
                logger.info(f"Using tempo from metadata: {context['tempo']} BPM")
            else:
                # Fallback: estimate tempo from drum audio
                if 'drums' in audio_data:
                    import librosa
                    y = audio_data['drums']['audio']
                    sr = audio_data['drums']['sample_rate']
                    
                    tempo, _ = librosa.beat.beat_track(y=y, sr=sr)
                    context['tempo'] = int(round(tempo))
                    logger.info(f"Estimated tempo from drums: {context['tempo']} BPM")
                else:
                    context['tempo'] = 120  # Default
                    logger.warning("Using default tempo: 120 BPM")
            
            # Get style from metadata
            style = metadata.get('style', metadata.get('genre', 'rock'))
            context['style'] = style.lower()
            logger.info(f"Using style: {context['style']}")
            
            # Get additional context
            context['key'] = metadata.get('key', 'C')
            context['time_signature'] = metadata.get('time_signature', '4/4')
            context['sections'] = metadata.get('sections', [])
            
            return context
            
        except Exception as e:
            logger.error(f"Context extraction error: {e}")
            return {'tempo': 120, 'style': 'rock'}
    
    def _store_analysis_results(self, source_file: str, analysis_results: Dict, metadata: Dict):
        """Store analysis results in the database"""
        try:
            # Extract drummer information
            drummer_id = metadata.get('drummer_id', 'unknown')
            track_name = metadata.get('track_name', Path(source_file).stem)
            
            # Store in complete system database
            analysis_id = self.complete_system.store_complete_analysis(
                drummer_id=drummer_id,
                track_name=track_name,
                source_file=source_file,
                analysis_results=analysis_results,
                metadata=metadata
            )
            
            logger.info(f"Stored analysis results with ID: {analysis_id}")
            
            # Update drummer profile with new analysis
            self.complete_system.update_drummer_profile(drummer_id, analysis_results)
            
        except Exception as e:
            logger.error(f"Failed to store analysis results: {e}")
            # Don't raise - analysis succeeded even if storage failed
    
    def _generate_visualization(self, analysis_results: Dict) -> Optional[object]:
        """Generate comprehensive visualization"""
        try:
            if not self.visualization_service:
                logger.warning("Visualization service not available")
                return None
            
            figure = self.visualization_service.create_complete_analysis_visualization(
                analysis_results
            )
            
            logger.info("Generated complete analysis visualization")
            return figure
            
        except Exception as e:
            logger.error(f"Visualization generation error: {e}")
            return None


class BatchCompleteIntegrationService(QObject):
    """Service for integrating batch processor with DrumTracKAI Complete System"""
    
    # Signals
    integration_ready = Signal()
    analysis_queued = Signal(str)  # file_path
    analysis_started = Signal(str)  # file_path
    analysis_progress = Signal(str, int)  # file_path, progress
    analysis_completed = Signal(str, dict)  # file_path, results
    analysis_failed = Signal(str, str)  # file_path, error
    visualization_ready = Signal(str, object)  # file_path, figure
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.worker = None
        self.worker_thread = None
        self.is_initialized = False
        self.pending_jobs = []
        
    def initialize(self) -> bool:
        """Initialize the integration service"""
        try:
            # Create worker thread
            self.worker = BatchCompleteIntegrationWorker()
            self.worker_thread = QThread()
            self.worker.moveToThread(self.worker_thread)
            
            # Connect signals
            self.worker.analysis_started.connect(self.analysis_started)
            self.worker.analysis_progress.connect(self.analysis_progress)
            self.worker.analysis_completed.connect(self.analysis_completed)
            self.worker.analysis_failed.connect(self.analysis_failed)
            self.worker.visualization_ready.connect(self.visualization_ready)
            
            # Start worker thread
            self.worker_thread.started.connect(self.worker.run)
            self.worker_thread.start()
            
            self.is_initialized = True
            self.integration_ready.emit()
            
            logger.info("Batch complete integration service initialized")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize integration service: {e}")
            return False
    
    def process_mvsep_output(self, mvsep_result: Dict):
        """Process MVSep output through complete analysis"""
        try:
            if not self.is_initialized:
                logger.error("Integration service not initialized")
                return False
            
            # Extract job data from MVSep result
            job_data = self._prepare_analysis_job(mvsep_result)
            
            if not job_data:
                logger.error("Failed to prepare analysis job from MVSep result")
                return False
            
            # Add to worker queue
            if self.worker:
                self.worker.add_analysis_job(job_data)
                self.analysis_queued.emit(job_data.get('source_file', 'Unknown'))
                logger.info(f"Queued complete analysis for: {job_data.get('source_file')}")
                return True
            else:
                logger.error("Worker not available")
                return False
                
        except Exception as e:
            logger.error(f"Failed to process MVSep output: {e}")
            return False
    
    def _prepare_analysis_job(self, mvsep_result: Dict) -> Optional[Dict]:
        """Prepare analysis job data from MVSep result"""
        try:
            # Extract source file information
            source_file = mvsep_result.get('source_file', '')
            if not source_file:
                logger.error("No source file in MVSep result")
                return None
            
            # Extract stem files
            stem_files = {}
            output_files = mvsep_result.get('output_files', {})
            
            for stem_type, file_path in output_files.items():
                if os.path.exists(file_path):
                    stem_files[stem_type] = file_path
                else:
                    logger.warning(f"Output file not found: {file_path}")
            
            if not stem_files:
                logger.error("No valid stem files found in MVSep result")
                return None
            
            # Extract metadata
            metadata = mvsep_result.get('metadata', {})
            
            # Add timestamp
            metadata['analysis_timestamp'] = datetime.now().isoformat()
            metadata['mvsep_job_id'] = mvsep_result.get('job_id', '')
            
            job_data = {
                'source_file': source_file,
                'stem_files': stem_files,
                'metadata': metadata,
                'job_id': f"complete_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            }
            
            logger.info(f"Prepared analysis job with {len(stem_files)} stems")
            return job_data
            
        except Exception as e:
            logger.error(f"Failed to prepare analysis job: {e}")
            return None
    
    def get_analysis_results(self, source_file: str) -> Optional[Dict]:
        """Get stored analysis results for a source file"""
        try:
            if not self.worker or not self.worker.complete_system:
                return None
            
            return self.worker.complete_system.get_analysis_by_source_file(source_file)
            
        except Exception as e:
            logger.error(f"Failed to get analysis results: {e}")
            return None
    
    def shutdown(self):
        """Shutdown the integration service"""
        try:
            if self.worker_thread and self.worker_thread.isRunning():
                self.worker_thread.quit()
                self.worker_thread.wait(5000)  # Wait up to 5 seconds
                
            self.is_initialized = False
            logger.info("Batch complete integration service shutdown")
            
        except Exception as e:
            logger.error(f"Error during shutdown: {e}")


# Global service instance
_integration_service = None

def get_batch_complete_integration() -> BatchCompleteIntegrationService:
    """Get the global batch complete integration service"""
    global _integration_service
    if _integration_service is None:
        _integration_service = BatchCompleteIntegrationService()
    return _integration_service

def initialize_batch_complete_integration() -> bool:
    """Initialize the global batch complete integration service"""
    service = get_batch_complete_integration()
    return service.initialize()

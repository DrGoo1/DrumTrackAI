"""
Batch Processor Complete System Integration
Adds DrumTracKAI Complete System integration to the existing batch processor
"""

import logging
from typing import Dict, Optional

logger = logging.getLogger(__name__)

class BatchProcessorCompleteIntegration:
    """Integration methods for connecting batch processor to complete system"""
    
    def __init__(self, batch_processor_widget):
        self.widget = batch_processor_widget
        self.complete_system_handler = None
        self.enable_complete_analysis = True
        
    def initialize_complete_system_integration(self) -> bool:
        """Initialize complete system integration"""
        try:
            # Import here to avoid circular imports
            from ui.complete_system_integration_handler import get_complete_system_integration_handler
            
            self.complete_system_handler = get_complete_system_integration_handler()
            
            if self.complete_system_handler.initialize():
                logger.info("Complete system integration initialized successfully")
                return True
            else:
                logger.error("Failed to initialize complete system integration")
                return False
                
        except ImportError as e:
            logger.warning(f"Complete system integration not available: {e}")
            return False
        except Exception as e:
            logger.error(f"Error initializing complete system integration: {e}")
            return False
    
    def handle_mvsep_completion(self, batch_id: str, file_path: str, output_files: Dict):
        """Handle MVSep completion and trigger complete analysis"""
        try:
            if not self.enable_complete_analysis or not self.complete_system_handler:
                logger.debug("Complete analysis disabled or handler not available")
                return
            
            # Prepare MVSep result for complete analysis
            mvsep_result = {
                'source_file': file_path,
                'output_files': output_files,
                'batch_id': batch_id,
                'metadata': self._extract_metadata_for_analysis(file_path, output_files)
            }
            
            # Trigger complete analysis
            success = self.complete_system_handler.handle_mvsep_completion(mvsep_result)
            
            if success:
                logger.info(f"Triggered complete analysis for: {file_path}")
            else:
                logger.warning(f"Failed to trigger complete analysis for: {file_path}")
                
        except Exception as e:
            logger.error(f"Error handling MVSep completion for complete analysis: {e}")
    
    def _extract_metadata_for_analysis(self, file_path: str, output_files: Dict) -> Dict:
        """Extract metadata needed for complete analysis"""
        try:
            import os
            from pathlib import Path
            
            metadata = {
                'source_file': file_path,
                'track_name': Path(file_path).stem,
                'output_directory': os.path.dirname(list(output_files.values())[0]) if output_files else '',
                'stem_count': len(output_files),
                'processing_timestamp': self._get_current_timestamp(),
            }
            
            # Try to extract additional metadata from the widget if available
            if hasattr(self.widget, '_current_metadata'):
                metadata.update(self.widget._current_metadata)
            
            return metadata
            
        except Exception as e:
            logger.error(f"Error extracting metadata: {e}")
            return {'source_file': file_path}
    
    def _get_current_timestamp(self) -> str:
        """Get current timestamp as ISO string"""
        from datetime import datetime
        return datetime.now().isoformat()
    
    def set_complete_analysis_enabled(self, enabled: bool):
        """Enable or disable complete analysis"""
        self.enable_complete_analysis = enabled
        logger.info(f"Complete analysis {'enabled' if enabled else 'disabled'}")
    
    def is_complete_analysis_available(self) -> bool:
        """Check if complete analysis is available"""
        return self.complete_system_handler is not None
    
    def shutdown(self):
        """Shutdown complete system integration"""
        try:
            if self.complete_system_handler:
                self.complete_system_handler.shutdown()
            logger.info("Complete system integration shutdown")
        except Exception as e:
            logger.error(f"Error during complete system integration shutdown: {e}")


def add_complete_system_integration(batch_processor_widget):
    """Add complete system integration to an existing batch processor widget"""
    try:
        # Create integration instance
        integration = BatchProcessorCompleteIntegration(batch_processor_widget)
        
        # Add to widget
        batch_processor_widget.complete_system_integration = integration
        
        # Add methods to widget
        batch_processor_widget._initialize_complete_system_integration = integration.initialize_complete_system_integration
        batch_processor_widget._handle_mvsep_completion_for_complete_analysis = integration.handle_mvsep_completion
        batch_processor_widget.set_complete_analysis_enabled = integration.set_complete_analysis_enabled
        batch_processor_widget.is_complete_analysis_available = integration.is_complete_analysis_available
        
        # Initialize
        success = integration.initialize_complete_system_integration()
        
        if success:
            logger.info("Successfully added complete system integration to batch processor")
            
            # Hook into existing completion handler
            if hasattr(batch_processor_widget, '_on_file_completed'):
                original_on_file_completed = batch_processor_widget._on_file_completed
                
                def enhanced_on_file_completed(batch_id, file_path, output_files, file_index, total_files):
                    # Call original handler
                    original_on_file_completed(batch_id, file_path, output_files, file_index, total_files)
                    
                    # Trigger complete analysis
                    integration.handle_mvsep_completion(batch_id, file_path, output_files)
                
                batch_processor_widget._on_file_completed = enhanced_on_file_completed
                logger.info("Enhanced file completion handler with complete analysis")
        
        return success
        
    except Exception as e:
        logger.error(f"Failed to add complete system integration: {e}")
        return False

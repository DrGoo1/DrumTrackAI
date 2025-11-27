"""
Training Service for Admin App
Integrates training system into the service container
"""

import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

try:
    from admin.training.data_extraction import SDSampleExtractor, CommercialSongAnalyzer, SensorDataCollector
    from admin.training.dataset_builder import DrumDatasetBuilder
    from admin.training.model_trainer import AutonomousTrainer, TrainingConfig
    from admin.training.validation import ModelValidator
    from admin.training.deployment import ModelDeployer
    TRAINING_AVAILABLE = True
except ImportError as e:
    logger.warning(f"Training modules not available: {e}")
    TRAINING_AVAILABLE = False


class TrainingService:
    """
    Service that manages the training system
    Registers with the admin app's service container
    """
    
    def __init__(self):
        if not TRAINING_AVAILABLE:
            logger.warning("Training service initialized but modules not available")
            self.available = False
            return
        
        self.available = True
        
        # Initialize components
        self.sd_extractor = SDSampleExtractor()
        self.song_analyzer = CommercialSongAnalyzer()
        self.sensor_collector = SensorDataCollector()
        self.dataset_builder = DrumDatasetBuilder()
        self.validator = ModelValidator()
        self.deployer = ModelDeployer()
        
        # Training state
        self.current_trainer: Optional[AutonomousTrainer] = None
        self.current_dataset = None
        self.is_training = False
        
        logger.info("Training Service initialized successfully")
    
    def get_data_stats(self) -> dict:
        """Get statistics about available training data"""
        if not self.available:
            return {'error': 'Training not available'}
        
        return self.dataset_builder.get_dataset_stats()
    
    def extract_sd_samples(self, limit: int = 100) -> int:
        """Extract Superior Drummer samples"""
        if not self.available:
            raise RuntimeError("Training not available")
        
        return self.sd_extractor.batch_extract(limit=limit)
    
    def analyze_commercial_songs(self, audio_paths: list) -> int:
        """Analyze commercial songs"""
        if not self.available:
            raise RuntimeError("Training not available")
        
        count = 0
        for audio_path in audio_paths:
            features = self.song_analyzer.analyze_song(Path(audio_path))
            if features:
                count += 1
        
        return count
    
    def build_dataset(self, min_samples: int = 50):
        """Build training dataset"""
        if not self.available:
            raise RuntimeError("Training not available")
        
        self.current_dataset = self.dataset_builder.build_humanization_dataset(
            min_samples=min_samples
        )
        
        return self.current_dataset
    
    def create_trainer(self, config: TrainingConfig = None) -> AutonomousTrainer:
        """Create new trainer instance"""
        if not self.available:
            raise RuntimeError("Training not available")
        
        self.current_trainer = AutonomousTrainer(config or TrainingConfig())
        self.current_trainer.create_model(input_size=3, output_size=9)
        
        return self.current_trainer
    
    def get_deployed_models(self) -> list:
        """Get list of deployed models"""
        if not self.available:
            return []
        
        return self.deployer.list_models()
    
    def set_active_model(self, model_name: str, version: str) -> bool:
        """Set active model version"""
        if not self.available:
            return False
        
        return self.deployer.set_active_model(model_name, version)
    
    def get_active_model(self, model_name: str = "drum_humanizer") -> Optional[dict]:
        """Get active model info"""
        if not self.available:
            return None
        
        return self.deployer.get_active_model(model_name)
    
    def shutdown(self):
        """Shutdown the training service"""
        if self.current_trainer and self.is_training:
            logger.info("Stopping active training...")
            self.current_trainer.stop_training()
        
        logger.info("Training Service shutdown complete")


# Factory function for service container
def create_training_service() -> TrainingService:
    """Factory function for creating the training service"""
    return TrainingService()

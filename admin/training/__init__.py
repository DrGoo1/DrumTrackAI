"""
DrumTracKAI Training Module
Autonomous LLM training system for learning human drum performance characteristics
"""

__version__ = "1.0.0"
__author__ = "DrumTracKAI Team"

from .data_extraction import SDSampleExtractor, CommercialSongAnalyzer, SensorDataCollector
from .dataset_builder import DrumDatasetBuilder, HumanizationDataset
from .model_trainer import DrumHumanizationModel, AutonomousTrainer
from .validation import ModelValidator, HumanEvaluator
from .deployment import ModelDeployer

# Database bootstrapper for quick knowledge base building
try:
    from .database_bootstrapper import (
        EGMDExtractor, 
        RudimentsExtractor, 
        SoundsTracksLoopsExtractor,
        bootstrap_knowledge_base
    )
    BOOTSTRAP_AVAILABLE = True
except ImportError:
    BOOTSTRAP_AVAILABLE = False

# YouTube downloader for training data
try:
    from .youtube_downloader import (
        YouTubeDrumDownloader,
        batch_download_drummer,
        FAMOUS_DRUMMER_SEARCHES
    )
    YOUTUBE_AVAILABLE = True
except ImportError:
    YOUTUBE_AVAILABLE = False

__all__ = [
    'SDSampleExtractor',
    'CommercialSongAnalyzer',
    'SensorDataCollector',
    'DrumDatasetBuilder',
    'HumanizationDataset',
    'DrumHumanizationModel',
    'AutonomousTrainer',
    'ModelValidator',
    'HumanEvaluator',
    'ModelDeployer',
]

# Add bootstrap exports if available
if BOOTSTRAP_AVAILABLE:
    __all__.extend([
        'EGMDExtractor',
        'RudimentsExtractor',
        'SoundsTracksLoopsExtractor',
        'bootstrap_knowledge_base'
    ])

# Add YouTube exports if available
if YOUTUBE_AVAILABLE:
    __all__.extend([
        'YouTubeDrumDownloader',
        'batch_download_drummer',
        'FAMOUS_DRUMMER_SEARCHES'
    ])

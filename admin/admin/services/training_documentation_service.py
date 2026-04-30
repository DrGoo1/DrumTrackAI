"""
Training Documentation Service for DrumTracKAI
==============================================
Comprehensive tracking and documentation of model training sophistication,
including training data, parameters, performance metrics, and capabilities.

Features:
- Training session documentation
- Model capability tracking
- Performance metrics logging
- Data provenance tracking
- Sophistication scoring
- Reproducibility documentation
"""

import logging
import os
import json
import sqlite3
import hashlib
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime
from dataclasses import dataclass, field, asdict

logger = logging.getLogger(__name__)

@dataclass
class TrainingDataset:
    """Documentation of a training dataset"""
    name: str
    path: str
    file_count: int
    total_size_mb: float
    categories: List[str]
    file_types: List[str]
    description: str
    data_hash: str = ""
    quality_score: float = 0.0
    coverage_score: float = 0.0

@dataclass
class TrainingPhase:
    """Documentation of a training phase"""
    phase_name: str
    phase_number: int
    datasets_used: List[str]
    start_time: str
    end_time: str
    duration_hours: float
    epochs: int
    batch_size: int
    learning_rate: float
    final_loss: float
    final_accuracy: float
    best_accuracy: float
    convergence_epoch: int
    model_parameters: int
    sophistication_score: float = 0.0

@dataclass
class ModelCapabilities:
    """Documentation of model capabilities and sophistication"""
    # Basic recognition capabilities
    individual_drum_recognition: float = 0.0
    rudiment_recognition: float = 0.0
    dynamics_recognition: float = 0.0
    timing_precision: float = 0.0
    
    # Pattern recognition capabilities
    pattern_classification: float = 0.0
    style_recognition: float = 0.0
    fill_detection: float = 0.0
    groove_analysis: float = 0.0
    
    # Professional capabilities
    technique_identification: float = 0.0
    humanness_detection: float = 0.0
    signature_analysis: float = 0.0
    complexity_scoring: float = 0.0
    
    # Advanced capabilities
    real_time_processing: bool = False
    multi_track_analysis: bool = False
    genre_classification: bool = False
    drummer_identification: bool = False
    
    # Overall sophistication metrics
    overall_sophistication: float = 0.0
    confidence_level: float = 0.0
    reliability_score: float = 0.0

@dataclass
class TrainingSession:
    """Complete documentation of a training session"""
    session_id: str
    session_name: str
    model_architecture: str
    start_time: str
    end_time: str
    total_duration_hours: float
    
    # Training configuration
    python_version: str
    pytorch_version: str
    cuda_version: str
    environment_hash: str
    
    # Data used
    datasets: List[TrainingDataset] = field(default_factory=list)
    total_training_files: int = 0
    total_training_size_gb: float = 0.0
    
    # Training phases
    phases: List[TrainingPhase] = field(default_factory=list)
    
    # Final model
    model_path: str = ""
    model_size_mb: float = 0.0
    model_hash: str = ""
    
    # Performance metrics
    capabilities: ModelCapabilities = field(default_factory=ModelCapabilities)
    
    # Validation results
    validation_accuracy: float = 0.0
    test_accuracy: float = 0.0
    cross_validation_scores: List[float] = field(default_factory=list)
    
    # Sophistication assessment
    sophistication_level: str = "Unknown"  # Basic, Intermediate, Advanced, Expert, Master
    sophistication_score: float = 0.0
    capability_breakdown: Dict[str, float] = field(default_factory=dict)
    
    # Documentation
    training_notes: str = ""
    known_limitations: List[str] = field(default_factory=list)
    recommended_use_cases: List[str] = field(default_factory=list)
    
    # Reproducibility
    random_seed: int = 42
    reproducible: bool = True
    reproduction_instructions: str = ""

class TrainingDocumentationService:
    """Service for tracking and documenting training sophistication"""
    
    def __init__(self, db_path: str = None):
        self.db_path = db_path or "training_documentation.db"
        self._initialize_database()
        
    def _initialize_database(self):
        """Initialize the training documentation database"""
        try:
            self.conn = sqlite3.connect(self.db_path)
            self.conn.row_factory = sqlite3.Row
            
            # Create tables
            self.conn.executescript("""
                CREATE TABLE IF NOT EXISTS training_sessions (
                    session_id TEXT PRIMARY KEY,
                    session_data TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                
                CREATE TABLE IF NOT EXISTS model_versions (
                    version_id TEXT PRIMARY KEY,
                    session_id TEXT NOT NULL,
                    model_path TEXT NOT NULL,
                    sophistication_score REAL NOT NULL,
                    capabilities TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (session_id) REFERENCES training_sessions (session_id)
                );
                
                CREATE TABLE IF NOT EXISTS performance_benchmarks (
                    benchmark_id TEXT PRIMARY KEY,
                    session_id TEXT NOT NULL,
                    test_name TEXT NOT NULL,
                    test_results TEXT NOT NULL,
                    score REAL NOT NULL,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (session_id) REFERENCES training_sessions (session_id)
                );
            """)
            
            self.conn.commit()
            logger.info("Training documentation database initialized")
            
        except Exception as e:
            logger.error(f"Error initializing database: {e}")
            raise
    
    def create_training_session(self, session_name: str, model_architecture: str) -> str:
        """Create a new training session documentation"""
        session_id = f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        session = TrainingSession(
            session_id=session_id,
            session_name=session_name,
            model_architecture=model_architecture,
            start_time=datetime.now().isoformat(),
            end_time="",
            total_duration_hours=0.0,
            python_version=self._get_python_version(),
            pytorch_version=self._get_pytorch_version(),
            cuda_version=self._get_cuda_version(),
            environment_hash=self._get_environment_hash()
        )
        
        self._save_session(session)
        logger.info(f"Created training session: {session_id}")
        return session_id
    
    def add_dataset_to_session(self, session_id: str, dataset: TrainingDataset):
        """Add dataset documentation to a training session"""
        session = self._load_session(session_id)
        if session:
            dataset.data_hash = self._calculate_dataset_hash(dataset.path)
            session.datasets.append(dataset)
            session.total_training_files += dataset.file_count
            session.total_training_size_gb += dataset.total_size_mb / 1024
            self._save_session(session)
            logger.info(f"Added dataset {dataset.name} to session {session_id}")
    
    def add_training_phase(self, session_id: str, phase: TrainingPhase):
        """Add training phase documentation"""
        session = self._load_session(session_id)
        if session:
            phase.sophistication_score = self._calculate_phase_sophistication(phase)
            session.phases.append(phase)
            self._save_session(session)
            logger.info(f"Added training phase {phase.phase_name} to session {session_id}")
    
    def finalize_training_session(self, session_id: str, model_path: str, 
                                 capabilities: ModelCapabilities, 
                                 validation_results: Dict[str, float],
                                 notes: str = "") -> Dict[str, Any]:
        """Finalize training session with final results and sophistication assessment"""
        session = self._load_session(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")
        
        # Update session with final information
        session.end_time = datetime.now().isoformat()
        session.model_path = model_path
        session.capabilities = capabilities
        session.validation_accuracy = validation_results.get('validation_accuracy', 0.0)
        session.test_accuracy = validation_results.get('test_accuracy', 0.0)
        session.training_notes = notes
        
        # Calculate sophistication metrics
        session.sophistication_score = self._calculate_overall_sophistication(session)
        session.sophistication_level = self._determine_sophistication_level(session.sophistication_score)
        session.capability_breakdown = self._analyze_capability_breakdown(capabilities)
        
        # Calculate total duration
        if session.phases:
            session.total_duration_hours = sum(phase.duration_hours for phase in session.phases)
        
        # Generate model hash and size
        if os.path.exists(model_path):
            session.model_hash = self._calculate_file_hash(model_path)
            session.model_size_mb = os.path.getsize(model_path) / (1024 * 1024)
        
        # Generate reproduction instructions
        session.reproduction_instructions = self._generate_reproduction_instructions(session)
        
        # Save final session
        self._save_session(session)
        
        # Create model version record
        self._create_model_version(session)
        
        # Generate comprehensive report
        report = self._generate_sophistication_report(session)
        
        logger.info(f"Finalized training session {session_id} with sophistication level: {session.sophistication_level}")
        return report
    
    def get_training_history(self) -> List[Dict[str, Any]]:
        """Get complete training history"""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT session_id, session_data, created_at 
            FROM training_sessions 
            ORDER BY created_at DESC
        """)
        
        history = []
        for row in cursor.fetchall():
            session_data = json.loads(row['session_data'])
            history.append({
                'session_id': row['session_id'],
                'session_name': session_data.get('session_name', 'Unknown'),
                'sophistication_level': session_data.get('sophistication_level', 'Unknown'),
                'sophistication_score': session_data.get('sophistication_score', 0.0),
                'created_at': row['created_at']
            })
        
        return history
    
    def get_current_model_capabilities(self) -> Optional[Dict[str, Any]]:
        """Get capabilities of the most recent model"""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT session_data FROM training_sessions 
            ORDER BY created_at DESC LIMIT 1
        """)
        
        row = cursor.fetchone()
        if row:
            session_data = json.loads(row['session_data'])
            return {
                'sophistication_level': session_data.get('sophistication_level', 'Unknown'),
                'sophistication_score': session_data.get('sophistication_score', 0.0),
                'capabilities': session_data.get('capabilities', {}),
                'capability_breakdown': session_data.get('capability_breakdown', {}),
                'model_architecture': session_data.get('model_architecture', 'Unknown'),
                'total_training_files': session_data.get('total_training_files', 0),
                'total_duration_hours': session_data.get('total_duration_hours', 0.0)
            }
        
        return None
    
    def _calculate_overall_sophistication(self, session: TrainingSession) -> float:
        """Calculate overall sophistication score"""
        # Base score from capabilities
        cap = session.capabilities
        capability_score = (
            cap.individual_drum_recognition * 0.15 +
            cap.rudiment_recognition * 0.10 +
            cap.pattern_classification * 0.20 +
            cap.style_recognition * 0.15 +
            cap.technique_identification * 0.15 +
            cap.humanness_detection * 0.10 +
            cap.signature_analysis * 0.15
        )
        
        # Bonus for advanced capabilities
        advanced_bonus = 0.0
        if cap.real_time_processing: advanced_bonus += 0.05
        if cap.multi_track_analysis: advanced_bonus += 0.05
        if cap.genre_classification: advanced_bonus += 0.03
        if cap.drummer_identification: advanced_bonus += 0.07
        
        # Training data quality bonus
        data_bonus = min(0.1, len(session.datasets) * 0.02)
        
        # Training duration bonus (more training = higher sophistication)
        duration_bonus = min(0.1, session.total_duration_hours / 50.0)
        
        total_score = capability_score + advanced_bonus + data_bonus + duration_bonus
        return min(1.0, total_score)
    
    def _determine_sophistication_level(self, score: float) -> str:
        """Determine sophistication level from score"""
        if score >= 0.95: return "Master"
        elif score >= 0.85: return "Expert"
        elif score >= 0.70: return "Advanced"
        elif score >= 0.50: return "Intermediate"
        else: return "Basic"
    
    def _generate_sophistication_report(self, session: TrainingSession) -> Dict[str, Any]:
        """Generate comprehensive sophistication report"""
        return {
            'session_summary': {
                'session_id': session.session_id,
                'session_name': session.session_name,
                'model_architecture': session.model_architecture,
                'sophistication_level': session.sophistication_level,
                'sophistication_score': session.sophistication_score,
                'total_duration_hours': session.total_duration_hours
            },
            'training_data': {
                'total_datasets': len(session.datasets),
                'total_files': session.total_training_files,
                'total_size_gb': session.total_training_size_gb,
                'dataset_breakdown': [
                    {
                        'name': ds.name,
                        'files': ds.file_count,
                        'categories': ds.categories
                    } for ds in session.datasets
                ]
            },
            'model_capabilities': asdict(session.capabilities),
            'capability_breakdown': session.capability_breakdown,
            'training_phases': [
                {
                    'phase': phase.phase_name,
                    'duration_hours': phase.duration_hours,
                    'final_accuracy': phase.final_accuracy,
                    'sophistication_score': phase.sophistication_score
                } for phase in session.phases
            ],
            'performance_metrics': {
                'validation_accuracy': session.validation_accuracy,
                'test_accuracy': session.test_accuracy,
                'confidence_level': session.capabilities.confidence_level
            },
            'reproducibility': {
                'reproducible': session.reproducible,
                'environment_hash': session.environment_hash,
                'model_hash': session.model_hash,
                'reproduction_instructions': session.reproduction_instructions
            }
        }
    
    def _save_session(self, session: TrainingSession):
        """Save session to database"""
        session_data = json.dumps(asdict(session), indent=2)
        now = datetime.now().isoformat()
        
        self.conn.execute("""
            INSERT OR REPLACE INTO training_sessions 
            (session_id, session_data, created_at, updated_at)
            VALUES (?, ?, ?, ?)
        """, (session.session_id, session_data, now, now))
        self.conn.commit()
    
    def _load_session(self, session_id: str) -> Optional[TrainingSession]:
        """Load session from database"""
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT session_data FROM training_sessions WHERE session_id = ?",
            (session_id,)
        )
        
        row = cursor.fetchone()
        if row:
            session_dict = json.loads(row['session_data'])
            # Convert back to TrainingSession object
            return TrainingSession(**session_dict)
        
        return None
    
    def _calculate_dataset_hash(self, path: str) -> str:
        """Calculate hash of dataset for reproducibility"""
        if not os.path.exists(path):
            return ""
        
        # Create hash based on file list and sizes
        hasher = hashlib.md5()
        for root, dirs, files in os.walk(path):
            for file in sorted(files):
                file_path = os.path.join(root, file)
                if os.path.isfile(file_path):
                    hasher.update(file.encode())
                    hasher.update(str(os.path.getsize(file_path)).encode())
        
        return hasher.hexdigest()
    
    def _calculate_file_hash(self, file_path: str) -> str:
        """Calculate hash of a file"""
        if not os.path.exists(file_path):
            return ""
        
        hasher = hashlib.md5()
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hasher.update(chunk)
        
        return hasher.hexdigest()
    
    def _get_python_version(self) -> str:
        """Get Python version"""
        import sys
        return f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    
    def _get_pytorch_version(self) -> str:
        """Get PyTorch version"""
        try:
            import torch
            return torch.__version__
        except ImportError:
            return "Unknown"
    
    def _get_cuda_version(self) -> str:
        """Get CUDA version"""
        try:
            import torch
            return torch.version.cuda if torch.cuda.is_available() else "CPU"
        except ImportError:
            return "Unknown"
    
    def _get_environment_hash(self) -> str:
        """Get environment hash for reproducibility"""
        # Create hash based on key environment factors
        hasher = hashlib.md5()
        hasher.update(self._get_python_version().encode())
        hasher.update(self._get_pytorch_version().encode())
        hasher.update(self._get_cuda_version().encode())
        return hasher.hexdigest()
    
    def _calculate_phase_sophistication(self, phase: TrainingPhase) -> float:
        """Calculate sophistication score for a training phase"""
        # Base score from accuracy
        accuracy_score = phase.final_accuracy
        
        # Bonus for convergence efficiency
        convergence_bonus = max(0, (phase.epochs - phase.convergence_epoch) / phase.epochs * 0.1)
        
        # Bonus for training duration (more epochs = more sophistication)
        duration_bonus = min(0.1, phase.epochs / 100.0)
        
        return min(1.0, accuracy_score + convergence_bonus + duration_bonus)
    
    def _analyze_capability_breakdown(self, capabilities: ModelCapabilities) -> Dict[str, float]:
        """Analyze capability breakdown"""
        return {
            'Basic Recognition': (
                capabilities.individual_drum_recognition +
                capabilities.rudiment_recognition +
                capabilities.dynamics_recognition +
                capabilities.timing_precision
            ) / 4,
            'Pattern Analysis': (
                capabilities.pattern_classification +
                capabilities.style_recognition +
                capabilities.fill_detection +
                capabilities.groove_analysis
            ) / 4,
            'Professional Skills': (
                capabilities.technique_identification +
                capabilities.humanness_detection +
                capabilities.signature_analysis +
                capabilities.complexity_scoring
            ) / 4,
            'Advanced Features': sum([
                capabilities.real_time_processing,
                capabilities.multi_track_analysis,
                capabilities.genre_classification,
                capabilities.drummer_identification
            ]) / 4
        }
    
    def _generate_reproduction_instructions(self, session: TrainingSession) -> str:
        """Generate instructions for reproducing this training"""
        instructions = f"""
# Reproduction Instructions for {session.session_name}

## Environment Setup
- Python: {session.python_version}
- PyTorch: {session.pytorch_version}
- CUDA: {session.cuda_version}
- Environment Hash: {session.environment_hash}

## Training Data
"""
        for dataset in session.datasets:
            instructions += f"- {dataset.name}: {dataset.file_count} files from {dataset.path}\n"
        
        instructions += f"""
## Training Configuration
- Model Architecture: {session.model_architecture}
- Total Training Time: {session.total_duration_hours:.1f} hours
- Random Seed: {session.random_seed}

## Training Phases
"""
        for i, phase in enumerate(session.phases, 1):
            instructions += f"""
### Phase {i}: {phase.phase_name}
- Epochs: {phase.epochs}
- Batch Size: {phase.batch_size}
- Learning Rate: {phase.learning_rate}
- Final Accuracy: {phase.final_accuracy:.4f}
"""
        
        instructions += f"""
## Expected Results
- Sophistication Level: {session.sophistication_level}
- Sophistication Score: {session.sophistication_score:.4f}
- Validation Accuracy: {session.validation_accuracy:.4f}
- Model Hash: {session.model_hash}
"""
        
        return instructions
    
    def _create_model_version(self, session: TrainingSession):
        """Create model version record"""
        version_id = f"v{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        self.conn.execute("""
            INSERT INTO model_versions 
            (version_id, session_id, model_path, sophistication_score, capabilities, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            version_id,
            session.session_id,
            session.model_path,
            session.sophistication_score,
            json.dumps(asdict(session.capabilities)),
            datetime.now().isoformat()
        ))
        self.conn.commit()


# Example usage
if __name__ == "__main__":
    # Initialize service
    doc_service = TrainingDocumentationService()
    
    # Create training session
    session_id = doc_service.create_training_session(
        "DrumTracKAI Expert Training",
        "DrumTracKAI-Expert (Maximum sophistication)"
    )
    
    # Add datasets
    dataset = TrainingDataset(
        name="SD3 Extracted Samples",
        path="E:\\DrumTracKAI_Database\\sd3_extracted_samples",
        file_count=500,
        total_size_mb=600.0,
        categories=["Kick", "Snare", "Hihat", "Crash", "Ride"],
        file_types=[".wav"],
        description="Superior Drummer 3 generated samples"
    )
    doc_service.add_dataset_to_session(session_id, dataset)
    
    # Add training phase
    phase = TrainingPhase(
        phase_name="Foundational Recognition",
        phase_number=1,
        datasets_used=["SD3 Extracted Samples"],
        start_time=datetime.now().isoformat(),
        end_time=datetime.now().isoformat(),
        duration_hours=4.0,
        epochs=75,
        batch_size=32,
        learning_rate=0.0001,
        final_loss=0.05,
        final_accuracy=0.95,
        best_accuracy=0.96,
        convergence_epoch=65,
        model_parameters=8000000
    )
    doc_service.add_training_phase(session_id, phase)
    
    # Finalize with capabilities
    capabilities = ModelCapabilities(
        individual_drum_recognition=0.95,
        rudiment_recognition=0.92,
        pattern_classification=0.88,
        style_recognition=0.85,
        technique_identification=0.82,
        humanness_detection=0.78,
        signature_analysis=0.75,
        real_time_processing=True,
        overall_sophistication=0.87
    )
    
    validation_results = {
        'validation_accuracy': 0.93,
        'test_accuracy': 0.91
    }
    
    report = doc_service.finalize_training_session(
        session_id,
        "models/foundational/foundational_model.pth",
        capabilities,
        validation_results,
        "Expert model training completed successfully with comprehensive database coverage."
    )
    
    print("Training Documentation Complete!")
    print(f"Sophistication Level: {report['session_summary']['sophistication_level']}")
    print(f"Sophistication Score: {report['session_summary']['sophistication_score']:.4f}")

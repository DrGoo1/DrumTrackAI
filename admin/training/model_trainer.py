"""
Model Trainer for Drum Humanization AI
Autonomous training system that learns humanization from real drummers
"""

import os
import json
import time
import logging
import numpy as np
from pathlib import Path
from typing import Dict, List, Optional, Callable
from dataclasses import dataclass
from datetime import datetime

logger = logging.getLogger(__name__)

# Check for PyTorch
try:
    import torch
    import torch.nn as nn
    import torch.optim as optim
    from torch.utils.data import DataLoader, TensorDataset
    TORCH_AVAILABLE = True
except ImportError:
    logger.warning("PyTorch not available - model training disabled")
    TORCH_AVAILABLE = False


@dataclass
class TrainingConfig:
    """Configuration for training"""
    epochs: int = 100
    batch_size: int = 32
    learning_rate: float = 0.001
    weight_decay: float = 0.0001
    early_stopping_patience: int = 10
    checkpoint_dir: Path = Path("admin/models/checkpoints")
    log_interval: int = 10
    use_gpu: bool = True


@dataclass
class TrainingMetrics:
    """Metrics tracked during training"""
    epoch: int
    train_loss: float
    val_loss: float
    train_accuracy: float = 0.0
    val_accuracy: float = 0.0
    timestamp: str = ""
    
    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()


class DrumHumanizationModel(nn.Module):
    """
    Neural network that learns humanization parameters
    
    Architecture:
    - Input: Pattern context (tempo, style, complexity)
    - Hidden layers: Learn relationships between context and humanization
    - Output: Humanization parameters (timing variance, velocity variance, etc.)
    """
    
    def __init__(self, input_size: int = 3, hidden_size: int = 64, output_size: int = 9):
        super().__init__()
        
        # Encoder network
        self.encoder = nn.Sequential(
            nn.Linear(input_size, hidden_size),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(hidden_size, hidden_size * 2),
            nn.ReLU(),
            nn.Dropout(0.2),
        )
        
        # Humanization parameter predictor
        self.predictor = nn.Sequential(
            nn.Linear(hidden_size * 2, hidden_size),
            nn.ReLU(),
            nn.Linear(hidden_size, output_size),
            nn.Sigmoid()  # Output between 0 and 1
        )
    
    def forward(self, x):
        encoded = self.encoder(x)
        humanization_params = self.predictor(encoded)
        return humanization_params


class AutonomousTrainer:
    """
    Autonomous training system that:
    1. Monitors for new training data
    2. Automatically retrains when sufficient new data available
    3. Validates improvements
    4. Saves best models
    """
    
    def __init__(self, config: TrainingConfig = None):
        self.config = config or TrainingConfig()
        self.model = None
        self.device = self._setup_device()
        self.training_active = False
        self.training_history = []
        
        # Create directories
        self.config.checkpoint_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"Autonomous Trainer initialized on {self.device}")
    
    def _setup_device(self) -> str:
        """Setup compute device (GPU or CPU)"""
        if not TORCH_AVAILABLE:
            return "cpu"
        
        if self.config.use_gpu and torch.cuda.is_available():
            device = "cuda"
            gpu_name = torch.cuda.get_device_name(0)
            logger.info(f"Using GPU: {gpu_name}")
        else:
            device = "cpu"
            logger.info("Using CPU")
        
        return device
    
    def create_model(self, input_size: int = 3, output_size: int = 9) -> nn.Module:
        """Create a new model instance"""
        if not TORCH_AVAILABLE:
            logger.error("PyTorch not available")
            return None
        
        model = DrumHumanizationModel(input_size=input_size, output_size=output_size)
        model = model.to(self.device)
        self.model = model
        
        # Count parameters
        total_params = sum(p.numel() for p in model.parameters())
        logger.info(f"Created model with {total_params:,} parameters")
        
        return model
    
    def train_model(self, 
                   X_train: np.ndarray,
                   y_train: np.ndarray,
                   X_val: np.ndarray,
                   y_val: np.ndarray,
                   progress_callback: Callable = None) -> List[TrainingMetrics]:
        """
        Train the humanization model
        
        Args:
            X_train: Training input features
            y_train: Training target features
            X_val: Validation input features
            y_val: Validation target features
            progress_callback: Optional callback for progress updates
        
        Returns:
            List of training metrics per epoch
        """
        if not TORCH_AVAILABLE or self.model is None:
            logger.error("Model not initialized or PyTorch not available")
            return []
        
        self.training_active = True
        start_time = time.time()
        
        # Convert to PyTorch tensors
        X_train_t = torch.FloatTensor(X_train).to(self.device)
        y_train_t = torch.FloatTensor(y_train).to(self.device)
        X_val_t = torch.FloatTensor(X_val).to(self.device)
        y_val_t = torch.FloatTensor(y_val).to(self.device)
        
        # Create data loaders
        train_dataset = TensorDataset(X_train_t, y_train_t)
        train_loader = DataLoader(train_dataset, batch_size=self.config.batch_size, shuffle=True)
        
        # Optimizer and loss
        optimizer = optim.Adam(
            self.model.parameters(),
            lr=self.config.learning_rate,
            weight_decay=self.config.weight_decay
        )
        criterion = nn.MSELoss()
        
        # Training loop
        best_val_loss = float('inf')
        patience_counter = 0
        metrics_history = []
        
        logger.info(f"Starting training for {self.config.epochs} epochs")
        
        for epoch in range(self.config.epochs):
            if not self.training_active:
                logger.info("Training stopped by user")
                break
            
            # Training phase
            self.model.train()
            train_loss = 0.0
            
            for batch_X, batch_y in train_loader:
                optimizer.zero_grad()
                predictions = self.model(batch_X)
                loss = criterion(predictions, batch_y)
                loss.backward()
                optimizer.step()
                train_loss += loss.item()
            
            train_loss /= len(train_loader)
            
            # Validation phase
            self.model.eval()
            with torch.no_grad():
                val_predictions = self.model(X_val_t)
                val_loss = criterion(val_predictions, y_val_t).item()
            
            # Record metrics
            metrics = TrainingMetrics(
                epoch=epoch + 1,
                train_loss=train_loss,
                val_loss=val_loss
            )
            metrics_history.append(metrics)
            
            # Log progress
            if (epoch + 1) % self.config.log_interval == 0:
                elapsed = time.time() - start_time
                logger.info(
                    f"Epoch {epoch+1}/{self.config.epochs} | "
                    f"Train Loss: {train_loss:.4f} | "
                    f"Val Loss: {val_loss:.4f} | "
                    f"Time: {elapsed:.1f}s"
                )
            
            # Call progress callback if provided (every epoch for UI updates)
            if progress_callback:
                # Call with signature: (epoch, total_epochs, train_loss, val_loss)
                should_continue = progress_callback(epoch + 1, self.config.epochs, train_loss, val_loss)
                if should_continue is False:
                    logger.info("Training stopped by callback")
                    break
            
            # Save best model
            if val_loss < best_val_loss:
                best_val_loss = val_loss
                patience_counter = 0
                self.save_checkpoint("best_model.pth", metrics)
                logger.info(f"✅ New best model saved (val_loss: {val_loss:.4f})")
            else:
                patience_counter += 1
            
            # Early stopping
            if patience_counter >= self.config.early_stopping_patience:
                logger.info(f"Early stopping triggered after {epoch+1} epochs")
                break
        
        # Save final model
        self.save_checkpoint("final_model.pth", metrics_history[-1])
        
        elapsed = time.time() - start_time
        logger.info(f"Training complete in {elapsed:.1f}s | Best val loss: {best_val_loss:.4f}")
        
        self.training_active = False
        self.training_history.extend(metrics_history)
        
        return metrics_history
    
    def save_checkpoint(self, filename: str, metrics):
        """Save model checkpoint - accepts dict or TrainingMetrics"""
        if not TORCH_AVAILABLE or self.model is None:
            return
        
        checkpoint_path = self.config.checkpoint_dir / filename
        
        # Handle both dict and TrainingMetrics dataclass
        if isinstance(metrics, dict):
            metrics_dict = metrics
        else:
            # It's a TrainingMetrics dataclass
            metrics_dict = {
                'epoch': metrics.epoch,
                'train_loss': metrics.train_loss,
                'val_loss': metrics.val_loss,
                'timestamp': getattr(metrics, 'timestamp', '')
            }
        
        torch.save({
            'model_state_dict': self.model.state_dict(),
            'metrics': metrics_dict
        }, checkpoint_path)
        
        logger.debug(f"Checkpoint saved: {checkpoint_path}")
    
    def load_checkpoint(self, filename: str) -> bool:
        """Load model checkpoint"""
        if not TORCH_AVAILABLE:
            return False
        
        checkpoint_path = self.config.checkpoint_dir / filename
        
        if not checkpoint_path.exists():
            logger.warning(f"Checkpoint not found: {checkpoint_path}")
            return False
        
        checkpoint = torch.load(checkpoint_path, map_location=self.device)
        
        if self.model is None:
            logger.warning("Model not initialized, cannot load checkpoint")
            return False
        
        self.model.load_state_dict(checkpoint['model_state_dict'])
        logger.info(f"Checkpoint loaded: {checkpoint_path}")
        
        return True
    
    def stop_training(self):
        """Stop training gracefully"""
        self.training_active = False
        logger.info("Training stop requested")
    
    def predict(self, X: np.ndarray) -> np.ndarray:
        """Make predictions with trained model"""
        if not TORCH_AVAILABLE or self.model is None:
            logger.error("Model not available")
            return None
        
        self.model.eval()
        with torch.no_grad():
            X_t = torch.FloatTensor(X).to(self.device)
            predictions = self.model(X_t)
            return predictions.cpu().numpy()
    
    def export_model(self, output_path: Path, format: str = 'pytorch'):
        """Export model for production use"""
        if not TORCH_AVAILABLE or self.model is None:
            logger.error("Model not available")
            return False
        
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        if format == 'pytorch':
            # Save as TorchScript for production
            self.model.eval()
            scripted_model = torch.jit.script(self.model)
            scripted_model.save(str(output_path))
            logger.info(f"Model exported as TorchScript: {output_path}")
            return True
        
        elif format == 'onnx':
            # Export as ONNX for cross-platform use
            try:
                import torch.onnx
                dummy_input = torch.randn(1, 3).to(self.device)
                torch.onnx.export(
                    self.model,
                    dummy_input,
                    str(output_path),
                    export_params=True,
                    opset_version=12,
                    input_names=['input'],
                    output_names=['output']
                )
                logger.info(f"Model exported as ONNX: {output_path}")
                return True
            except Exception as e:
                logger.error(f"ONNX export failed: {e}")
                return False
        
        else:
            logger.error(f"Unsupported export format: {format}")
            return False


def test_model_trainer():
    """Test the model trainer"""
    print("🧪 Testing Model Trainer")
    print("=" * 60)
    
    if not TORCH_AVAILABLE:
        print("⚠️ PyTorch not available - install with:")
        print("   pip install torch torchvision torchaudio")
        return
    
    # Create trainer
    config = TrainingConfig(epochs=10, batch_size=16)
    trainer = AutonomousTrainer(config)
    
    # Create test model
    model = trainer.create_model(input_size=3, output_size=9)
    print(f"\n✅ Model created on {trainer.device}")
    
    # Create dummy training data
    print("\n🔨 Creating dummy training data...")
    X_train = np.random.randn(100, 3).astype(np.float32)
    y_train = np.random.rand(100, 9).astype(np.float32)
    X_val = np.random.randn(20, 3).astype(np.float32)
    y_val = np.random.rand(20, 9).astype(np.float32)
    
    # Train model
    print("\n🚀 Starting training...")
    def progress_callback(percent, msg):
        if percent % 20 == 0:
            print(f"   {msg} ({percent}%)")
    
    metrics = trainer.train_model(X_train, y_train, X_val, y_val, progress_callback)
    
    print(f"\n✅ Training complete: {len(metrics)} epochs")
    print(f"   Final train loss: {metrics[-1].train_loss:.4f}")
    print(f"   Final val loss: {metrics[-1].val_loss:.4f}")
    
    # Test prediction
    print("\n🔮 Testing prediction...")
    test_input = np.array([[120.0, 0, 0.7]]).astype(np.float32)
    prediction = trainer.predict(test_input)
    print(f"   Input: tempo=120, style=rock, complexity=0.7")
    print(f"   Predicted humanization: {prediction[0][:3]}")
    
    print("\n✅ Model trainer test complete")


if __name__ == "__main__":
    test_model_trainer()

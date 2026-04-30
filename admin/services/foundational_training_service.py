"""
Foundational Training Service for DrumTracKAI
============================================
Phase 1: Individual Drum Samples + Snare Rudiments Recognition Training

This service implements the foundational phase of the comprehensive training pipeline,
focusing on maximum recognition accuracy for basic drum components and rudiments
before advancing to pattern and style analysis.

Key Features:
- Individual drum sample classification (kick, snare, hihat, crash, ride, toms)
- Snare rudiment recognition and analysis (40+ standard rudiments)
- Dynamics recognition (soft, medium, hard)
- Timbral characteristic analysis
- Progressive complexity training
"""

import logging
import os
import json
import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
import torchaudio
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any, Union
from datetime import datetime
from dataclasses import dataclass, field
import librosa
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder
from torch.utils.data import Dataset, DataLoader
import torch.nn.functional as F

logger = logging.getLogger(__name__)

@dataclass
class TrainingConfig:
    """Configuration for foundational training"""
    # Model parameters
    model_type: str = "DrumTracKAI-Foundation"
    sample_rate: int = 44100
    n_mels: int = 128
    n_fft: int = 2048
    hop_length: int = 512
    max_duration: float = 4.0  # Maximum audio duration in seconds
    
    # Training parameters
    batch_size: int = 64
    epochs: int = 50
    learning_rate: float = 0.0001
    weight_decay: float = 1e-5
    dropout_rate: float = 0.3
    
    # Data augmentation
    use_augmentation: bool = True
    noise_factor: float = 0.005
    time_shift_ms: int = 100
    pitch_shift_steps: int = 2
    
    # Training strategy
    progressive_training: bool = True
    class_balancing: bool = True
    early_stopping_patience: int = 10
    
    # Output paths
    model_save_path: str = "models/foundational"
    checkpoint_path: str = "checkpoints/foundational"
    logs_path: str = "logs/foundational"

class DrumSampleDataset(Dataset):
    """Dataset for individual drum samples and rudiments"""
    
    def __init__(self, 
                 file_paths: List[str], 
                 labels: List[str],
                 config: TrainingConfig,
                 transform=None,
                 is_training: bool = True):
        self.file_paths = file_paths
        self.labels = labels
        self.config = config
        self.transform = transform
        self.is_training = is_training
        
        # Create label encoder
        self.label_encoder = LabelEncoder()
        self.encoded_labels = self.label_encoder.fit_transform(labels)
        self.num_classes = len(self.label_encoder.classes_)
        
        logger.info(f"Dataset created with {len(file_paths)} samples, {self.num_classes} classes")
        logger.info(f"Classes: {list(self.label_encoder.classes_)}")
    
    def __len__(self):
        return len(self.file_paths)
    
    def __getitem__(self, idx):
        file_path = self.file_paths[idx]
        label = self.encoded_labels[idx]
        
        try:
            # Load audio
            audio, sr = torchaudio.load(file_path)
            
            # Convert to mono if stereo
            if audio.shape[0] > 1:
                audio = torch.mean(audio, dim=0, keepdim=True)
            
            # Resample if necessary
            if sr != self.config.sample_rate:
                resampler = torchaudio.transforms.Resample(sr, self.config.sample_rate)
                audio = resampler(audio)
            
            # Normalize duration
            target_length = int(self.config.max_duration * self.config.sample_rate)
            current_length = audio.shape[1]
            
            if current_length > target_length:
                # Trim to target length
                start_idx = (current_length - target_length) // 2
                audio = audio[:, start_idx:start_idx + target_length]
            elif current_length < target_length:
                # Pad to target length
                padding = target_length - current_length
                audio = F.pad(audio, (0, padding), mode='constant', value=0)
            
            # Apply data augmentation if training
            if self.is_training and self.config.use_augmentation:
                audio = self._apply_augmentation(audio)
            
            # Convert to mel spectrogram
            mel_transform = torchaudio.transforms.MelSpectrogram(
                sample_rate=self.config.sample_rate,
                n_fft=self.config.n_fft,
                hop_length=self.config.hop_length,
                n_mels=self.config.n_mels,
                power=2.0
            )
            
            mel_spec = mel_transform(audio)
            mel_spec = torch.log(mel_spec + 1e-8)  # Log mel spectrogram
            
            # Normalize
            mel_spec = (mel_spec - mel_spec.mean()) / (mel_spec.std() + 1e-8)
            
            return mel_spec.squeeze(0), label
            
        except Exception as e:
            logger.error(f"Error loading {file_path}: {e}")
            # Return zeros and label if loading fails
            mel_spec = torch.zeros(self.config.n_mels, 
                                 int(self.config.max_duration * self.config.sample_rate // self.config.hop_length) + 1)
            return mel_spec, label
    
    def _apply_augmentation(self, audio: torch.Tensor) -> torch.Tensor:
        """Apply data augmentation techniques"""
        # Add noise
        if np.random.random() < 0.5:
            noise = torch.randn_like(audio) * self.config.noise_factor
            audio = audio + noise
        
        # Time shifting
        if np.random.random() < 0.5:
            shift_samples = int(np.random.uniform(-self.config.time_shift_ms, 
                                                self.config.time_shift_ms) * self.config.sample_rate / 1000)
            if shift_samples != 0:
                audio = torch.roll(audio, shift_samples, dims=1)
        
        # Volume scaling
        if np.random.random() < 0.5:
            scale_factor = np.random.uniform(0.8, 1.2)
            audio = audio * scale_factor
        
        return audio

class DrumClassificationModel(nn.Module):
    """Neural network model for drum classification"""
    
    def __init__(self, num_classes: int, config: TrainingConfig):
        super().__init__()
        self.config = config
        self.num_classes = num_classes
        
        # Convolutional layers for feature extraction
        self.conv_layers = nn.Sequential(
            # First conv block
            nn.Conv2d(1, 32, kernel_size=3, padding=1),
            nn.BatchNorm2d(32),
            nn.ReLU(),
            nn.MaxPool2d(2, 2),
            nn.Dropout2d(0.1),
            
            # Second conv block
            nn.Conv2d(32, 64, kernel_size=3, padding=1),
            nn.BatchNorm2d(64),
            nn.ReLU(),
            nn.MaxPool2d(2, 2),
            nn.Dropout2d(0.2),
            
            # Third conv block
            nn.Conv2d(64, 128, kernel_size=3, padding=1),
            nn.BatchNorm2d(128),
            nn.ReLU(),
            nn.MaxPool2d(2, 2),
            nn.Dropout2d(0.2),
            
            # Fourth conv block
            nn.Conv2d(128, 256, kernel_size=3, padding=1),
            nn.BatchNorm2d(256),
            nn.ReLU(),
            nn.MaxPool2d(2, 2),
            nn.Dropout2d(0.3),
        )
        
        # Calculate the size of flattened features
        self._calculate_conv_output_size()
        
        # Fully connected layers
        self.classifier = nn.Sequential(
            nn.Linear(self.conv_output_size, 512),
            nn.BatchNorm1d(512),
            nn.ReLU(),
            nn.Dropout(config.dropout_rate),
            
            nn.Linear(512, 256),
            nn.BatchNorm1d(256),
            nn.ReLU(),
            nn.Dropout(config.dropout_rate),
            
            nn.Linear(256, 128),
            nn.BatchNorm1d(128),
            nn.ReLU(),
            nn.Dropout(config.dropout_rate),
            
            nn.Linear(128, num_classes)
        )
        
        # Initialize weights
        self._initialize_weights()
    
    def _calculate_conv_output_size(self):
        """Calculate the output size of convolutional layers"""
        # Dummy input to calculate conv output size
        dummy_input = torch.zeros(1, 1, self.config.n_mels, 
                                int(self.config.max_duration * self.config.sample_rate // self.config.hop_length) + 1)
        with torch.no_grad():
            conv_output = self.conv_layers(dummy_input)
            self.conv_output_size = conv_output.view(1, -1).size(1)
    
    def _initialize_weights(self):
        """Initialize model weights"""
        for m in self.modules():
            if isinstance(m, nn.Conv2d):
                nn.init.kaiming_normal_(m.weight, mode='fan_out', nonlinearity='relu')
                if m.bias is not None:
                    nn.init.constant_(m.bias, 0)
            elif isinstance(m, nn.BatchNorm2d) or isinstance(m, nn.BatchNorm1d):
                nn.init.constant_(m.weight, 1)
                nn.init.constant_(m.bias, 0)
            elif isinstance(m, nn.Linear):
                nn.init.normal_(m.weight, 0, 0.01)
                nn.init.constant_(m.bias, 0)
    
    def forward(self, x):
        # Add channel dimension if not present
        if x.dim() == 3:
            x = x.unsqueeze(1)
        
        # Convolutional feature extraction
        features = self.conv_layers(x)
        
        # Flatten for classifier
        features = features.view(features.size(0), -1)
        
        # Classification
        output = self.classifier(features)
        
        return output

class FoundationalTrainingService:
    """Service for foundational drum recognition training"""
    
    def __init__(self, config: TrainingConfig = None):
        self.config = config or TrainingConfig()
        self.model = None
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        self.training_history = []
        
        # Create output directories
        os.makedirs(self.config.model_save_path, exist_ok=True)
        os.makedirs(self.config.checkpoint_path, exist_ok=True)
        os.makedirs(self.config.logs_path, exist_ok=True)
        
        logger.info(f"Foundational Training Service initialized on {self.device}")
    
    def prepare_datasets(self, database_paths: Dict[str, str]) -> Tuple[DataLoader, DataLoader, Dict]:
        """Prepare training and validation datasets from database paths"""
        all_files = []
        all_labels = []
        dataset_info = {}
        
        # Process each database
        for db_name, db_path in database_paths.items():
            db_files, db_labels = self._scan_database(db_path, db_name)
            all_files.extend(db_files)
            all_labels.extend(db_labels)
            
            dataset_info[db_name] = {
                "files": len(db_files),
                "categories": list(set(db_labels))
            }
        
        logger.info(f"Total files collected: {len(all_files)}")
        logger.info(f"Total unique labels: {len(set(all_labels))}")
        
        # Split into train/validation
        train_files, val_files, train_labels, val_labels = train_test_split(
            all_files, all_labels, test_size=0.2, random_state=42, stratify=all_labels
        )
        
        # Create datasets
        train_dataset = DrumSampleDataset(train_files, train_labels, self.config, is_training=True)
        val_dataset = DrumSampleDataset(val_files, val_labels, self.config, is_training=False)
        
        # Create data loaders
        train_loader = DataLoader(
            train_dataset, 
            batch_size=self.config.batch_size, 
            shuffle=True, 
            num_workers=4,
            pin_memory=True if self.device.type == 'cuda' else False
        )
        
        val_loader = DataLoader(
            val_dataset, 
            batch_size=self.config.batch_size, 
            shuffle=False, 
            num_workers=4,
            pin_memory=True if self.device.type == 'cuda' else False
        )
        
        # Store label encoder for later use
        self.label_encoder = train_dataset.label_encoder
        
        dataset_info["total_files"] = len(all_files)
        dataset_info["train_files"] = len(train_files)
        dataset_info["val_files"] = len(val_files)
        dataset_info["num_classes"] = train_dataset.num_classes
        dataset_info["classes"] = list(self.label_encoder.classes_)
        
        return train_loader, val_loader, dataset_info
    
    def _scan_database(self, db_path: str, db_name: str) -> Tuple[List[str], List[str]]:
        """Scan a database directory for audio files"""
        db_path = Path(db_path)
        files = []
        labels = []
        
        if not db_path.exists():
            logger.warning(f"Database path not found: {db_path}")
            return files, labels
        
        # Audio file extensions
        audio_extensions = {'.wav', '.mp3', '.flac', '.aiff', '.m4a'}
        
        for audio_file in db_path.rglob('*'):
            if audio_file.suffix.lower() in audio_extensions:
                files.append(str(audio_file))
                
                # Determine label from path structure
                relative_path = audio_file.relative_to(db_path)
                
                if db_name == "Snare Rudiments":
                    # For rudiments, use the parent directory name as the label
                    label = f"rudiment_{relative_path.parts[0].lower().replace(' ', '_')}"
                elif db_name == "Drum Samples":
                    # For drum samples, extract drum type from path
                    if "kick" in str(relative_path).lower():
                        label = "kick"
                    elif "snare" in str(relative_path).lower():
                        label = "snare"
                    elif "hihat" in str(relative_path).lower():
                        label = "hihat"
                    elif "crash" in str(relative_path).lower():
                        label = "crash"
                    elif "ride" in str(relative_path).lower():
                        label = "ride"
                    elif "tom" in str(relative_path).lower():
                        label = "tom"
                    else:
                        label = relative_path.parts[0].lower().replace(' ', '_')
                elif db_name == "SD3 Extracted Samples":
                    # For SD3 samples, extract from filename
                    filename = audio_file.stem.lower()
                    if filename.startswith('kick'):
                        label = "kick"
                    elif filename.startswith('snare'):
                        label = "snare"
                    elif filename.startswith('hihat'):
                        label = "hihat"
                    elif filename.startswith('crash'):
                        label = "crash"
                    elif filename.startswith('ride'):
                        label = "ride"
                    elif filename.startswith('china'):
                        label = "china"
                    elif filename.startswith('tom'):
                        label = "tom"
                    else:
                        label = "unknown"
                else:
                    # Default: use parent directory name
                    label = relative_path.parts[0].lower().replace(' ', '_') if relative_path.parts else "unknown"
                
                labels.append(label)
        
        logger.info(f"Scanned {db_name}: {len(files)} files, {len(set(labels))} categories")
        return files, labels
    
    def create_model(self, num_classes: int) -> nn.Module:
        """Create and initialize the model"""
        self.model = DrumClassificationModel(num_classes, self.config)
        self.model.to(self.device)
        
        logger.info(f"Model created with {num_classes} classes")
        logger.info(f"Model parameters: {sum(p.numel() for p in self.model.parameters()):,}")
        
        return self.model
    
    def train(self, train_loader: DataLoader, val_loader: DataLoader, 
              progress_callback=None) -> Dict:
        """Train the foundational model"""
        if self.model is None:
            raise ValueError("Model not created. Call create_model() first.")
        
        # Setup training
        criterion = nn.CrossEntropyLoss()
        optimizer = optim.AdamW(
            self.model.parameters(), 
            lr=self.config.learning_rate,
            weight_decay=self.config.weight_decay
        )
        
        scheduler = optim.lr_scheduler.ReduceLROnPlateau(
            optimizer, mode='min', factor=0.5, patience=5, verbose=True
        )
        
        best_val_accuracy = 0.0
        patience_counter = 0
        
        logger.info("Starting foundational training...")
        
        for epoch in range(self.config.epochs):
            # Training phase
            train_loss, train_accuracy = self._train_epoch(train_loader, criterion, optimizer)
            
            # Validation phase
            val_loss, val_accuracy = self._validate_epoch(val_loader, criterion)
            
            # Learning rate scheduling
            scheduler.step(val_loss)
            
            # Record history
            epoch_info = {
                "epoch": epoch + 1,
                "train_loss": train_loss,
                "train_accuracy": train_accuracy,
                "val_loss": val_loss,
                "val_accuracy": val_accuracy,
                "learning_rate": optimizer.param_groups[0]['lr']
            }
            self.training_history.append(epoch_info)
            
            # Progress callback
            if progress_callback:
                progress_callback(epoch + 1, self.config.epochs, epoch_info)
            
            # Early stopping and checkpointing
            if val_accuracy > best_val_accuracy:
                best_val_accuracy = val_accuracy
                patience_counter = 0
                self._save_checkpoint(epoch + 1, "best_model.pth")
            else:
                patience_counter += 1
            
            # Save regular checkpoint
            if (epoch + 1) % 10 == 0:
                self._save_checkpoint(epoch + 1, f"checkpoint_epoch_{epoch + 1}.pth")
            
            logger.info(
                f"Epoch {epoch + 1}/{self.config.epochs} - "
                f"Train Loss: {train_loss:.4f}, Train Acc: {train_accuracy:.4f}, "
                f"Val Loss: {val_loss:.4f}, Val Acc: {val_accuracy:.4f}"
            )
            
            # Early stopping
            if patience_counter >= self.config.early_stopping_patience:
                logger.info(f"Early stopping triggered after {epoch + 1} epochs")
                break
        
        # Save final model
        self._save_final_model()
        
        # Training summary
        training_summary = {
            "total_epochs": len(self.training_history),
            "best_val_accuracy": best_val_accuracy,
            "final_train_accuracy": self.training_history[-1]["train_accuracy"],
            "final_val_accuracy": self.training_history[-1]["val_accuracy"],
            "training_history": self.training_history
        }
        
        logger.info("Foundational training completed!")
        logger.info(f"Best validation accuracy: {best_val_accuracy:.4f}")
        
        return training_summary
    
    def _train_epoch(self, train_loader: DataLoader, criterion, optimizer) -> Tuple[float, float]:
        """Train for one epoch"""
        self.model.train()
        total_loss = 0.0
        correct_predictions = 0
        total_samples = 0
        
        for batch_idx, (data, target) in enumerate(train_loader):
            data, target = data.to(self.device), target.to(self.device)
            
            optimizer.zero_grad()
            output = self.model(data)
            loss = criterion(output, target)
            loss.backward()
            optimizer.step()
            
            total_loss += loss.item()
            pred = output.argmax(dim=1, keepdim=True)
            correct_predictions += pred.eq(target.view_as(pred)).sum().item()
            total_samples += target.size(0)
        
        avg_loss = total_loss / len(train_loader)
        accuracy = correct_predictions / total_samples
        
        return avg_loss, accuracy
    
    def _validate_epoch(self, val_loader: DataLoader, criterion) -> Tuple[float, float]:
        """Validate for one epoch"""
        self.model.eval()
        total_loss = 0.0
        correct_predictions = 0
        total_samples = 0
        
        with torch.no_grad():
            for data, target in val_loader:
                data, target = data.to(self.device), target.to(self.device)
                output = self.model(data)
                loss = criterion(output, target)
                
                total_loss += loss.item()
                pred = output.argmax(dim=1, keepdim=True)
                correct_predictions += pred.eq(target.view_as(pred)).sum().item()
                total_samples += target.size(0)
        
        avg_loss = total_loss / len(val_loader)
        accuracy = correct_predictions / total_samples
        
        return avg_loss, accuracy
    
    def _save_checkpoint(self, epoch: int, filename: str):
        """Save model checkpoint"""
        checkpoint_path = Path(self.config.checkpoint_path) / filename
        torch.save({
            'epoch': epoch,
            'model_state_dict': self.model.state_dict(),
            'config': self.config,
            'label_encoder': self.label_encoder,
            'training_history': self.training_history
        }, checkpoint_path)
    
    def _save_final_model(self):
        """Save the final trained model"""
        model_path = Path(self.config.model_save_path) / "foundational_model.pth"
        torch.save({
            'model_state_dict': self.model.state_dict(),
            'config': self.config,
            'label_encoder': self.label_encoder,
            'training_history': self.training_history,
            'model_architecture': str(self.model)
        }, model_path)
        
        # Save training summary
        summary_path = Path(self.config.logs_path) / "training_summary.json"
        with open(summary_path, 'w') as f:
            json.dump({
                'config': self.config.__dict__,
                'training_history': self.training_history,
                'label_classes': list(self.label_encoder.classes_),
                'timestamp': datetime.now().isoformat()
            }, f, indent=2)
        
        logger.info(f"Final model saved to {model_path}")
        logger.info(f"Training summary saved to {summary_path}")


# Example usage and testing
if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(level=logging.INFO)
    
    # Example database paths
    database_paths = {
        "Drum Samples": "E:\\Drum Samples",
        "Snare Rudiments": "E:\\Snare Rudiments",
        "SD3 Extracted Samples": "E:\\DrumTracKAI_Database\\sd3_extracted_samples"
    }
    
    # Create training service
    config = TrainingConfig(epochs=5, batch_size=32)  # Small values for testing
    service = FoundationalTrainingService(config)
    
    # Prepare datasets
    train_loader, val_loader, dataset_info = service.prepare_datasets(database_paths)
    print(f"Dataset info: {dataset_info}")
    
    # Create model
    model = service.create_model(dataset_info["num_classes"])
    
    # Train model (with progress callback)
    def progress_callback(epoch, total_epochs, epoch_info):
        print(f"Progress: {epoch}/{total_epochs} - Val Acc: {epoch_info['val_accuracy']:.4f}")
    
    training_summary = service.train(train_loader, val_loader, progress_callback)
    print(f"Training completed! Best accuracy: {training_summary['best_val_accuracy']:.4f}")

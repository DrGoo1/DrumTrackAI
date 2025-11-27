"""
Train GrooVAE Model on 91,074 Drum Patterns
Complete training pipeline with monitoring and checkpointing
"""

import torch
import torch.optim as optim
from torch.utils.data import Dataset, DataLoader
import numpy as np
import pickle
from pathlib import Path
import json
from datetime import datetime
from tqdm import tqdm

from groove_vae_model import GrooVAE, GrooVAETrainer

class DrumPatternDataset(Dataset):
    """PyTorch dataset for drum patterns"""
    
    def __init__(self, features_file, metadata_file):
        self.features = np.load(features_file)
        with open(metadata_file, 'rb') as f:
            metadata = pickle.load(f)
        self.labels = metadata['labels']
        self.patterns = metadata['patterns']
    
    def __len__(self):
        return len(self.features)
    
    def __getitem__(self, idx):
        return torch.FloatTensor(self.features[idx]), self.labels[idx]


def train_groove_vae():
    """Complete training pipeline"""
    print("🎓 GrooVAE Training Pipeline")
    print("="*70)
    
    # Configuration
    config = {
        'latent_dim': 64,
        'hidden_dim': 512,
        'batch_size': 32,
        'learning_rate': 0.001,
        'epochs': 100,
        'beta': 1.0,  # β-VAE parameter
        'beta_schedule': 'constant',  # or 'linear', 'cyclical'
        'save_every': 10,
        'device': 'cuda' if torch.cuda.is_available() else 'cpu'
    }
    
    print(f"Device: {config['device']}")
    print(f"Epochs: {config['epochs']}")
    print(f"Batch size: {config['batch_size']}")
    print(f"Latent dim: {config['latent_dim']}")
    
    # Load datasets
    print("\n📊 Loading datasets...")
    data_dir = "E:/DrumTracKAI_Master/03_Training_Data/preprocessed"
    
    train_dataset = DrumPatternDataset(
        f"{data_dir}/train_features.npy",
        f"{data_dir}/train_metadata.pkl"
    )
    
    val_dataset = DrumPatternDataset(
        f"{data_dir}/val_features.npy",
        f"{data_dir}/val_metadata.pkl"
    )
    
    test_dataset = DrumPatternDataset(
        f"{data_dir}/test_features.npy",
        f"{data_dir}/test_metadata.pkl"
    )
    
    print(f"✓ Train: {len(train_dataset):,} patterns")
    print(f"✓ Val:   {len(val_dataset):,} patterns")
    print(f"✓ Test:  {len(test_dataset):,} patterns")
    
    # Create data loaders
    train_loader = DataLoader(
        train_dataset, 
        batch_size=config['batch_size'],
        shuffle=True,
        num_workers=4,
        pin_memory=True if config['device'] == 'cuda' else False
    )
    
    val_loader = DataLoader(
        val_dataset,
        batch_size=config['batch_size'],
        shuffle=False,
        num_workers=4,
        pin_memory=True if config['device'] == 'cuda' else False
    )
    
    # Initialize model
    print("\n🧠 Initializing model...")
    model = GrooVAE(
        latent_dim=config['latent_dim'],
        hidden_dim=config['hidden_dim']
    )
    
    total_params = sum(p.numel() for p in model.parameters())
    print(f"✓ Model parameters: {total_params:,}")
    
    # Optimizer
    optimizer = optim.Adam(model.parameters(), lr=config['learning_rate'])
    
    # Learning rate scheduler
    scheduler = optim.lr_scheduler.ReduceLROnPlateau(
        optimizer, mode='min', factor=0.5, patience=5, verbose=True
    )
    
    # Trainer
    trainer = GrooVAETrainer(model, device=config['device'])
    
    # Training loop
    print("\n🚀 Starting training...")
    print("="*70)
    
    output_dir = "E:/DrumTracKAI_Master/04_Models/current"
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    
    training_history = {
        'train_loss': [],
        'val_loss': [],
        'learning_rates': [],
        'epochs': []
    }
    
    best_val_loss = float('inf')
    
    for epoch in range(1, config['epochs'] + 1):
        print(f"\nEpoch {epoch}/{config['epochs']}")
        print("-" * 70)
        
        # Training
        train_loss = trainer.train_epoch(train_loader, optimizer, config['beta'])
        
        # Validation
        val_loss = trainer.validate(val_loader, config['beta'])
        
        # Learning rate scheduling
        scheduler.step(val_loss)
        current_lr = optimizer.param_groups[0]['lr']
        
        # Record history
        training_history['train_loss'].append(train_loss)
        training_history['val_loss'].append(val_loss)
        training_history['learning_rates'].append(current_lr)
        training_history['epochs'].append(epoch)
        
        print(f"Train Loss: {train_loss:.4f}")
        print(f"Val Loss:   {val_loss:.4f}")
        print(f"LR:         {current_lr:.6f}")
        
        # Save best model
        if val_loss < best_val_loss:
            best_val_loss = val_loss
            best_model_path = f"{output_dir}/groove_vae_best.pth"
            trainer.save_checkpoint(
                epoch, optimizer, train_loss, val_loss,
                best_model_path
            )
            print(f"✓ Saved best model (val_loss: {val_loss:.4f})")
        
        # Save checkpoint
        if epoch % config['save_every'] == 0:
            checkpoint_path = f"{output_dir}/groove_vae_epoch_{epoch}.pth"
            trainer.save_checkpoint(
                epoch, optimizer, train_loss, val_loss,
                checkpoint_path
            )
            print(f"✓ Saved checkpoint: epoch {epoch}")
        
        # Save training history
        history_path = f"{output_dir}/training_history.json"
        with open(history_path, 'w') as f:
            json.dump(training_history, f, indent=2)
    
    print("\n" + "="*70)
    print("✅ TRAINING COMPLETE!")
    print("="*70)
    print(f"Best validation loss: {best_val_loss:.4f}")
    print(f"Final train loss: {train_loss:.4f}")
    print(f"Models saved to: {output_dir}")
    
    # Save final model
    final_model_path = f"{output_dir}/groove_vae_final.pth"
    trainer.save_checkpoint(
        config['epochs'], optimizer, train_loss, val_loss,
        final_model_path
    )
    
    # Save config
    config_path = f"{output_dir}/training_config.json"
    with open(config_path, 'w') as f:
        json.dump(config, f, indent=2)
    
    print(f"\n📊 Training history: {history_path}")
    print(f"⚙️  Configuration: {config_path}")
    print(f"🎯 Best model: {best_model_path}")
    
    print("\n🎯 Next Steps:")
    print("1. Test model: python test_groove_vae.py")
    print("2. Integrate with backend")
    print("3. Deploy to production")


if __name__ == "__main__":
    # Check PyTorch installation
    print("🔧 Environment Check")
    print("="*70)
    print(f"PyTorch version: {torch.__version__}")
    print(f"CUDA available: {torch.cuda.is_available()}")
    if torch.cuda.is_available():
        print(f"CUDA version: {torch.version.cuda}")
        print(f"GPU: {torch.cuda.get_device_name(0)}")
    print("="*70)
    print()
    
    # Start training
    train_groove_vae()

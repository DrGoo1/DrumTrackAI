"""
GrooVAE - Variational Autoencoder for Drum Groove Generation
Based on MusicVAE architecture adapted for drum patterns
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
from typing import Tuple

class GrooVAE(nn.Module):
    """
    Variational Autoencoder for Drum Patterns
    
    Architecture:
    - Encoder: Piano roll (8x128) → Latent space (64 dim)
    - Decoder: Latent space (64 dim) → Piano roll (8x128)
    - VAE loss: Reconstruction + KL divergence
    """
    
    def __init__(self, latent_dim: int = 64, hidden_dim: int = 512):
        super(GrooVAE, self).__init__()
        
        self.latent_dim = latent_dim
        self.hidden_dim = hidden_dim
        self.input_dim = 8 * 128 + 6  # Piano roll + metadata features
        
        # Encoder: input → hidden → latent
        self.encoder = nn.Sequential(
            nn.Linear(self.input_dim, 1024),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(1024, hidden_dim),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(hidden_dim, hidden_dim),
            nn.ReLU()
        )
        
        # Latent space projections
        self.fc_mu = nn.Linear(hidden_dim, latent_dim)
        self.fc_logvar = nn.Linear(hidden_dim, latent_dim)
        
        # Decoder: latent → hidden → output
        self.decoder = nn.Sequential(
            nn.Linear(latent_dim, hidden_dim),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(hidden_dim, hidden_dim),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(hidden_dim, 1024),
            nn.ReLU(),
            nn.Linear(1024, 8 * 128),  # Piano roll only
            nn.Sigmoid()  # Output probabilities [0, 1]
        )
    
    def encode(self, x: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor]:
        """Encode input to latent space"""
        h = self.encoder(x)
        mu = self.fc_mu(h)
        logvar = self.fc_logvar(h)
        return mu, logvar
    
    def reparameterize(self, mu: torch.Tensor, logvar: torch.Tensor) -> torch.Tensor:
        """Reparameterization trick for VAE"""
        std = torch.exp(0.5 * logvar)
        eps = torch.randn_like(std)
        return mu + eps * std
    
    def decode(self, z: torch.Tensor) -> torch.Tensor:
        """Decode latent vector to piano roll"""
        return self.decoder(z)
    
    def forward(self, x: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        """Forward pass through VAE"""
        mu, logvar = self.encode(x)
        z = self.reparameterize(mu, logvar)
        recon = self.decode(z)
        return recon, mu, logvar
    
    def generate(self, z: torch.Tensor = None, num_samples: int = 1) -> torch.Tensor:
        """Generate new patterns from latent space"""
        if z is None:
            # Sample from standard normal on the same device as model
            device = next(self.parameters()).device
            z = torch.randn(num_samples, self.latent_dim, device=device)
        
        with torch.no_grad():
            generated = self.decode(z)
        
        return generated
    
    def interpolate(self, pattern1: torch.Tensor, pattern2: torch.Tensor, 
                   steps: int = 5) -> torch.Tensor:
        """Interpolate between two patterns in latent space"""
        with torch.no_grad():
            # Encode both patterns
            mu1, _ = self.encode(pattern1)
            mu2, _ = self.encode(pattern2)
            
            # Interpolate in latent space
            alphas = torch.linspace(0, 1, steps, device=mu1.device).unsqueeze(1)
            z_interp = alphas * mu2 + (1 - alphas) * mu1
            
            # Decode interpolated latents
            interpolated = self.decode(z_interp)
        
        return interpolated
    
    def blend_patterns(self, patterns: list, weights: list) -> torch.Tensor:
        """Blend multiple patterns with specified weights"""
        with torch.no_grad():
            # Encode all patterns
            latents = []
            for pattern in patterns:
                mu, _ = self.encode(pattern)
                latents.append(mu)
            
            # Weighted sum in latent space
            z_blend = torch.zeros_like(latents[0])
            for latent, weight in zip(latents, weights):
                z_blend += latent * weight
            
            # Decode blended latent
            blended = self.decode(z_blend)
        
        return blended


def vae_loss(recon_x, x, mu, logvar, beta=1.0):
    """
    VAE loss = Reconstruction loss + Beta * KL divergence
    
    Args:
        recon_x: Reconstructed output
        x: Original input (piano roll only, first 1024 dims)
        mu: Mean of latent distribution
        logvar: Log variance of latent distribution
        beta: Weight for KL term (β-VAE)
    """
    # Reconstruction loss (Binary Cross Entropy for piano roll)
    x_piano_roll = x[:, :1024]  # First 1024 dims are piano roll
    BCE = F.binary_cross_entropy(recon_x, x_piano_roll, reduction='sum')
    
    # KL divergence
    KLD = -0.5 * torch.sum(1 + logvar - mu.pow(2) - logvar.exp())
    
    return BCE + beta * KLD


class GrooVAETrainer:
    """Trainer for GrooVAE model"""
    
    def __init__(self, model: GrooVAE, device: str = 'cuda' if torch.cuda.is_available() else 'cpu'):
        self.model = model.to(device)
        self.device = device
        
    def train_epoch(self, train_loader, optimizer, beta=1.0):
        """Train for one epoch"""
        self.model.train()
        train_loss = 0
        
        for batch_idx, (data, _) in enumerate(train_loader):
            data = data.to(self.device)
            optimizer.zero_grad()
            
            recon, mu, logvar = self.model(data)
            loss = vae_loss(recon, data, mu, logvar, beta)
            
            loss.backward()
            optimizer.step()
            
            train_loss += loss.item()
        
        return train_loss / len(train_loader.dataset)
    
    def validate(self, val_loader, beta=1.0):
        """Validate model"""
        self.model.eval()
        val_loss = 0
        
        with torch.no_grad():
            for data, _ in val_loader:
                data = data.to(self.device)
                recon, mu, logvar = self.model(data)
                loss = vae_loss(recon, data, mu, logvar, beta)
                val_loss += loss.item()
        
        return val_loss / len(val_loader.dataset)
    
    def save_checkpoint(self, epoch, optimizer, train_loss, val_loss, path):
        """Save model checkpoint"""
        torch.save({
            'epoch': epoch,
            'model_state_dict': self.model.state_dict(),
            'optimizer_state_dict': optimizer.state_dict(),
            'train_loss': train_loss,
            'val_loss': val_loss,
        }, path)
    
    def load_checkpoint(self, path, optimizer=None):
        """Load model checkpoint"""
        checkpoint = torch.load(path, map_location=self.device)
        self.model.load_state_dict(checkpoint['model_state_dict'])
        
        if optimizer is not None:
            optimizer.load_state_dict(checkpoint['optimizer_state_dict'])
        
        return checkpoint['epoch'], checkpoint['train_loss'], checkpoint['val_loss']


if __name__ == "__main__":
    # Test model
    print("🧠 GrooVAE Model Test")
    print("="*70)
    
    model = GrooVAE(latent_dim=64, hidden_dim=512)
    
    # Count parameters
    total_params = sum(p.numel() for p in model.parameters())
    trainable_params = sum(p.numel() for p in model.parameters() if p.requires_grad)
    
    print(f"Total parameters: {total_params:,}")
    print(f"Trainable parameters: {trainable_params:,}")
    
    # Test forward pass
    batch_size = 16
    test_input = torch.randn(batch_size, 8 * 128 + 6)
    
    recon, mu, logvar = model(test_input)
    print(f"\nInput shape: {test_input.shape}")
    print(f"Reconstruction shape: {recon.shape}")
    print(f"Latent mu shape: {mu.shape}")
    print(f"Latent logvar shape: {logvar.shape}")
    
    # Test generation
    generated = model.generate(num_samples=4)
    print(f"Generated shape: {generated.shape}")
    
    print("\n✅ Model architecture validated!")

"""
Comprehensive Training - MIDI + Audio Analysis
Uses advanced feature extraction for maximum quality
"""

import sys
import time
import sqlite3
import numpy as np
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from admin.training.advanced_feature_extractor import ComprehensiveFeatureExtractor
from admin.training.model_trainer import AutonomousTrainer, TrainingConfig
from admin.training.validation import ModelValidator
from admin.training.deployment import ModelDeployer
from sklearn.model_selection import train_test_split
import torch

print("=" * 80)
print("🎯 COMPREHENSIVE TRAINING - MIDI + AUDIO ANALYSIS")
print("=" * 80)

start_time = time.time()

# Load patterns from database
db_path = Path("admin/drumtrackai.db")
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

cursor.execute("SELECT file_path, tempo_bpm, style FROM drum_patterns LIMIT 5000")
patterns = cursor.fetchall()
conn.close()

print(f"✅ Loaded {len(patterns):,} patterns")

# Extract comprehensive features
print("\n📊 Extracting comprehensive features...")
extractor = ComprehensiveFeatureExtractor()

X_samples = []
y_samples = []

for i, (file_path, tempo, style) in enumerate(patterns):
    if i % 500 == 0:
        print(f"   Processing: {i}/{len(patterns)}")
    
    midi_path = Path(file_path)
    if not midi_path.exists():
        continue
    
    features = extractor.extract_features(
        midi_path=midi_path,
        metadata={'tempo': tempo, 'style': style}
    )
    
    if features:
        # Input: tempo, complexity estimate, style encoding
        X_samples.append([
            features.tempo / 200.0,
            (features.kick_pattern_density + features.snare_pattern_density) / 2.0,
            features.hihat_pattern_complexity
        ])
        
        # Output: ALL humanization parameters
        y_samples.append([
            features.micro_timing_variance,
            features.velocity_variance,
            features.systematic_drift,
            features.groove_swing,
            features.accent_strength,
            features.ghost_note_frequency,
            features.velocity_humanization,
            features.offbeat_hihat_ratio,
            features.syncopation_level,
            features.kick_snare_relationship,
            features.ride_usage_ratio,
            features.fill_frequency
        ])

X = np.array(X_samples, dtype=np.float32)
y = np.array(y_samples, dtype=np.float32)

print(f"\n✅ Features extracted: {len(X):,} samples")
print(f"   Input dims: {X.shape[1]}")
print(f"   Output dims: {y.shape[1]}")

# Split dataset
X_train, X_temp, y_train, y_temp = train_test_split(X, y, test_size=0.3, random_state=42)
X_val, X_test, y_val, y_test = train_test_split(X_temp, y_temp, test_size=0.5, random_state=42)

print(f"\n📦 Dataset split:")
print(f"   Train: {len(X_train):,}")
print(f"   Val: {len(X_val):,}")
print(f"   Test: {len(X_test):,}")

# Train model
print("\n🚀 Training comprehensive model...")
config = TrainingConfig(epochs=150, batch_size=64, learning_rate=0.001, use_gpu=True)

trainer = AutonomousTrainer(config)
trainer.create_model(input_size=3, output_size=12)  # 12 output features!

def progress(pct, msg):
    if pct % 20 == 0:
        print(f"   [{pct}%] {msg}")

metrics = trainer.train_model(X_train, y_train, X_val, y_val, progress)

print(f"\n✅ Training complete!")
print(f"   Final loss: {metrics[-1].train_loss:.6f}")

# Validate
validator = ModelValidator()
val_metrics = validator.validate_model(trainer, X_test, y_test)

print(f"\n📊 Validation:")
print(f"   Score: {val_metrics.humanization_score:.1f}/100")
print(f"   R²: {val_metrics.r2_score:.3f}")

# Deploy
model_path = Path("models/drumtrackai_COMPREHENSIVE.pt")
model_path.parent.mkdir(exist_ok=True)

torch.save({
    'model_state': trainer.model.state_dict(),
    'config': {'input_size': 3, 'output_size': 12},
    'metrics': {
        'score': val_metrics.humanization_score,
        'r2': val_metrics.r2_score,
        'samples': len(X_train)
    }
}, model_path)

deployer = ModelDeployer()
deployer.deploy_model(model_path, "drumtrackai_comprehensive", "4.0.0", 
                     {'score': val_metrics.humanization_score})

print(f"\n🎉 COMPREHENSIVE MODEL COMPLETE!")
print(f"⏱️  Time: {(time.time() - start_time)/60:.1f} min")
print(f"📁 Saved: {model_path.absolute()}")
print(f"\nFeatures analyzed:")
print("   ✅ Micro-timing variance")
print("   ✅ Velocity humanization")
print("   ✅ Ghost notes & accents")
print("   ✅ Groove consistency")
print("   ✅ Hihat/ride patterns")
print("   ✅ Syncopation & fills")
print("=" * 80)

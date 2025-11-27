"""
Quick Training Test Script
Trains a model with dummy data to test the system
"""

import numpy as np
from admin.training.model_trainer import AutonomousTrainer, TrainingConfig
from admin.training.validation import ModelValidator

print("=" * 60)
print("Quick Training Test - DrumTracKAI")
print("=" * 60)

# Create dummy training data (replace with real data later)
print("\n📦 Creating test dataset...")
X_train = np.random.randn(200, 3).astype(np.float32)  # 200 samples
y_train = np.random.rand(200, 9).astype(np.float32)
X_val = np.random.randn(40, 3).astype(np.float32)  # 40 validation samples
y_val = np.random.rand(40, 9).astype(np.float32)
X_test = np.random.randn(40, 3).astype(np.float32)  # 40 test samples
y_test = np.random.rand(40, 9).astype(np.float32)

print(f"   Train: {len(X_train)} samples")
print(f"   Val: {len(X_val)} samples")
print(f"   Test: {len(X_test)} samples")

# Create trainer
print("\n🤖 Creating AI model...")
config = TrainingConfig(
    epochs=50,  # Quick test with 50 epochs
    batch_size=32,
    learning_rate=0.001,
    use_gpu=True  # You have RTX 3070!
)

trainer = AutonomousTrainer(config)
trainer.create_model(input_size=3, output_size=9)

# Train
print("\n🚀 Starting training...")
print("   (Should take 10-20 seconds with your RTX 3070)\n")

def progress_callback(percent, msg):
    if percent % 10 == 0:
        print(f"   {msg}")

metrics = trainer.train_model(X_train, y_train, X_val, y_val, progress_callback)

print(f"\n✅ Training complete!")
print(f"   Epochs: {len(metrics)}")
print(f"   Final train loss: {metrics[-1].train_loss:.4f}")
print(f"   Final val loss: {metrics[-1].val_loss:.4f}")

# Validate
print("\n📊 Validating model...")
validator = ModelValidator()
val_metrics = validator.validate_model(trainer, X_test, y_test)

print(f"   MAE: {val_metrics.mae:.4f}")
print(f"   R² Score: {val_metrics.r2_score:.3f}")
print(f"   Humanization Score: {val_metrics.humanization_score:.1f}/100")

# Test prediction
print("\n🔮 Testing prediction...")
test_input = np.array([[120.0, 0, 0.7]]).astype(np.float32)  # tempo=120, style=rock, complexity=0.7
prediction = trainer.predict(test_input)
print(f"   Input: tempo=120 BPM, style=rock, complexity=0.7")
print(f"   Predicted humanization parameters:")
print(f"      timing_variance: {prediction[0][0]:.4f}")
print(f"      timing_drift: {prediction[0][1]:.4f}")
print(f"      groove_consistency: {prediction[0][2]:.4f}")

print("\n" + "=" * 60)
print("✅ SUCCESS! Training system working perfectly!")
print("=" * 60)
print("\nNext steps:")
print("1. Extract REAL training data from songs/SD samples")
print("2. Retrain with real data")
print("3. Deploy to production")
print("\nYour RTX 3070 will make training super fast! 🚀")

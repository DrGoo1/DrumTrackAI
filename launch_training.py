#!/usr/bin/env python3
"""
Quick LLM Training Launcher
Launch training with existing data
"""

import sys
from pathlib import Path

print("=" * 70)
print("🤖 DrumTracKAI LLM Training Launcher")
print("=" * 70)

# Add admin to path
admin_path = Path(__file__).parent / "admin"
sys.path.insert(0, str(admin_path))

try:
    from training.model_trainer import AutonomousTrainer, TrainingConfig
    from training.dataset_builder import DrumDatasetBuilder
    print("\n✅ Training modules loaded successfully")
except ImportError as e:
    print(f"\n❌ Failed to import training modules: {e}")
    print("\nPlease ensure you're in the drumtrackai_env environment:")
    print("  cd f:\\DrumTracKAI_v1.1.11")
    print("  drumtrackai_env\\Scripts\\activate")
    sys.exit(1)

# Check for existing data
print("\n📊 Checking training data...")
builder = DrumDatasetBuilder()
stats = builder.get_dataset_stats()

print(f"\n   Total samples: {stats['total_samples']}")
print(f"   Drummers: {stats['drummers']}")
print(f"   Styles: {stats['styles']}")

if stats['total_samples'] < 10:
    print("\n⚠️  WARNING: Less than 10 training samples")
    print("   Consider extracting more data first")
    response = input("\nContinue anyway? (y/n): ")
    if response.lower() != 'y':
        sys.exit(0)

# Build dataset
print("\n🔨 Building dataset...")
try:
    dataset = builder.build_humanization_dataset(min_samples=10)
    print(f"   Train samples: {len(dataset.X_train)}")
    print(f"   Validation samples: {len(dataset.X_val)}")
    print(f"   Test samples: {len(dataset.X_test)}")
except Exception as e:
    print(f"   ❌ Failed to build dataset: {e}")
    sys.exit(1)

# Configure training
print("\n⚙️  Training Configuration:")
print("   Epochs: 50")
print("   Batch size: 16")
print("   Learning rate: 0.001")
print("   GPU: Auto-detect")

response = input("\nStart training? (y/n): ")
if response.lower() != 'y':
    print("\n❌ Training cancelled")
    sys.exit(0)

# Create trainer
# Use absolute path for checkpoints
admin_path = Path(__file__).parent / "admin"
checkpoint_dir = admin_path / "models" / "checkpoints"
config = TrainingConfig(
    epochs=50,
    batch_size=16,
    learning_rate=0.001,
    use_gpu=True,
    checkpoint_dir=checkpoint_dir,
    early_stopping_patience=10,
)

trainer = AutonomousTrainer(config)

# Create model
input_size = dataset.X_train.shape[1]
output_size = dataset.y_train.shape[1]

print(f"\n🤖 Creating model...")
print(f"   Input features: {input_size}")
print(f"   Output features: {output_size}")

trainer.create_model(input_size=input_size, output_size=output_size)

# Train
print("\n🚀 Starting training...")
print("=" * 70)

try:
    metrics = trainer.train_model(
        dataset.X_train, 
        dataset.y_train,
        dataset.X_val,
        dataset.y_val
    )
    
    print("\n" + "=" * 70)
    print("✅ Training Complete!")
    print("=" * 70)
    
    if metrics:
        last_metrics = metrics[-1]
        print(f"\n📊 Final Metrics:")
        print(f"   Train Loss: {last_metrics.get('train_loss', 'N/A'):.6f}")
        print(f"   Val Loss: {last_metrics.get('val_loss', 'N/A'):.6f}")
        print(f"   Best Epoch: {last_metrics.get('epoch', 'N/A')}")
    
    # Save checkpoint
    print(f"\n💾 Saving final checkpoint...")
    checkpoint_path = trainer.save_checkpoint("final_model.pth", metrics[-1] if metrics else {})
    print(f"   Saved to: {checkpoint_path}")
    
    print("\n🎉 Training session complete!")
    print("\nNext steps:")
    print("   1. Check admin/models/checkpoints/ for saved models")
    print("   2. Run validation with test_set")
    print("   3. Deploy to production if satisfied")
    
except KeyboardInterrupt:
    print("\n\n⏹️  Training interrupted by user")
    print("   Progress has been saved to checkpoints")
except Exception as e:
    print(f"\n\n❌ Training failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n" + "=" * 70)

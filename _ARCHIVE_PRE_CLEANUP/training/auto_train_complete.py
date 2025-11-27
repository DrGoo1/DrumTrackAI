"""
Fully Automated Training - Zero User Input Required
Scans, trains, and reports final model path
"""

import sys
import time
from pathlib import Path

# Add admin to path
sys.path.insert(0, str(Path(__file__).parent))

from admin.training.database_bootstrapper import bootstrap_knowledge_base
from admin.training.dataset_builder import DrumDatasetBuilder
from admin.training.model_trainer import AutonomousTrainer, TrainingConfig
from admin.training.validation import ModelValidator
from admin.training.deployment import ModelDeployer

print("=" * 80)
print("🤖 DrumTracKAI - FULLY AUTOMATED TRAINING")
print("=" * 80)
print("\nStarting training system with zero user input required...\n")

start_time = time.time()

# Step 1: Auto-locate databases
print("🔍 STEP 1: Auto-locating databases...")
print("-" * 80)

def quick_scan(root, pattern, max_files=50):
    """Quick scan - stops after finding max_files"""
    try:
        count = 0
        for item in root.rglob(pattern):
            count += 1
            if count >= max_files:
                return root, count
        return root if count > 0 else None, count
    except:
        return None, 0

# Check common E-GMD locations
egmd_candidates = [
    Path("E:/DrumTracKAI_Master/01_MIDI_Patterns/Datasets/E-GMD"),
    Path("E:/Datasets/E-GMD"),
    Path("E:/E-GMD"),
    Path("F:/Datasets/E-GMD"),
]

egmd_dir = None
for candidate in egmd_candidates:
    if candidate.exists():
        found, count = quick_scan(candidate, "*.mid", max_files=10)
        if found and count > 0:
            egmd_dir = candidate
            print(f"✅ E-GMD: {egmd_dir} ({count}+ MIDI files)")
            break

if not egmd_dir:
    print("⏭️  E-GMD: Not found (will use rudiments only)")

# Check common loop locations
loops_candidates = [
    Path("E:/DrumTracKAI_Master/01_MIDI_Patterns/Datasets/SoundTracksLoops"),
    Path("E:/SoundTracksLoops"),
    Path("E:/Loops"),
    Path("E:/Drum Samples"),
    Path("F:/Loops"),
]

loops_dir = None
for candidate in loops_candidates:
    if candidate.exists():
        found, count = quick_scan(candidate, "*.wav", max_files=10)
        if found and count > 0:
            loops_dir = candidate
            print(f"✅ Loops: {loops_dir} ({count}+ WAV files)")
            break

if not loops_dir:
    print("⏭️  Loops: Not found (will use rudiments only)")

print(f"✅ Rudiments: Built-in")

# Step 2: Bootstrap
print("\n" + "=" * 80)
print("📦 STEP 2: Bootstrapping training data...")
print("=" * 80)

try:
    results = bootstrap_knowledge_base(
        egmd_dir=egmd_dir,
        rudiments=True,
        loops_dir=loops_dir,
        egmd_limit=500,
        loops_limit=100
    )
    
    total_samples = sum(results.values())
    print(f"\n✅ Extracted {total_samples} training samples")
    for source, count in results.items():
        print(f"   {source}: {count}")
    
except Exception as e:
    print(f"⚠️  Bootstrap failed: {e}")
    print("   Continuing with rudiments only...")

# Step 3: Build dataset
print("\n" + "=" * 80)
print("📊 STEP 3: Building dataset...")
print("=" * 80)

builder = DrumDatasetBuilder()
dataset = builder.build_humanization_dataset(min_samples=10)

print(f"✅ Dataset ready:")
print(f"   Train: {len(dataset.X_train)}")
print(f"   Val: {len(dataset.X_val)}")
print(f"   Test: {len(dataset.X_test)}")

# Step 4: Train
print("\n" + "=" * 80)
print("🚀 STEP 4: Training on RTX 3070...")
print("=" * 80)

config = TrainingConfig(
    epochs=100,
    batch_size=32,
    learning_rate=0.001,
    use_gpu=True
)

trainer = AutonomousTrainer(config)
trainer.create_model(input_size=3, output_size=9)

print("Training in progress...\n")

def progress_callback(percent, msg):
    if percent % 25 == 0:
        print(f"   [{percent}%] {msg}")

train_start = time.time()

metrics = trainer.train_model(
    dataset.X_train, dataset.y_train,
    dataset.X_val, dataset.y_val,
    progress_callback
)

train_time = time.time() - train_start

print(f"\n✅ Training complete: {train_time:.1f}s")
print(f"   Final loss: {metrics[-1].train_loss:.4f}")

# Step 5: Validate
print("\n" + "=" * 80)
print("✅ STEP 5: Validating...")
print("=" * 80)

validator = ModelValidator()
val_metrics = validator.validate_model(trainer, dataset.X_test, dataset.y_test)

print(f"   Humanization Score: {val_metrics.humanization_score:.1f}/100")
print(f"   R² Score: {val_metrics.r2_score:.3f}")

# Step 6: Deploy
print("\n" + "=" * 80)
print("💾 STEP 6: Deploying model...")
print("=" * 80)

deployer = ModelDeployer()

# Save model first
models_dir = Path("models")
models_dir.mkdir(exist_ok=True)
model_path = models_dir / "drumtrackai_model_v1.pt"

import torch
torch.save({
    'model_state': trainer.model.state_dict(),
    'config': {
        'input_size': 3,
        'output_size': 9
    },
    'metrics': {
        'validation_score': val_metrics.humanization_score,
        'r2_score': val_metrics.r2_score,
        'train_samples': len(dataset.X_train),
        'sources': list(results.keys()) if 'results' in locals() else ['rudiments']
    }
}, model_path)

# Deploy to production
deployer.deploy_model(
    model_path=model_path,
    model_name="drumtrackai",
    version="1.0.0",
    metadata={
        'validation_score': val_metrics.humanization_score,
        'r2_score': val_metrics.r2_score,
        'train_samples': len(dataset.X_train),
        'sources': list(results.keys()) if 'results' in locals() else ['rudiments']
    }
)

total_time = time.time() - start_time

# Final summary
print("\n\n" + "=" * 80)
print("🎉 TRAINING COMPLETE!")
print("=" * 80)

print(f"\n⏱️  Total Time: {total_time:.1f} seconds")
print(f"📊 Score: {val_metrics.humanization_score:.1f}/100")
print(f"🎯 Model Quality: {'Excellent' if val_metrics.humanization_score > 80 else 'Good' if val_metrics.humanization_score > 60 else 'Basic'}")

print(f"\n📁 MODEL SAVED TO:")
print(f"   {model_path.absolute()}")

print(f"\n💡 To use this model:")
print(f"   1. Load: torch.load('{model_path}')")
print(f"   2. Or integrate into admin app")
print(f"   3. Or deploy to production")

print("\n" + "=" * 80)

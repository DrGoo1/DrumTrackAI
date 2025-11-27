"""
Bootstrap Training System with Existing Databases
Quickly build a robust drum knowledge base from:
- E-GMD (E-Groove MIDI Dataset)
- Snare Rudiments
- SoundsTracks Loops

Then train the AI model!
"""

from pathlib import Path
from admin.training.database_bootstrapper import bootstrap_knowledge_base
from admin.training.dataset_builder import DrumDatasetBuilder
from admin.training.model_trainer import AutonomousTrainer, TrainingConfig
from admin.training.validation import ModelValidator
from admin.training.deployment import ModelDeployer

print("=" * 80)
print("🎯 DrumTracKAI - Knowledge Base Bootstrap + Training")
print("=" * 80)
print("\nThis will:")
print("1. Extract from E-GMD MIDI dataset")
print("2. Extract from Snare Rudiments")
print("3. Extract from SoundsTracks Loops")
print("4. Build training dataset")
print("5. Train AI model on RTX 3070")
print("6. Deploy to production")
print("\n" + "=" * 80)

# Configure your database locations
print("\n📁 Configure Database Locations:")
print("\nEnter paths to your databases (press Enter to skip):\n")

egmd_path = input("E-GMD directory (e.g., C:/Datasets/E-GMD): ").strip()
loops_path = input("SoundsTracks Loops directory (e.g., C:/Loops/Drums): ").strip()

# Rudiments are built-in, always available
use_rudiments = True

# Convert to Path objects
egmd_dir = Path(egmd_path) if egmd_path else None
loops_dir = Path(loops_path) if loops_path else None

# Check what's available
print("\n📊 Available Databases:")
if egmd_dir and egmd_dir.exists():
    egmd_files = len(list(egmd_dir.rglob('*.mid')))
    print(f"   ✅ E-GMD: {egmd_files} MIDI files")
else:
    print(f"   ⏭️ E-GMD: Skipped")

if use_rudiments:
    print(f"   ✅ Rudiments: 40+ patterns (built-in)")

if loops_dir and loops_dir.exists():
    loop_files = len(list(loops_dir.rglob('*.wav')))
    print(f"   ✅ SoundsTracks: {loop_files} loops")
else:
    print(f"   ⏭️ SoundsTracks: Skipped")

proceed = input("\n🚀 Proceed with extraction? (y/n): ").strip().lower()

if proceed != 'y':
    print("❌ Aborted")
    exit(0)

# Step 1: Bootstrap knowledge base
print("\n\n" + "=" * 80)
print("STEP 1: Extract from Databases")
print("=" * 80)

results = bootstrap_knowledge_base(
    egmd_dir=egmd_dir,
    rudiments=use_rudiments,
    loops_dir=loops_dir,
    egmd_limit=500,  # Process 500 E-GMD files
    loops_limit=100  # Process 100 loops
)

total_samples = sum(results.values())

if total_samples < 10:
    print("\n❌ Not enough samples to train")
    print(f"   Need at least 10, have {total_samples}")
    print("\nOptions:")
    print("1. Add database directories")
    print("2. Run: python train_from_youtube.py")
    print("3. Run: python extract_and_train.py")
    exit(1)

# Step 2: Build dataset
print("\n\n" + "=" * 80)
print("STEP 2: Build Training Dataset")
print("=" * 80)

builder = DrumDatasetBuilder()
stats = builder.get_dataset_stats()

print(f"\n📊 Dataset Statistics:")
print(f"   Total samples: {stats['total_samples']}")
print(f"   Sources: {stats['sources']}")
print(f"   Styles: {list(stats['styles'].keys())}")

dataset = builder.build_humanization_dataset(min_samples=10)

print(f"\n✅ Dataset Built:")
print(f"   Train: {len(dataset.X_train)} samples")
print(f"   Val: {len(dataset.X_val)} samples")
print(f"   Test: {len(dataset.X_test)} samples")
print(f"   Features: {len(dataset.feature_names)}")

# Step 3: Train model
print("\n\n" + "=" * 80)
print("STEP 3: Train AI Model on RTX 3070")
print("=" * 80)

config = TrainingConfig(
    epochs=100,
    batch_size=32,
    learning_rate=0.001,
    use_gpu=True
)

trainer = AutonomousTrainer(config)
trainer.create_model(input_size=3, output_size=9)

print("\n🚀 Training with GPU acceleration...")
print("This should take 30-60 seconds with your RTX 3070...\n")

def progress_callback(percent, msg):
    if percent % 20 == 0:
        print(f"   {msg}")

metrics = trainer.train_model(
    dataset.X_train, dataset.y_train,
    dataset.X_val, dataset.y_val,
    progress_callback
)

print(f"\n✅ Training Complete!")
print(f"   Epochs: {len(metrics)}")
print(f"   Final train loss: {metrics[-1].train_loss:.4f}")
print(f"   Final val loss: {metrics[-1].val_loss:.4f}")

# Step 4: Validate
print("\n\n" + "=" * 80)
print("STEP 4: Validate Model")
print("=" * 80)

validator = ModelValidator()
val_metrics = validator.validate_model(trainer, dataset.X_test, dataset.y_test)

print(f"\n📊 Validation Results:")
print(f"   MAE: {val_metrics.mae:.4f}")
print(f"   R² Score: {val_metrics.r2_score:.3f}")
print(f"   Humanization Score: {val_metrics.humanization_score:.1f}/100")

print(f"\n📈 Per-Parameter Performance:")
for param, mae in list(val_metrics.per_param_mae.items())[:5]:
    print(f"   {param}: {mae:.4f}")

# Step 5: Deploy
print("\n\n" + "=" * 80)
print("STEP 5: Deploy to Production")
print("=" * 80)

deployer = ModelDeployer()

success = deployer.deploy_model(
    trainer.config.checkpoint_dir / "best_model.pth",
    "drum_humanizer_bootstrap",
    "1.0.0",
    metadata={
        'source': 'bootstrap',
        'egmd_samples': results.get('egmd', 0),
        'rudiment_samples': results.get('rudiments', 0),
        'loop_samples': results.get('loops', 0),
        'total_samples': stats['total_samples'],
        'humanization_score': val_metrics.humanization_score,
        'mae': val_metrics.mae
    }
)

if success:
    print("\n✅ Model Deployed Successfully!")
    print("\nModel location:")
    print("   models/production/drum_humanizer_bootstrap_1.0.0/")
else:
    print("\n⚠️ Deployment failed")

# Summary
print("\n\n" + "=" * 80)
print("🎉 BOOTSTRAP COMPLETE!")
print("=" * 80)

print(f"\n📊 Training Summary:")
print(f"   E-GMD grooves: {results.get('egmd', 0)}")
print(f"   Rudiment patterns: {results.get('rudiments', 0)}")
print(f"   Drum loops: {results.get('loops', 0)}")
print(f"   Total samples: {stats['total_samples']}")
print(f"   Humanization score: {val_metrics.humanization_score:.1f}/100")

print(f"\n🎯 Knowledge Base Includes:")
if results.get('egmd', 0) > 0:
    print(f"   ✅ {results['egmd']} MIDI grooves (timing patterns)")
if results.get('rudiments', 0) > 0:
    print(f"   ✅ {results['rudiments']} rudiments (accent patterns, ghost notes)")
if results.get('loops', 0) > 0:
    print(f"   ✅ {results['loops']} professional loops (real performances)")

print(f"\n✨ Your AI now has a robust drum knowledge base!")
print(f"   It learned from structured databases + real performances")

print("\n💡 Next Steps:")
print("   1. Add more data: python train_from_youtube.py")
print("   2. Test in production: Use drum_generation_api.py")
print("   3. Retrain periodically with new data")

print("\n" + "=" * 80)

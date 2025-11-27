"""
Extract training data from your music and train a real model
"""

from pathlib import Path
from admin.training.data_extraction import CommercialSongAnalyzer
from admin.training.dataset_builder import DrumDatasetBuilder
from admin.training.model_trainer import AutonomousTrainer, TrainingConfig
from admin.training.validation import ModelValidator
from admin.training.deployment import ModelDeployer

print("=" * 70)
print("DrumTracKAI - Extract Data and Train Model")
print("=" * 70)

# Step 1: Analyze commercial songs
print("\n📥 STEP 1: Extract training data from songs")
print("-" * 70)

analyzer = CommercialSongAnalyzer()

# TODO: Add your music files here!
music_files = [
    # Example: Path("C:/Music/rock_songs/song1.wav"),
    # Add paths to your audio files...
]

# Or scan a directory
music_dir = Path("C:/Music")  # Change to your music directory
if music_dir.exists():
    music_files = list(music_dir.glob("**/*.wav"))[:10]  # First 10 WAV files
    music_files += list(music_dir.glob("**/*.mp3"))[:10]  # First 10 MP3 files

if not music_files:
    print("⚠️ No music files found!")
    print("\nTo add training data:")
    print("1. Edit this file (extract_and_train.py)")
    print("2. Add paths to your audio files in the music_files list")
    print("3. Or set music_dir to your music folder")
    print("\nFor now, training with existing data...")
else:
    print(f"Found {len(music_files)} audio files")
    
    for i, audio_file in enumerate(music_files, 1):
        print(f"\n   [{i}/{len(music_files)}] Analyzing: {audio_file.name}")
        try:
            features = analyzer.analyze_song(audio_file)
            if features:
                print(f"      ✅ Extracted features")
        except Exception as e:
            print(f"      ⚠️ Error: {e}")

# Step 2: Build dataset
print("\n\n📊 STEP 2: Build training dataset")
print("-" * 70)

builder = DrumDatasetBuilder()
stats = builder.get_dataset_stats()

print(f"Total samples available: {stats['total_samples']}")

if stats['total_samples'] < 10:
    print("\n⚠️ Not enough training data yet!")
    print("Need at least 10 samples to train.")
    print("\nOptions:")
    print("1. Add more audio files and run again")
    print("2. Run: python admin/training/data_extraction.py")
    print("3. Use admin app to extract SD samples")
    exit(1)

try:
    dataset = builder.build_humanization_dataset(min_samples=10)
    print(f"\n✅ Dataset built:")
    print(f"   Train: {len(dataset.X_train)} samples")
    print(f"   Val: {len(dataset.X_val)} samples")
    print(f"   Test: {len(dataset.X_test)} samples")
except Exception as e:
    print(f"\n❌ Error building dataset: {e}")
    exit(1)

# Step 3: Train model
print("\n\n🚀 STEP 3: Train AI model")
print("-" * 70)

config = TrainingConfig(
    epochs=100,
    batch_size=32,
    learning_rate=0.001,
    use_gpu=True  # RTX 3070!
)

trainer = AutonomousTrainer(config)
trainer.create_model(input_size=3, output_size=9)

print("Training on RTX 3070 GPU...")
print("This should take 30-60 seconds...\n")

def progress_callback(percent, msg):
    if percent % 20 == 0:
        print(f"   {msg}")

metrics = trainer.train_model(
    dataset.X_train, dataset.y_train,
    dataset.X_val, dataset.y_val,
    progress_callback
)

print(f"\n✅ Training complete!")
print(f"   Epochs: {len(metrics)}")
print(f"   Final train loss: {metrics[-1].train_loss:.4f}")
print(f"   Final val loss: {metrics[-1].val_loss:.4f}")

# Step 4: Validate
print("\n\n✅ STEP 4: Validate model")
print("-" * 70)

validator = ModelValidator()
val_metrics = validator.validate_model(trainer, dataset.X_test, dataset.y_test)

print(f"Validation Results:")
print(f"   MAE: {val_metrics.mae:.4f}")
print(f"   R² Score: {val_metrics.r2_score:.3f}")
print(f"   Humanization Score: {val_metrics.humanization_score:.1f}/100")

# Step 5: Deploy
print("\n\n🎯 STEP 5: Deploy model")
print("-" * 70)

deployer = ModelDeployer()

try:
    success = deployer.deploy_model(
        trainer.config.checkpoint_dir / "best_model.pth",
        "drum_humanizer",
        "1.0.0",
        metadata={
            'samples': stats['total_samples'],
            'humanization_score': val_metrics.humanization_score,
            'mae': val_metrics.mae
        }
    )
    
    if success:
        print("✅ Model deployed successfully!")
        print("\nModel is now in production at:")
        print("   models/production/drum_humanizer_1.0.0/")
    else:
        print("⚠️ Deployment failed")
except Exception as e:
    print(f"⚠️ Deployment error: {e}")

print("\n" + "=" * 70)
print("🎉 TRAINING COMPLETE!")
print("=" * 70)
print("\nYour AI model has learned from real drummer performances!")
print("It will now make generated drums sound more human.")
print("\nNext: Integrate with drum_generation_api.py to use in production")

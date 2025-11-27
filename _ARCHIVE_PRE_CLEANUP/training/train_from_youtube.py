"""
Complete YouTube Training Pipeline
Downloads drum videos from YouTube and trains the AI
"""

from pathlib import Path
from admin.training.youtube_downloader import YouTubeDrumDownloader, batch_download_drummer, FAMOUS_DRUMMER_SEARCHES
from admin.training.data_extraction import CommercialSongAnalyzer
from admin.training.dataset_builder import DrumDatasetBuilder
from admin.training.model_trainer import AutonomousTrainer, TrainingConfig
from admin.training.validation import ModelValidator
from admin.training.deployment import ModelDeployer

print("=" * 80)
print("🎥 DrumTracKAI - YouTube Training Pipeline")
print("=" * 80)
print("\nThis will:")
print("1. Download drum performances from YouTube")
print("2. Analyze them with Rust audio-core")
print("3. Train AI model on your RTX 3070")
print("4. Deploy to production")
print("\n" + "=" * 80)

# Check if yt-dlp is installed
try:
    import yt_dlp
except ImportError:
    print("\n❌ ERROR: yt-dlp not installed")
    print("\nInstall with:")
    print("   pip install yt-dlp")
    print("\nOr run:")
    print("   pip install -r admin/training/requirements_youtube.txt")
    exit(1)

# Step 1: Download from YouTube
print("\n\n📥 STEP 1: Download drum performances from YouTube")
print("-" * 80)

downloader = YouTubeDrumDownloader()

print("\n🎯 Choose what to download:")
print("\nOption 1: Download specific drummer (recommended)")
print("Available drummers:")
for i, drummer in enumerate(FAMOUS_DRUMMER_SEARCHES.keys(), 1):
    print(f"   {i}. {drummer}")

print("\nOption 2: Download from URL")
print("   Single video or playlist")

print("\nOption 3: Search and download")
print("   Search for specific terms")

choice = input("\nEnter option (1/2/3) or press Enter to skip download: ").strip()

downloaded_files = []

if choice == "1":
    # Download drummer
    print("\nAvailable drummers:")
    drummers = list(FAMOUS_DRUMMER_SEARCHES.keys())
    for i, drummer in enumerate(drummers, 1):
        print(f"   {i}. {drummer}")
    
    drummer_choice = input("\nEnter number: ").strip()
    try:
        drummer_idx = int(drummer_choice) - 1
        if 0 <= drummer_idx < len(drummers):
            drummer_name = drummers[drummer_idx]
            max_per_search = input(f"\nMax videos per search (default 3): ").strip() or "3"
            
            print(f"\n🎵 Downloading {drummer_name} performances...")
            downloaded_files = batch_download_drummer(
                downloader,
                drummer_name,
                style='rock',  # Can be changed
                max_per_search=int(max_per_search)
            )
        else:
            print("Invalid selection")
    except ValueError:
        print("Invalid input")

elif choice == "2":
    # Download from URL
    url = input("\nEnter YouTube URL (video or playlist): ").strip()
    drummer_name = input("Drummer name (optional): ").strip() or None
    style = input("Style (rock/jazz/funk/etc, optional): ").strip() or None
    
    if "playlist" in url or "list=" in url:
        max_videos = input("Max videos to download (press Enter for all): ").strip()
        max_videos = int(max_videos) if max_videos else None
        
        print(f"\n🎵 Downloading playlist...")
        downloaded_files = downloader.download_playlist(url, drummer_name, style, max_videos)
    else:
        print(f"\n🎵 Downloading video...")
        file = downloader.download_video(url, drummer_name, style)
        if file:
            downloaded_files = [file]

elif choice == "3":
    # Search and download
    search_query = input("\nEnter search query (e.g., 'Jeff Porcaro drum solo'): ").strip()
    max_results = input("Max results (default 5): ").strip() or "5"
    drummer_name = input("Drummer name (optional): ").strip() or None
    style = input("Style (optional): ").strip() or None
    
    print(f"\n🔍 Searching YouTube...")
    downloaded_files = downloader.download_search_results(
        search_query,
        max_results=int(max_results),
        drummer_name=drummer_name,
        style=style
    )

else:
    print("\n⏭️ Skipping download, using existing files...")
    downloaded_files = downloader.get_downloaded_files()

if not downloaded_files:
    print("\n⚠️ No files available for training")
    exit(1)

print(f"\n✅ Have {len(downloaded_files)} audio files ready")

# Step 2: Analyze with Rust audio-core
print("\n\n📊 STEP 2: Analyze audio files")
print("-" * 80)

analyzer = CommercialSongAnalyzer()
analyzed_count = 0

for i, audio_file in enumerate(downloaded_files, 1):
    print(f"\n[{i}/{len(downloaded_files)}] Analyzing: {audio_file.name}")
    
    # Get metadata
    metadata = None
    for download in downloader.get_download_history():
        if Path(download['file_path']) == audio_file:
            metadata = download
            break
    
    drummer_name = metadata.get('drummer_name') if metadata else None
    style = metadata.get('style') if metadata else None
    
    try:
        features = analyzer.analyze_song(audio_file, drummer_name, style)
        if features:
            print(f"   ✅ Extracted humanization features")
            analyzed_count += 1
        else:
            print(f"   ⚠️ Analysis failed")
    except Exception as e:
        print(f"   ❌ Error: {e}")

print(f"\n✅ Analyzed {analyzed_count}/{len(downloaded_files)} files")

# Step 3: Build dataset
print("\n\n📦 STEP 3: Build training dataset")
print("-" * 80)

builder = DrumDatasetBuilder()
stats = builder.get_dataset_stats()

print(f"Total training samples: {stats['total_samples']}")
print(f"Drummers: {list(stats['drummers'].keys())}")
print(f"Styles: {list(stats['styles'].keys())}")

if stats['total_samples'] < 10:
    print("\n⚠️ Not enough data to train (need at least 10 samples)")
    print(f"Current: {stats['total_samples']}, Need: 10")
    print("\nOptions:")
    print("1. Download more videos")
    print("2. Add other data sources (SD samples, local files)")
    exit(1)

dataset = builder.build_humanization_dataset(min_samples=10)

print(f"\n✅ Dataset built:")
print(f"   Train: {len(dataset.X_train)} samples")
print(f"   Val: {len(dataset.X_val)} samples")
print(f"   Test: {len(dataset.X_test)} samples")

# Step 4: Train model
print("\n\n🚀 STEP 4: Train AI model on RTX 3070")
print("-" * 80)

config = TrainingConfig(
    epochs=100,
    batch_size=32,
    learning_rate=0.001,
    use_gpu=True
)

trainer = AutonomousTrainer(config)
trainer.create_model(input_size=3, output_size=9)

print("Training with GPU acceleration...")
print("This should take 30-60 seconds with your RTX 3070...\n")

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

# Step 5: Validate
print("\n\n✅ STEP 5: Validate model")
print("-" * 80)

validator = ModelValidator()
val_metrics = validator.validate_model(trainer, dataset.X_test, dataset.y_test)

print(f"Validation Results:")
print(f"   MAE: {val_metrics.mae:.4f}")
print(f"   R² Score: {val_metrics.r2_score:.3f}")
print(f"   Humanization Score: {val_metrics.humanization_score:.1f}/100")

# Step 6: Deploy
print("\n\n🎯 STEP 6: Deploy to production")
print("-" * 80)

deployer = ModelDeployer()

success = deployer.deploy_model(
    trainer.config.checkpoint_dir / "best_model.pth",
    "drum_humanizer_youtube",
    "1.0.0",
    metadata={
        'source': 'youtube',
        'samples': stats['total_samples'],
        'drummers': list(stats['drummers'].keys()),
        'humanization_score': val_metrics.humanization_score,
        'mae': val_metrics.mae,
        'downloaded_files': len(downloaded_files)
    }
)

if success:
    print("✅ Model deployed successfully!")
    print("\nModel location:")
    print("   models/production/drum_humanizer_youtube_1.0.0/")
else:
    print("⚠️ Deployment failed")

# Summary
print("\n\n" + "=" * 80)
print("🎉 TRAINING COMPLETE!")
print("=" * 80)

print(f"\n📊 Summary:")
print(f"   YouTube videos downloaded: {len(downloaded_files)}")
print(f"   Files analyzed: {analyzed_count}")
print(f"   Training samples: {stats['total_samples']}")
print(f"   Drummers learned: {', '.join(stats['drummers'].keys())}")
print(f"   Model humanization score: {val_metrics.humanization_score:.1f}/100")

print(f"\n🎵 Your AI has learned from:")
for drummer, count in stats['drummers'].items():
    print(f"   - {drummer}: {count} samples")

print(f"\n✨ The model will now make drums sound more human!")
print(f"   Based on real performances from YouTube!")

print("\n" + "=" * 80)

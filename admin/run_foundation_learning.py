"""
Foundation Learning - Standalone Runner
=======================================
Simple script that ensures all paths are set correctly.
"""

import sys
from pathlib import Path

# Ensure admin directory is in path
admin_dir = Path(__file__).parent
if str(admin_dir) not in sys.path:
    sys.path.insert(0, str(admin_dir))

print("🚀 Foundation Learning Standalone Runner")
print("=" * 70)

# Import with explicit path handling
print("\n📦 Loading modules...")

try:
    from training.youtube_downloader import YouTubeDrumDownloader
    print("✅ YouTube downloader loaded")
except ImportError as e:
    print(f"❌ Failed to load YouTube downloader: {e}")
    print(f"\nChecking file: {admin_dir / 'training' / 'youtube_downloader.py'}")
    print(f"Exists: {(admin_dir / 'training' / 'youtube_downloader.py').exists()}")
    sys.exit(1)

try:
    from services.youtube_llm_learning_service import YouTubeLLMLearningPipeline
    print("✅ YouTube LLM service loaded")
except ImportError as e:
    print(f"⚠️  YouTube LLM service not available: {e}")
    YouTubeLLMLearningPipeline = None

print("\n✅ All modules loaded successfully!")
print("=" * 70)

# Now run the actual foundation learning
from datetime import datetime
import time
import json

class SimpleFoundationLearner:
    """Simplified foundation learner that doesn't rely on complex imports."""
    
    def __init__(self):
        self.base_dir = Path("data/youtube_foundation_learning")
        self.base_dir.mkdir(parents=True, exist_ok=True)
        
        self.downloads_dir = self.base_dir / "downloads"
        self.downloads_dir.mkdir(parents=True, exist_ok=True)
        
        self.downloader = YouTubeDrumDownloader(self.downloads_dir)
        print(f"\n📁 Initialized: {self.base_dir}")
    
    def run_learning(self, max_videos_per_technique=2):
        """Run foundation learning."""
        
        # Define techniques to learn
        techniques = {
            'beginner': [
                'basic rock beat',
                'four on the floor',
                'simple jazz ride pattern',
                'basic funk groove',
            ],
            'intermediate': [
                'paradiddle',
                'single stroke roll',
                'snare ghost notes',
                'basic tom fill',
            ],
            'advanced': [
                'polyrhythm 3 over 4',
                'odd time signatures',
                'four limb independence',
            ]
        }
        
        print(f"\n🎓 Starting Foundation Learning")
        print(f"   Videos per technique: {max_videos_per_technique}")
        print("=" * 70)
        
        total_downloaded = 0
        results_by_level = {}
        
        for level, technique_list in techniques.items():
            print(f"\n📚 Learning {level.upper()} techniques...")
            level_downloads = 0
            
            for technique in technique_list:
                print(f"\n🎯 {technique}")
                query = f"{technique} drum lesson"
                
                try:
                    files = self.downloader.download_search_results(
                        search_query=query,
                        max_results=max_videos_per_technique,
                        style=level
                    )
                    
                    if files:
                        print(f"   ✅ Downloaded {len(files)} video(s)")
                        level_downloads += len(files)
                        total_downloaded += len(files)
                    else:
                        print(f"   ⚠️  No videos found")
                    
                    # Small delay to be nice to YouTube
                    time.sleep(2)
                    
                except Exception as e:
                    print(f"   ❌ Error: {e}")
                    continue
            
            results_by_level[level] = {
                'techniques': len(technique_list),
                'videos': level_downloads
            }
            
            print(f"\n✅ {level.upper()} complete: {level_downloads} videos")
        
        # Summary
        print("\n" + "=" * 70)
        print("✅ FOUNDATION LEARNING COMPLETE!")
        print("=" * 70)
        print(f"Total Videos Downloaded: {total_downloaded}")
        print(f"\nBy Level:")
        for level, stats in results_by_level.items():
            print(f"  {level.capitalize()}: {stats['videos']} videos, {stats['techniques']} techniques")
        
        print("\n" + "=" * 70)
        print("Next: Evaluate Track A expertise")
        print("=" * 70)
        
        return {
            'total_videos': total_downloaded,
            'by_level': results_by_level
        }

# Run it
print("\n" + "=" * 70)
response = input("Start foundation learning? (y/n): ")

if response.lower() == 'y':
    learner = SimpleFoundationLearner()
    result = learner.run_learning(max_videos_per_technique=2)
    
    print(f"\n🎉 Done! Downloaded {result['total_videos']} videos")
else:
    print("Cancelled")

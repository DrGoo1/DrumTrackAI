"""
Simple Foundation Learning Starter
==================================
Starts foundation learning without complex imports.
"""

import sys
from pathlib import Path

# Add current directory to path
sys.path.insert(0, str(Path(__file__).parent))

print("🚀 Starting Foundation Learning...")
print("=" * 70)

# Test imports
try:
    from services.youtube_foundation_learning import (
        YouTubeFoundationLearning,
        full_foundation_curriculum
    )
    print("✅ Foundation learning service imported successfully")
except ImportError as e:
    print(f"❌ Import failed: {e}")
    print("\nTrying alternative import method...")
    
    # Try adding parent to path
    admin_dir = Path(__file__).parent
    sys.path.insert(0, str(admin_dir))
    
    try:
        from services.youtube_foundation_learning import (
            YouTubeFoundationLearning,
            full_foundation_curriculum
        )
        print("✅ Foundation learning service imported (alternative method)")
    except ImportError as e2:
        print(f"❌ Still failed: {e2}")
        print("\nDebugging info:")
        print(f"Current directory: {Path.cwd()}")
        print(f"Script directory: {admin_dir}")
        print(f"Services path: {admin_dir / 'services'}")
        print(f"Services exists: {(admin_dir / 'services').exists()}")
        print(f"Foundation file exists: {(admin_dir / 'services' / 'youtube_foundation_learning.py').exists()}")
        sys.exit(1)

print("\n" + "=" * 70)
print("Starting autonomous foundation learning...")
print("This will download ~110 videos (2-3 hours)")
print("=" * 70)
print()

# Ask for confirmation
response = input("Start now? (y/n): ")

if response.lower() != 'y':
    print("Cancelled.")
    sys.exit(0)

print("\n🎓 Starting foundation curriculum...")
print("=" * 70)

try:
    # Run the full curriculum
    result = full_foundation_curriculum(max_videos_per_technique=2)
    
    print("\n" + "=" * 70)
    print("✅ FOUNDATION LEARNING COMPLETE!")
    print("=" * 70)
    print(f"Total Videos: {result['total_videos']}")
    print(f"Total Techniques: {result['total_techniques']}")
    print(f"Levels Completed: {len(result['levels_completed'])}")
    
    for level_result in result['levels_completed']:
        print(f"\n{level_result['level'].upper()}:")
        print(f"  Videos: {level_result['videos_downloaded']}")
        print(f"  Techniques: {level_result['techniques_learned']}")
    
    print("\n" + "=" * 70)
    print("Next step: Evaluate Track A score")
    print("Run: python -c \"from services.expertise_tracking_service import ExpertiseTrackingService; t=ExpertiseTrackingService(); r=t.evaluate_general_expertise(); print(f'Track A: {r[\\\"overall_score\\\"]}%')\"")
    print("=" * 70)
    
except Exception as e:
    print(f"\n❌ Error during learning: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

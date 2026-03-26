"""
Test Foundation Learning Imports
================================
Diagnostic script to check if all imports work.
"""

import sys
from pathlib import Path

print("🔍 Testing Foundation Learning Imports")
print("=" * 70)

# Show environment
print("\n📁 Environment:")
print(f"Current directory: {Path.cwd()}")
print(f"Script directory: {Path(__file__).parent}")
print(f"Python path: {sys.path[:3]}")

# Check file existence
admin_dir = Path(__file__).parent
services_dir = admin_dir / "services"
foundation_file = services_dir / "youtube_foundation_learning.py"

print("\n📂 File System Check:")
print(f"Admin directory: {admin_dir}")
print(f"  Exists: {admin_dir.exists()}")
print(f"Services directory: {services_dir}")
print(f"  Exists: {services_dir.exists()}")
print(f"Foundation file: {foundation_file}")
print(f"  Exists: {foundation_file.exists()}")

# List services directory
print("\n📋 Files in services/:")
if services_dir.exists():
    for file in services_dir.iterdir():
        print(f"  - {file.name}")

# Try imports
print("\n🔬 Testing Imports:")

# Test 1: Basic import
print("\n1. Testing: from services.youtube_foundation_learning import YouTubeFoundationLearning")
try:
    from services.youtube_foundation_learning import YouTubeFoundationLearning
    print("   ✅ SUCCESS")
except ImportError as e:
    print(f"   ❌ FAILED: {e}")
    
    # Try adding to path
    print("\n2. Adding admin to sys.path and retrying...")
    sys.path.insert(0, str(admin_dir))
    
    try:
        from services.youtube_foundation_learning import YouTubeFoundationLearning
        print("   ✅ SUCCESS (after adding to path)")
    except ImportError as e2:
        print(f"   ❌ FAILED: {e2}")

# Test yt-dlp
print("\n3. Testing: import yt_dlp")
try:
    import yt_dlp
    print("   ✅ SUCCESS - yt-dlp is installed")
except ImportError:
    print("   ❌ FAILED - yt-dlp NOT installed")
    print("   Install with: pip install yt-dlp")

# Test YouTube downloader
print("\n4. Testing: from training.youtube_downloader import YouTubeDrumDownloader")
try:
    from training.youtube_downloader import YouTubeDrumDownloader
    print("   ✅ SUCCESS")
except ImportError as e:
    print(f"   ❌ FAILED: {e}")

print("\n" + "=" * 70)
print("Diagnostic complete!")
print("=" * 70)

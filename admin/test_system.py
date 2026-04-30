"""
System Test - Verify Foundation Learning is Fully Working
=========================================================
Tests all components and attempts a single download.
"""

import sys
from pathlib import Path

# Add admin to path
admin_dir = Path(__file__).parent
sys.path.insert(0, str(admin_dir))

print("🔍 SYSTEM TEST - Foundation Learning")
print("=" * 70)

# Test 1: Module imports
print("\n✅ Test 1: Module Imports")
try:
    from training.youtube_downloader import YouTubeDrumDownloader
    print("   ✅ YouTube downloader imported")
except ImportError as e:
    print(f"   ❌ Failed: {e}")
    sys.exit(1)

# Test 2: yt-dlp version
print("\n✅ Test 2: yt-dlp Version")
try:
    import yt_dlp
    print(f"   ✅ yt-dlp version: {yt_dlp.version.__version__}")
except ImportError:
    print("   ❌ yt-dlp not installed")
    sys.exit(1)

# Test 3: Create downloader
print("\n✅ Test 3: Initialize Downloader")
try:
    test_dir = Path("data/test_download")
    test_dir.mkdir(parents=True, exist_ok=True)
    downloader = YouTubeDrumDownloader(test_dir)
    print(f"   ✅ Downloader initialized: {downloader.download_dir}")
except Exception as e:
    print(f"   ❌ Failed: {e}")
    sys.exit(1)

# Test 4: Attempt a single download
print("\n✅ Test 4: Test Download (Single Video)")
print("   Searching for: 'basic drum beat tutorial'")
print("   This may take 30-60 seconds...")

try:
    # Try to download just 1 video as a test
    files = downloader.download_search_results(
        search_query="basic drum beat tutorial",
        max_results=1,
        drummer_name="Test",
        style="test"
    )
    
    if files and len(files) > 0:
        print(f"   ✅ SUCCESS! Downloaded: {files[0].name}")
        print(f"   ✅ File size: {files[0].stat().st_size / 1024 / 1024:.2f} MB")
        print(f"   ✅ Location: {files[0]}")
        
        # Clean up test file
        response = input("\n   Delete test file? (y/n): ")
        if response.lower() == 'y':
            files[0].unlink()
            print("   ✅ Test file deleted")
        
        result = "SUCCESS"
    else:
        print("   ⚠️  No files downloaded (but no error)")
        result = "PARTIAL"
        
except Exception as e:
    print(f"   ❌ Download failed: {e}")
    result = "FAILED"
    import traceback
    traceback.print_exc()

# Final verdict
print("\n" + "=" * 70)
print("SYSTEM TEST RESULTS")
print("=" * 70)

if result == "SUCCESS":
    print("✅ ALL SYSTEMS OPERATIONAL!")
    print("\n   The foundation learning system is fully working and ready to use.")
    print("\n   Next steps:")
    print("   1. Run: python run_foundation_learning.py")
    print("   2. Type 'y' to start learning")
    print("   3. System will download ~11 technique videos")
    print("   4. Takes about 30-45 minutes")
    
elif result == "PARTIAL":
    print("⚠️  SYSTEM PARTIALLY WORKING")
    print("\n   Modules load but download failed.")
    print("   This could be:")
    print("   - YouTube rate limiting")
    print("   - Network issue")
    print("   - Video not available")
    print("\n   Try running the full learning - it may work with different queries.")
    
else:
    print("❌ SYSTEM NOT WORKING")
    print("\n   There's an issue with the download functionality.")
    print("   Check the error above.")

print("=" * 70)

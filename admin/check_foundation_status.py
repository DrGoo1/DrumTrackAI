"""
Check Foundation Learning Status
================================
Quick script to check current foundation learning status.
"""

import sys
from pathlib import Path

def check_status():
    """Check current foundation learning status."""
    print("\n" + "="*70)
    print("🔍 FOUNDATION LEARNING STATUS CHECK")
    print("="*70)
    
    # Check if service is available
    try:
        from services.youtube_foundation_learning import (
            YouTubeFoundationLearning,
            show_available_techniques
        )
        print("\n✅ Foundation learning service: AVAILABLE")
    except ImportError as e:
        print(f"\n❌ Foundation learning service: NOT AVAILABLE")
        print(f"   Error: {e}")
        return False
    
    # Check if YouTube downloader is available
    try:
        import yt_dlp
        print("✅ yt-dlp: INSTALLED")
    except ImportError:
        print("❌ yt-dlp: NOT INSTALLED")
        print("   Install with: pip install yt-dlp")
        return False
    
    # Check base directory
    learner = YouTubeFoundationLearning()
    print(f"\n📁 Base Directory: {learner.base_dir}")
    print(f"   Downloads: {learner.downloads_dir}")
    print(f"   Analysis: {learner.analysis_dir}")
    print(f"   Datasets: {learner.datasets_dir}")
    
    # Check if any learning has been done
    download_history = learner.youtube_downloader.get_download_history()
    
    if download_history:
        print(f"\n📊 Progress:")
        print(f"   Videos downloaded: {len(download_history)}")
        print(f"   Latest download: {download_history[-1].get('title', 'Unknown')}")
    else:
        print(f"\n📊 Progress:")
        print(f"   Videos downloaded: 0")
        print(f"   Status: NOT STARTED")
    
    # Show available techniques
    print("\n" + "="*70)
    print("📚 AVAILABLE TECHNIQUES (Can be learned autonomously)")
    print("="*70)
    
    summary = learner.get_available_techniques()
    print(f"\nTotal Categories: {summary['total_categories']}")
    print(f"Total Techniques: {summary['total_techniques']}")
    
    print("\n📊 BY LEVEL:")
    for level in ['beginner', 'intermediate', 'advanced']:
        info = summary['by_level'][level]
        print(f"\n{level.upper()}: {info['count']} techniques")
        for tech in info['techniques'][:3]:
            print(f"  ✓ {tech}")
        if len(info['techniques']) > 3:
            print(f"  ... and {len(info['techniques']) - 3} more")
    
    print("\n" + "="*70)
    
    # Check if running
    if download_history:
        print("\n🎯 SYSTEM STATUS: Foundation learning has been started")
        print(f"   Progress: {len(download_history)}/~110 videos")
        percentage = int((len(download_history) / 110) * 100)
        print(f"   Estimated: {percentage}% complete")
    else:
        print("\n🎯 SYSTEM STATUS: Foundation learning NOT started")
        print("\n   To start learning:")
        print("   1. Run: START_FOUNDATION_LEARNING.bat")
        print("   2. Or use Python:")
        print("      from services.youtube_foundation_learning import full_foundation_curriculum")
        print("      result = full_foundation_curriculum(2)")
    
    print("\n" + "="*70)
    
    return True


def show_monitoring_options():
    """Show how to monitor progress."""
    print("\n📊 MONITORING OPTIONS:")
    print("\n1. GUI Monitor (RECOMMENDED):")
    print("   - Run: START_FOUNDATION_LEARNING.bat")
    print("   - Real-time progress bars")
    print("   - Live logging")
    print("   - Visual status tracking")
    
    print("\n2. Command Line Status:")
    print("   - Run: python check_foundation_status.py")
    print("   - Quick status check")
    print("   - Download count")
    
    print("\n3. Direct File Check:")
    print("   - Check: admin/data/youtube_foundation_learning/downloads/")
    print("   - Count .wav files")
    print("   - Read download_metadata.json")
    
    print("\n4. Programmatic Check:")
    print("""
from services.youtube_foundation_learning import YouTubeFoundationLearning
learner = YouTubeFoundationLearning()
history = learner.youtube_downloader.get_download_history()
print(f"Downloaded: {len(history)} videos")
""")


if __name__ == "__main__":
    success = check_status()
    
    if success:
        show_monitoring_options()
        
        print("\n" + "="*70)
        print("✅ System check complete!")
        print("="*70 + "\n")
    else:
        print("\n" + "="*70)
        print("❌ System check failed - missing dependencies")
        print("="*70 + "\n")
        sys.exit(1)

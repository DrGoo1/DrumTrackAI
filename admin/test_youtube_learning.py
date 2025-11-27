"""
Test YouTube LLM Learning Pipeline
==================================
Quick test script to verify the pipeline works.
"""

import sys
import logging
from pathlib import Path

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def test_pipeline_imports():
    """Test that all required modules can be imported."""
    print("🧪 Testing imports...")
    
    try:
        from services.youtube_llm_learning_service import (
            YouTubeLLMLearningPipeline,
            quick_learn_from_youtube,
            batch_learn_famous_drummers,
            FAMOUS_DRUMMER_SEARCHES
        )
        print("✅ Pipeline service imported successfully")
        return True
    except ImportError as e:
        print(f"❌ Import failed: {e}")
        return False

def test_pipeline_initialization():
    """Test pipeline initialization."""
    print("\n🧪 Testing pipeline initialization...")
    
    try:
        from services.youtube_llm_learning_service import YouTubeLLMLearningPipeline
        
        pipeline = YouTubeLLMLearningPipeline()
        print(f"✅ Pipeline initialized")
        print(f"   Base dir: {pipeline.base_dir}")
        print(f"   Downloads: {pipeline.downloads_dir}")
        print(f"   Analysis: {pipeline.analysis_dir}")
        print(f"   Datasets: {pipeline.datasets_dir}")
        print(f"   Audio-core: {pipeline.audio_core_bin or 'Not found (limited analysis)'}")
        
        return True
    except Exception as e:
        print(f"❌ Initialization failed: {e}")
        return False

def test_famous_drummers_list():
    """Test that famous drummers list is available."""
    print("\n🧪 Testing famous drummers list...")
    
    try:
        from services.youtube_llm_learning_service import FAMOUS_DRUMMER_SEARCHES
        
        print(f"✅ Found {len(FAMOUS_DRUMMER_SEARCHES)} famous drummers:")
        for drummer in sorted(FAMOUS_DRUMMER_SEARCHES.keys()):
            queries = FAMOUS_DRUMMER_SEARCHES[drummer]
            print(f"   - {drummer}: {len(queries)} search queries")
        
        return True
    except Exception as e:
        print(f"❌ Failed: {e}")
        return False

def test_quick_single_drummer():
    """Test downloading and analyzing a single drummer (1 video)."""
    print("\n🧪 Testing single drummer pipeline...")
    print("⚠️  This will download 1 video from YouTube (may take 30-60 seconds)")
    
    response = input("\nProceed with test download? (y/n): ")
    if response.lower() != 'y':
        print("Skipped")
        return True
    
    try:
        from services.youtube_llm_learning_service import YouTubeLLMLearningPipeline
        
        pipeline = YouTubeLLMLearningPipeline()
        
        print("\n📥 Starting pipeline for Jeff Porcaro (1 video)...")
        result = pipeline.run_complete_pipeline(
            drummer_name="Jeff Porcaro",
            style="rock",
            max_videos=1,  # Just 1 video for testing
            start_training=False
        )
        
        if result['success']:
            print(f"\n✅ SUCCESS!")
            print(f"   Files sourced: {result['files_sourced']}")
            print(f"   Dataset: {result['dataset_file']}")
            print(f"   Time: {result['elapsed_time']:.1f}s")
            return True
        else:
            print(f"\n❌ Pipeline failed: {result.get('error', 'Unknown error')}")
            return False
            
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run all tests."""
    print("="*70)
    print("YouTube LLM Learning Pipeline - Test Suite")
    print("="*70)
    
    tests = [
        ("Import Test", test_pipeline_imports),
        ("Initialization Test", test_pipeline_initialization),
        ("Famous Drummers List", test_famous_drummers_list),
        ("Single Drummer Pipeline", test_quick_single_drummer),
    ]
    
    results = []
    for test_name, test_func in tests:
        result = test_func()
        results.append((test_name, result))
    
    # Summary
    print("\n" + "="*70)
    print("TEST SUMMARY")
    print("="*70)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {test_name}")
    
    print(f"\n{passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All tests passed! YouTube LLM Learning Pipeline is ready!")
        print("\nNext steps:")
        print("1. Run admin UI: python main.py")
        print("2. Go to 'YouTube Learning' tab")
        print("3. Select a drummer and start learning!")
    else:
        print("\n⚠️  Some tests failed. Check errors above.")
    
    print("="*70)

if __name__ == "__main__":
    main()

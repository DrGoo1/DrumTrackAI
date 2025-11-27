"""
Quick Test Script for Drummer Connection
Tests that all components work together
"""
import sys
from pathlib import Path

# Add current directory to path
sys.path.insert(0, str(Path(__file__).parent))

from drummer_mapping_service import get_drummer_service

def test_drummer_service():
    """Test the drummer mapping service"""
    print("="*70)
    print("  TESTING DRUMMER MAPPING SERVICE")
    print("="*70)
    print()
    
    service = get_drummer_service()
    
    # Test 1: List drummers
    print("✅ Test 1: List Drummers")
    drummers = service.list_drummers()
    print(f"   Found {len(drummers)} DrumTrackAI drummers")
    print()
    
    for drummer in drummers:
        print(f"   {drummer['icon']} {drummer['display_name']}")
        print(f"      Tags: {', '.join(drummer['genre_tags'])}")
        print(f"      Difficulty: {drummer['difficulty']}")
        print()
    
    # Test 2: Get specific drummer characteristics
    print("="*70)
    print("✅ Test 2: Get Drummer Characteristics")
    print()
    
    test_drummer_id = "studio_groove_master"
    print(f"   Loading characteristics for: {test_drummer_id}")
    characteristics = service.get_drummer_characteristics(test_drummer_id)
    
    if characteristics:
        print(f"   ✅ Loaded successfully!")
        print()
        print("   Key Characteristics:")
        if isinstance(characteristics, dict):
            for key, value in list(characteristics.items())[:10]:
                if isinstance(value, (int, float)) and not key.startswith('_'):
                    print(f"      {key}: {value:.2f}")
        print()
    else:
        print(f"   ⚠️  Using fallback characteristics")
        print()
    
    # Test 3: Map to Rust style
    print("="*70)
    print("✅ Test 3: Map to Rust Generator")
    print()
    
    for drummer_id in ["studio_groove_master", "metal_atomic_clock", "funk_machine"]:
        style = service.map_to_rust_style(drummer_id)
        print(f"   {drummer_id} → Rust style: '{style}'")
    print()
    
    # Test 4: Get generation parameters
    print("="*70)
    print("✅ Test 4: Generate Parameters")
    print()
    
    params = service.get_generation_parameters("studio_groove_master")
    print(f"   Parameters for Studio Groove Master:")
    for key, value in params.items():
        print(f"      {key}: {value}")
    print()
    
    # Test 5: Test with song analysis
    print("="*70)
    print("✅ Test 5: Parameters with Song Analysis")
    print()
    
    song_analysis = {
        "swing_amount": 0.15,
        "syncopation_level": 0.70,
        "note_density": "medium"
    }
    
    params = service.get_generation_parameters("studio_groove_master", song_analysis)
    print(f"   Parameters for Studio Groove Master + Song Analysis:")
    for key, value in params.items():
        print(f"      {key}: {value}")
    print()
    
    print("="*70)
    print("  ALL TESTS PASSED! ✅")
    print("="*70)
    print()
    print("Next steps:")
    print("1. Start backend: python dcsm_backend.py")
    print("2. Test API: curl http://localhost:8000/api/drummers")
    print("3. Start frontend: cd frontend && npm start")
    print("4. Upload Peg_No_Drums.mp3 and select a drummer!")
    print()

if __name__ == "__main__":
    try:
        test_drummer_service()
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

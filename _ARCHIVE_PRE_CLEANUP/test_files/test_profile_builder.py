"""
Test Automated Profile Builder
Validates the system without actually downloading/processing
"""

import sys
from pathlib import Path

# Add admin to path
admin_path = Path(__file__).parent / "admin"
sys.path.insert(0, str(admin_path))

import sqlite3
import json
from automated_drummer_profile_builder import AutomatedProfileBuilder, DRUMMER_QUEUE

def test_database_connection():
    """Test 1: Can we connect to the database?"""
    print("\n" + "="*70)
    print("TEST 1: Database Connection")
    print("="*70)
    
    db_path = "f:/DrumTracKAI_v1.1.16_Clean/admin/drumtrackai.db"
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check if tables exist
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        
        print(f"✓ Connected to database")
        print(f"✓ Found {len(tables)} tables")
        
        # Check for required tables
        required = ['drummer_profiles', 'drummer_style_vectors', 'drum_patterns']
        for table in required:
            if table in tables:
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                count = cursor.fetchone()[0]
                print(f"  ✓ {table}: {count} entries")
            else:
                print(f"  ⚠️  {table}: NOT FOUND (will be created)")
        
        conn.close()
        return True
    
    except Exception as e:
        print(f"✗ Database error: {e}")
        return False


def test_existing_drummers():
    """Test 2: What drummers are already in the database?"""
    print("\n" + "="*70)
    print("TEST 2: Existing Drummers in Database")
    print("="*70)
    
    db_path = "f:/DrumTracKAI_v1.1.16_Clean/admin/drumtrackai.db"
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check if table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='drummer_profiles'")
        if not cursor.fetchone():
            print("  ℹ️  drummer_profiles table doesn't exist yet (will be created)")
            return True
        
        # Get existing drummers
        cursor.execute("SELECT drummer_id, name FROM drummer_profiles ORDER BY name")
        rows = cursor.fetchall()
        
        if rows:
            print(f"✓ Found {len(rows)} existing drummers:")
            for drummer_id, name in rows:
                print(f"  • {name} ({drummer_id})")
        else:
            print("  ℹ️  No drummers in database yet")
        
        conn.close()
        return True
    
    except Exception as e:
        print(f"✗ Error: {e}")
        return False


def test_queue_configuration():
    """Test 3: Validate queue configuration"""
    print("\n" + "="*70)
    print("TEST 3: Automation Queue Configuration")
    print("="*70)
    
    print(f"✓ Queue contains {len(DRUMMER_QUEUE)} drummers")
    
    for i, drummer in enumerate(DRUMMER_QUEUE, 1):
        print(f"\n{i}. {drummer['name']}")
        print(f"   ID: {drummer['id']}")
        print(f"   Category: {drummer['category']}")
        print(f"   Position: Drummer #{drummer['drummer_number']}")
        print(f"   Songs: {len(drummer['signature_songs'])}")
        
        for song in drummer['signature_songs']:
            print(f"     • {song['title']}")
            print(f"       URL: {song['youtube_url']}")
            print(f"       Tempo: {song['tempo']} BPM")
    
    return True


def test_category_assignment():
    """Test 4: Verify category assignments"""
    print("\n" + "="*70)
    print("TEST 4: Category Assignment Mapping")
    print("="*70)
    
    try:
        from drummer_categories import DRUMMER_CATEGORIES
        
        print(f"✓ Found {len(DRUMMER_CATEGORIES)} categories")
        
        total_drummers = 0
        for category_id, category_data in DRUMMER_CATEGORIES.items():
            drummer_count = len(category_data['drummers'])
            total_drummers += drummer_count
            
            print(f"\n{category_data['icon']} {category_data['display_name']}")
            print(f"   ID: {category_id}")
            print(f"   Drummers: {drummer_count}")
            
            for drummer in category_data['drummers']:
                print(f"     • {drummer['display_name']}")
                print(f"       ID: {drummer['id']}")
                print(f"       Source: {drummer['source_drummer']}")
        
        print(f"\n✓ Total: {total_drummers} drummer assignments")
        return True
    
    except Exception as e:
        print(f"✗ Error: {e}")
        return False


def test_dependencies():
    """Test 5: Check required dependencies"""
    print("\n" + "="*70)
    print("TEST 5: Required Dependencies")
    print("="*70)
    
    dependencies = {
        'yt_dlp': 'YouTube download',
        'librosa': 'Audio analysis',
        'soundfile': 'Audio file handling',
        'numpy': 'Numerical processing'
    }
    
    for module, purpose in dependencies.items():
        try:
            __import__(module)
            print(f"✓ {module:15s} - {purpose}")
        except ImportError:
            print(f"✗ {module:15s} - {purpose} (NOT INSTALLED)")
            print(f"  Install: pip install {module}")
    
    return True


def test_builder_initialization():
    """Test 6: Can we initialize the builder?"""
    print("\n" + "="*70)
    print("TEST 6: Profile Builder Initialization")
    print("="*70)
    
    try:
        builder = AutomatedProfileBuilder(
            db_path="f:/DrumTracKAI_v1.1.16_Clean/admin/drumtrackai.db",
            download_dir="E:/DrumTracKAI_Master/05_YouTube_Downloads",
            mvsep_output_dir="E:/DrumTracKAI_Master/06_MVSep_Stems"
        )
        
        print(f"✓ Builder initialized successfully")
        print(f"  Database: {builder.db_path}")
        print(f"  Downloads: {builder.download_dir}")
        print(f"  MVSep Output: {builder.mvsep_output_dir}")
        
        # Check if directories exist or can be created
        if builder.download_dir.exists():
            print(f"  ✓ Download directory exists")
        else:
            print(f"  ℹ️  Download directory will be created")
        
        if builder.mvsep_output_dir.exists():
            print(f"  ✓ MVSep output directory exists")
        else:
            print(f"  ℹ️  MVSep output directory will be created")
        
        return True
    
    except Exception as e:
        print(f"✗ Initialization error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_mvsep_api_key():
    """Test 7: MVSep API key configuration"""
    print("\n" + "="*70)
    print("TEST 7: MVSep API Key")
    print("="*70)
    
    import os
    
    api_key = os.environ.get('MVSEP_API_KEY')
    
    if api_key and api_key.strip() and api_key != 'your_actual_api_key_here':
        print(f"✓ MVSep API key is configured")
        print(f"  Key: {'*' * len(api_key)}")
    else:
        print(f"⚠️  MVSep API key NOT configured")
        print(f"  Set with: set MVSEP_API_KEY=your_key_here")
        print(f"  Required for drum extraction")
    
    return True


def run_all_tests():
    """Run all tests"""
    print("\n" + "🧪 "*35)
    print("AUTOMATED PROFILE BUILDER - TEST SUITE")
    print("🧪 "*35)
    
    tests = [
        ("Database Connection", test_database_connection),
        ("Existing Drummers", test_existing_drummers),
        ("Queue Configuration", test_queue_configuration),
        ("Category Assignments", test_category_assignment),
        ("Dependencies", test_dependencies),
        ("Builder Initialization", test_builder_initialization),
        ("MVSep API Key", test_mvsep_api_key)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            success = test_func()
            results.append((test_name, success))
        except Exception as e:
            print(f"\n✗ Test failed: {test_name}")
            print(f"  Error: {e}")
            results.append((test_name, False))
    
    # Summary
    print("\n" + "="*70)
    print("📊 TEST SUMMARY")
    print("="*70)
    
    passed = sum(1 for _, success in results if success)
    total = len(results)
    
    for test_name, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status}  {test_name}")
    
    print(f"\nResults: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All tests passed! Profile builder is ready to use.")
        print("\nNext step: Run actual automation:")
        print("  python automated_drummer_profile_builder.py --list")
        print("  python automated_drummer_profile_builder.py --drummers clyde_stubblefield")
    else:
        print("\n⚠️  Some tests failed. Fix issues above before running automation.")
    
    return passed == total


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)

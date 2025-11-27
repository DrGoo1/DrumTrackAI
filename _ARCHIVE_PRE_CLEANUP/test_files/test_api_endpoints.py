"""
Quick API Endpoint Test Script
Tests all DrumTracKAI v1.1.16 endpoints
"""

import requests
import json
import base64

BASE_URL = "http://localhost:8000"

def test_endpoint(name, method, url, data=None):
    """Test a single endpoint"""
    print(f"\n{'='*70}")
    print(f"TEST: {name}")
    print(f"{'='*70}")
    
    try:
        if method == "GET":
            response = requests.get(url, timeout=10)
        else:
            response = requests.post(url, json=data, timeout=10)
        
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ SUCCESS")
            print(json.dumps(result, indent=2)[:500])  # First 500 chars
            return True
        else:
            print(f"❌ FAILED: {response.status_code}")
            print(response.text[:200])
            return False
            
    except Exception as e:
        print(f"❌ ERROR: {e}")
        return False

def main():
    print("\n" + "🧪 "*35)
    print("DRUMTRACKAI V1.1.16 - API ENDPOINT TESTS")
    print("🧪 "*35)
    
    tests = []
    
    # Test 1: AI Status
    tests.append(test_endpoint(
        "AI System Status",
        "GET",
        f"{BASE_URL}/api/ai/status"
    ))
    
    # Test 2: Drummer Categories
    tests.append(test_endpoint(
        "Drummer Categories",
        "GET",
        f"{BASE_URL}/api/ai/drummer-categories"
    ))
    
    # Test 3: Progressive Drummers
    tests.append(test_endpoint(
        "Progressive Masters Drummers",
        "GET",
        f"{BASE_URL}/api/ai/drummers/progressive_masters"
    ))
    
    # Test 4: Maturity Stats
    tests.append(test_endpoint(
        "Maturity Stats",
        "GET",
        f"{BASE_URL}/api/ai/maturity-stats"
    ))
    
    # Test 5: Generate Pattern
    tests.append(test_endpoint(
        "Generate AI Pattern",
        "POST",
        f"{BASE_URL}/api/ai/generate",
        {
            "tempo": 120,
            "style": "rock",
            "drummer_id": "rock_power_1",
            "complexity": 0.6,
            "creativity": 0.5
        }
    ))
    
    # Summary
    print("\n" + "="*70)
    print("📊 TEST SUMMARY")
    print("="*70)
    
    passed = sum(tests)
    total = len(tests)
    
    print(f"\n✅ Passed: {passed}/{total}")
    print(f"❌ Failed: {total - passed}/{total}")
    
    if passed == total:
        print("\n🎉 ALL TESTS PASSED! System is fully operational!")
    else:
        print(f"\n⚠️  {total - passed} test(s) failed. Check output above.")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)

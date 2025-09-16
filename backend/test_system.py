"""
Simple test script to verify the Voice Authentication System is working
"""
import requests
import json

BASE_URL = "http://127.0.0.1:8000"

def test_health_check():
    """Test the health check endpoint"""
    print("🔍 Testing health check...")
    try:
        response = requests.get(f"{BASE_URL}/health")
        if response.status_code == 200:
            print("✅ Health check passed!")
            print(f"Response: {response.json()}")
            return True
        else:
            print(f"❌ Health check failed with status: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Health check failed with error: {e}")
        return False

def test_system_info():
    """Test the system info endpoint"""
    print("\n🔍 Testing system info...")
    try:
        response = requests.get(f"{BASE_URL}/")
        if response.status_code == 200:
            print("✅ System info retrieved successfully!")
            data = response.json()
            print(f"Service: {data.get('service')}")
            print(f"Version: {data.get('version')}")
            print(f"Status: {data.get('status')}")
            return True
        else:
            print(f"❌ System info failed with status: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ System info failed with error: {e}")
        return False

def test_system_status():
    """Test the system status API endpoint"""
    print("\n🔍 Testing system status API...")
    try:
        response = requests.get(f"{BASE_URL}/api/v1/status")
        if response.status_code == 200:
            print("✅ System status API works!")
            data = response.json()
            print(f"Status: {data.get('status')}")
            print(f"Voice Engine: {data.get('voice_engine')}")
            print(f"Security Features: {', '.join(data.get('security_features', []))}")
            return True
        else:
            print(f"❌ System status failed with status: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ System status failed with error: {e}")
        return False

def test_user_registration():
    """Test user registration"""
    print("\n🔍 Testing user registration...")
    try:
        user_data = {
            "username": "test_user_demo",
            "email": "test@example.com",
            "full_name": "Test User Demo"
        }
        
        response = requests.post(
            f"{BASE_URL}/api/v1/register",
            headers={"Content-Type": "application/json"},
            data=json.dumps(user_data)
        )
        
        if response.status_code == 200:
            print("✅ User registration works!")
            data = response.json()
            print(f"Message: {data.get('message')}")
            print(f"User ID: {data.get('user_id')}")
            return True
        elif response.status_code == 409:
            print("ℹ️ User already exists (expected if running multiple times)")
            return True
        else:
            print(f"❌ User registration failed with status: {response.status_code}")
            print(f"Response: {response.text}")
            return False
    except Exception as e:
        print(f"❌ User registration failed with error: {e}")
        return False

def main():
    """Run all tests"""
    print("🎙️ Voice Authentication System - Test Suite")
    print("=" * 50)
    
    tests = [
        test_health_check,
        test_system_info,
        test_system_status,
        test_user_registration
    ]
    
    results = []
    for test in tests:
        results.append(test())
    
    print("\n" + "=" * 50)
    print("📊 Test Results Summary:")
    print(f"✅ Passed: {sum(results)}/{len(results)}")
    print(f"❌ Failed: {len(results) - sum(results)}/{len(results)}")
    
    if all(results):
        print("\n🎉 All tests passed! Your Voice Authentication System is working correctly.")
        print("🌐 Visit http://127.0.0.1:8000/docs to explore the interactive API documentation.")
    else:
        print("\n⚠️ Some tests failed. Please check if the server is running:")
        print("   python main.py")

if __name__ == "__main__":
    main()

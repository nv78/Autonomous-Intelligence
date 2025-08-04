#!/usr/bin/env python3
"""
Test script for the /public/submit_model API endpoint
"""

import requests
import json
import sys
import os

# Add the backend directory to path to import from database modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Test configuration
API_BASE_URL = 'http://localhost:8000'  # Docker maps port 8000 -> 5000

def create_test_api_key():
    """Create a test API key in the database (local connection to Docker MySQL)"""
    try:
        import mysql.connector
        
        # Local connection to Docker MySQL
        conn = mysql.connector.connect(
            host='localhost',
            port=3307,           # Docker maps 3307 -> 3306
            user='root',
            password='',
            database='agents'
        )
        cursor = conn.cursor(dictionary=True)
        
        # Check if test user exists, create if not
        cursor.execute("SELECT id FROM users WHERE email = 'api@example.com'")
        user = cursor.fetchone()
        
        if not user:
            cursor.execute("""
                INSERT INTO users (email, person_name, credits) 
                VALUES ('api@example.com', 'Test API User', 1000)
            """)
            user_id = cursor.lastrowid
        else:
            user_id = user['id']
        
        # Create test API key
        test_api_key = 'test-api-key-12345'
        cursor.execute("""
            INSERT INTO apiKeys (user_id, api_key, key_name) 
            VALUES (%s, %s, %s)
            ON DUPLICATE KEY UPDATE api_key = VALUES(api_key)
        """, (user_id, test_api_key, 'Test API Key'))
        
        conn.commit()
        cursor.close()
        conn.close()
        
        print(f"✅ Created test API key: {test_api_key}")
        return test_api_key
        
    except Exception as e:
        print(f"❌ Failed to create test API key: {str(e)}")
        return None

def test_submit_model(api_key):
    """Test the submit_model API endpoint"""
    
    print("🧪 Testing /public/submit_model API endpoint...")
    
    # Test data
    test_data = {
        "benchmarkDatasetName": "flores_spanish_translation",
        "modelName": "test-gpt-model-v1",
        "modelResults": [
            "Hola mundo",
            "Buenos días", 
            "Gracias por su ayuda",
            "¿Cómo está usted?",
            "Hasta luego"
        ]
    }
    
    headers = {
        'Authorization': f'Bearer {api_key}',
        'Content-Type': 'application/json'
    }
    
    try:
        print(f"📤 Sending request to {API_BASE_URL}/public/submit_model")
        print(f"📦 Data: {json.dumps(test_data, indent=2)}")
        
        response = requests.post(
            f"{API_BASE_URL}/public/submit_model",
            json=test_data,
            headers=headers
        )
        
        print(f"📊 Response Status: {response.status_code}")
        print(f"📋 Response Body: {json.dumps(response.json(), indent=2)}")
        
        if response.status_code == 200:
            result = response.json()
            if result.get('success'):
                print("✅ API test PASSED!")
                print(f"🎯 Score: {result.get('score')}")
                print(f"🆔 Submission ID: {result.get('submission_id')}")
                return True
            else:
                print("❌ API returned success=False")
                return False
        else:
            print(f"❌ API test FAILED with status {response.status_code}")
            return False
            
    except requests.exceptions.ConnectionError:
        print("❌ Connection error - is the Flask server running on port 8000?")
        return False
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return False

def test_invalid_data(api_key):
    """Test API with invalid data"""
    print("\n🧪 Testing with invalid data...")
    
    # Test missing fields
    invalid_data = {
        "modelName": "test-model",
        # Missing benchmarkDatasetName and modelResults
    }
    
    headers = {
        'Authorization': f'Bearer {api_key}',
        'Content-Type': 'application/json'
    }
    
    try:
        response = requests.post(
            f"{API_BASE_URL}/public/submit_model",
            json=invalid_data,
            headers=headers
        )
        
        print(f"📊 Response Status: {response.status_code}")
        print(f"📋 Response Body: {json.dumps(response.json(), indent=2)}")
        
        if response.status_code == 400:
            print("✅ Invalid data test PASSED (correctly rejected)")
            return True
        else:
            print("❌ Invalid data test FAILED (should have been rejected)")
            return False
            
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return False

if __name__ == "__main__":
    print("🚀 Starting API tests...\n")
    
    # Create test API key
    api_key = create_test_api_key()
    if not api_key:
        print("😞 Cannot proceed without API key. Make sure database is running.")
        sys.exit(1)
    
    # Run tests
    test1_passed = test_submit_model(api_key)
    test2_passed = test_invalid_data(api_key)
    
    print(f"\n📊 Results:")
    print(f"Valid data test: {'✅ PASSED' if test1_passed else '❌ FAILED'}")
    print(f"Invalid data test: {'✅ PASSED' if test2_passed else '❌ FAILED'}")
    
    if test1_passed and test2_passed:
        print("\n🎉 All tests passed!")
    else:
        print("\n😞 Some tests failed. Check the Flask server and database setup.") 
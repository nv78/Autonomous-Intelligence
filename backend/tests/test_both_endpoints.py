#!/usr/bin/env python3
"""
Comprehensive test script for both BLEU evaluation endpoints:
1. Angela's /spanish-gpt-evaluation (real-time GPT translation + evaluation)
2. Josh's /public/submit_model (universal leaderboard submission with Option C)
"""

import requests
import json
import mysql.connector
import os
import pytest

# API Configuration with multiple fallback options
def get_api_base_url():
    # 1. Check environment variable first (for CI/CD flexibility)
    if os.getenv('TEST_API_BASE_URL'):
        return os.getenv('TEST_API_BASE_URL')
    
    # 2. Check if running inside Docker container
    if os.path.exists('/.dockerenv'):
        return "http://localhost:5000"
    
    # 3. Try to detect if we're in CI environment
    if os.getenv('CI') or os.getenv('GITHUB_ACTIONS'):
        return "http://localhost:5000"  # CI usually runs services on internal ports
    
    # 4. Default to external port for local development
    return "http://localhost:5001"

def check_api_connection(url):
    """Check if the API is accessible at the given URL"""
    try:
        response = requests.get(f"{url}/health", timeout=2)
        return response.status_code == 200
    except:
        return False

def get_working_api_url():
    """Get the first working API URL from possible options"""
    primary_url = get_api_base_url()
    
    # Try primary URL first
    if check_api_connection(primary_url):
        return primary_url
    
    # Try alternative ports if primary fails
    alternative_urls = [
        "http://localhost:5000",
        "http://localhost:5001", 
        "http://localhost:8000"
    ]
    
    for url in alternative_urls:
        if url != primary_url and check_api_connection(url):
            print(f"⚠️  Primary URL {primary_url} failed, using {url}")
            return url
    
    # If nothing works, return primary URL and let the test fail with clear error
    print(f"⚠️  No working API found, using {primary_url} (may fail)")
    return primary_url

API_BASE_URL = get_working_api_url()

# Check if API is available for all tests
def check_api_available():
    """Check if the API is available for testing"""
    try:
        response = requests.get(f"{API_BASE_URL}/health", timeout=5)
        return response.status_code == 200
    except:
        return False

# Skip all tests if API is not available
pytestmark = pytest.mark.skipif(
    not check_api_available(),
    reason=f"API not available at {API_BASE_URL}"
)

DB_CONFIG = {
    'host': 'localhost',
    'port': 3307,  # Docker mapped port
    'user': 'root',
    'password': '',
    'database': 'agents'
}

def create_test_api_key(api_key="test-api-key-12345"):
    """Create a test API key for submit_model endpoint"""
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        # Delete existing test key
        cursor.execute("DELETE FROM apiKeys WHERE key_value = %s", (api_key,))
        
        # Create new test key
        cursor.execute("""
            INSERT INTO apiKeys (key_value, user_id, created_at, is_active)
            VALUES (%s, 1, NOW(), 1)
        """, (api_key,))
        
        conn.commit()
        cursor.close()
        conn.close()
    
        return api_key
        
    except Exception as e:
        print(f"❌ Failed to create API key: {e}")
        return None

def test_angela_endpoint():
    """Test Angela's /spanish-gpt-evaluation endpoint"""
    print("\n" + "="*60)
    print("🧪 Testing Angela's /spanish-gpt-evaluation endpoint")
    print("="*60)
    
    try:
        response = requests.post(
            f"{API_BASE_URL}/spanish-gpt-evaluation",
            json={"count": 2},
            headers={"Content-Type": "application/json"}
        )
        
        print(f"📊 Response Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"🎯 BLEU Score: {data.get('bleu_score', 'N/A')}")
            print(f"📝 Number of translations: {len(data.get('translations', []))}")
            print(f"📚 Number of references: {len(data.get('references', []))}")
            
            # Show first translation pair
            if data.get('translations') and data.get('references'):
                print(f"\n📖 Example translation pair:")
                print(f"   GPT Translation: {data['translations'][0][:100]}...")
                print(f"   FLORES+ Reference: {data['references'][0][:100]}...")
            
            return True
        else:
            print(f"❌ Error: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Request failed: {e}")
        return False

def test_get_source_sentences():
    """Test the new /public/get_source_sentences endpoint"""
    print("\n" + "="*60)
    print("🧪 Testing /public/get_source_sentences endpoint")
    print("="*60)
    
    try:
        response = requests.get(
            f"{API_BASE_URL}/public/get_source_sentences",
            params={"count": 3, "start_idx": 0}
        )
        
        print(f"📊 Response Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Success: {data.get('success')}")
            print(f"📝 Sentence IDs: {data.get('sentence_ids')}")
            print(f"🌍 Total available: {data.get('total_available')}")
            
            # Show source sentences
            sources = data.get('source_sentences', [])
            print(f"\n📖 Source sentences to translate:")
            for i, sentence in enumerate(sources):
                print(f"   [{data['sentence_ids'][i]}]: {sentence[:80]}...")
            
            return data.get('sentence_ids', []), sources
        else:
            print(f"❌ Error: {response.text}")
            return [], []
            
    except Exception as e:
        print(f"❌ Request failed: {e}")
        return [], []

def test_submit_model_with_option_c():
    """Test /public/submit_model with Option C (sentence_ids)"""
    print("\n" + "="*60)
    print("🧪 Testing /public/submit_model with Option C (sentence_ids)")
    print("="*60)
    
    # First, get source sentences to translate
    sentence_ids, sources = test_get_source_sentences()
    if not sentence_ids:
        print("❌ Failed to get source sentences, skipping test")
        return
    
    # Create mock translations for the sentences we got
    mock_translations = [
        "Esta es una traducción de prueba para la oración uno.",
        "Esta es una traducción de prueba para la oración dos.", 
        "Esta es una traducción de prueba para la oración tres."
    ][:len(sentence_ids)]  # Only as many as we have sentence_ids
    
    # Generate a test API key (this test might need to be updated if API key validation is strict)
    api_key = "test-api-key-12345"
    
    payload = {
        "benchmarkDatasetName": "flores_spanish_translation",
        "modelName": "test-model-option-c",
        "modelResults": mock_translations,
        "sentence_ids": sentence_ids  # Option C: specify which sentences we translated
    }
    
    try:
        response = requests.post(
            f"{API_BASE_URL}/public/submit_model",
            json=payload,
            headers={
                "Content-Type": "application/json",
                "X-API-Key": api_key
            }
        )
        
        print(f"📊 Response Status: {response.status_code}")
        print(f"📦 Sent sentence_ids: {sentence_ids}")
        print(f"📦 Sent translations: {[t[:50] + '...' for t in mock_translations]}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Success: {data.get('success')}")
            print(f"🎯 BLEU Score: {data.get('bleu_score')}")
            print(f"🆔 Submission ID: {data.get('submission_id')}")
            
            eval_details = data.get('evaluation_details', {})
            print(f"📋 Evaluation Note: {eval_details.get('note')}")
            print(f"📋 Sentence IDs Used: {eval_details.get('sentence_ids')}")
            
            return True
        else:
            print(f"❌ Error: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Request failed: {e}")
        return False

def test_submit_model_legacy():
    """Test /public/submit_model without sentence_ids (legacy behavior)"""
    print("\n" + "="*60)
    print("🧪 Testing /public/submit_model without sentence_ids (legacy)")
    print("="*60)
    
    payload = {
        "benchmarkDatasetName": "flores_spanish_translation",
        "modelName": "test-model-legacy",
        "modelResults": ["Hola mundo", "Buenos días"]
        # No sentence_ids - should use first N sentences
    }
    
    try:
        response = requests.post(
            f"{API_BASE_URL}/public/submit_model",
            json=payload,
            headers={
                "Content-Type": "application/json",
                "X-API-Key": create_test_api_key("legacy-test-key")
            }
        )
        
        print(f"📊 Response Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Success: {data.get('success')}")
            print(f"🎯 BLEU Score: {data.get('bleu_score')} (expected low - different content)")
            
            eval_details = data.get('evaluation_details', {})
            print(f"📋 Evaluation Note: {eval_details.get('note')}")
            
            return True
        else:
            print(f"❌ Error: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Request failed: {e}")
        return False

def main():
    """Run comprehensive tests for both endpoints"""
    print("🚀 Starting comprehensive BLEU endpoint tests...")
    
    # Test 1: Angela's endpoint
    angela_success = test_angela_endpoint()
    
    # Test 2: Get source sentences for Option C
    sentence_ids, source_sentences = test_get_source_sentences()
    
    # Test 3: Submit model with Option C (proper sentence matching)
    if sentence_ids and source_sentences:
        # Create mock translations (in real use, user would translate these)
        mock_translations = [
            "Actualmente, tenemos ratones de cuatro meses que ya no son diabéticos",  # Close to reference
            "La investigación está en etapas tempranas según el Dr. Ehud Ur",        # Close to reference  
            "Los expertos son escépticos sobre la cura de la diabetes"               # Close to reference
        ][:len(sentence_ids)]  # Match the number of source sentences
        
        api_key = create_test_api_key()
        if api_key:
            option_c_success = test_submit_model_with_option_c(api_key, sentence_ids, mock_translations)
        else:
            option_c_success = False
    else:
        option_c_success = False
    
    # Test 4: Legacy behavior (without sentence_ids)
    legacy_success = test_submit_model_legacy()
    
    # Summary
    print("\n" + "="*60)
    print("📊 TEST SUMMARY")
    print("="*60)
    print(f"Angela's /spanish-gpt-evaluation: {'✅ PASS' if angela_success else '❌ FAIL'}")
    print(f"/public/get_source_sentences: {'✅ PASS' if sentence_ids else '❌ FAIL'}")
    print(f"/public/submit_model (Option C): {'✅ PASS' if option_c_success else '❌ FAIL'}")
    print(f"/public/submit_model (Legacy): {'✅ PASS' if legacy_success else '❌ FAIL'}")
    
    if all([angela_success, sentence_ids, option_c_success, legacy_success]):
        print("\n🎉 ALL TESTS PASSED! Both endpoints working correctly.")
        print("\n💡 Reminder: Message Angela about Option C workflow:")
        print("   'Hey Angela! Both endpoints now working. Should users specify")
        print("   sentence_ids when submitting to leaderboard for proper BLEU")
        print("   evaluation? The Option C flow is ready: get_source_sentences → ")
        print("   translate → submit_model with sentence_ids. What do you think?'")
    else:
        print("\n❌ Some tests failed. Check the output above for details.")

if __name__ == "__main__":
    main() 
#!/usr/bin/env python3
"""
Comprehensive test script for both BLEU evaluation endpoints:
1. Angela's /spanish-gpt-evaluation (real-time GPT translation + evaluation)
2. Josh's /public/submit_model (universal leaderboard submission with Option C)
"""

import requests
import json
import mysql.connector

# API Configuration
API_BASE_URL = "http://localhost:8000"
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

def test_submit_model_with_option_c(api_key, sentence_ids, mock_translations):
    """Test /public/submit_model with Option C (sentence_ids)"""
    print("\n" + "="*60)
    print("🧪 Testing /public/submit_model with Option C (sentence_ids)")
    print("="*60)
    
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
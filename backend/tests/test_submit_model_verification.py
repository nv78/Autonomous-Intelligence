#!/usr/bin/env python3
"""
Comprehensive verification of submit_model endpoint to ensure it works properly
and produces meaningful BLEU scores
"""

import requests
import json

API_BASE_URL = "http://localhost:8000"

def test_high_quality_translations():
    """Test with high-quality translations (should get good BLEU scores)"""
    print("🧪 Testing with HIGH-quality translations...")
    
    # Step 1: Get source sentences
    response = requests.get(f"{API_BASE_URL}/public/get_source_sentences?count=3&start_idx=0")
    data = response.json()
    sentence_ids = data["sentence_ids"]
    source_sentences = data["source_sentences"]
    
    print(f"📖 Source sentences:")
    for i, sentence in enumerate(source_sentences):
        print(f"   [{sentence_ids[i]}]: {sentence}")
    
    # Step 2: High-quality translations (close to FLORES+ references)
    high_quality_translations = [
        "«Actualmente, tenemos ratones de cuatro meses de edad que antes solían ser diabéticos y que ya no lo son», agregó.",
        "La investigación todavía se ubica en su etapa inicial, conforme indicara el Dr. Ehud Ur, docente en la carrera de medicina de la Universidad de Dalhousie, en Halifax, Nueva Escocia, y director del departamento clínico y científico de la Asociación Canadiense de Diabetes.",
        "Como algunos otros expertos, es escéptico sobre si la diabetes puede curarse, en lugar de simplemente controlarse."
    ]
    
    print(f"\n📝 High-quality translations:")
    for i, translation in enumerate(high_quality_translations):
        print(f"   [{sentence_ids[i]}]: {translation[:80]}...")
    
    # Submit high-quality translations
    payload = {
        "benchmarkDatasetName": "flores_spanish_translation",
        "modelName": "high-quality-model",
        "modelResults": high_quality_translations,
        "sentence_ids": sentence_ids
    }
    
    response = requests.post(f"{API_BASE_URL}/public/submit_model", json=payload)
    
    if response.status_code == 200:
        data = response.json()
        score = data.get('score', 0)
        print(f"🎯 High-quality BLEU Score: {score:.4f}")
        return score
    else:
        print(f"❌ Error: {response.text}")
        return 0

def test_low_quality_translations():
    """Test with low-quality translations (should get poor BLEU scores)"""
    print("\n🧪 Testing with LOW-quality translations...")
    
    # Get same source sentences
    response = requests.get(f"{API_BASE_URL}/public/get_source_sentences?count=3&start_idx=0")
    data = response.json()
    sentence_ids = data["sentence_ids"]
    
    # Low-quality translations (completely wrong)
    low_quality_translations = [
        "Hola mundo",
        "El gato está en la mesa",
        "Me gusta la pizza"
    ]
    
    print(f"📝 Low-quality translations:")
    for i, translation in enumerate(low_quality_translations):
        print(f"   [{sentence_ids[i]}]: {translation}")
    
    # Submit low-quality translations
    payload = {
        "benchmarkDatasetName": "flores_spanish_translation",
        "modelName": "low-quality-model",
        "modelResults": low_quality_translations,
        "sentence_ids": sentence_ids
    }
    
    response = requests.post(f"{API_BASE_URL}/public/submit_model", json=payload)
    
    if response.status_code == 200:
        data = response.json()
        score = data.get('score', 0)
        print(f"🎯 Low-quality BLEU Score: {score:.4f}")
        return score
    else:
        print(f"❌ Error: {response.text}")
        return 0

def test_medium_quality_translations():
    """Test with medium-quality translations"""
    print("\n🧪 Testing with MEDIUM-quality translations...")
    
    # Get same source sentences
    response = requests.get(f"{API_BASE_URL}/public/get_source_sentences?count=3&start_idx=0")
    data = response.json()
    sentence_ids = data["sentence_ids"]
    
    # Medium-quality translations (reasonable but not perfect)
    medium_quality_translations = [
        "Ahora tenemos ratones de 4 meses que no son diabéticos pero antes sí lo eran",
        "La investigación está en etapas tempranas según el Dr. Ehud Ur de la Universidad Dalhousie",
        "Como otros expertos, él duda si la diabetes puede curarse en lugar de controlarse"
    ]
    
    print(f"📝 Medium-quality translations:")
    for i, translation in enumerate(medium_quality_translations):
        print(f"   [{sentence_ids[i]}]: {translation}")
    
    # Submit medium-quality translations
    payload = {
        "benchmarkDatasetName": "flores_spanish_translation",
        "modelName": "medium-quality-model",
        "modelResults": medium_quality_translations,
        "sentence_ids": sentence_ids
    }
    
    response = requests.post(f"{API_BASE_URL}/public/submit_model", json=payload)
    
    if response.status_code == 200:
        data = response.json()
        score = data.get('score', 0)
        print(f"🎯 Medium-quality BLEU Score: {score:.4f}")
        return score
    else:
        print(f"❌ Error: {response.text}")
        return 0

def show_actual_references():
    """Show what the actual FLORES+ references look like"""
    print("\n📚 Let's see the actual FLORES+ Spanish references...")
    
    # We can't directly access FLORES+ from here, but Angela's endpoint can show us
    response = requests.post(f"{API_BASE_URL}/spanish-gpt-evaluation", json={"count": 3})
    
    if response.status_code == 200:
        data = response.json()
        references = data.get('references', [])
        
        print(f"🌟 FLORES+ Spanish references (what we're comparing against):")
        for i, ref in enumerate(references):
            print(f"   [{i}]: {ref}")
        
        return references
    else:
        print(f"❌ Couldn't get references: {response.text}")
        return []

def test_validation():
    """Test validation scenarios"""
    print("\n🧪 Testing validation scenarios...")
    
    # Test missing sentence_ids
    payload = {
        "benchmarkDatasetName": "flores_spanish_translation",
        "modelName": "missing-ids-model",
        "modelResults": ["Test translation"]
        # Missing sentence_ids
    }
    
    response = requests.post(f"{API_BASE_URL}/public/submit_model", json=payload)
    missing_ids_valid = response.status_code == 400
    print(f"Missing sentence_ids: {'✅ Correctly rejected' if missing_ids_valid else '❌ Should have been rejected'}")
    
    # Test mismatched lengths
    payload = {
        "benchmarkDatasetName": "flores_spanish_translation", 
        "modelName": "mismatched-model",
        "modelResults": ["Translation 1", "Translation 2"],
        "sentence_ids": [0, 1, 2]  # 3 IDs but only 2 translations
    }
    
    response = requests.post(f"{API_BASE_URL}/public/submit_model", json=payload)
    mismatch_valid = response.status_code == 400
    print(f"Mismatched lengths: {'✅ Correctly rejected' if mismatch_valid else '❌ Should have been rejected'}")
    
    return missing_ids_valid and mismatch_valid

def main():
    print("🚀 Comprehensive submit_model verification...")
    
    # Show references first so we understand what we're comparing against
    references = show_actual_references()
    
    # Run translation quality tests
    high_score = test_high_quality_translations()
    medium_score = test_medium_quality_translations()
    low_score = test_low_quality_translations()
    
    # Test validation
    validation_passed = test_validation()
    
    print("\n" + "="*80)
    print("📊 VERIFICATION RESULTS")
    print("="*80)
    print(f"High-quality translations BLEU:   {high_score:.4f}")
    print(f"Medium-quality translations BLEU: {medium_score:.4f}")
    print(f"Low-quality translations BLEU:    {low_score:.4f}")
    print(f"Validation tests: {'✅ PASS' if validation_passed else '❌ FAIL'}")
    
    # Check if scores make sense
    scores_logical = high_score > medium_score > low_score
    
    print(f"\n🔍 Score Analysis:")
    print(f"Scores follow expected pattern (high > medium > low): {'✅ YES' if scores_logical else '❌ NO'}")
    
    if high_score > 0.3:
        print(f"✅ High-quality score ({high_score:.4f}) is reasonable (>0.3)")
    else:
        print(f"⚠️  High-quality score ({high_score:.4f}) seems low (<0.3)")
    
    if low_score < 0.1:
        print(f"✅ Low-quality score ({low_score:.4f}) is appropriately low (<0.1)")
    else:
        print(f"⚠️  Low-quality score ({low_score:.4f}) seems high (should be <0.1)")
    
    print(f"\n🎯 OVERALL ASSESSMENT:")
    if scores_logical and validation_passed and high_score > 0.2:
        print("✅ submit_model is working CORRECTLY!")
        print("   - BLEU scores are meaningful and logical")
        print("   - Option C flow produces proper evaluation")
        print("   - Validation works as expected")
        print("   - Results make sense compared to quality")
    else:
        print("❌ submit_model has issues that need investigation")
    
    print(f"\n🔄 THE FLOW:")
    print("1. User calls GET /public/get_source_sentences?count=N")
    print("   → Gets English sentences with IDs [0,1,2,...]")
    print("2. User translates English sentences to Spanish")
    print("3. User calls POST /public/submit_model with:")
    print("   - modelResults: [their Spanish translations]")
    print("   - sentence_ids: [0,1,2,...] (matches step 1)")
    print("4. API loads FLORES+ Spanish references at those exact positions")
    print("5. API calculates BLEU: user translations vs correct references")
    print("6. Returns: {success: true, score: BLEU_value}")
    print("\n💡 This ensures meaningful evaluation - users translate specific")
    print("   benchmark sentences, not random content!")

if __name__ == "__main__":
    main() 
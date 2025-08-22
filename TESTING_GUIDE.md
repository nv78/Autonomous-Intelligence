# 🧪 **Testing Guide: Model Evaluation & Submission**

## 🚀 **Quick Start**

### **1. Start the Application**
```bash
# Start backend (includes database)
cd backend && docker-compose up --build -d

# Start frontend  
cd frontend && npm install && PORT=3001 npm start
```

### **2. Access Points**
- **Evaluations Page**: http://localhost:3001/evaluations
- **Submit Models**: Click "Submit Your Model" button
- **Backend API**: http://localhost:8000

## 📁 **Available Test Files**

### **BLEU Score Testing:**
| Language | Test File | Expected Score | Performance Level |
|----------|-----------|----------------|-------------------|
| **Spanish** | `demo_test_spanish.csv` | ~0.40 | ✅ Good lexical overlap |
| **Arabic** | `demo_test_arabic.csv` | ~0.10 | ✅ Moderate overlap |
| **Korean** | `demo_test_korean.csv` | ~0.13 | ✅ Moderate overlap |
| **Japanese** | `demo_test_japanese.csv` | ~0.00 | ⚠️ Different valid translation style |
| **Chinese** | `demo_test_chinese.csv` | ~0.00 | ⚠️ Different valid translation style |

**Note**: BLEU measures exact word/phrase overlap. Different (but correct) translations can get low scores, especially for languages with multiple valid translation approaches.

### **BERTScore Testing:**
| Language | Test File | Expected Score | Why This Works? |
|----------|-----------|----------------|-----------------|
| **Spanish** | `demo_test_spanish_bertscore.csv` | ~0.65 | ✅ Semantic similarity captures meaning |
| **Japanese** | `demo_test_japanese.csv` | ~0.62 | ✅ Works with Asian languages |
| **Arabic** | `demo_test_arabic.csv` | ~0.65 | ✅ Works with RTL languages |
| **Chinese** | `demo_test_chinese.csv` | ~0.62 | ✅ Works with character-based |
| **Korean** | `demo_test_korean.csv` | ~0.60 | ✅ Works with agglutinative |

**Note**: BERTScore gives meaningful scores for all languages because it measures semantic similarity, not exact word matches.

### **Score Range Testing:**
| File | Expected BLEU | Use Case |
|------|---------------|----------|
| `test_high_score.csv` | ~0.8-1.0 | Perfect/near-perfect translations |
| `test_medium_score.csv` | ~0.3-0.6 | Decent translations |
| `test_low_score.csv` | ~0.0-0.2 | Poor translations |

## 🎯 **How to Test Each Metric**

### **BLEU Score Testing:**
1. Go to: http://localhost:3001/evaluations
2. Click: "Submit Your Model"
3. Select: "Spanish Translation (FLORES+ BLEU)"
4. Upload: `demo_test_spanish.csv`
5. Expected: ~0.43 BLEU score

### **BERTScore Testing:**
1. Go to: http://localhost:3001/evaluations  
2. Click: "Submit Your Model"
3. Select: "Spanish Translation (FLORES+ BERTScore)"
4. Upload: `demo_test_spanish_bertscore.csv`
5. Expected: ~0.65 BERTScore (higher than BLEU)

## ⏱️ **Performance Expectations**

### **BLEU Evaluation:**
- **Time**: ~1-2 seconds
- **Process**: Simple n-gram matching

### **BERTScore Evaluation:**
- **First Call**: ~10-15 seconds (model download/loading)
- **Subsequent Calls**: ~3-5 seconds (model cached)
- **Process**: BERT embedding + cosine similarity

## 🔧 **Verification Checklist**

### **✅ BERTScore Working Correctly If:**
1. **Scores in 0.6-0.8 range** for good translations
2. **Higher than corresponding BLEU** for same text
3. **Consistent across languages** (unlike BLEU's 0s)
4. **Takes longer than BLEU** (expected due to model)

### **❌ BERTScore Issues If:**
1. Always returns 0.0 (dependency missing)
2. Takes >30 seconds consistently
3. Crashes with tensor errors
4. Returns identical scores for different inputs

## 🚀 **Quick Test Commands**

```bash
# Test BLEU (fast)
curl -X POST "http://localhost:8000/public/submit_model" \
  -H "Content-Type: application/json" \
  -d '{"benchmarkDatasetName": "flores_spanish_translation", "modelName": "Quick-BLEU-Test", "modelResults": ["El gato está en la alfombra."], "sentence_ids": [1]}'

# Test BERTScore (slower, first time)
curl -X POST "http://localhost:8000/public/submit_model" \
  -H "Content-Type: application/json" \
  -d '{"benchmarkDatasetName": "flores_spanish_translation_bertscore", "modelName": "Quick-BERTScore-Test", "modelResults": ["El gato está en la alfombra."], "sentence_ids": [1]}'
```

**Expected Results:**
- BLEU: ~0.3-0.5
- BERTScore: ~0.6-0.7 (higher semantic similarity) 
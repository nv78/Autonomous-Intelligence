# End-to-End Testing Guide

This guide covers how to test both the **Spanish GPT Evaluation** and **Submit Model** APIs from start to finish.

## 🚀 Prerequisites

### Start Both Services:

```bash
# Terminal 1: Start Backend (Docker)
cd backend
docker-compose up --build

# Terminal 2: Start Frontend
cd frontend
npm install  # Only needed first time
npm start
```

**Verify Services Running:**
- Backend: http://localhost:8000/health (should return "Healthy")
- Frontend: http://localhost:3000 (should load React app)

---

## 🧪 Test 1: Spanish GPT Evaluation API

### **What it does:**
- Loads English sentences from FLORES+ dataset
- Calls GPT-4 to translate them to Spanish
- Compares GPT translations vs reference Spanish translations
- Returns BLEU score + translations

### **A. API Testing (Backend Only)**

```bash
# Test with 2 sentences (faster for testing)
curl -X POST http://localhost:8000/spanish-gpt-evaluation \
  -H "Content-Type: application/json" \
  -d '{"count": 2}'

# Expected Response:
{
  "bleu_score": 0.453,
  "references": ["Spanish reference 1", "Spanish reference 2"],
  "translations": ["GPT translation 1", "GPT translation 2"]
}
```

**⚠️ Note:** This takes 10-15 seconds because it calls GPT API

### **B. Frontend Testing (UI)**

1. **Navigate to:** http://localhost:3000/evaluations
2. **Click:** "Generate GPT Spanish Score" button
3. **Wait:** 10-15 seconds (GPT API calls)
4. **Expect to see:**
   - List of GPT's Spanish translations
   - BLEU score (e.g., 0.4532)
   - No errors

**Common Issues:**
- ❌ "Error occurred while translating" → Check backend logs
- ❌ Long loading → Normal, GPT API is slow
- ❌ Network error → Check if backend is running on port 8000

---

## 🎯 Test 2: Submit Model API

### **What it does:**
- User submits their model's translation results
- Compares against FLORES+ reference translations
- Returns BLEU score
- Stores submission in database

### **A. API Testing (Backend Only)**

```bash
# Create test data
echo '"Hola mundo"
"Adiós mundo"
"¿Cómo estás?"' > test_translations.csv

# Test submit_model API
curl -X POST http://localhost:8000/public/submit_model \
  -H "Content-Type: application/json" \
  -d '{
    "benchmarkDatasetName": "flores_spanish_translation",
    "modelName": "my-test-model",
    "modelResults": ["Hola mundo", "Adiós mundo", "¿Cómo estás?"],
    "sentence_ids": [0, 1, 2]
  }'

# Expected Response:
{
  "success": true,
  "score": 0.134
}
```

### **B. Frontend Testing (Complete Flow)**

#### **Step 1: Navigate to Leaderboard**
1. Go to: http://localhost:3000/leaderboard
2. See: Rankings table with different models
3. Click: "Submit Model to Leaderboard" button
4. Should navigate to: http://localhost:3000/submit-to-leaderboard

#### **Step 2: Fill Submission Form**
1. **Benchmark Dataset:** Select "flores_spanish_translation"
2. **Submission Name:** Enter "my-test-model-v1"
3. **Your Name:** Enter your name
4. **Email:** Enter your email
5. **Organization:** Enter organization (optional)

#### **Step 3: Upload Model Results**
Create a CSV file with your translations:

```csv
model_output
"Hola mundo"
"Adiós mundo"
"¿Cómo estás?"
```

1. Click "Choose File" next to "Model Results"
2. Upload your CSV file
3. Should see: File name displayed

#### **Step 4: Submit**
1. Click "Submit" button
2. Wait 2-3 seconds
3. Should see: "Success! Your model scored 0.1234 BLEU score."

#### **Step 5: Verify API Response**
Check browser console (F12) for:
```javascript
API Response: {
  success: true,
  score: 0.1234
}
```

---

## 🔍 Test 3: Get Source Sentences API (Helper)

### **What it does:**
- Returns English sentences that need to be translated
- Useful for users to know what to translate

```bash
# Get 3 source sentences
curl -X GET "http://localhost:8000/public/get_source_sentences?count=3"

# Expected Response:
{
  "success": true,
  "source_sentences": [
    "Now we have 4-month-old mice that are non-diabetic that used to be diabetic,\" he added.",
    "Dr. Ehud Ur, professor of medicine at Dalhousie University in Halifax, Nova Scotia and chair of the clinical and scientific division of the Canadian Diabetes Association, cautioned that the research is still in its early days.",
    "Like some other experts, he is skeptical about whether diabetes can be cured, noting that these findings have no relevance to people who already have Type 1 diabetes."
  ],
  "sentence_ids": [0, 1, 2],
  "dataset": "flores_plus",
  "total_available": 1012
}
```

---

## 🚨 Troubleshooting

### **Backend Issues:**
```bash
# Check if backend is running
curl http://localhost:8000/health

# Check Docker containers
docker ps

# View backend logs
docker logs anote-backend
```

### **Frontend Issues:**
```bash
# Check if frontend is running
curl http://localhost:3000

# Restart frontend
cd frontend
npm start
```

### **Common Errors:**

| Error | Cause | Solution |
|-------|-------|----------|
| "Error occurred while translating" | Backend API issue | Check backend logs |
| "Network Error" | Backend not running | Start Docker backend |
| "CORS Error" | Port mismatch | Use localhost:8000 for API |
| "File upload failed" | Wrong file format | Use CSV with "model_output" header |
| "Missing sentence_ids" | API validation | Include sentence_ids array |

---

## ✅ Success Criteria

### **Spanish GPT Evaluation:**
- ✅ Returns BLEU score (0.0 - 1.0)
- ✅ Shows GPT translations
- ✅ Shows reference translations
- ✅ No errors in console

### **Submit Model:**
- ✅ File upload works
- ✅ Form validation passes
- ✅ Returns success: true
- ✅ Returns BLEU score
- ✅ Data stored in database

### **Overall Flow:**
- ✅ Leaderboard → Submit → Results
- ✅ All APIs respond correctly
- ✅ Frontend displays results
- ✅ No console errors

---

## 🎯 Quick Test Script

```bash
#!/bin/bash
echo "🧪 Running End-to-End Tests..."

# Test 1: Health Check
echo "1. Testing Backend Health..."
curl -s http://localhost:8000/health && echo " ✅ Backend OK" || echo " ❌ Backend Failed"

# Test 2: Get Source Sentences
echo "2. Testing Get Source Sentences..."
curl -s "http://localhost:8000/public/get_source_sentences?count=1" | grep -q "success" && echo " ✅ Get Sources OK" || echo " ❌ Get Sources Failed"

# Test 3: Submit Model
echo "3. Testing Submit Model..."
curl -s -X POST http://localhost:8000/public/submit_model \
  -H "Content-Type: application/json" \
  -d '{"benchmarkDatasetName": "flores_spanish_translation", "modelName": "test", "modelResults": ["Hola"], "sentence_ids": [0]}' | grep -q "success" && echo " ✅ Submit Model OK" || echo " ❌ Submit Model Failed"

# Test 4: Frontend
echo "4. Testing Frontend..."
curl -s http://localhost:3000 | grep -q "html" && echo " ✅ Frontend OK" || echo " ❌ Frontend Failed"

echo "🎉 Tests Complete!"
```

Save as `test.sh`, run with: `chmod +x test.sh && ./test.sh` 
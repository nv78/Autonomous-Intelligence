# 🎯 DEMO TEST GUIDE - Multi-Language Translation Evaluation

## 🚀 Quick Start
1. **Backend**: `cd backend && docker-compose up -d`
2. **Frontend**: `cd frontend && npm start`
3. **Access**: http://localhost:3000/evaluations

---

## 📋 Test Cases for Demo

### **Test Case 1: Spanish Translation**
**Steps:**
1. Go to `http://localhost:3000/evaluations`
2. Current button says "Generate GPT Spanish Score" - click it
3. See 5 English sentences + Spanish translations + BLEU score
4. Click "Submit to Leaderboard"
5. Upload `demo_test_spanish.csv`
6. Submit and see score
7. Go back to `/evaluations` - see your submission in the Spanish BLEU leaderboard!

**Expected Results:**
- BLEU score from GPT evaluation: ~0.3-0.6
- CSV submission score: ~0.4-0.7 (decent translations)
- Submission appears in leaderboard immediately

---

### **Test Case 2: Multi-Language API Testing**

**Test Japanese:**
```bash
# Test source sentences
curl "http://localhost:8000/public/get_source_sentences?dataset=flores_japanese_translation&count=3"

# Test evaluation API
curl -X POST "http://localhost:8000/multi-language-gpt-evaluation" \
  -H "Content-Type: application/json" \
  -d '{"language": "japanese", "count": 2}'
```

**Test Arabic:**
```bash
curl "http://localhost:8000/public/get_source_sentences?dataset=flores_arabic_translation&count=3"
```

**Test Chinese:**
```bash
curl "http://localhost:8000/public/get_source_sentences?dataset=flores_chinese_translation&count=3"
```

---

### **Test Case 3: Submit Model Flow**

**For each language:**
1. Go to `http://localhost:3000/submit-to-leaderboard`
2. Select benchmark dataset:
   - Spanish Translation (FLORES+)
   - Japanese Translation (FLORES+) 
   - Arabic Translation (FLORES+)
   - Chinese Translation (FLORES+)
3. Upload corresponding CSV file:
   - `demo_test_spanish.csv`
   - `demo_test_japanese.csv`
   - `demo_test_arabic.csv`
   - `demo_test_chinese.csv`
4. Submit and get BLEU score
5. Check leaderboard updates

---

## 🎯 Demo Script (5-minute demo)

### **Minute 1: Show Current System**
- "Here's our translation evaluation system"
- Navigate to `/evaluations`
- "Currently shows Spanish, Japanese, Arabic, Chinese leaderboards"
- "Click Generate GPT Spanish Score" → show real evaluation

### **Minute 2: Submit Model**
- Click "Submit to Leaderboard"
- "Here users can submit their translation models"
- Show 4 language dataset options
- Upload `demo_test_spanish.csv`
- Submit → get BLEU score

### **Minute 3: Show Dynamic Results**
- Go back to `/evaluations`
- "The leaderboard updates in real-time"
- Point out your new submission in Spanish BLEU section
- "This data comes from our API, not static"

### **Minute 4: Multi-Language Support**
- "We support 4 languages through FLORES+ dataset"
- Show API working: `curl "http://localhost:8000/public/get_source_sentences?dataset=flores_japanese_translation&count=2"`
- "Same evaluation pipeline for all languages"

### **Minute 5: Architecture**
- "Backend: Flask + MySQL + FLORES+ integration"
- "Frontend: React with dynamic data fetching"
- "Users can evaluate and submit models for any language"
- "All submissions tracked and ranked automatically"

---

## 🧪 Expected Test Results

### **API Responses:**
- ✅ All 4 languages return source sentences
- ✅ Spanish evaluation works (has GPT + FLORES+ reference)
- ⚠️ Other languages work but may have lower BLEU (GPT translation quality varies)

### **CSV Submissions:**
- **Spanish**: BLEU ~0.4-0.7 (good translations)
- **Japanese**: BLEU ~0.2-0.5 (depends on translation quality)
- **Arabic**: BLEU ~0.2-0.5 (depends on translation quality)
- **Chinese**: BLEU ~0.3-0.6 (depends on translation quality)

### **Leaderboard Updates:**
- ✅ Submissions appear immediately in `/evaluations`
- ✅ Real-time ranking by BLEU score
- ✅ Dynamic data from database

---

## 🚨 Troubleshooting

**If evaluation fails:**
- Check backend logs: `docker-compose logs backend`
- Verify HF_TOKEN environment variable set
- Test API manually with curl commands

**If leaderboard doesn't update:**
- Refresh `/evaluations` page
- Check browser console for API errors
- Verify backend is running on port 8000

**If CSV upload fails:**
- Check CSV format (must have 'model_output' column)
- Ensure 5 rows of data (matching sentence count)
- Check network connection to backend

---

## 📁 Demo Files Created:
- `demo_test_spanish.csv` - Spanish translations
- `demo_test_japanese.csv` - Japanese translations  
- `demo_test_arabic.csv` - Arabic translations
- `demo_test_chinese.csv` - Chinese translations

**Ready for your demo! 🎉** 
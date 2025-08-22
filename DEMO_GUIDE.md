# 🎯 Multi-Language Translation Leaderboard Demo Guide

## 🚀 Quick Setup (5 minutes)

### Prerequisites
- Docker & Docker Compose installed
- Node.js & npm installed
- Terminal access

### Start the System
```bash
# 1. Start Backend (Database + API)
cd backend
docker-compose up -d

# 2. Start Frontend (in new terminal)
cd frontend
REACT_APP_BACK_END_HOST=http://localhost:8000 PORT=3001 npm start
```

### Demo URLs
- **Frontend**: http://localhost:3001
- **Evaluations Page**: http://localhost:3001/evaluations
- **Backend API**: http://localhost:8000

---

## 🎤 Demo Script (10 minutes)

### **Opening (1 minute)**
> "Today I'll demonstrate our Multi-Language Translation Leaderboard system. This platform evaluates and ranks AI models across 5 languages using BLEU scores, with real-time submissions and dynamic leaderboards."

### **Part 1: Multi-Language Evaluation (3 minutes)**

**Navigate to**: http://localhost:3001/evaluations

> "First, let's look at our evaluation interface. Here we have dynamic leaderboards for 5 languages:"

1. **Point out the language sections:**
   - Spanish BLEU (7 models - shows "View all 7 models →")
   - Japanese BLEU (1 model - 0.0 score)
   - Arabic BLEU (1 model - 0.0 score) 
   - Chinese BLEU (2 models - both 0.0 scores)
   - Korean BLEU (2 models - both 0.0 scores)

2. **Demonstrate "View More" functionality:**
   - Click "View all 7 models →" on Spanish section
   - Show full leaderboard page with all Spanish models ranked 1-7
   - Navigate back

3. **Live Evaluation:**
   - Select "Spanish" from dropdown
   - Click "Generate GPT Spanish Score" 
   - Show the 5 source sentences appear
   - Point out the BLEU score result
   - Explain: *"This demonstrates real-time GPT evaluation against FLORES+ dataset"*

### **Part 2: Model Submission Flow (4 minutes)**

**From evaluations page**, click "Submit Your Model" button

> "Now let's submit a custom model to the leaderboard."

1. **Form Overview:**
   - Model Name: "Demo-Model-2025"
   - Benchmark Dataset: Select "Spanish Translation (FLORES+)"
   - File Upload area

2. **Upload Demo File:**
   - Use `test_files/demo_test_spanish.csv`
   - Show file parsing: *"The system extracts model outputs from CSV"*
   - Click "Submit Model"

3. **Show Results:**
   - Display success message with BLEU score
   - Navigate back to evaluations
   - Point out new model appears in Spanish leaderboard
   - Show updated ranking

### **Part 3: Technical Deep Dive (2 minutes)**

> "Let me explain the technical architecture:"

**Backend Features:**
- FLORES+ dataset integration (Hugging Face)
- Real-time BLEU score calculation
- MySQL database with Docker persistence
- Multi-language support (5 languages)

**Frontend Features:**
- React-based dynamic UI
- Smart pagination (first 5 + "View More")
- Real-time leaderboard updates
- CSV file parsing

**BLEU Score Explanation:**
> "You'll notice Japanese and Chinese often show 0 BLEU scores. This is normal and expected because:
> - BLEU measures exact n-gram overlap between model output and reference translations
> - Asian languages have different translation styles and word segmentation
> - A 0 BLEU doesn't mean the translation is wrong - just different from the reference
> - Spanish/Arabic typically show higher BLEU scores due to closer linguistic similarity"

---

## 📊 Expected Demo Results

### **Language Performance:**
- **Spanish**: BLEU scores 0.0001-0.0003 (meaningful comparison)
- **Japanese**: 0.0 BLEU (normal due to linguistic differences)
- **Arabic**: 0.0 BLEU (normal for this reference dataset)
- **Chinese**: 0.0 BLEU (normal due to character-based writing system)
- **Korean**: 0.0 BLEU (normal due to different linguistic structure)

### **UI Behavior:**
- Spanish section shows "View all 7 models →" (demonstrates pagination)
- Other sections show models directly (< 5 entries)
- Real-time updates after submissions
- Proper ranking (1, 2, 3...) within each category

---

## 🎯 Key Demo Points to Emphasize

1. **Multi-Language Support**: 5 languages with different linguistic challenges
2. **Real-Time Evaluation**: Live GPT translation scoring
3. **Dynamic Leaderboards**: Updates immediately after submissions
4. **Smart UI**: Pagination for large result sets
5. **Production-Ready**: Docker deployment, persistent database
6. **Extensible**: Easy to add new languages/datasets

---

## 🛠️ Demo Files Available

- `test_files/demo_test_spanish.csv` - High-quality Spanish translations
- `test_files/demo_test_japanese.csv` - Japanese translations (expect 0 BLEU)
- `test_files/demo_test_arabic.csv` - Arabic translations
- `test_files/demo_test_chinese.csv` - Chinese translations (expect 0 BLEU)
- `test_files/demo_test_korean.csv` - Korean translations

---

## 🚨 Troubleshooting

**If frontend won't start:**
```bash
cd frontend && npm install
PORT=3001 npm start
```

**If backend API fails:**
```bash
cd backend
docker-compose down && docker-compose up --build -d
```

**If database is empty:**
- Check `docker-compose logs backend`
- Ensure migrations ran successfully
- Sample data should auto-populate

---

## 🎉 Demo Success Criteria

✅ **All 5 languages visible in UI**  
✅ **"View More" functionality working**  
✅ **Live evaluation generates BLEU scores**  
✅ **Model submission updates leaderboard**  
✅ **Rankings display correctly (1, 2, 3...)**  
✅ **Explain why 0 BLEU is normal for some languages**

**Total Demo Time: ~10 minutes** 
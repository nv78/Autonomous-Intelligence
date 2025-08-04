# Leaderboard Submission API

## Overview
Built a complete model submission and evaluation system for automated leaderboard management.

## What Was Added

### 🗄️ Database Schema (3 new tables)
- **`benchmark_datasets`** - Available benchmark tests (e.g., "flores_spanish_translation")
- **`model_submissions`** - User-submitted model results with metadata
- **`evaluation_results`** - Calculated scores and evaluation details

### 🚀 API Endpoints

#### `/public/submit_model` (POST)
Submit model results for evaluation on a benchmark dataset.

**Input:**
```json
{
  "benchmarkDatasetName": "flores_spanish_translation",
  "modelName": "my-model-v1", 
  "modelResults": ["Hola mundo", "Buenos días", ...]
}
```

**Output:**
```json
{
  "success": true,
  "score": 0.234,
  "submission_id": 1,
  "evaluation_details": {
    "metric": "bleu",
    "num_predictions": 5
  }
}
```

### 🧪 Testing
- **Test suite**: `backend/tests/test_submit_model_api.py`
- **Usage**: `cd backend/tests && python test_submit_model_api.py`

## Current Status

### ✅ Working
- Complete API endpoint with validation
- Database storage of submissions and results  
- Automated API key creation and validation
- Mock BLEU evaluation (returns 0.234)

### 🔄 Next Steps  
- Replace mock evaluation with Angela's real BLEU implementation
- Connect to existing BLEU functions: `get_bleu()`, `translate_gpt()`
- Use real FLORES+ benchmark data instead of mock scores

## Usage Example

```python
# Using the Python SDK
from frontend.src.docs.fsdk.leaderboard_submit import AnoteLeaderboardSubmission

api = AnoteLeaderboardSubmission('your-api-key')
success, score = api.add_model_to_dataset(
    "flores_spanish_translation",
    "my-model-v1", 
    ["Hola mundo", "Buenos días", "Gracias"]
)
print(f"Success: {success}, Score: {score}")
```

## Environment Configuration

- Database host: `db` (Docker container name)  
- Database connection: Uses `global_constants.py` values

## Database Migration

**Current**: New tables added to `schema.sql` (applied on fresh container builds)

**For Existing Databases**: Optional migration available
```bash
# If you need to add tables to an existing database:
cd backend/database && python run_migration.py
```

**Files:**
- `database/migrations/001_add_leaderboard_tables.sql` - Migration SQL
- `database/run_migration.py` - Python migration runner

## 🔐 Hugging Face Authentication Setup

**Required for FLORES+ Dataset Access**

The BLEU evaluation uses the `openlanguagedata/flores_plus` dataset, which is gated and requires authentication.

### Step 1: Create Hugging Face Account
1. Go to https://huggingface.co/join
2. Sign up for a free account
3. Verify your email

### Step 2: Request Dataset Access
1. Visit https://huggingface.co/datasets/openlanguagedata/flores_plus
2. Click "Request Access" button  
3. Fill out the form (agree to terms)
4. Wait for approval (usually instant to 24 hours)

### Step 3: Login via CLI in Docker Container
Once you have access, authenticate inside the Docker container:

```bash
# Enter the running Docker container
docker exec -it anote-backend bash

# Login to Hugging Face (inside container)
huggingface-cli login
# Enter your HF username and password when prompted

# Exit container
exit
```

### Step 4: Restart Backend
```bash
cd backend
docker-compose restart backend
```

### Verification
Test that the dataset loads correctly:
```bash
curl -X POST http://localhost:8000/public/submit_model \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-api-key" \
  -d '{
    "benchmarkDatasetName": "flores_spanish_translation",
    "modelName": "test-model",
    "modelResults": ["Hola mundo", "Buenos días"]
  }'
```

**Expected**: Real BLEU scores (0.0-1.0 range) instead of mock scores.

**Example successful response:**
```json
{
  "success": true,
  "bleu_score": 0.543,
  "submission_id": 6,
  "evaluation_details": {
    "metric": "bleu",
    "note": "Real BLEU evaluation using FLORES+ dataset",
    "num_predictions": 5,
    "num_references": 5
  }
}
```

## 📝 Notes

- **Authentication persists** across container restarts
- **One-time setup** per environment  
- **Required for real BLEU evaluation** - without this, the API falls back to mock scores
- **Alternative**: Use sample reference data for testing (modify code to skip dataset loading) 
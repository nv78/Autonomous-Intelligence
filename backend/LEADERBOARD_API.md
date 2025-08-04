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
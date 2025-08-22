# Multi-Language Translation Leaderboard

A research platform for evaluating and ranking AI translation models across 5 languages using both BLEU and BERTScore metrics. Features real-time submissions, dynamic leaderboards, and comprehensive multi-language evaluation.

## Key Features

- **5 Languages**: Spanish, Japanese, Arabic, Chinese, Korean
- **2 Evaluation Metrics**: BLEU (exact matching) + BERTScore (semantic similarity)  
- **Real-time Leaderboards**: Dynamic rankings with live updates
- **Model Submission**: Easy CSV upload interface for translation results
- **FLORES+ Integration**: Industry-standard benchmark datasets
- **Research-Grade Evaluation**: Comprehensive metric comparison

## Quick Start

### Prerequisites
- Docker and Docker Compose
- Node.js and npm
- Git

### Setup and Run

1. **Clone and Start Backend**
   ```bash
   git clone <repository-url>
   cd Autonomous-Intelligence-chatbots-leaderboard-api
   cd backend
   docker-compose up --build -d
   ```

2. **Start Frontend**
   ```bash
   cd ../frontend
   npm install
   PORT=3001 npm start
   ```

3. **Access Applications**
   - **Evaluations**: http://localhost:3001/evaluations
   - **Backend API**: http://localhost:8000
   - **Health Check**: http://localhost:8000/health

## Evaluation Metrics Comparison

| Metric | Spanish | Arabic | Korean | Japanese | Chinese | Advantage |
|--------|---------|--------|--------|----------|---------|-----------|
| **BLEU** | ~0.40 | ~0.10 | ~0.13 | ~0.00 | ~0.00 | Fast, established standard |
| **BERTScore** | ~0.65 | ~0.65 | ~0.60 | ~0.62 | ~0.62 | Semantic similarity, works for all languages |

**Key Insight**: BERTScore provides meaningful evaluation for all languages, while BLEU struggles with Asian languages due to structural differences.

## How It Works

1. **Browse Leaderboards**: View current model rankings by language and metric
2. **Submit Your Model**: Upload CSV with translation results
3. **Get Evaluated**: System calculates BLEU/BERTScore against FLORES+ references  
4. **See Results**: Your model appears in real-time leaderboard rankings

## Testing & Demo

**Quick Demo**: See `TESTING_GUIDE.md` for complete instructions

**Test Files Available**: All testing files are in `test_files/` directory
- Language-specific demos for each supported language
- Score range examples (high/medium/low performance)

## API Endpoints

### Submit Model
```bash
POST /public/submit_model
{
  "benchmarkDatasetName": "flores_spanish_translation",
  "modelName": "my-model-v1", 
  "modelResults": ["Translation 1", "Translation 2"],
  "sentence_ids": [0, 1]
}
```

### Get Source Sentences
```bash
GET /public/get_source_sentences?dataset_name=flores_spanish_translation&count=5
```

### Get Leaderboard
```bash
GET /public/get_leaderboard
```

## Development

### Workflow
1. **Make Changes**: Edit code in your preferred IDE
2. **Test Locally**: Use endpoints above to verify functionality  
3. **Commit & Push**: 
   ```bash
   git add .
   git commit -m "Your change description"
   git push origin chatbots-leaderboard-api
   ```

### Architecture
- **Backend**: Flask API with MySQL database
- **Frontend**: React with dynamic leaderboard components
- **Evaluation**: BLEU (nltk) + BERTScore (bert-base-multilingual-cased)
- **Data**: FLORES+ benchmark datasets via Hugging Face

## Documentation

- **`TESTING_GUIDE.md`**: Comprehensive testing instructions + demo guide
- **`CODEBASE_SETUP.md`**: Development environment setup

## Contributing

See `CONTRIBUTING.md` for contribution guidelines.

## License

See `LICENSE.md` for details.

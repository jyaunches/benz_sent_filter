# Benz Sent Filter

MNLS-based sentiment classification service for article title analysis.

## Overview

Benz Sent Filter provides zero-shot natural language inference capabilities to classify news headlines along two dimensions:

1. **Opinion vs News**: Detects whether a headline is opinionated or straight news
2. **Temporal Category**: Classifies whether content is about past events, future events, or general topics

The service is designed to:
- Run on CPU (no GPU required)
- Use open-source models
- Require no custom training for v1
- Process headline-length inputs efficiently

## Quick Start

### Prerequisites

- Python 3.11+
- [uv](https://github.com/astral-sh/uv) package manager

### Installation

```bash
# Install development dependencies
make dev

# Copy environment configuration
cp .env.example .env
```

### Running the Service

```bash
# Development server with hot reload
make serve

# Production server
make serve-prod
```

The service will be available at `http://localhost:8002`.

## Development

### Available Commands

```bash
make help              # Show all available commands
make dev               # Install all dependencies
make test              # Run unit tests
make test-cov          # Run tests with coverage
make test-integration  # Run integration tests
make lint              # Check code quality
make format            # Format code
make check             # Run lint + tests
make clean             # Clean build artifacts
```

### Project Structure

```
src/
  benz_sent_filter/
    __init__.py
    __main__.py          # Entry point
    api/                 # FastAPI routes
    models/              # Pydantic models
    services/            # Classification service logic
    config/              # Configuration management

tests/                   # Unit tests
integration/             # Integration tests
config/                  # Configuration files
```

### Testing

Tests use pytest with the following structure:
- Unit tests: `tests/`
- Integration tests: `integration/`
- Coverage reports: `htmlcov/`

```bash
# Run all tests
make test

# Run specific test file
make test-file FILE=tests/test_example.py

# Generate coverage report
make test-cov
```

## API Endpoints

### Health Check

Check service health status:

```bash
curl http://localhost:8002/health
```

Response:
```json
{
  "status": "healthy",
  "service": "benz_sent_filter",
  "timestamp": "2025-11-16T22:00:00.000Z"
}
```

### Single Headline Classification

Classify a single headline:

```bash
curl -X POST http://localhost:8002/classify \
  -H "Content-Type: application/json" \
  -d '{"headline": "Why the Fed Is Wrong About Inflation"}'
```

Response:
```json
{
  "is_opinion": true,
  "is_straight_news": false,
  "temporal_category": "general_topic",
  "scores": {
    "opinion_score": 0.85,
    "news_score": 0.15,
    "past_score": 0.10,
    "future_score": 0.15,
    "general_score": 0.75
  },
  "headline": "Why the Fed Is Wrong About Inflation"
}
```

### Batch Classification

Classify multiple headlines in one request:

```bash
curl -X POST http://localhost:8002/classify/batch \
  -H "Content-Type: application/json" \
  -d '{
    "headlines": [
      "Fed Raises Interest Rates by 25 Basis Points",
      "Tesla to Report Q4 Earnings Next Week"
    ]
  }'
```

Response:
```json
{
  "results": [
    {
      "is_opinion": false,
      "is_straight_news": true,
      "temporal_category": "past_event",
      "scores": {
        "opinion_score": 0.15,
        "news_score": 0.85,
        "past_score": 0.70,
        "future_score": 0.10,
        "general_score": 0.20
      },
      "headline": "Fed Raises Interest Rates by 25 Basis Points"
    },
    {
      "is_opinion": false,
      "is_straight_news": false,
      "temporal_category": "future_event",
      "scores": {
        "opinion_score": 0.20,
        "news_score": 0.55,
        "past_score": 0.10,
        "future_score": 0.80,
        "general_score": 0.10
      },
      "headline": "Tesla to Report Q4 Earnings Next Week"
    }
  ]
}
```

## Classification Output

The service returns comprehensive classification data for each headline:

### Boolean Flags
- **is_opinion**: `true` if opinion score ≥ 0.6 (opinion/editorial content)
- **is_straight_news**: `true` if news score ≥ 0.6 (factual news reporting)

Both flags can be `false` (uncertain), or both `true` (mixed content).

### Temporal Category
One of three values:
- **past_event**: Content about events that already happened
- **future_event**: Content about upcoming events or forecasts
- **general_topic**: Content about general analysis or timeless topics

Determined by the highest-scoring temporal label.

### Raw Scores
All probability scores (0.0 - 1.0) are exposed for transparency:
- **opinion_score**: Probability of opinion/editorial content
- **news_score**: Probability of factual news content
- **past_score**: Probability of past event content
- **future_score**: Probability of future event content
- **general_score**: Probability of general topic content

## Integration with Benz Ecosystem

This service is part of the benz ecosystem of financial data analysis microservices:
- **benz_eval_prep** - Historical financial data preparation
- **benz_evaluator** - Historical data evaluation
- **benz_realtime_trader** - Real-time news ingestion and trading
- **benz_bridge** - Database observer and event distribution
- **benz_analyzer** - LLM-based news analysis
- **benz_researcher** - Realtime stock information API
- **benz_fly_listener** - Event coordination and decision making
- **benz_sent_filter** - Article sentiment classification (this service)

## ML Model Details

### Model
- **Name**: `typeform/distilbert-base-uncased-mnli`
- **Type**: DistilBERT fine-tuned for Multi-Genre Natural Language Inference
- **Size**: ~66M parameters (~250MB download)
- **Runtime**: CPU-only (no GPU required)

### Classification Method
The service uses zero-shot classification with carefully designed candidate labels:

**Opinion vs News:**
- "This is an opinion piece or editorial"
- "This is a factual news report"

**Temporal Classification:**
- "This is about a past event that already happened"
- "This is about a future event or forecast"
- "This is a general topic or analysis"

All 5 labels are evaluated in a single inference call for efficiency.

### Threshold Logic
- **Boolean conversion**: Score ≥ 0.6 → `true`, Score < 0.6 → `false`
- **Temporal category**: Highest-scoring temporal label wins
- **Edge cases**: Both opinion and news flags can be true/false simultaneously

### Performance
- **Single headline**: < 2 seconds on CPU
- **Batch of 10**: < 10 seconds on CPU
- **Startup time**: < 30 seconds (includes model download on first run)
- **Memory**: < 1GB

### Model Caching
The model is downloaded once and cached locally in `~/.cache/huggingface/transformers/`.
Subsequent startups use the cached model (fast startup).

## License

MIT

## Contributing

See the main benz ecosystem documentation for contribution guidelines.

# Benz Sent Filter

MNLS-based sentiment classification service for article title analysis.

## Overview

Benz Sent Filter provides zero-shot natural language inference capabilities to classify news headlines along multiple dimensions:

1. **Opinion vs News**: Detects whether a headline is opinionated or straight news
2. **Temporal Category**: Classifies whether content is about past events, future events, or general topics
3. **Company Relevance**: Detects whether a headline is about a specific company (optional)
4. **Far-Future Forecast Detection**: Identifies multi-year forecasts vs near-term guidance (automatic for future events)
5. **Routine Operations Filter**: Detects routine business operations with immaterial financial impact (optional)

The service is designed to:
- Run on CPU (no GPU required)
- Use open-source models
- Require no custom training for v1
- Process headline-length inputs efficiently
- Support optional company-specific filtering

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

### Company Relevance Detection

Check if a headline is about a specific company by adding the optional `company` parameter:

```bash
curl -X POST http://localhost:8002/classify \
  -H "Content-Type: application/json" \
  -d '{
    "headline": "Dell Unveils AI Data Platform Updates; Launches First 2U Server With NVIDIA Blackwell GPUs",
    "company": "Dell"
  }'
```

Response (includes company relevance fields):
```json
{
  "is_opinion": false,
  "is_straight_news": true,
  "temporal_category": "past_event",
  "scores": {
    "opinion_score": 0.20,
    "news_score": 0.75,
    "past_score": 0.80,
    "future_score": 0.10,
    "general_score": 0.10
  },
  "headline": "Dell Unveils AI Data Platform Updates; Launches First 2U Server With NVIDIA Blackwell GPUs",
  "is_about_company": true,
  "company_score": 0.92,
  "company": "Dell"
}
```

The company relevance feature:
- Returns `is_about_company` (boolean) indicating if the headline discusses the specified company
- Returns `company_score` (0.0 - 1.0) showing confidence level
- Uses threshold of 0.5 (lower than opinion/news threshold)
- Works with company name variations: "Dell", "DELL", "Dell Technologies"
- Handles multi-company headlines: checks relevance to the specified company only

To check a different company with the same headline:

```bash
# Check NVIDIA relevance (also mentioned in headline)
curl -X POST http://localhost:8002/classify \
  -H "Content-Type: application/json" \
  -d '{
    "headline": "Dell Unveils AI Data Platform Updates; Launches First 2U Server With NVIDIA Blackwell GPUs",
    "company": "NVIDIA"
  }'
# Returns: is_about_company: true, company_score: 0.88

# Check unrelated company
curl -X POST http://localhost:8002/classify \
  -H "Content-Type: application/json" \
  -d '{
    "headline": "Dell Unveils AI Data Platform Updates; Launches First 2U Server With NVIDIA Blackwell GPUs",
    "company": "Tesla"
  }'
# Returns: is_about_company: false, company_score: 0.12
```

### Far-Future Forecast Detection

When classifying headlines with `temporal_category: "future_event"`, the service automatically detects far-future forecasts (>1 year timeframes):

```bash
curl -X POST http://localhost:8002/classify \
  -H "Content-Type: application/json" \
  -d '{"headline": "Forecasts $1B Launch-Year Revenue, Sees $18B–$22B Over 5 Years"}'
```

Response (includes far-future fields when detected):
```json
{
  "is_opinion": false,
  "is_straight_news": true,
  "temporal_category": "future_event",
  "scores": {
    "opinion_score": 0.20,
    "news_score": 0.75,
    "past_score": 0.10,
    "future_score": 0.80,
    "general_score": 0.10
  },
  "headline": "Forecasts $1B Launch-Year Revenue, Sees $18B–$22B Over 5 Years",
  "far_future_forecast": true,
  "forecast_timeframe": "over 5 years"
}
```

How it works:
- Only applies when `temporal_category` is `future_event`
- Pattern-based detection using regex for multi-year timeframes
- Detects patterns like: "over X years", "by 2028", "X-year forecast"
- Returns `null` for near-term forecasts (<1 year)
- Helps downstream systems filter out speculative long-term projections

### Routine Operations Filter

Detect routine business operations with immaterial financial impact by providing the optional `company_symbol` parameter:

```bash
curl -X POST http://localhost:8002/classify \
  -H "Content-Type: application/json" \
  -d '{
    "headline": "Fannie Mae Begins Marketing Its Most Recent Sale Of Reperforming Loans... $560.5M",
    "company_symbol": "FNMA"
  }'
```

Response (includes routine operation fields):
```json
{
  "is_opinion": false,
  "is_straight_news": true,
  "temporal_category": "past_event",
  "scores": {
    "opinion_score": 0.15,
    "news_score": 0.85,
    "past_score": 0.75,
    "future_score": 0.10,
    "general_score": 0.15
  },
  "headline": "Fannie Mae Begins Marketing Its Most Recent Sale Of Reperforming Loans... $560.5M",
  "routine_operation": true,
  "routine_confidence": 0.85,
  "routine_metadata": {
    "routine_score": 4,
    "materiality_score": -2,
    "detected_patterns": ["process_language", "routine_transaction", "frequency_indicator"],
    "transaction_value": 560500000.0,
    "materiality_ratio": 0.00014,
    "process_stage": "early"
  }
}
```

How it works:
- Detects process language ("begins marketing", "plans to", "exploring")
- Identifies routine transaction types (loan sales, buybacks, dividends)
- Assesses materiality relative to company size
- Provides detailed metadata for transparency
- Focuses on financial services industry
- Reduces false positives on routine operations by 50%+

Supported companies: FNMA, BAC, JPM, WFC, C, GS, MS, USB, TFC, PNC

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

**Batch with Company Filter**: Add `company` parameter to check all headlines against one company:

```bash
curl -X POST http://localhost:8002/classify/batch \
  -H "Content-Type: application/json" \
  -d '{
    "headlines": [
      "Tesla Reports Record Q3 Deliveries",
      "Apple Announces New iPhone",
      "Tesla Stock Jumps on Earnings Beat"
    ],
    "company": "Tesla"
  }'
```

Response includes company relevance for all headlines:
```json
{
  "results": [
    {
      "is_opinion": false,
      "is_straight_news": true,
      "temporal_category": "past_event",
      "scores": { "...": "..." },
      "headline": "Tesla Reports Record Q3 Deliveries",
      "is_about_company": true,
      "company_score": 0.95,
      "company": "Tesla"
    },
    {
      "is_opinion": false,
      "is_straight_news": true,
      "temporal_category": "past_event",
      "scores": { "...": "..." },
      "headline": "Apple Announces New iPhone",
      "is_about_company": false,
      "company_score": 0.08,
      "company": "Tesla"
    },
    {
      "is_opinion": false,
      "is_straight_news": true,
      "temporal_category": "past_event",
      "scores": { "...": "..." },
      "headline": "Tesla Stock Jumps on Earnings Beat",
      "is_about_company": true,
      "company_score": 0.93,
      "company": "Tesla"
    }
  ]
}
```

## Classification Output

The service returns comprehensive classification data for each headline:

### Boolean Flags
- **is_opinion**: `true` if opinion score ≥ 0.6 (opinion/editorial content)
- **is_straight_news**: `true` if news score ≥ 0.6 (factual news reporting)
- **is_about_company**: `true` if company score ≥ 0.5 (only present when `company` parameter provided)
- **far_future_forecast**: `true` if multi-year forecast detected (only present when `temporal_category` is `future_event`)
- **routine_operation**: `true` if routine business operation detected (only present when `company_symbol` parameter provided)

Both opinion/news flags can be `false` (uncertain), or both `true` (mixed content).

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
- **company_score**: Probability headline is about specified company (only when `company` provided)

### Optional Fields

**Company Relevance** (when `company` parameter is provided):
- **is_about_company**: Boolean flag (score ≥ 0.5)
- **company_score**: Raw probability score (0.0 - 1.0)
- **company**: The company name that was checked

**Far-Future Forecast Detection** (when `temporal_category` is `future_event`):
- **far_future_forecast**: Boolean indicating multi-year forecast (>1 year)
- **forecast_timeframe**: String describing the timeframe (e.g., "over 5 years", "by 2028")

**Routine Operations Filter** (when `company_symbol` parameter is provided):
- **routine_operation**: Boolean indicating routine business operation
- **routine_confidence**: Confidence score (0.0 - 1.0)
- **routine_metadata**: Object with detailed analysis:
  - `routine_score`: Numeric score for routine operation indicators
  - `materiality_score`: Numeric score for materiality assessment
  - `detected_patterns`: List of detected pattern types
  - `transaction_value`: Dollar value if detected
  - `materiality_ratio`: Transaction value / company market cap
  - `process_stage`: Stage of the process (e.g., "early", "completion")

All optional fields use Pydantic `exclude_none=True` for backward compatibility (omitted when not applicable).

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

**Company Relevance (when `company` parameter provided):**
- Hypothesis template: "This article is about {company_name}"
- Evaluated in a separate inference call (only when company specified)
- Reuses the same MNLI model pipeline

### Threshold Logic
- **Opinion/News boolean conversion**: Score ≥ 0.6 → `true`, Score < 0.6 → `false`
- **Company relevance boolean conversion**: Score ≥ 0.5 → `true`, Score < 0.5 → `false`
- **Temporal category**: Highest-scoring temporal label wins
- **Edge cases**: Both opinion and news flags can be true/false simultaneously
- **Why lower threshold for company?**: Company mentions are typically binary (name appears or doesn't). Lower threshold reduces false negatives for edge cases like indirect references.

### Performance
- **Single headline (no company)**: < 2 seconds on CPU
- **Single headline (with company)**: < 3 seconds on CPU (adds < 500ms overhead)
- **Batch of 10 (no company)**: < 10 seconds on CPU
- **Batch of 10 (with company)**: < 15 seconds on CPU
- **Startup time**: < 30 seconds (includes model download on first run)
- **Memory**: < 1GB

### Model Caching
The model is downloaded once and cached locally in `~/.cache/huggingface/transformers/`.
Subsequent startups use the cached model (fast startup).

## License

MIT

## Contributing

See the main benz ecosystem documentation for contribution guidelines.

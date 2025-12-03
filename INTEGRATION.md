# Benz Sent Filter - Integration Guide

## Overview

Benz Sent Filter is a FastAPI service providing MNLI-based (Multi-Genre Natural Language Inference) headline classification and sentiment analysis for financial news. It uses zero-shot classification to categorize headlines across multiple dimensions without requiring training data.

## API Documentation

When the service is running, interactive API documentation is available at:
- **Swagger UI**: `http://<host>:8002/docs`
- **ReDoc**: `http://<host>:8002/redoc`
- **OpenAPI Schema**: `http://<host>:8002/openapi.json`

## Quick Start

### Health Check
```bash
curl http://localhost:8002/health

# Response
{
  "status": "healthy",
  "service": "benz_sent_filter",
  "timestamp": "2025-01-15T15:30:00Z"
}
```

### Version Info
```bash
curl http://localhost:8002/version

# Response
{
  "service": "benz_sent_filter",
  "version": "1.0.0",
  "models": {
    "primary": "typeform/distilbert-base-uncased-mnli",
    "secondary": "facebook/bart-large-mnli"
  }
}
```

## Core Endpoints

### 1. Single Headline Classification

Classify a single headline with optional ticker context:

```bash
curl -X POST http://localhost:8002/classify_sentiment \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Apple Reports Record Q4 Earnings, Beats Expectations",
    "tickers": ["AAPL"]
  }'
```

Response:
```json
{
  "is_opinion": false,
  "opinion_confidence": 0.85,
  "is_past_event": false,
  "past_event_confidence": 0.92,
  "is_future_speculation": false,
  "future_speculation_confidence": 0.88,
  "is_routine": false,
  "routine_confidence": 0.91,
  "primary_classification": "factual_news",
  "classification_confidence": 0.93,
  "sentiment_score": 0.78,
  "sentiment_label": "positive",
  "should_filter": false,
  "filter_reasons": [],
  "processing_time_ms": 245
}
```

### 2. Multi-Ticker Classification

Classify a headline affecting multiple tickers:

```bash
curl -X POST http://localhost:8002/classify_multi_ticker \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Tech Giants Apple and Microsoft Post Strong Quarterly Results",
    "tickers": ["AAPL", "MSFT"]
  }'
```

Response:
```json
{
  "AAPL": {
    "is_opinion": false,
    "is_routine": false,
    "sentiment_score": 0.82,
    "sentiment_label": "positive",
    "should_filter": false,
    "ticker_mentioned": true
  },
  "MSFT": {
    "is_opinion": false,
    "is_routine": false,
    "sentiment_score": 0.80,
    "sentiment_label": "positive",
    "should_filter": false,
    "ticker_mentioned": true
  },
  "processing_time_ms": 312
}
```

### 3. Batch Classification

Process multiple headlines in a single request:

```bash
curl -X POST http://localhost:8002/classify_batch \
  -H "Content-Type: application/json" \
  -d '{
    "headlines": [
      {
        "id": "1",
        "text": "Fed Announces Rate Decision",
        "tickers": ["SPY"]
      },
      {
        "id": "2",
        "text": "Tesla Recalls 50,000 Vehicles",
        "tickers": ["TSLA"]
      }
    ]
  }'
```

Response:
```json
{
  "results": [
    {
      "id": "1",
      "classification": { /* full classification */ }
    },
    {
      "id": "2",
      "classification": { /* full classification */ }
    }
  ],
  "total_processing_time_ms": 520
}
```

### 4. Routine Operations Detection

Check if a headline describes routine business operations:

```bash
curl -X POST http://localhost:8002/detect_routine \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Apple Opens New Store in Chicago",
    "ticker": "AAPL"
  }'
```

Response:
```json
{
  "is_routine": true,
  "confidence": 0.89,
  "routine_type": "expansion",
  "routine_indicators": [
    "store opening",
    "geographic expansion"
  ],
  "market_impact_expectation": "minimal"
}
```

### 5. Catalyst Detection

Identify if headline contains quantitative catalysts:

```bash
curl -X POST http://localhost:8002/detect_catalyst \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Apple Beats Q4 Earnings by $0.15 per Share",
    "ticker": "AAPL"
  }'
```

Response:
```json
{
  "has_catalyst": true,
  "catalyst_type": "earnings_beat",
  "confidence": 0.94,
  "quantitative_elements": [
    "$0.15 per share",
    "Q4 earnings"
  ],
  "expected_impact": "positive"
}
```

## Classification Categories

### Primary Classifications
- **factual_news**: Objective reporting of events
- **opinion_piece**: Analysis, commentary, or speculation
- **past_event**: Historical or already-occurred events
- **future_speculation**: Predictions or forward-looking statements
- **routine_operations**: Regular business activities

### Sentiment Labels
- **positive**: Bullish or favorable news
- **negative**: Bearish or unfavorable news
- **neutral**: No clear directional bias

### Filter Recommendations
Headlines are flagged for filtering (`should_filter: true`) when:
- Classified as opinion (low confidence in factual nature)
- Identified as past event (already priced in)
- Marked as routine operations (minimal market impact)
- Below confidence threshold (default: 0.6)

## Advanced Features

### Custom Thresholds
```bash
curl -X POST http://localhost:8002/classify_sentiment \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Apple May See Growth Next Quarter",
    "tickers": ["AAPL"],
    "config": {
      "opinion_threshold": 0.7,
      "routine_threshold": 0.8,
      "min_confidence": 0.65
    }
  }'
```

### Include Model Explanations
```bash
curl -X POST http://localhost:8002/classify_sentiment?explain=true \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Apple Announces Dividend Increase",
    "tickers": ["AAPL"]
  }'
```

Response includes:
```json
{
  // ... standard response ...
  "explanation": {
    "model_used": "typeform/distilbert-base-uncased-mnli",
    "classification_scores": {
      "opinion_piece": 0.12,
      "factual_news": 0.88
    },
    "key_phrases": ["announces", "dividend increase"],
    "confidence_factors": ["strong action verb", "quantifiable event"]
  }
}
```

## Model Information

### Primary Model: DistilBERT-MNLI
- **Model**: `typeform/distilbert-base-uncased-mnli`
- **Parameters**: ~67M (lightweight, fast)
- **Use Cases**: Opinion detection, temporal classification
- **Performance**: 200-500ms per classification (CPU)

### Secondary Model: BART-Large-MNLI
- **Model**: `facebook/bart-large-mnli`
- **Parameters**: ~400M (more powerful, slower)
- **Use Cases**: Routine detection, catalyst identification
- **Performance**: 300-700ms per classification (CPU)

## Integration Patterns

### For Article Filtering (benz_analyzer)
```python
import httpx

async def filter_headlines(articles: list[dict]):
    async with httpx.AsyncClient() as client:
        filtered = []
        for article in articles:
            response = await client.post(
                "http://benz-sent-filter:8002/classify_sentiment",
                json={
                    "text": article["title"],
                    "tickers": article["tickers"]
                }
            )
            result = response.json()
            if not result["should_filter"]:
                filtered.append(article)
        return filtered
```

### For Sentiment Enrichment
```python
def enrich_with_sentiment(headline: str, ticker: str) -> dict:
    response = requests.post(
        "http://benz-sent-filter:8002/classify_sentiment",
        json={"text": headline, "tickers": [ticker]}
    )
    data = response.json()
    return {
        "sentiment": data["sentiment_label"],
        "confidence": data["sentiment_score"],
        "is_actionable": not data["should_filter"]
    }
```

### For Batch Processing
```python
def process_news_batch(headlines: list[dict]) -> dict:
    response = requests.post(
        "http://benz-sent-filter:8002/classify_batch",
        json={"headlines": headlines}
    )
    return response.json()["results"]
```

## Performance Considerations

- **Caching**: Repeated headlines are cached for 1 hour
- **Batch Processing**: Batch endpoint reduces model loading overhead
- **GPU Support**: Set `DEVICE=cuda` for GPU acceleration if available
- **Model Preloading**: Models loaded at startup, not per request

## Environment Configuration

```env
# Service Configuration
PORT=8002
HOST=0.0.0.0
WORKERS=2

# Model Configuration
MODEL_DEVICE=cpu  # or 'cuda' for GPU
MODEL_CACHE_DIR=/models
PRIMARY_MODEL=typeform/distilbert-base-uncased-mnli
SECONDARY_MODEL=facebook/bart-large-mnli

# Classification Thresholds
DEFAULT_OPINION_THRESHOLD=0.65
DEFAULT_ROUTINE_THRESHOLD=0.70
DEFAULT_MIN_CONFIDENCE=0.60

# Caching
CACHE_TTL_SECONDS=3600
CACHE_MAX_SIZE=10000
```

## Error Handling

### 400 - Invalid Request
```json
{
  "detail": "Missing required field: 'text'"
}
```

### 422 - Validation Error
```json
{
  "detail": [
    {
      "loc": ["body", "tickers"],
      "msg": "ensure this value has at most 10 items",
      "type": "value_error"
    }
  ]
}
```

### 503 - Model Not Ready
```json
{
  "detail": "Model is still loading. Please retry in a few seconds."
}
```

## Monitoring and Health

### Model Load Status
```bash
curl http://localhost:8002/health/models

{
  "primary_model": {
    "loaded": true,
    "load_time_seconds": 2.3
  },
  "secondary_model": {
    "loaded": true,
    "load_time_seconds": 4.1
  }
}
```

### Performance Metrics
```bash
curl http://localhost:8002/metrics

{
  "requests_total": 10000,
  "avg_latency_ms": 285,
  "cache_hit_rate": 0.35,
  "model_inference_time_ms": {
    "p50": 250,
    "p95": 450,
    "p99": 680
  }
}
```
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

_(To be implemented)_

### Health Check
```
GET /health
```

### Single Headline Classification
```
POST /classify
```

### Batch Classification
```
POST /classify/batch
```

## Classification Output

The service returns both boolean classifications and raw scores:

```json
{
  "is_opinion": true,
  "is_straight_news": false,
  "temporal_category": "FUTURE_EVENT",
  "scores": {
    "opinion": 0.85,
    "news": 0.15,
    "past": 0.10,
    "future": 0.80,
    "general": 0.10
  }
}
```

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

_(To be configured during implementation)_

Default model: `facebook/bart-large-mnli`

The service uses a zero-shot classification pipeline:
- Input: News headline text
- Output: Probabilities for each classification label
- Method: Natural Language Inference (NLI)

## License

MIT

## Contributing

See the main benz ecosystem documentation for contribution guidelines.

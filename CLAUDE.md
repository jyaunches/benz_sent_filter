# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository Purpose

This repository implements **benz_sent_filter** - an MNLS-based sentiment classification service for article title analysis. It provides zero-shot natural language inference capabilities to classify news headlines along multiple dimensions:

1. **Opinion vs News**: Detect whether a headline is opinionated or straight news
2. **Temporal Category**: Classify whether content is about past events, future events, or general topics
3. **Company Relevance**: Detect whether a headline is about a specific company (optional, via `company` parameter)
4. **Far-Future Forecast Detection**: Identify multi-year forecasts vs near-term guidance (automatic for future events)
5. **Routine Operations Filter**: Detect routine business operations with immaterial impact (optional, via `company_symbol` parameter)

The service runs on CPU and uses open-source models without requiring custom training.

## Cross-Repository Work

For architectural and system knowledge about this repository, invoke the `sentiment-filter-expert` skill which provides comprehensive understanding of MNLS-based classification, zero-shot inference, and filtering logic. For tasks spanning multiple benz ecosystem repositories, use the `cross-repo-helper` agent in benz_mgmt. Agents and slash commands automatically invoke skills when deep system knowledge is needed.

## Architecture

### Service Type
- **REST API** service built with FastAPI
- **Stateless** - no database integration
- Returns classification results directly to callers
- Port: 8002 (development)

### Core Technologies
- **FastAPI** for REST API endpoints
- **Pydantic** for data validation
- **Transformers** (added during implementation) for MNLS model inference
- **uv** for package management

### Directory Structure
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

## Development Workflow

### Setup
```bash
make dev              # Install all dependencies
make test             # Run tests
make lint             # Check code quality
make serve            # Start dev server (port 8002)
```

### Package Management
- Use `uv` for all package operations (NEVER pip)
- Dependencies defined in `pyproject.toml`
- Add ML dependencies during implementation phase

### Testing
- Unit tests in `tests/` directory
- PYTHONPATH=src for imports
- Use pytest with coverage reporting
- Follow dataclass patterns and type annotations

### Code Quality
- Ruff for linting and formatting
- Type annotations required
- Follow existing patterns in benz ecosystem

## Integration Patterns

When working across the ecosystem:
- Integrate directly into existing files rather than creating parallel systems
- Maintain consistency with other benz services
- Use shared documentation via `shared_docs/` symlink
- Follow patterns documented in `.claude/PATTERNS.md`

## Slash Commands

Available via `.claude/commands/` (symlinked from benz_mgmt):
- `/spec` - Create feature specifications
- `/bug` - TDD bug fixing workflow
- `/implement-phase` - Execute implementation phases
- `/fix-tests` - Run and fix failing tests

## Implemented Features

### Core Classification
- **Model**: `typeform/distilbert-base-uncased-mnli` (DistilBERT fine-tuned for MNLI)
- **Method**: Zero-shot classification with carefully designed candidate labels
- **Performance**: <2s single headline, <10s batch of 10 (CPU-only)
- **Thresholds**: 0.6 for opinion/news, 0.5 for company relevance

### Optional Filters

1. **Company Relevance Detection** (via `company` parameter):
   - Zero-shot NLI with hypothesis: "This article is about {company}"
   - Returns `is_about_company` boolean and `company_score` (0.0-1.0)
   - Adds ~500ms overhead per classification

2. **Far-Future Forecast Detection** (automatic for FUTURE_EVENT):
   - Pattern-based detection using regex for multi-year timeframes
   - Returns `far_future_forecast` boolean and `forecast_timeframe` string
   - Examples: "over 5 years", "by 2028", "X-year forecast"
   - Helps filter out speculative long-term projections

3. **Routine Operations Filter** (via `company_symbol` parameter):
   - Detects process language, routine transactions, materiality
   - Returns `routine_operation` boolean, `routine_confidence`, and detailed metadata
   - Company context for FNMA, BAC, JPM, WFC, C, GS, MS, USB, TFC, PNC
   - Focuses on financial services industry
   - Reduces false positives on routine operations by 50%+

## API Design

Service provides classification endpoints for:
- Single headline classification (`/classify`)
- Batch headline processing (`/classify/batch`)
- Health check endpoint (`/health`)

**Request Parameters**:
- `headline` (required): Headline text to classify
- `company` (optional): Company name for relevance detection
- `company_symbol` (optional): Ticker symbol for routine operations filter

**Response Fields**:
- Core: `is_opinion`, `is_straight_news`, `temporal_category`, `scores`
- Company relevance: `is_about_company`, `company_score`, `company`
- Far-future: `far_future_forecast`, `forecast_timeframe`
- Routine operations: `routine_operation`, `routine_confidence`, `routine_metadata`

Returns both boolean classifications and raw scores for transparency.
All optional fields use Pydantic `exclude_none=True` for backward compatibility.

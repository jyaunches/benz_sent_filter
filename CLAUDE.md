# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository Purpose

This repository implements **benz_sent_filter** - an MNLS-based sentiment classification service for article title analysis. It provides zero-shot natural language inference capabilities to classify news headlines along two dimensions:

1. **Opinion vs News**: Detect whether a headline is opinionated or straight news
2. **Temporal Category**: Classify whether content is about past events, future events, or general topics

The service runs on CPU and uses open-source models without requiring custom training.

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

## ML Model Integration (To Be Implemented)

When adding MNLS classification:
- Add dependencies: `transformers`, `torch`
- Use zero-shot classification pipeline
- Model: `facebook/bart-large-mnli` or similar
- CPU-only inference required
- Cache models appropriately (see .gitignore)

## API Design

Service provides classification endpoints for:
- Single headline classification
- Batch headline processing
- Health check endpoint

Return both boolean classifications and raw scores for transparency.

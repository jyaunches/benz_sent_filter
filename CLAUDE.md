# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository Purpose

This repository implements **benz_sent_filter** - an MNLS-based sentiment classification service for article title analysis. It provides zero-shot natural language inference capabilities to classify news headlines along multiple dimensions:

1. **Opinion vs News**: Detect whether a headline is opinionated or straight news
2. **Temporal Category**: Classify whether content is about past events, future events, or general topics
3. **Company Relevance**: Detect whether a headline is about a specific company (optional, via `company` parameter)
4. **Far-Future Forecast Detection**: Identify multi-year forecasts vs near-term guidance (automatic for future events)
5. **Routine Operations Filter**: Detect routine business operations with immaterial impact (optional, via `company_symbol` parameter)
6. **Quantitative Catalyst Detection**: Identify financial catalysts with dollar amounts (dividends, acquisitions, buybacks, earnings, guidance)
7. **Strategic Catalyst Detection**: Identify strategic corporate events (executive changes, mergers, partnerships, product launches, rebranding, clinical trials)

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

### Testing
- Unit tests in `tests/` directory
- PYTHONPATH=src for imports
- Use pytest with coverage reporting
- Follow dataclass patterns and type annotations

### Code Quality
- Ruff for linting and formatting
- Type annotations required
- Follow existing patterns in benz ecosystem

## Deployment

### CPU Deployment (Fly.io)

All CPU deployment tasks (GitHub Actions, Fly.io deployments, production operations) are managed through the `benz_mgmt` repository's centralized deployment utilities. See `benz_deployment/fly/` in benz_mgmt for:
- Configuration management via `config.yml`
- Workflow generation and updates
- Secret management and auditing
- Tier-based deployment orchestration

If user requests deployment operations, direct them to use `benz_mgmt` repository.

### GPU Deployment (RunPod Serverless)

For GPU-accelerated inference, the service can be deployed to RunPod Serverless:

**Files**:
- `src/benz_sent_filter/runpod_handler.py` - Thin handler wrapper around ClassificationService
- `Dockerfile.runpod` - GPU-optimized Docker image with pre-downloaded model
- `scripts/test_runpod_local.sh` - Local testing script
- `docs/RUNPOD_DEPLOYMENT.md` - Complete deployment guide

**Quick Start**:
```bash
# Build and push Docker image
docker build --platform linux/amd64 -f Dockerfile.runpod -t YOUR_DOCKERHUB/benz-sent-filter:v1.0.0 .
docker push YOUR_DOCKERHUB/benz-sent-filter:v1.0.0

# Local testing
python src/benz_sent_filter/runpod_handler.py --rp_serve_api --rp_api_port 8080
./scripts/test_runpod_local.sh
```

**RunPod Handler Operations**:
- `classify` - Single headline classification
- `classify_batch` - Batch headline processing
- `routine_operations` - Multi-ticker routine operations
- `company_relevance` - Company relevance check
- `company_relevance_batch` - Batch company relevance
- `detect_quantitative_catalyst` - Quantitative catalyst detection
- `detect_strategic_catalyst` - Strategic catalyst detection

See `docs/RUNPOD_DEPLOYMENT.md` for API reference, cost optimization, and troubleshooting.

## Integration Patterns

When working across the ecosystem:
- Integrate directly into existing files rather than creating parallel systems
- Maintain consistency with other benz services
- Use shared documentation via `shared_docs/` symlink
- Follow patterns documented in `.claude/PATTERNS.md`

## Task Tracking with Beads

This repository uses the Beads task management system (MCP server) for tracking issues, features, and bugs.

**Basic Commands**:
- `mcp__beads__list` - List all issues with optional filters
- `mcp__beads__create` - Create new tasks, bugs, or features
- `mcp__beads__show` - View detailed issue information
- `mcp__beads__update` - Update issue status or details
- `mcp__beads__ready` - Find tasks ready to work on

**Workflow**:
1. Create issues for new work: `create(title="...", issue_type="task|bug|feature")`
2. Find ready work: `ready()` - shows tasks with no blockers
3. Claim work: `update(issue_id="...", status="in_progress")`
4. Complete work: `close(issue_id="...", reason="Completed")`

See `.beads/` directory for task database. All MCP functions use `workspace_root` parameter (auto-set to repository root).

## Slash Commands

Available via `.claude/commands/` (symlinked from benz_mgmt):
- `/spec` - Create feature specifications
- `/bug` - TDD bug fixing workflow
- `/implement-phase` - Execute implementation phases
- `/fix-tests` - Run and fix failing tests

## Implemented Features

### Core Classification
- **Model**: `MoritzLaurer/deberta-v3-large-zeroshot-v2.0` (DeBERTa-v3-large fine-tuned for multi-dataset NLI)
- **Parameters**: ~400M (6x larger than DistilBERT, superior financial text understanding)
- **Method**: Zero-shot classification with carefully designed candidate labels
- **Performance**: ~4-5s single headline (CPU-only, accuracy tradeoff from ~1s DistilBERT)
- **Memory**: ~1.5GB (increased from ~250MB)
- **Startup**: 5.9s model load (increased from ~1s)
- **Thresholds**: 0.6 for opinion/news, 0.5 for company relevance, 0.85 for quantitative catalyst presence

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

### Catalyst Detection

4. **Quantitative Catalyst Detection** (via `/detect-quantitative-catalyst` endpoint):
   - MNLI-based presence detection (PRESENCE_THRESHOLD: 0.85) + regex value extraction
   - Returns `has_quantitative_catalyst`, `catalyst_type`, `catalyst_values`, `confidence`
   - Types: dividend, acquisition, buyback, earnings, guidance
   - Extracts dollar amounts, percentages, and per-share values
   - Distinguishes divestiture/sell from acquisition, financing from dividend/buyback
   - Performance: ~4-5s for single headline

5. **Strategic Catalyst Detection** (via `/detect-strategic-catalyst` endpoint):
   - MNLI-based presence detection and type classification
   - Returns `has_strategic_catalyst`, `catalyst_subtype`, `confidence`
   - Types: executive_changes, m&a, partnership, product_launch, corporate_restructuring, clinical_trial
   - Examples:
     - Executive change: "X4 Pharmaceuticals CEO and CFO Step Down" → executive_changes (0.94 confidence)
     - Merger: "Workhorse Group And ATW Partners Announce Merger Agreement" → m&a (0.88 confidence)
     - Product launch: "SMX Partners with UN to Launch Global Product Platform" → product_launch (0.82 confidence)
   - Performance: ~4-5s for single headline
   - Accuracy: 90%+ on 11 real-world test cases with improved disambiguation
   - Shares MNLI pipeline with other detectors for efficiency

## API Design

Service provides classification endpoints for:
- Single headline classification (`/classify`)
- Batch headline processing (`/classify/batch`)
- Company relevance check (`/company-relevance`, `/company-relevance/batch`)
- Routine operations analysis (`/routine-operations`)
- Quantitative catalyst detection (`/detect-quantitative-catalyst`)
- Strategic catalyst detection (`/detect-strategic-catalyst`)
- Health check endpoint (`/health`)

**Request Parameters** (`/classify`, `/classify/batch`):
- `headline` (required): Headline text to classify
- `company` (optional): Company name for relevance detection
- `company_symbol` (optional): Ticker symbol for routine operations filter

**Response Fields** (`/classify`):
- Core: `is_opinion`, `is_straight_news`, `temporal_category`, `scores`
- Company relevance: `is_about_company`, `company_score`, `company`
- Far-future: `far_future_forecast`, `forecast_timeframe`
- Routine operations: `routine_operation`, `routine_confidence`, `routine_metadata`

**Request/Response** (`/detect-strategic-catalyst`):
- Request: `{"headline": "Company appoints new CEO"}`
- Response: `{"headline": "...", "has_strategic_catalyst": true, "catalyst_subtype": "executive_changes", "confidence": 0.89}`

**Request/Response** (`/detect-quantitative-catalyst`):
- Request: `{"headline": "Company announces $1 dividend"}`
- Response: `{"headline": "...", "has_quantitative_catalyst": true, "catalyst_type": "dividend", "catalyst_values": ["$1"], "confidence": 0.87}`

Returns both boolean classifications and raw scores for transparency.
All optional fields use Pydantic `exclude_none=True` for backward compatibility.

## Team Member Role (benz_orchestrator)

This repo participates in the benz_orchestrator multi-agent optimization team as the **Sent Filter Team**.

**Brief**: Read your full role brief at `../benz_orchestrator/agents/sent-filter-team-brief.md`

**Communication Protocol**:
- Check for tasks: `../benz_orchestrator/comms/tasks/sent-filter/`
- Write results: `../benz_orchestrator/comms/results/sent-filter/`
- Join discussions: `../benz_orchestrator/comms/discussions/`

**After ANY change**: Run `make test`, then restart your server (`make serve`).
Report the git commit SHA and test results in your result file.

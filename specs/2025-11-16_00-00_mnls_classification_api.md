# Specification: MNLS-based Article Title Classification API

**Created**: 2025-11-16
**Status**: Draft
**Author**: System

## 1. Overview & Objectives

### Problem Statement
The benz ecosystem requires a service to classify news article headlines along two dimensions:
1. **Opinion vs News**: Distinguish between opinionated editorial content and straight factual news
2. **Temporal Category**: Classify content as relating to past events, future events, or general topics

This classification must run on CPU without custom training, using open-source models via zero-shot natural language inference (NLI).

### Goals
- Provide REST API endpoints for single and batch headline classification
- Return both boolean classifications and raw probability scores
- Achieve sub-second response times for single headlines on CPU
- Support integration with existing benz services
- Enable transparency through score exposure for tuning and debugging

### Success Criteria
- API endpoints return correct classification structure
- Classifications align with expected behavior on test fixtures
- Service starts in under 30 seconds with eager model loading
- All tests pass with >90% coverage
- Service follows benz ecosystem patterns

## 2. Current State Analysis

### What Exists
- FastAPI skeleton with health check endpoint at `/health`
- Package structure with empty modules: `api/`, `models/`, `services/`, `config/`
- Entry point configured to start uvicorn on port 8002
- Test fixtures prepared with example headlines (opinion, news, past, future, general)
- Standard dependencies: FastAPI, Pydantic, uvicorn, pytest

### What's Needed
- ML dependencies: `transformers`, `torch`
- Configuration management for model settings and thresholds
- Pydantic models for requests and responses
- Classification service using zero-shot NLI pipeline
- API endpoints for classification operations
- Comprehensive test coverage
- Error handling for model failures

### Gaps
1. No ML dependencies in pyproject.toml
2. No configuration settings defined
3. No data models for classification I/O
4. No classification logic implementation
5. No classification endpoints
6. Limited test coverage (only health endpoint)

## 3. Architecture Design

### Model Selection
- **NLI Model**: `typeform/distilbert-base-uncased-mnli`
- **Rationale**: Smaller model (~66M parameters) optimized for CPU inference while maintaining good accuracy
- **Loading Strategy**: Eager loading at server startup to minimize first-request latency
- **Cache Strategy**: Use transformers default cache, configured via environment variables

### Classification Approach
The service uses zero-shot classification with carefully designed candidate labels:

**Opinion/News Dimension**:
- Label 1: "This is an opinion piece or editorial"
- Label 2: "This is a factual news report"
- Output: `is_opinion` (score ≥ 0.6 for Label 1), `is_straight_news` (score ≥ 0.6 for Label 2)

**Temporal Dimension**:
- Label 1: "This is about a past event that already happened"
- Label 2: "This is about a future event or forecast"
- Label 3: "This is a general topic or analysis"
- Output: Highest scoring label becomes `temporal_category`, individual scores exposed

**Threshold Strategy**:
- Use 0.6 threshold for boolean conversion (higher confidence)
- Always return raw scores for transparency and tuning
- Allow edge cases where both or neither opinion/news flags are true

### API Design

**Endpoint 1: Single Classification**
- Method: POST
- Path: `/classify`
- Input: Single headline string
- Output: Classification result with booleans and scores

**Endpoint 2: Batch Classification**
- Method: POST
- Path: `/classify/batch`
- Input: Array of headlines
- Output: Array of classification results

**Error Handling**:
- Model load failures return 503 Service Unavailable
- Invalid input returns 422 Unprocessable Entity
- Classification errors return 500 Internal Server Error with details

### Configuration Management
Use simple constants in config module for ML settings only:
- Model name: `typeform/distilbert-base-uncased-mnli` (constant)
- Classification threshold: 0.6 (constant)
- Transformers cache: Use transformers default
- Server settings: Managed by uvicorn CLI or environment variables (not in config module)

### Data Flow
1. Client sends POST request with headline(s)
2. FastAPI validates input using Pydantic models
3. Classification service runs zero-shot inference
4. Service converts scores to booleans using threshold
5. Response returns structured classification with all data
6. Client receives JSON with boolean flags, scores, and temporal category

## 4. Implementation Phases

### Phase 1: Dependencies & Configuration

**Description**: Add ML dependencies and create configuration module to prepare environment for classification service.

**Core Functionality**:
- Add transformers and torch to project dependencies
- Create simple settings module with constants

**Implementation Approach**:
- Modify `pyproject.toml` to add `transformers>=4.35.0` and `torch>=2.0.0` to dependencies
- Create `src/benz_sent_filter/config/settings.py` with ML configuration constants
- Define constants: MODEL_NAME, CLASSIFICATION_THRESHOLD
- Export constants for import by other modules

**Unit Test Requirements**:
- Create `tests/test_config.py`
- Test configuration values are accessible
- Test constants have expected types

**Acceptance Criteria**:
- [ ] Dependencies added to pyproject.toml
- [ ] Constants defined in config module
- [ ] Configuration tests pass

### Phase 2: Data Models

**Description**: Define Pydantic models for API request/response schemas to ensure type safety and validation.

**Core Functionality**:
- Request models for single and batch classification
- Response models with scores and boolean fields
- Temporal category enumeration
- Input validation (non-empty headlines)

**Implementation Approach**:
- Create models in `src/benz_sent_filter/models/classification.py`
- Define `TemporalCategory` enum with values: PAST_EVENT, FUTURE_EVENT, GENERAL_TOPIC
- Define `ClassifyRequest` with single headline field (str, min_length=1)
- Define `BatchClassifyRequest` with headlines field (list of str, min_items=1)
- Define `ClassificationScores` with fields: opinion_score, news_score, past_score, future_score, general_score (all float)
- Define `ClassificationResult` with fields: is_opinion, is_straight_news (bool), temporal_category (enum), scores (ClassificationScores), headline (str)
- Define `BatchClassificationResult` with results field (list of ClassificationResult)
- Export all models from `src/benz_sent_filter/models/__init__.py`

**Unit Test Requirements**:
- Create `tests/test_models.py`
- Test valid single request validates successfully
- Test valid batch request validates successfully
- Test empty headline is rejected
- Test temporal category enum has all three values

**Acceptance Criteria**:
- [ ] All Pydantic models created with proper validation
- [ ] Models handle empty headline validation
- [ ] TemporalCategory enum defined with three values
- [ ] Models export cleanly from models module
- [ ] All model tests pass

### Phase 3: Classification Service Core

**Description**: Implement the classification service that loads the NLI model and performs zero-shot inference on headlines.

**Core Functionality**:
- Load DistilBERT-MNLI model at initialization
- Run zero-shot classification with predefined candidate labels
- Convert model outputs to structured scores
- Apply threshold to generate boolean flags
- Determine temporal category from highest-scoring temporal label

**Implementation Approach**:
- Create `src/benz_sent_filter/services/classifier.py`
- Define `ClassificationService` class with model loading in `__init__`
- Use transformers `pipeline("zero-shot-classification")` with model from settings
- Define class-level constants for candidate labels (opinion/news and temporal)
- Implement public `classify_headline(headline)` method that:
  - Calls transformers pipeline with candidate labels
  - Extracts scores from pipeline result
  - Applies 0.6 threshold to generate boolean flags
  - Determines temporal category from highest score
  - Returns ClassificationResult
- Implement public `classify_batch(headlines)` method that loops over headlines
- Add error handling for model load failures and inference errors
- Export service from `src/benz_sent_filter/services/__init__.py`

**Unit Test Requirements**:
- Create `tests/test_classifier.py`
- Use pytest fixtures from `conftest.py` (sample headlines)
- Mock transformers pipeline to avoid loading real model in tests
- Test service initialization succeeds
- Test classify_headline returns ClassificationResult with all fields
- Test opinion headline gets is_opinion=True (using mocked high score)
- Test news headline gets is_straight_news=True
- Test past event gets temporal_category=PAST_EVENT
- Test future event gets temporal_category=FUTURE_EVENT
- Test general topic gets temporal_category=GENERAL_TOPIC
- Test threshold logic: score 0.59 → False, score 0.60 → True
- Test batch classification returns correct number of results
- Test error handling when model fails to load
- Test error handling when inference fails

**Acceptance Criteria**:
- [ ] ClassificationService loads model successfully
- [ ] Single headline classification works end-to-end
- [ ] Batch classification works for multiple headlines
- [ ] Boolean flags correctly reflect threshold application
- [ ] Temporal category determined from highest score
- [ ] All service tests pass with mocked pipeline
- [ ] Error handling prevents crashes on failures

### Phase 4: API Endpoints

**Description**: Create FastAPI endpoints for single and batch classification, integrating the classification service.

**Core Functionality**:
- Initialize classification service at application startup
- Expose POST /classify endpoint for single headlines
- Expose POST /classify/batch endpoint for multiple headlines
- Return appropriate HTTP status codes and error messages
- Maintain existing /health endpoint

**Implementation Approach**:
- Modify `src/benz_sent_filter/api/app.py`
- Add application state to store ClassificationService instance
- Create startup event handler that initializes service (eager loading)
- Define POST /classify route that accepts ClassifyRequest and returns ClassificationResult
- Define POST /classify/batch route that accepts BatchClassifyRequest and returns BatchClassificationResult
- Add exception handlers for model failures (503), validation errors (422), and runtime errors (500)
- Keep existing health endpoint unchanged
- Update `src/benz_sent_filter/api/__init__.py` to export app

**Unit Test Requirements**:
- Update `tests/test_api.py` with new endpoint tests
- Use FastAPI TestClient for all endpoint tests
- Mock ClassificationService to avoid model loading
- Test POST /classify with valid opinion headline returns correct structure
- Test POST /classify with valid news headline returns expected flags
- Test POST /classify/batch with multiple headlines returns array
- Test empty headline returns 422 validation error
- Test headline too long returns 422 validation error
- Test batch exceeding max items returns 422
- Test health endpoint still works (existing test)
- Test startup event initializes service
- Verify response schemas match Pydantic models

**Acceptance Criteria**:
- [ ] Service initializes on startup
- [ ] POST /classify endpoint works with single headline
- [ ] POST /classify/batch endpoint works with multiple headlines
- [ ] Validation errors return 422 with details
- [ ] Responses match defined schemas
- [ ] Health endpoint remains functional
- [ ] All API tests pass

### Phase 5: Integration Testing & Error Handling

**Description**: Add integration tests with real model and comprehensive error handling scenarios.

**Core Functionality**:
- Test actual model loading and inference (not mocked)
- Verify classification accuracy on known test cases
- Test error scenarios end-to-end

**Implementation Approach**:
- Create `integration/test_classification_integration.py`
- Load actual DistilBERT-MNLI model for integration tests
- Mark integration tests with pytest marker for optional execution
- Test classification on all fixture headlines from conftest.py
- Verify opinion headline scores opinion > 0.5
- Verify news headline scores news > 0.5
- Verify temporal categories match expectations
- Update README with instructions for running integration tests

**Unit Test Requirements**:
- All integration tests should be marked with `@pytest.mark.integration`
- Test real model loads successfully
- Test inference produces valid scores (0-1 range)
- Test opinion detection on "Why the Fed Is Wrong About Inflation"
- Test news detection on "Fed Raises Interest Rates by 25 Basis Points"
- Test past event detection on "Tesla Shares Surge After Yesterday's Earnings Beat"
- Test future event detection on "Tesla to Report Q4 Earnings Next Week"
- Test general topic detection on "How Tesla Changed the EV Market"
- Test batch processing maintains individual accuracy

**Acceptance Criteria**:
- [ ] Integration test suite created
- [ ] Real model loads and runs successfully
- [ ] Test fixtures produce expected classifications
- [ ] Integration tests pass when run with real model
- [ ] Documentation updated with integration test instructions

### Phase 6: Documentation & Examples

**Description**: Update documentation with API usage examples, deployment instructions, and architectural details.

**Core Functionality**:
- Document API endpoints with request/response examples
- Provide curl command examples
- Explain classification logic

**Implementation Approach**:
- Update README.md with basic usage section
- Add API endpoint documentation with JSON examples
- Include example curl commands for /classify and /classify/batch
- Add section explaining candidate labels and scoring logic
- Include example responses showing all fields

**Unit Test Requirements**:
- No new tests required for documentation phase

**Acceptance Criteria**:
- [ ] README updated with basic API documentation
- [ ] Example requests/responses included
- [ ] Curl commands provided
- [ ] Classification logic explained

## 5. Technical Decisions & Rationale

### Model Selection: DistilBERT-MNLI
**Decision**: Use `typeform/distilbert-base-uncased-mnli` instead of `facebook/bart-large-mnli`
**Rationale**:
- 6x smaller (66M vs 400M parameters)
- Faster CPU inference (critical for responsiveness)
- Sufficient accuracy for headline-length text
- Well-maintained and widely used

### Threshold: 0.6
**Decision**: Use 0.6 confidence threshold for boolean conversion
**Rationale**:
- Higher confidence reduces false positives
- Allows "uncertain" cases where both/neither flags are true
- Can be tuned via environment variable without code changes
- Exposes raw scores for manual review of edge cases

### Eager Loading
**Decision**: Load model at startup rather than on first request
**Rationale**:
- Predictable startup time (acceptable for service initialization)
- First request latency is critical for user experience
- Simpler error handling (fail fast on startup)
- Easier to monitor and debug initialization issues

### Single Pipeline Call
**Decision**: Run one zero-shot call with all labels rather than separate calls
**Rationale**:
- Reduces inference overhead
- Model sees all labels simultaneously for better comparison
- Simpler code with fewer API calls
- Faster overall classification

### Separate Endpoints
**Decision**: Provide /classify and /classify/batch instead of single smart endpoint
**Rationale**:
- Clearer API contracts
- Type-safe request validation
- Easier client-side usage
- Standard RESTful pattern
- Allows future optimization of batch processing

## 6. Future Enhancements (Out of Scope)

- Fine-tuning on labeled financial news headlines
- Multi-language support for non-English headlines
- Confidence calibration based on production data
- Caching layer for frequently classified headlines
- Async batch processing for large volumes
- Additional dimensions (bullish/bearish sentiment, sector relevance)
- GPU support for higher throughput
- Model versioning and A/B testing infrastructure

## 7. Dependencies & Risks

### Dependencies
- External: Hugging Face model repository availability
- Internal: None (first benz service with ML)

### Risks
1. **Model Download**: First startup requires downloading ~250MB model
   - Mitigation: Document cache configuration, consider pre-loading in deployment
2. **CPU Performance**: Inference may be slower than expected
   - Mitigation: Chose DistilBERT for speed, can optimize batch processing
3. **Classification Accuracy**: Zero-shot may not match fine-tuned models
   - Mitigation: Expose scores for validation, can iterate on label design
4. **Memory Usage**: Model requires ~500MB RAM
   - Mitigation: Document requirements, acceptable for dedicated service

## 8. Success Metrics

### Functional Metrics
- API endpoints return valid responses
- Classification structure matches specification
- All tests pass (unit + integration)

### Performance Metrics
- Single headline classification: <2 seconds on CPU
- Batch of 10 headlines: <10 seconds on CPU
- Service startup: <30 seconds with model loading
- Memory footprint: <1GB

### Quality Metrics
- Test coverage: >90%
- Classification consistency: Same headline → same result
- Error rate: <1% on valid inputs

---

**End of Specification**

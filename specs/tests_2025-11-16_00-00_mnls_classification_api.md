# Test Specification: MNLS-based Article Title Classification API

**Created**: 2025-11-16
**Spec File**: specs/2025-11-16_00-00_mnls_classification_api.md
**Purpose**: Comprehensive test guide for TDD implementation of all specification phases

## Testing Strategy

All tests follow these principles:
- Use pytest fixtures from `conftest.py` for sample headlines
- Mock external dependencies (transformers pipeline) in unit tests
- Test real model only in integration tests (marked with `@pytest.mark.integration`)
- Verify both happy paths and error conditions
- Ensure >90% code coverage

## Phase 1: Dependencies & Configuration - Test Guide

**New Tests to Create:**

### tests/test_config.py

1. `test_model_name_constant_exists`
   - **Input**: Import settings module
   - **Expected**: MODEL_NAME constant is accessible and is a string
   - **Covers**: Configuration constants defined

2. `test_classification_threshold_constant`
   - **Input**: Import settings module
   - **Expected**: CLASSIFICATION_THRESHOLD equals 0.6
   - **Covers**: Threshold configuration

3. `test_model_name_value`
   - **Input**: Check MODEL_NAME value
   - **Expected**: Equals "typeform/distilbert-base-uncased-mnli"
   - **Covers**: Correct model specified

**Test Implementation Notes:**
- No mocks needed - simple constant access tests
- Verify types (str, float, int) match expectations
- Check exact values match specification

## Phase 2: Data Models - Test Guide

**New Tests to Create:**

### tests/test_models.py

1. `test_temporal_category_enum_values`
   - **Input**: Access TemporalCategory enum
   - **Expected**: Has PAST_EVENT, FUTURE_EVENT, GENERAL_TOPIC values
   - **Covers**: Temporal category enumeration

2. `test_classify_request_valid_headline`
   - **Input**: ClassifyRequest(headline="Valid headline text")
   - **Expected**: Model validates successfully
   - **Covers**: Valid single request

3. `test_classify_request_empty_headline_rejected`
   - **Input**: ClassifyRequest(headline="")
   - **Expected**: ValidationError raised (min_length=1)
   - **Covers**: Empty headline validation

4. `test_batch_classify_request_valid`
   - **Input**: BatchClassifyRequest(headlines=["headline1", "headline2"])
   - **Expected**: Model validates successfully
   - **Covers**: Valid batch request

5. `test_batch_classify_request_empty_list_rejected`
   - **Input**: BatchClassifyRequest(headlines=[])
   - **Expected**: ValidationError raised (min_items=1)
   - **Covers**: Empty batch validation

6. `test_classification_scores_all_fields`
   - **Input**: ClassificationScores(opinion_score=0.8, news_score=0.2, past_score=0.1, future_score=0.7, general_score=0.2)
   - **Expected**: All fields accessible and correct type (float)
   - **Covers**: Score structure

7. `test_classification_result_structure`
   - **Input**: ClassificationResult with all fields populated
   - **Expected**: Has is_opinion, is_straight_news (bool), temporal_category (enum), scores, headline fields
   - **Covers**: Complete result structure

8. `test_batch_classification_result_structure`
   - **Input**: BatchClassificationResult(results=[result1, result2])
   - **Expected**: Contains list of ClassificationResult objects
   - **Covers**: Batch response structure

**Test Implementation Notes:**
- Use pytest.raises for validation error tests
- Verify Pydantic validation messages are helpful
- Test edge cases (very long headlines, special characters)

## Phase 3: Classification Service Core - Test Guide

**New Tests to Create:**

### tests/test_classifier.py

1. `test_service_initialization_success`
   - **Input**: Mock transformers.pipeline, create ClassificationService()
   - **Expected**: Service initializes without errors, pipeline called with correct model
   - **Covers**: Service initialization

2. `test_service_initialization_model_load_failure`
   - **Input**: Mock pipeline to raise exception
   - **Expected**: Service raises appropriate error on init
   - **Covers**: Model load error handling

3. `test_classify_headline_opinion_detection`
   - **Input**: Mock pipeline to return high opinion score (0.75), classify opinion headline
   - **Expected**: ClassificationResult with is_opinion=True, opinion_score=0.75
   - **Covers**: Opinion classification

4. `test_classify_headline_news_detection`
   - **Input**: Mock pipeline to return high news score (0.85), classify news headline
   - **Expected**: ClassificationResult with is_straight_news=True, news_score=0.85
   - **Covers**: News classification

5. `test_classify_headline_threshold_boundary_below`
   - **Input**: Mock pipeline to return score of 0.59 for opinion
   - **Expected**: is_opinion=False (below 0.6 threshold)
   - **Covers**: Threshold logic - below

6. `test_classify_headline_threshold_boundary_at`
   - **Input**: Mock pipeline to return score of 0.60 for opinion
   - **Expected**: is_opinion=True (at threshold)
   - **Covers**: Threshold logic - at boundary

7. `test_classify_headline_past_event_temporal`
   - **Input**: Mock pipeline to return highest score for past label (0.8)
   - **Expected**: temporal_category=TemporalCategory.PAST_EVENT
   - **Covers**: Past event detection

8. `test_classify_headline_future_event_temporal`
   - **Input**: Mock pipeline to return highest score for future label (0.75)
   - **Expected**: temporal_category=TemporalCategory.FUTURE_EVENT
   - **Covers**: Future event detection

9. `test_classify_headline_general_topic_temporal`
   - **Input**: Mock pipeline to return highest score for general label (0.7)
   - **Expected**: temporal_category=TemporalCategory.GENERAL_TOPIC
   - **Covers**: General topic detection

10. `test_classify_headline_all_scores_present`
    - **Input**: Classify any headline with mocked scores
    - **Expected**: Result.scores contains all 5 score fields (opinion, news, past, future, general)
    - **Covers**: Complete score exposure

11. `test_classify_headline_original_headline_preserved`
    - **Input**: Classify "Test Headline Text"
    - **Expected**: Result.headline equals "Test Headline Text"
    - **Covers**: Headline preservation in result

12. `test_classify_batch_multiple_headlines`
    - **Input**: classify_batch(["headline1", "headline2", "headline3"])
    - **Expected**: Returns 3 ClassificationResult objects
    - **Covers**: Batch processing

13. `test_classify_batch_maintains_order`
    - **Input**: Batch with distinct headlines
    - **Expected**: Results match input order (result[i].headline == input[i])
    - **Covers**: Batch ordering

14. `test_classify_headline_inference_error`
    - **Input**: Mock pipeline to raise exception during inference
    - **Expected**: Service raises appropriate error with context
    - **Covers**: Inference error handling

**Test Implementation Notes:**
- Mock `transformers.pipeline` using pytest monkeypatch or unittest.mock
- Mock pipeline return format: `{"labels": [...], "scores": [...]}`
- Create helper fixture for mocked pipeline with configurable scores
- Test both opinion/news dimension and temporal dimension in each test
- Verify candidate labels match specification

**Required Mocks:**
```python
@pytest.fixture
def mock_pipeline(monkeypatch):
    """Mock transformers pipeline with configurable scores."""
    def _mock_pipeline(task, model):
        def pipeline_fn(text, candidate_labels):
            # Return configurable mock scores
            return {"labels": candidate_labels, "scores": [0.7, 0.3, ...]}
        return pipeline_fn
    monkeypatch.setattr("transformers.pipeline", _mock_pipeline)
```

## Phase 4: API Endpoints - Test Guide

**Existing Tests to Modify:**
- `test_health_check` in `tests/test_api.py`
  - Current behavior: Tests /health endpoint returns status
  - Required changes: No changes needed - should still pass

**New Tests to Create:**

### tests/test_api.py (additions)

1. `test_startup_event_initializes_service`
   - **Input**: Start TestClient (triggers startup event)
   - **Expected**: app.state.classifier exists and is ClassificationService instance
   - **Covers**: Startup event handler

2. `test_classify_endpoint_valid_opinion_headline`
   - **Input**: POST /classify with {"headline": "Why the Fed Is Wrong About Inflation"}
   - **Expected**: 200 status, response matches ClassificationResult schema, is_opinion=True
   - **Covers**: Single classification endpoint - opinion

3. `test_classify_endpoint_valid_news_headline`
   - **Input**: POST /classify with {"headline": "Fed Raises Interest Rates by 25 Basis Points"}
   - **Expected**: 200 status, is_straight_news=True
   - **Covers**: Single classification endpoint - news

4. `test_classify_endpoint_empty_headline_validation_error`
   - **Input**: POST /classify with {"headline": ""}
   - **Expected**: 422 status, validation error details
   - **Covers**: Empty headline validation

5. `test_classify_endpoint_missing_headline_field`
   - **Input**: POST /classify with {}
   - **Expected**: 422 status, missing field error
   - **Covers**: Required field validation

6. `test_classify_batch_endpoint_multiple_headlines`
   - **Input**: POST /classify/batch with {"headlines": ["headline1", "headline2"]}
   - **Expected**: 200 status, results array with 2 items
   - **Covers**: Batch endpoint

7. `test_classify_batch_endpoint_empty_list_validation_error`
   - **Input**: POST /classify/batch with {"headlines": []}
   - **Expected**: 422 status, min_items validation error
   - **Covers**: Batch validation

8. `test_classify_batch_endpoint_response_structure`
   - **Input**: POST /classify/batch with valid headlines
   - **Expected**: Response has "results" field containing array of classification results
   - **Covers**: Batch response schema

9. `test_classify_endpoint_response_includes_all_scores`
   - **Input**: POST /classify with any headline
   - **Expected**: Response.scores contains opinion_score, news_score, past_score, future_score, general_score
   - **Covers**: Score transparency

10. `test_classify_endpoint_response_includes_temporal_category`
    - **Input**: POST /classify with any headline
    - **Expected**: Response has temporal_category field with valid enum value
    - **Covers**: Temporal category in response

**Test Implementation Notes:**
- Mock ClassificationService at app startup to avoid model loading
- Use FastAPI TestClient for all endpoint tests
- Verify exact response schema matches Pydantic models
- Test both successful and error responses
- Check HTTP status codes match specification

**Required Mocks:**
```python
@pytest.fixture
def client_with_mocked_service(monkeypatch):
    """Create test client with mocked classification service."""
    mock_service = Mock(spec=ClassificationService)
    mock_service.classify_headline.return_value = ClassificationResult(...)

    def mock_init(self):
        self.classifier = mock_service

    monkeypatch.setattr("benz_sent_filter.api.app.startup_event", mock_init)
    return TestClient(app)
```

## Phase 5: Integration Testing & Error Handling - Test Guide

**New Tests to Create:**

### integration/test_classification_integration.py

1. `test_real_model_loads_successfully`
   - **Input**: Create ClassificationService() with real transformers
   - **Expected**: Service initializes, model downloads/loads without errors
   - **Covers**: Real model loading
   - **Marker**: `@pytest.mark.integration`

2. `test_real_inference_produces_valid_scores`
   - **Input**: Classify any headline with real model
   - **Expected**: All scores in range [0, 1]
   - **Covers**: Valid score ranges
   - **Marker**: `@pytest.mark.integration`

3. `test_opinion_headline_detection_real_model`
   - **Input**: "Why the Fed Is Wrong About Inflation" (fixture: sample_headline_opinion)
   - **Expected**: opinion_score > 0.5 (model actually detects opinion)
   - **Covers**: Real opinion detection
   - **Marker**: `@pytest.mark.integration`

4. `test_news_headline_detection_real_model`
   - **Input**: "Fed Raises Interest Rates by 25 Basis Points" (fixture: sample_headline_news)
   - **Expected**: news_score > 0.5
   - **Covers**: Real news detection
   - **Marker**: `@pytest.mark.integration`

5. `test_past_event_temporal_classification_real_model`
   - **Input**: "Tesla Shares Surge After Yesterday's Earnings Beat" (fixture: sample_headline_past)
   - **Expected**: temporal_category == TemporalCategory.PAST_EVENT
   - **Covers**: Real past event detection
   - **Marker**: `@pytest.mark.integration`

6. `test_future_event_temporal_classification_real_model`
   - **Input**: "Tesla to Report Q4 Earnings Next Week" (fixture: sample_headline_future)
   - **Expected**: temporal_category == TemporalCategory.FUTURE_EVENT
   - **Covers**: Real future event detection
   - **Marker**: `@pytest.mark.integration`

7. `test_general_topic_temporal_classification_real_model`
   - **Input**: "How Tesla Changed the EV Market" (fixture: sample_headline_general)
   - **Expected**: temporal_category == TemporalCategory.GENERAL_TOPIC
   - **Covers**: Real general topic detection
   - **Marker**: `@pytest.mark.integration`

8. `test_batch_processing_maintains_accuracy_real_model`
   - **Input**: Batch with all 5 fixture headlines
   - **Expected**: Each result matches expected category (same as individual tests)
   - **Covers**: Batch accuracy
   - **Marker**: `@pytest.mark.integration`

9. `test_classification_consistency_real_model`
   - **Input**: Same headline classified twice
   - **Expected**: Identical scores and categories both times
   - **Covers**: Consistency/reproducibility
   - **Marker**: `@pytest.mark.integration`

10. `test_response_time_single_headline_real_model`
    - **Input**: Classify one headline, measure time
    - **Expected**: Response time < 2 seconds
    - **Covers**: Performance metric
    - **Marker**: `@pytest.mark.integration`

11. `test_response_time_batch_10_headlines_real_model`
    - **Input**: Classify batch of 10 headlines, measure time
    - **Expected**: Response time < 10 seconds
    - **Covers**: Batch performance metric
    - **Marker**: `@pytest.mark.integration`

**Test Implementation Notes:**
- All tests use `@pytest.mark.integration` decorator
- Tests download real model on first run (cache for subsequent runs)
- Run with: `pytest -m integration`
- Skip in CI/fast test runs: `pytest -m "not integration"`
- Allow reasonable variance in scores (opinion_score > 0.5, not exact value)
- Document expected first-run model download in test docstrings

**Required Setup:**
```python
# integration/conftest.py
import pytest

@pytest.fixture(scope="module")
def real_classifier():
    """Create real classification service (shared across integration tests)."""
    from benz_sent_filter.services.classifier import ClassificationService
    return ClassificationService()
```

## Phase 6: Documentation & Examples - Test Guide

**No new tests required for documentation phase.**

**Verification Steps:**
- Review README for completeness
- Test curl commands in documentation manually
- Verify example responses match actual API output

---

## Test Execution Strategy

### Unit Tests (Phases 1-4)
```bash
# Run all unit tests with coverage
pytest tests/ --cov=src/benz_sent_filter --cov-report=term-missing

# Run specific phase tests
pytest tests/test_config.py          # Phase 1
pytest tests/test_models.py          # Phase 2
pytest tests/test_classifier.py      # Phase 3
pytest tests/test_api.py             # Phase 4
```

### Integration Tests (Phase 5)
```bash
# Run integration tests (requires model download)
pytest -m integration

# Skip integration tests for fast CI
pytest -m "not integration"

# Run with verbose output
pytest integration/ -v
```

### Coverage Target
- Overall coverage: >90%
- Per-module coverage: >85%
- Critical paths (classification logic): 100%

## Mock Strategy Summary

**Unit Tests Mock:**
- `transformers.pipeline` - avoid model loading
- `ClassificationService` - when testing API endpoints
- Return structured data matching transformers output format

**Integration Tests Use Real:**
- Actual DistilBERT-MNLI model
- Real transformers pipeline
- Actual inference on test fixtures

---

**End of Test Specification**

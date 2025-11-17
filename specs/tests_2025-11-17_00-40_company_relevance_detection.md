# Test Specification: Company Relevance Detection Extension

**Created**: 2025-11-17
**Specification**: specs/2025-11-17_00-40_company_relevance_detection.md
**Status**: Draft

## Overview

This document provides comprehensive test guides for all implementation phases of the company relevance detection feature. Tests follow TDD principles and integrate with existing test patterns in the codebase.

## Test Patterns & Fixtures

### Existing Test Patterns

The codebase uses:
- pytest for test framework
- `mock_transformers_pipeline` fixture for mocking NLI model
- Module cache clearing pattern for fresh imports
- `TestClient` from FastAPI for API testing
- Pydantic `ValidationError` for model validation testing

### Key Fixtures (from conftest.py)

- `mock_transformers_pipeline`: Returns mock function to simulate transformers pipeline
- `sample_headline_opinion`: Opinion headline fixture
- `sample_headline_news`: News headline fixture
- `sample_headline_past`: Past event headline fixture
- `sample_headline_future`: Future event headline fixture
- `sample_headline_general`: General topic headline fixture

---

## Phase 1: Extend Request/Response Models - Test Guide

### Existing Tests to Modify

**None** - Phase 1 adds new optional fields without breaking existing functionality. All existing model tests should continue to pass without modification.

### New Tests to Create

#### File: `tests/test_models.py`

1. `test_classify_request_with_company_parameter`
   - **Input**: `ClassifyRequest(headline="Test headline", company="Dell")`
   - **Expected**: Request validates successfully, `company` field equals "Dell"
   - **Covers**: Request models accept optional company parameter

2. `test_classify_request_without_company_parameter_defaults_none`
   - **Input**: `ClassifyRequest(headline="Test headline")`
   - **Expected**: Request validates successfully, `company` field is None
   - **Covers**: Backward compatibility maintained (None company works)

3. `test_classify_request_with_none_company_explicit`
   - **Input**: `ClassifyRequest(headline="Test headline", company=None)`
   - **Expected**: Request validates successfully, `company` field is None
   - **Covers**: Explicit None company parameter accepted

4. `test_classification_result_with_company_fields_present`
   - **Input**: Create `ClassificationResult` with all fields including `is_about_company=True`, `company_score=0.85`, `company="Dell"`
   - **Expected**: Result serializes correctly, company fields present in dict/JSON
   - **Covers**: Response models include optional company relevance fields

5. `test_classification_result_with_company_fields_none`
   - **Input**: Create `ClassificationResult` with company fields set to None
   - **Expected**: Result serializes correctly, company fields absent or None in dict/JSON
   - **Covers**: Response serializes correctly with company fields absent (None)

6. `test_classification_result_json_excludes_none_company_fields`
   - **Input**: Create `ClassificationResult` without company fields (defaults to None)
   - **Expected**: JSON serialization excludes company fields or sets them to null
   - **Covers**: JSON serialization includes/excludes fields appropriately

7. `test_batch_classify_request_with_company_parameter`
   - **Input**: `BatchClassifyRequest(headlines=["h1", "h2"], company="Tesla")`
   - **Expected**: Request validates successfully, `company` field equals "Tesla"
   - **Covers**: Batch request with company parameter

8. `test_batch_classify_request_without_company_defaults_none`
   - **Input**: `BatchClassifyRequest(headlines=["h1", "h2"])`
   - **Expected**: Request validates successfully, `company` field is None
   - **Covers**: Batch request backward compatibility

**Test Implementation Notes:**
- Use `model.model_dump()` or `model.model_dump_json()` to check serialization
- Verify Pydantic's `exclude_none` or `exclude_unset` behavior
- Test both dict and JSON serialization formats
- No mocking required - pure Pydantic model testing
- Follow same test patterns as existing model tests in lines 25-42 (`test_classify_request_*`) and 90-124 (`test_classification_result_*`)

---

## Phase 2: Add Company Relevance Service Logic - Test Guide

### Existing Tests to Modify

**None** - Existing classifier tests should continue to pass. New tests validate company relevance logic without modifying existing behavior.

### New Tests to Create

#### File: `tests/test_classifier.py`

1. `test_check_company_relevance_high_score_above_threshold`
   - **Input**: Mock pipeline to return score 0.85 for "This article is about Dell" hypothesis with headline "Dell Unveils AI Platform"
   - **Expected**: Method returns `CompanyRelevance(is_relevant=True, score=0.85)` - access via `result.is_relevant` and `result.score`
   - **Covers**: Company relevance returns structured namedtuple when score above threshold

2. `test_check_company_relevance_low_score_below_threshold`
   - **Input**: Mock pipeline to return score 0.15 for "This article is about Tesla" hypothesis with headline "Dell Unveils AI Platform"
   - **Expected**: Method returns `CompanyRelevance(is_relevant=False, score=0.15)` - access via named fields
   - **Covers**: Company relevance returns structured namedtuple when score below threshold

3. `test_check_company_relevance_threshold_boundary_at_point_five`
   - **Input**: Mock pipeline to return score 0.50 exactly
   - **Expected**: Method returns `CompanyRelevance(is_relevant=True, score=0.50)` - is_relevant=True because 0.50 >= `COMPANY_RELEVANCE_THRESHOLD`
   - **Covers**: Threshold logic correctly generates boolean flag using config constant

4. `test_check_company_relevance_threshold_boundary_below_point_five`
   - **Input**: Mock pipeline to return score 0.49
   - **Expected**: Method returns `CompanyRelevance(is_relevant=False, score=0.49)` - is_relevant=False because 0.49 < `COMPANY_RELEVANCE_THRESHOLD`
   - **Covers**: Threshold boundary testing with config constant

5. `test_check_company_relevance_uses_correct_hypothesis_template`
   - **Input**: Mock pipeline, call with company="NVIDIA"
   - **Expected**: Pipeline called with hypothesis "This article is about NVIDIA"
   - **Covers**: Method uses correct hypothesis template

6. `test_classify_headline_with_company_includes_relevance_fields`
   - **Input**: Mock pipeline for both existing classification and company relevance (score 0.85), call `classify_headline("Dell headline", company="Dell")`
   - **Expected**: Result includes `is_about_company=True`, `company_score=0.85`, `company="Dell"`, plus existing fields
   - **Covers**: Service detects company relevance using NLI pipeline, Integration with existing classification works

7. `test_classify_headline_with_none_company_excludes_relevance_fields`
   - **Input**: Mock pipeline for existing classification only, call `classify_headline("Dell headline", company=None)`
   - **Expected**: Result has `is_about_company=None`, `company_score=None`, `company=None`
   - **Covers**: None company handled gracefully, Service excludes company fields when company is None

8. `test_classify_batch_with_company_all_headlines`
   - **Input**: Mock pipeline, call `classify_batch(["h1", "h2", "h3"], company="Dell")`
   - **Expected**: Returns 3 results, each with company relevance fields populated
   - **Covers**: Batch endpoint handles company checks for all headlines

9. `test_classify_batch_with_none_company_no_relevance_checks`
    - **Input**: Mock pipeline, call `classify_batch(["h1", "h2"], company=None)`
    - **Expected**: Returns 2 results without company relevance fields
    - **Covers**: Batch processing backward compatibility

10. `test_classify_headline_existing_tests_still_pass`
    - **Input**: Run existing tests without company parameter
    - **Expected**: All existing tests pass without modification
    - **Covers**: No regression in existing functionality

**Test Implementation Notes:**
- Mock `self._pipeline` to return controlled scores (same mocking pattern as existing opinion/news tests)
- Use `mock_transformers_pipeline` fixture pattern from existing tests
- Clear module cache with `sys.modules` deletion before each test
- Mock should return dict with `scores` list matching hypothesis order (identical to existing classification tests)
- Test both single classification and batch processing
- Company relevance testing follows exact same patterns as existing `test_classify_headline_*` tests
- Test namedtuple field access using `.is_relevant` and `.score` attributes
- Verify None guard pattern: company relevance only called when `company is not None`

**Mocking Pattern:**
```python
mock_transformers_pipeline({
    "This is an opinion piece or editorial": 0.7,
    "This is a factual news report": 0.3,
    "This is about a past event that already happened": 0.2,
    "This is about a future event or forecast": 0.3,
    "This is a general topic or analysis": 0.5,
    "This article is about Dell": 0.85,  # Company relevance score
})
```

---

## Phase 3: Update API Endpoints - Test Guide

### Existing Tests to Modify

**None** - Existing API tests should continue to pass without modification. New tests validate company parameter acceptance.

### New Tests to Create

#### File: `tests/test_api.py`

1. `test_classify_endpoint_with_company_returns_relevance_fields`
   - **Input**: POST `/classify` with `{"headline": "Dell launches product", "company": "Dell"}`
   - **Expected**: 200 response with `is_about_company`, `company_score`, `company` fields present
   - **Covers**: API endpoints accept optional company parameter, Responses include company relevance when company provided

2. `test_classify_endpoint_without_company_omits_relevance_fields`
   - **Input**: POST `/classify` with `{"headline": "Dell launches product"}`
   - **Expected**: 200 response without company relevance fields (or fields are None/null)
   - **Covers**: Backward compatibility maintained for existing clients

3. `test_classify_endpoint_with_none_company_explicit`
   - **Input**: POST `/classify` with `{"headline": "Test", "company": null}`
   - **Expected**: 200 response, company fields are None
   - **Covers**: Explicit null company parameter handled

4. `test_classify_endpoint_with_company_response_schema_complete`
   - **Input**: POST `/classify` with company parameter
   - **Expected**: Response includes all existing fields plus `is_about_company` (bool), `company_score` (float), `company` (str)
   - **Covers**: Response schema matches updated Pydantic models

5. `test_classify_endpoint_with_company_and_empty_headline_validation_error`
   - **Input**: POST `/classify` with `{"headline": "", "company": "Dell"}`
   - **Expected**: 422 validation error (headline validation takes precedence)
   - **Covers**: Validation errors handled correctly

6. `test_classify_endpoint_company_field_type_validation`
   - **Input**: POST `/classify` with `{"headline": "Test", "company": 123}`
   - **Expected**: 422 validation error (company must be string or null)
   - **Covers**: Type validation for company parameter

7. `test_classify_batch_endpoint_with_company_all_results_include_relevance`
   - **Input**: POST `/classify/batch` with `{"headlines": ["h1", "h2"], "company": "Tesla"}`
   - **Expected**: 200 response, both results include company relevance fields
   - **Covers**: Batch endpoint accepts company parameter

8. `test_classify_batch_endpoint_without_company_backward_compatible`
   - **Input**: POST `/classify/batch` with `{"headlines": ["h1", "h2"]}`
   - **Expected**: 200 response, results do not include company fields
   - **Covers**: Batch endpoint backward compatibility

9. `test_classify_batch_endpoint_with_company_response_structure`
   - **Input**: POST `/classify/batch` with company parameter
   - **Expected**: Response has correct structure with `results` array, each item has company fields
   - **Covers**: Response structure validation

10. `test_health_endpoint_unaffected_by_company_feature`
    - **Input**: GET `/health`
    - **Expected**: 200 response with existing health check structure
    - **Covers**: Health endpoint unaffected

11. `test_existing_api_tests_still_pass`
    - **Input**: Run all existing API tests
    - **Expected**: All pass without modification
    - **Covers**: No regression in existing endpoints

**Test Implementation Notes:**
- Use `TestClient` fixture from existing tests
- Mock `mock_transformers_pipeline` to return company scores
- Test both presence and absence of optional company parameter
- Verify JSON response structure matches OpenAPI schema
- Test validation errors return 422 status code
- No need to modify existing test fixtures

**Client Usage Pattern:**
```python
response = client.post("/classify", json={
    "headline": "Dell Unveils AI Data Platform",
    "company": "Dell"
})
assert response.status_code == 200
data = response.json()
assert "is_about_company" in data
assert data["company"] == "Dell"
```

---

## Phase 4: Integration Testing & Validation - Test Guide

### Existing Tests to Modify

**None** - Integration tests are new and do not modify existing unit tests.

### New Tests to Create

#### File: `integration/test_classification_integration.py`

1. `test_company_relevance_positive_match_dell`
   - **Input**: Headline "Dell Unveils AI Data Platform Updates; Launches First 2U Server With NVIDIA Blackwell GPUs", company="Dell"
   - **Expected**: `is_about_company=True`, `company_score >= 0.5` (real model inference)
   - **Covers**: Dell headline correctly identifies Dell relevance
   - **Marker**: `@pytest.mark.integration`

2. `test_company_relevance_negative_match_tesla`
   - **Input**: Same Dell headline, company="Tesla"
   - **Expected**: `is_about_company=False`, `company_score < 0.5` (real model inference)
   - **Covers**: Dell headline correctly rejects Tesla relevance
   - **Marker**: `@pytest.mark.integration`

3. `test_company_relevance_multi_company_nvidia`
   - **Input**: Same Dell headline (mentions NVIDIA), company="NVIDIA"
   - **Expected**: `is_about_company=True`, `company_score >= 0.5`
   - **Covers**: Dell headline correctly identifies NVIDIA relevance (multi-company)
   - **Marker**: `@pytest.mark.integration`

4. `test_company_relevance_multi_company_unrelated`
   - **Input**: Same Dell headline, company="Apple"
   - **Expected**: `is_about_company=False`, `company_score < 0.5`
   - **Covers**: Edge cases handled correctly - unrelated company rejected
   - **Marker**: `@pytest.mark.integration`

5. `test_company_relevance_accuracy_threshold`
   - **Input**: Suite of 10 headlines with known company associations
   - **Expected**: Accuracy >= 80% across test set
   - **Covers**: Company relevance achieves >80% accuracy on test fixtures
   - **Marker**: `@pytest.mark.integration`

6. `test_company_relevance_performance_single_headline`
   - **Input**: Single headline with company parameter
   - **Expected**: Total response time < 3 seconds on CPU
   - **Covers**: Performance target met (<3s total for single headline with company)
   - **Marker**: `@pytest.mark.integration`

7. `test_company_relevance_performance_overhead`
   - **Input**: Same headline classified with and without company parameter
   - **Expected**: Company check adds < 500ms latency
   - **Covers**: Company check adds minimal latency (<500ms)
   - **Marker**: `@pytest.mark.integration`

8. `test_company_relevance_batch_processing_performance`
   - **Input**: Batch of 10 headlines with company parameter
   - **Expected**: Total processing time < 5 seconds
   - **Covers**: Performance target met for batch processing
   - **Marker**: `@pytest.mark.integration`

9. `test_company_name_variation_uppercase`
   - **Input**: Headline "DELL announces earnings", company="Dell"
   - **Expected**: Correctly identifies relevance despite case difference
   - **Covers**: Edge cases handled correctly - case variations
   - **Marker**: `@pytest.mark.integration`

10. `test_company_name_variation_full_name`
    - **Input**: Headline about "Dell Technologies", company="Dell"
    - **Expected**: Correctly identifies relevance despite name variation
    - **Covers**: Edge cases handled correctly - company name variations
    - **Marker**: `@pytest.mark.integration`

11. `test_existing_classification_dimensions_no_regression`
    - **Input**: Run tests for opinion/news and temporal classification with company parameter
    - **Expected**: Existing classification dimensions still accurate
    - **Covers**: No regression in existing classification dimensions
    - **Marker**: `@pytest.mark.integration`

**Test Implementation Notes:**
- Use real transformers model (no mocking) - real inference
- Mark all tests with `@pytest.mark.integration` for selective running
- Use inline test data (no separate fixtures file)
- Measure performance with `time` module or pytest timing
- Test fixtures inline in test functions or module-level constants
- May require model download on first run (acceptable for integration tests)
- Skip if model not available or on CI without model cache

**Test Data Structure:**
```python
TEST_HEADLINES = [
    {
        "headline": "Dell Unveils AI Data Platform Updates; Launches First 2U Server With NVIDIA Blackwell GPUs",
        "relevant_companies": ["Dell", "NVIDIA"],
        "irrelevant_companies": ["Tesla", "Apple", "Microsoft"],
    },
    # ... more test cases
]
```

**Performance Measurement Pattern:**
```python
import time
start = time.time()
result = service.classify_headline(headline, company=company)
elapsed = time.time() - start
assert elapsed < 3.0  # 3 second threshold
```

---

## Phase 5: Documentation & Examples - Test Guide

### Existing Tests to Modify

**None** - Documentation phase has minimal test requirements.

### New Tests to Create

#### File: `tests/test_documentation.py` (optional)

1. `test_readme_example_json_is_valid`
   - **Input**: Parse JSON example from README.md
   - **Expected**: JSON is valid and matches request schema
   - **Covers**: Verify example JSON in docs is valid
   - **Implementation**: Use `json.loads()` to parse, validate against Pydantic model

2. `test_readme_curl_example_against_running_service` (manual validation)
   - **Input**: Copy curl command from README, run against dev server
   - **Expected**: Returns 200 with expected response structure
   - **Covers**: Test example curl commands against running service
   - **Implementation**: Manual test or integration test with subprocess

**Test Implementation Notes:**
- Documentation tests are optional and primarily for validation
- Most documentation validation happens through manual review
- Example JSON can be validated in unit tests
- Curl commands tested manually during development
- No acceptance criteria blocked on automated documentation tests

**Alternative Validation:**
- Include example request/response in docstrings of API endpoints
- FastAPI auto-generates OpenAPI schema - validate examples there
- Manual testing of curl commands as part of development workflow

---

## Test Execution & Coverage

### Running Tests

```bash
# Run all unit tests
make test

# Run specific phase tests
pytest tests/test_models.py -v
pytest tests/test_classifier.py -v
pytest tests/test_api.py -v

# Run integration tests (requires model download)
pytest -m integration integration/test_classification_integration.py -v

# Run with coverage
pytest --cov=src/benz_sent_filter --cov-report=term-missing
```

### Coverage Targets

- Overall coverage: >90%
- New code coverage: 100% (all new company relevance logic)
- Existing code: No regression in coverage

### Test Organization

```
tests/
  test_models.py           # Phase 1: Model validation
  test_classifier.py       # Phase 2: Service logic
  test_api.py              # Phase 3: API endpoints
  conftest.py              # Shared fixtures

integration/
  test_classification_integration.py  # Phase 4: Integration tests
```

---

## Dependencies Between Phases

- **Phase 2** depends on **Phase 1**: Service logic requires updated models
- **Phase 3** depends on **Phase 1 & 2**: API endpoints require models and service
- **Phase 4** depends on **Phase 1, 2, & 3**: Integration tests validate full stack
- **Phase 5** has no test dependencies

---

**End of Test Specification**

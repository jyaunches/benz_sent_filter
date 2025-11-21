# Test Specification: Strategic Catalyst Detection

**Created**: 2025-11-20
**Spec File**: specs/2025-11-20_21-59_strategic_catalyst_detection.md
**Bead**: benz_sent_filter-ae65

## Overview

This test specification provides comprehensive test guides for all implementation phases of the strategic catalyst detection feature. Tests follow TDD methodology: write tests first, implement code to make them pass, commit, and proceed to next phase.

## Test File Organization

All tests will be added to existing test files following current patterns:
- **Detector logic tests**: `tests/test_strategic_catalyst_detector_mnls.py` (new file)
- **API integration tests**: `tests/test_api.py` (extend existing test classes)
- **Service integration tests**: `tests/test_classifier.py` (extend existing test classes)
- **Model field tests**: `tests/test_models.py` (extend existing test classes)

---

## Phase 1: Core Detector Implementation - Test Guide

**Existing Tests to Modify:**
None - this is a new detector with new test file.

**New Tests to Create:**

### Test File: tests/test_strategic_catalyst_detector_mnls.py

Location: `tests/test_strategic_catalyst_detector_mnls.py` (new file)

**Test Class: TestStrategicCatalystDetector**

#### Presence Detection Tests

1. **test_detect_executive_change_xfor_triple_transition**
   - **Input**: "X4 Pharmaceuticals' President And CEO Paula Ragan And CFO Adam Mostafa Have Stepped Down..."
   - **Expected**: `has_strategic_catalyst=True`
   - **Covers**: Executive change presence detection (triple C-suite transition)

2. **test_detect_executive_change_shco_cfo_appointment**
   - **Input**: "Soho House & Co Inc. Appoints David Bowie As Chief Financial Officer"
   - **Expected**: `has_strategic_catalyst=True`
   - **Covers**: CFO appointment presence detection

3. **test_detect_merger_wkhs_agreement**
   - **Input**: "Workhorse Group And ATW Partners Announce Merger Agreement"
   - **Expected**: `has_strategic_catalyst=True`
   - **Covers**: Merger agreement presence detection

4. **test_detect_product_launch_smx_global**
   - **Input**: "SMX (SECURITY MATTERS) PLC Partners with UN to Launch Global Product Authentication Platform"
   - **Expected**: `has_strategic_catalyst=True`
   - **Covers**: Product launch presence detection

5. **test_detect_partnership_img_mou**
   - **Input**: "Imgn Media Signs Mou With Adl Intelligent Labs For Gene-Editing Product Development"
   - **Expected**: `has_strategic_catalyst=True`
   - **Covers**: Strategic partnership presence detection

6. **test_detect_rebranding_nehc_name_change**
   - **Input**: "NorthEast Healthcare Announces Name Change to Alliance HealthCare Services"
   - **Expected**: `has_strategic_catalyst=True`
   - **Covers**: Rebranding/name change presence detection

7. **test_detect_clinical_trial_pstv_results**
   - **Input**: "Positron Announces Positive Phase 1 Clinical Trial Results"
   - **Expected**: `has_strategic_catalyst=True`
   - **Covers**: Clinical trial results presence detection

#### Negative Detection Tests

8. **test_reject_financial_results**
   - **Input**: "Company reports Q3 earnings of $1.2B revenue"
   - **Expected**: `has_strategic_catalyst=False`
   - **Covers**: Rejects financial results as non-catalyst

9. **test_reject_stock_movement**
   - **Input**: "Stock rises 10% on strong trading volume"
   - **Expected**: `has_strategic_catalyst=False`
   - **Covers**: Rejects stock price movements as non-catalyst

10. **test_reject_routine_operations**
    - **Input**: "Bank files quarterly MBS disclosure report with SEC"
    - **Expected**: `has_strategic_catalyst=False`
    - **Covers**: Rejects routine operations as non-catalyst

#### Type Classification Tests

11. **test_classify_executive_change_type**
    - **Input**: "X4 Pharmaceuticals' President And CEO Paula Ragan And CFO Adam Mostafa Have Stepped Down..."
    - **Expected**: `catalyst_type="executive_change"`, `confidence >= 0.6`
    - **Covers**: Executive change type classification

12. **test_classify_executive_change_cfo_appointment**
    - **Input**: "Soho House & Co Inc. Appoints David Bowie As Chief Financial Officer"
    - **Expected**: `catalyst_type="executive_change"`, `confidence >= 0.6`
    - **Covers**: CFO appointment classified as executive_change

13. **test_classify_merger_agreement_type**
    - **Input**: "Workhorse Group And ATW Partners Announce Merger Agreement"
    - **Expected**: `catalyst_type="merger_agreement"`, `confidence >= 0.6`
    - **Covers**: Merger agreement type classification

14. **test_classify_product_launch_type**
    - **Input**: "SMX (SECURITY MATTERS) PLC Partners with UN to Launch Global Product Authentication Platform"
    - **Expected**: `catalyst_type="product_launch"`, `confidence >= 0.6`
    - **Covers**: Product launch type classification

15. **test_classify_strategic_partnership_type**
    - **Input**: "Imgn Media Signs Mou With Adl Intelligent Labs For Gene-Editing Product Development"
    - **Expected**: `catalyst_type="strategic_partnership"`, `confidence >= 0.6`
    - **Covers**: Strategic partnership type classification

16. **test_classify_rebranding_type**
    - **Input**: "NorthEast Healthcare Announces Name Change to Alliance HealthCare Services"
    - **Expected**: `catalyst_type="rebranding"`, `confidence >= 0.6`
    - **Covers**: Rebranding type classification

17. **test_classify_clinical_trial_results_type**
    - **Input**: "Positron Announces Positive Phase 1 Clinical Trial Results"
    - **Expected**: `catalyst_type="clinical_trial_results"`, `confidence >= 0.6`
    - **Covers**: Clinical trial results type classification

#### Edge Case Tests

18. **test_handle_none_input**
    - **Input**: `None`
    - **Expected**: `has_strategic_catalyst=False`, `catalyst_type=None`, `confidence=0.0`
    - **Covers**: None input handling

19. **test_handle_empty_string**
    - **Input**: `""`
    - **Expected**: `has_strategic_catalyst=False`, `catalyst_type=None`, `confidence=0.0`
    - **Covers**: Empty string handling

20. **test_ambiguous_headline_returns_mixed**
    - **Input**: "Company announces major strategic initiative"
    - **Expected**: `catalyst_type="mixed"` (if best score < 0.6)
    - **Covers**: Ambiguous headlines return "mixed" type

21. **test_confidence_score_range**
    - **Input**: Any valid strategic catalyst headline
    - **Expected**: `0.0 <= confidence <= 1.0`
    - **Covers**: Confidence scores within valid range

#### All 11 Real-World Examples Test

22. **test_all_real_world_examples**
    - **Test Data**:
      1. XFOR: "X4 Pharmaceuticals' President And CEO Paula Ragan And CFO Adam Mostafa Have Stepped Down..." → executive_change
      2. SHCO: "Soho House & Co Inc. Appoints David Bowie As Chief Financial Officer" → executive_change
      3. OPEN: "Opendoor CEO Eric Wu Steps Down" → executive_change
      4. OPCH: "Option Care Health Appoints John Rademacher as CFO" → executive_change
      5. WKHS: "Workhorse Group And ATW Partners Announce Merger Agreement" → merger_agreement
      6. NEHC: "NorthEast Healthcare Announces Name Change to Alliance HealthCare Services" → rebranding
      7. SMX: "SMX (SECURITY MATTERS) PLC Partners with UN to Launch Global Product Authentication Platform" → product_launch
      8. CTXR: "Citius Pharmaceuticals Launches AI Platform for Drug Development" → product_launch
      9. IMG: "Imgn Media Signs Mou With Adl Intelligent Labs For Gene-Editing Product Development" → strategic_partnership
      10. WDAY: "Workday Partners with IBM on Enterprise AI Solutions" → strategic_partnership
      11. PSTV: "Positron Announces Positive Phase 1 Clinical Trial Results" → clinical_trial_results
    - **Expected**: All correctly classified with confidence >= 0.6
    - **Covers**: 90%+ accuracy requirement on test set

**Test Implementation Notes:**
- Import `StrategicCatalystDetectorMNLS` from `benz_sent_filter.services.strategic_catalyst_detector_mnls`
- Use real MNLI pipeline (not mocked) to test actual classification behavior
- Test constructor with optional pipeline parameter for sharing
- Verify all 11 real-world examples classify correctly
- Ensure performance <1s for single headline classification
- Test edge cases (None, empty, ambiguous)

---

## Phase 2: API Integration - Endpoint and Models - Test Guide

**Existing Tests to Modify:**
None - adding new endpoint tests to existing API test file.

**New Tests to Create:**

### Test Class: (Add to `tests/test_api.py`)

1. **test_detect_strategic_catalyst_endpoint_executive_change**
   - **Setup**: POST to `/detect-strategic-catalyst`
   - **Input**: `{"headline": "X4 Pharmaceuticals' President And CEO Paula Ragan And CFO Adam Mostafa Have Stepped Down..."}`
   - **Expected**:
     - Response status 200
     - `has_strategic_catalyst` = true
     - `catalyst_type` = "executive_change"
     - `confidence` >= 0.6
     - `headline` matches input
   - **Covers**: Endpoint returns correct structure for executive change

2. **test_detect_strategic_catalyst_endpoint_merger**
   - **Setup**: POST to `/detect-strategic-catalyst`
   - **Input**: `{"headline": "Workhorse Group And ATW Partners Announce Merger Agreement"}`
   - **Expected**:
     - Response status 200
     - `has_strategic_catalyst` = true
     - `catalyst_type` = "merger_agreement"
     - `confidence` >= 0.6
   - **Covers**: Endpoint returns correct structure for merger

3. **test_detect_strategic_catalyst_endpoint_no_catalyst**
   - **Setup**: POST to `/detect-strategic-catalyst`
   - **Input**: `{"headline": "Company reports Q3 earnings of $1.2B revenue"}`
   - **Expected**:
     - Response status 200
     - `has_strategic_catalyst` = false
     - `catalyst_type` NOT in response (excluded via exclude_none)
     - `confidence` value present
   - **Covers**: Endpoint handles non-catalyst headlines correctly

4. **test_detect_strategic_catalyst_endpoint_validation_empty_headline**
   - **Setup**: POST to `/detect-strategic-catalyst`
   - **Input**: `{"headline": ""}`
   - **Expected**:
     - Response status 422 (validation error)
   - **Covers**: Request validation rejects empty headline

5. **test_detect_strategic_catalyst_endpoint_validation_missing_headline**
   - **Setup**: POST to `/detect-strategic-catalyst`
   - **Input**: `{}`
   - **Expected**:
     - Response status 422 (validation error)
   - **Covers**: Request validation requires headline field

6. **test_detect_strategic_catalyst_response_model_structure**
   - **Setup**: POST to `/detect-strategic-catalyst` with valid catalyst
   - **Input**: `{"headline": "Positron Announces Positive Phase 1 Clinical Trial Results"}`
   - **Expected**:
     - Response contains: headline, has_strategic_catalyst, catalyst_type, confidence
     - All fields have correct types (str, bool, str|None, float)
   - **Covers**: Response model structure matches specification

7. **test_detect_strategic_catalyst_backward_compatibility**
   - **Setup**: Verify existing endpoints unchanged
   - **Input**: GET to `/health`, POST to `/classify`
   - **Expected**:
     - All existing endpoints work unchanged
     - Response structures preserved
   - **Covers**: Backward compatibility with existing API

**Test Implementation Notes:**
- Use FastAPI TestClient for endpoint testing
- Follow existing API test patterns from `test_api.py`
- Verify response structure and status codes
- Test field presence/absence based on exclude_none
- Validate JSON serialization
- Ensure backward compatibility with existing endpoints

### Test Class: (Add to `tests/test_models.py`)

8. **test_strategic_catalyst_request_model_valid**
   - **Input**: `StrategicCatalystRequest(headline="Test headline")`
   - **Expected**: Model instantiates successfully
   - **Covers**: Request model accepts valid headline

9. **test_strategic_catalyst_request_model_rejects_empty**
   - **Input**: `StrategicCatalystRequest(headline="")`
   - **Expected**: Validation error (min_length=1)
   - **Covers**: Request model validation

10. **test_strategic_catalyst_result_model_with_catalyst**
    - **Input**:
      ```python
      StrategicCatalystResult(
          headline="Test",
          has_strategic_catalyst=True,
          catalyst_type="executive_change",
          confidence=0.85
      )
      ```
    - **Expected**: Model instantiates with all fields
    - **Covers**: Result model with catalyst present

11. **test_strategic_catalyst_result_model_without_catalyst**
    - **Input**:
      ```python
      StrategicCatalystResult(
          headline="Test",
          has_strategic_catalyst=False,
          catalyst_type=None,
          confidence=0.2
      )
      ```
    - **Expected**: Model instantiates, `model_dump(exclude_none=True)` excludes catalyst_type
    - **Covers**: Result model with no catalyst, exclude_none behavior

### Test Class: (Add to `tests/test_classifier.py`)

12. **test_classification_service_detect_strategic_catalyst_integration**
    - **Setup**: Initialize ClassificationService with shared pipeline
    - **Input**: `headline="Workhorse Group And ATW Partners Announce Merger Agreement"`
    - **Expected**: Returns StrategicCatalystResult with correct fields
    - **Covers**: ClassificationService integration with detector

13. **test_classification_service_detector_shares_pipeline**
    - **Setup**: Initialize ClassificationService
    - **Expected**: Strategic catalyst detector uses same pipeline as other detectors
    - **Covers**: Pipeline sharing to avoid duplicate model loading

**Test Implementation Notes:**
- Test Pydantic model instantiation and validation
- Test model_dump with exclude_none=True
- Verify ClassificationService integration
- Confirm pipeline sharing

---

## Phase 3: Documentation and Testing - Test Guide

**Existing Tests to Modify:**
All existing tests must continue to pass (backward compatibility validation).

**New Tests to Create:**

### Performance Tests (Add to `tests/test_strategic_catalyst_detector_mnls.py`)

1. **test_detector_performance_single_headline**
   - **Setup**: Measure latency for single headline classification
   - **Input**: Any valid strategic catalyst headline
   - **Expected**: Latency < 1 second
   - **Covers**: Performance requirement

2. **test_detector_accuracy_on_full_test_set**
   - **Setup**: Run detector on all 11 real-world examples
   - **Expected**: 90%+ accuracy (at least 10/11 correct)
   - **Covers**: Accuracy requirement

### Documentation Validation Tests (Manual)

3. **verify_claude_md_updated**
   - **Check**: CLAUDE.md includes strategic catalyst detection in feature list
   - **Check**: 6 catalyst types documented
   - **Check**: Example API request/response included
   - **Covers**: Documentation completeness

4. **verify_api_endpoint_documented**
   - **Check**: `/detect-strategic-catalyst` endpoint documented
   - **Check**: Request/response models documented
   - **Check**: Integration point for benz_analyzer noted
   - **Covers**: API documentation

### Regression Tests (Run full test suite)

5. **test_no_regressions_on_existing_endpoints**
   - **Setup**: Run full test suite: `pytest tests/ -v`
   - **Expected**: All existing tests continue to pass
   - **Covers**: Zero regressions requirement

**Test Implementation Notes:**
- Use `time.time()` for performance measurement
- Calculate accuracy as (correct classifications / total examples)
- Run full test suite to verify backward compatibility
- Manual documentation review

---

## Test Execution Order

### Phase 1 Tests
Run: `pytest tests/test_strategic_catalyst_detector_mnls.py -v`
- All tests should fail initially (detector doesn't exist)
- Implement `StrategicCatalystDetectorMNLS` in `strategic_catalyst_detector_mnls.py`
- All tests should pass
- Commit: "Phase 1: Implement strategic catalyst detector with MNLI"

### Phase 2 Tests
Run: `pytest tests/test_api.py -k strategic_catalyst -v && pytest tests/test_models.py -k strategic_catalyst -v && pytest tests/test_classifier.py -k strategic_catalyst -v`
- All tests should fail initially (endpoint/models don't exist)
- Add endpoint to `app.py`
- Add models to `classification.py`
- Integrate with `classifier.py`
- All tests should pass (including existing tests)
- Commit: "Phase 2: Add strategic catalyst detection API endpoint and models"

### Phase 3 Tests
Run: `pytest tests/ -v`
- Performance tests should pass (<1s latency, 90%+ accuracy)
- All existing tests should continue to pass
- Manual documentation review
- Commit: "Phase 3: Documentation and comprehensive testing for strategic catalyst detection"

---

## Success Criteria

### Phase 1 Complete When:
- 22 detector tests pass
- `StrategicCatalystDetectorMNLS` class exists in `strategic_catalyst_detector_mnls.py`
- All 11 real-world examples correctly classified
- Presence detection works for positive and negative cases
- Type classification across all 6 categories works
- Edge cases handled (None, empty, ambiguous)
- Performance <1s for single headline

### Phase 2 Complete When:
- 13 integration tests pass (7 API + 4 model + 2 service)
- `/detect-strategic-catalyst` endpoint exists and works
- Request/response models defined and validated
- ClassificationService integration complete
- Pipeline sharing implemented
- Backward compatibility preserved

### Phase 3 Complete When:
- 5 documentation/regression tests pass
- 90%+ accuracy on full test set (10+/11 examples)
- <1s average latency
- CLAUDE.md updated with strategic catalyst feature
- API endpoint documented
- All existing tests continue to pass (zero regressions)

---

## Dependencies Between Phases

- **Phase 2** depends on Phase 1: `StrategicCatalystDetectorMNLS` must exist
- **Phase 3** depends on Phases 1-2: Full integration requires detector and API

## Backward Compatibility Validation

After all phases complete, run full test suite:
```bash
pytest tests/ -v
```

All existing tests must continue to pass, ensuring:
- Existing API responses unchanged
- No changes to `/classify` endpoint
- `exclude_none=True` serialization working correctly
- No performance degradation

---

**Total Test Count**: 40+ tests
- Phase 1: 22 tests (detector logic)
- Phase 2: 13 tests (API/models/service integration)
- Phase 3: 5+ tests (performance/documentation/regression)

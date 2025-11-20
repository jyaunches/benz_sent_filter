# Test Specification: Conditional Language Detection for Future Events

**Created**: 2025-11-19
**Spec File**: specs/2025-11-19_21-30_conditional_language_detection.md
**Bead**: benz_sent_filter-d439

## Overview

This test specification provides comprehensive test guides for all implementation phases of the conditional language detection feature. Tests follow TDD methodology: write tests first, implement code to make them pass, commit, and proceed to next phase.

## Test File Organization

All tests will be added to existing test files following current patterns:
- **Pattern matching tests**: `tests/test_classifier.py` (new test class)
- **Service integration tests**: `tests/test_classifier.py` (extend existing test classes)
- **Model field tests**: `tests/test_models.py` (extend existing test classes)
- **API integration tests**: `tests/test_api.py` (extend existing test classes)

---

## Phase 1: Core Pattern Detection Function - Test Guide

**Existing Tests to Modify:**
None - this is a new function with no existing tests.

**New Tests to Create:**

### Test Class: TestConditionalLanguagePatternDetection

Location: `tests/test_classifier.py`

1. **test_conditional_language_detects_intention_verbs**
   - **Input**: "Apple plans to expand into new markets next year"
   - **Expected**: `(True, ["plans to"])`
   - **Covers**: Intention verb pattern detection ("plans to")

2. **test_conditional_language_detects_expectation_patterns**
   - **Input**: "Company expected to announce results in Q4"
   - **Expected**: `(True, ["expected to"])`
   - **Covers**: Expectation language pattern ("expected to")

3. **test_conditional_language_detects_modal_uncertainty**
   - **Input**: "Microsoft may acquire startup for undisclosed sum"
   - **Expected**: `(True, ["may"])`
   - **Covers**: Modal uncertainty pattern ("may", "could", "might")

4. **test_conditional_language_detects_exploration_language**
   - **Input**: "Tesla exploring opportunities in autonomous vehicles"
   - **Expected**: `(True, ["exploring"])`
   - **Covers**: Exploration/consideration patterns ("exploring", "considering")

5. **test_conditional_language_detects_multiple_patterns**
   - **Input**: "Company plans to explore potential acquisitions and may announce by Q2"
   - **Expected**: `(True, ["plans to", "explore", "potential", "may"])`
   - **Covers**: Multiple pattern detection in single headline

6. **test_conditional_language_no_match_concrete_language**
   - **Input**: "Apple will launch new iPhone in September"
   - **Expected**: `(False, [])`
   - **Covers**: No false positives on concrete future statements

7. **test_conditional_language_case_insensitive_matching**
   - **Input**: "Company AIMS TO increase revenue next quarter"
   - **Expected**: `(True, ["aims to"])`
   - **Covers**: Case-insensitive pattern matching

**Test Implementation Notes:**
- Import `matches_conditional_language` from `benz_sent_filter.services.forecast_analyzer`
- No mocks required - pure function testing
- Test both positive cases (patterns present) and negative cases (no patterns)
- Verify matched pattern list accuracy (not just boolean)
- Function uses precompiled `re.compile()` patterns at module level for performance

---

## Phase 2: ClassificationService Integration - Test Guide

**Existing Tests to Modify:**
None - this phase adds new private method and extends existing service method.

**New Tests to Create:**

### Test Class: TestConditionalLanguageServiceIntegration

Location: `tests/test_classifier.py`

1. **test_analyze_conditional_language_future_event_with_patterns**
   - **Setup**: Mock pipeline for FUTURE_EVENT temporal classification
   - **Input**: `headline="Apple plans to explore AI opportunities", temporal_category=TemporalCategory.FUTURE_EVENT`
   - **Expected**: `{"conditional_language": True, "conditional_patterns": ["plans to", "explore"]}`
   - **Covers**: Conditional execution for FUTURE_EVENT + pattern detection

2. **test_analyze_conditional_language_future_event_no_patterns**
   - **Setup**: Mock pipeline for FUTURE_EVENT temporal classification
   - **Input**: `headline="Apple will launch product in Q2", temporal_category=TemporalCategory.FUTURE_EVENT`
   - **Expected**: `{"conditional_language": None, "conditional_patterns": None}`
   - **Covers**: FUTURE_EVENT without conditional language returns None

3. **test_analyze_conditional_language_past_event_skipped**
   - **Setup**: Mock pipeline for PAST_EVENT temporal classification
   - **Input**: `headline="Apple planned to expand markets", temporal_category=TemporalCategory.PAST_EVENT`
   - **Expected**: `{"conditional_language": None, "conditional_patterns": None}`
   - **Covers**: Conditional execution - PAST_EVENT skips analysis

4. **test_classify_headline_integrates_conditional_language_fields**
   - **Setup**: Mock pipeline for FUTURE_EVENT with conditional language
   - **Input**: `headline="Microsoft may consider acquisitions"`
   - **Expected**: ClassificationResult with `conditional_language=True`, `conditional_patterns=["may", "consider"]`
   - **Covers**: End-to-end integration through `classify_headline()` method

**Test Implementation Notes:**
- Use existing `mock_transformers_pipeline` fixture pattern
- Test `_analyze_conditional_language()` method directly for unit tests
- Test integration via `classify_headline()` for end-to-end validation
- Clear module cache before each test to ensure fresh import
- Verify no impact on existing classification fields

---

## Phase 3: Response Model Extension - Test Guide

**Existing Tests to Modify:**
None - adding new optional fields to existing model.

**New Tests to Create:**

### Test Class: (Add to existing model tests in `tests/test_models.py`)

1. **test_classification_result_with_conditional_language_fields_present**
   - **Input**:
     ```python
     ClassificationResult(
         is_opinion=False,
         is_straight_news=True,
         temporal_category=TemporalCategory.FUTURE_EVENT,
         scores=scores,
         headline="Apple plans to expand market",
         conditional_language=True,
         conditional_patterns=["plans to"]
     )
     ```
   - **Expected**: Fields accessible and serialized correctly
   - **Covers**: New optional fields accept values and serialize

2. **test_classification_result_json_excludes_none_conditional_fields**
   - **Input**:
     ```python
     ClassificationResult(
         is_opinion=False,
         is_straight_news=True,
         temporal_category=TemporalCategory.PAST_EVENT,
         scores=scores,
         headline="Apple reported Q2 results"
     )
     ```
   - **Expected**: `model_dump(exclude_none=True)` excludes `conditional_language` and `conditional_patterns`
   - **Covers**: Backward compatibility via `exclude_none=True`

3. **test_classification_result_conditional_with_other_optional_fields**
   - **Input**:
     ```python
     ClassificationResult(
         # All fields including company, far_future, and conditional
         conditional_language=True,
         conditional_patterns=["may"],
         far_future_forecast=True,
         forecast_timeframe="by 2028",
         is_about_company=True,
         company="Dell"
     )
     ```
   - **Expected**: All optional fields coexist and serialize correctly
   - **Covers**: Integration with existing optional fields

**Test Implementation Notes:**
- Follow existing pattern from far-future and company relevance field tests
- Test field access, serialization with values, and exclusion when None
- Verify `exclude_none=True` behavior for backward compatibility
- Test combination scenarios with other optional fields

---

## Phase 4: Integration Testing and Validation - Test Guide

**Existing Tests to Modify:**
None - adding new integration tests to existing API test file.

**New Tests to Create:**

### Test Class: (Add to `tests/test_api.py`)

1. **test_classify_endpoint_conditional_language_detected_future_event**
   - **Setup**: POST to `/classify` with headline containing conditional language
   - **Input**: `{"headline": "Apple plans to explore AI opportunities in 2025"}`
   - **Expected**:
     - Response status 200
     - `temporal_category` = "future_event"
     - `conditional_language` = true
     - `conditional_patterns` includes "plans to" and "explore"
   - **Covers**: API endpoint returns conditional language fields for FUTURE_EVENT

2. **test_classify_endpoint_no_conditional_language_concrete_future**
   - **Setup**: POST to `/classify` with concrete future headline
   - **Input**: `{"headline": "Apple will launch iPhone 16 in September"}`
   - **Expected**:
     - Response status 200
     - `temporal_category` = "future_event"
     - `conditional_language` and `conditional_patterns` NOT in response (excluded via exclude_none)
   - **Covers**: Concrete language doesn't trigger detection

3. **test_classify_endpoint_conditional_language_not_detected_past_event**
   - **Setup**: POST to `/classify` with past tense conditional language
   - **Input**: `{"headline": "Apple planned to expand but changed direction"}`
   - **Expected**:
     - Response status 200
     - `temporal_category` = "past_event"
     - `conditional_language` and `conditional_patterns` NOT in response
   - **Covers**: Conditional execution - only FUTURE_EVENT analyzed

4. **test_classify_endpoint_conditional_with_far_future_combination**
   - **Setup**: POST to `/classify` with both conditional and far-future patterns
   - **Input**: `{"headline": "Dell may target $10B revenue by 2028"}`
   - **Expected**:
     - Response status 200
     - `temporal_category` = "future_event"
     - `conditional_language` = true
     - `conditional_patterns` includes "may"
     - `far_future_forecast` = true
     - `forecast_timeframe` = "by 2028"
   - **Covers**: Combination of conditional language + far-future detection

**Test Implementation Notes:**
- Use FastAPI TestClient for endpoint testing
- Follow existing API test patterns from `test_api.py`
- Verify response structure and status codes
- Test field presence/absence based on conditional logic
- Validate JSON serialization excludes None fields

---

## Test Execution Order

### Phase 1 Tests
Run: `pytest tests/test_classifier.py::TestConditionalLanguagePatternDetection -v`
- All tests should fail initially (function doesn't exist)
- Implement `matches_conditional_language()` in `forecast_analyzer.py`
- All tests should pass
- Commit: "Phase 1: Implement conditional language pattern detection"

### Phase 2 Tests
Run: `pytest tests/test_classifier.py::TestConditionalLanguageServiceIntegration -v`
- All tests should fail initially (method doesn't exist)
- Implement `_analyze_conditional_language()` in `classifier.py`
- Integrate into `classify_headline()` method
- All tests should pass (including existing tests)
- Commit: "Phase 2: Integrate conditional language into ClassificationService"

### Phase 3 Tests
Run: `pytest tests/test_models.py -k conditional -v`
- All tests should fail initially (fields don't exist)
- Add `conditional_language` and `conditional_patterns` fields to ClassificationResult
- Update `classify_headline()` to pass new fields
- All tests should pass
- Commit: "Phase 3: Extend ClassificationResult with conditional language fields"

### Phase 4 Tests
Run: `pytest tests/test_api.py -k conditional -v`
- All tests should fail initially (integration not complete)
- Verify end-to-end flow through API
- All tests should pass
- Commit: "Phase 4: End-to-end integration testing for conditional language"

---

## Success Criteria

### Phase 1 Complete When:
- 7 pattern detection tests pass
- `matches_conditional_language()` function exists in `forecast_analyzer.py`
- Function detects all pattern categories correctly
- No false positives on concrete language

### Phase 2 Complete When:
- 4 service integration tests pass
- `_analyze_conditional_language()` method exists in `classifier.py`
- Method only executes for FUTURE_EVENT temporal category
- Integration with `classify_headline()` works correctly
- All existing tests continue to pass

### Phase 3 Complete When:
- 3 model field tests pass
- `conditional_language` and `conditional_patterns` fields exist in ClassificationResult
- Fields serialize correctly when present
- Fields excluded from JSON when None (backward compatible)
- Coexistence with other optional fields verified

### Phase 4 Complete When:
- 4 API integration tests pass
- `/classify` endpoint returns conditional language fields for FUTURE_EVENT
- Fields excluded for PAST_EVENT and GENERAL_TOPIC
- Combination scenarios work (conditional + far-future)
- Existing API contracts preserved (backward compatible)

---

## Dependencies Between Phases

- **Phase 2** depends on Phase 1: `matches_conditional_language()` must exist
- **Phase 3** depends on Phase 2: `_analyze_conditional_language()` must exist
- **Phase 4** depends on Phases 1-3: Full integration requires all components

## Backward Compatibility Validation

After all phases complete, run full test suite:
```bash
pytest tests/ -v
```

All existing tests must continue to pass, ensuring:
- Existing API responses unchanged when no conditional language present
- `exclude_none=True` serialization working correctly
- No performance degradation (<100ms overhead measured in integration tests)

---

**Total Test Count**: 14-18 tests
- Phase 1: 7 tests
- Phase 2: 4 tests
- Phase 3: 3 tests
- Phase 4: 4 tests

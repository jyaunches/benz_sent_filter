# Specification: Conditional Language Detection for Future Events

**Created**: 2025-11-19
**Bead**: benz_sent_filter-d439
**Status**: Draft

## Overview & Objectives

### Problem Statement
The service currently classifies headlines into temporal categories (PAST_EVENT, FUTURE_EVENT, GENERAL_TOPIC) and can detect far-future forecasts (multi-year timeframes). However, it lacks the ability to distinguish between **committed future actions** versus **vague, hedged, or exploratory future statements**.

Headlines like "Apple plans to explore AI opportunities" and "Microsoft may consider acquisitions" contain conditional, non-committal language that signals uncertainty or early-stage considerations. These should be distinguished from concrete announcements like "Apple will launch new product in Q2" or "Microsoft acquires LinkedIn for $26B".

### Goals
1. Detect conditional/hedging language patterns in headlines
2. Return detection results with matched patterns for transparency
3. Integrate seamlessly with existing classification pipeline
4. Provide optional filtering capability for downstream consumers

### Non-Goals
- Replacing temporal classification (PAST/FUTURE/GENERAL remains primary)
- Replacing far-future detection (multi-year timeframes still separate)
- Scoring certainty levels (boolean detection only)
- Language analysis beyond pattern matching

## Current State Analysis

### What Exists
**Temporal Classification** (`classifier.py`):
- MNLI-based classification into PAST_EVENT, FUTURE_EVENT, GENERAL_TOPIC
- Integrated into `classify_headline()` method
- Returns `temporal_category` in ClassificationResult

**Far-Future Detection** (`forecast_analyzer.py`):
- Pattern-based detection of multi-year timeframes
- `is_far_future()` function with tuple return (bool, timeframe)
- `_analyze_far_future()` integration in ClassificationService
- Conditional execution (only for FUTURE_EVENT temporal category)
- Returns `far_future_forecast` and `forecast_timeframe` fields

**Response Model** (`models/classification.py`):
- ClassificationResult Pydantic model with `exclude_none=True`
- Optional fields for far-future detection
- Backward-compatible additions

### What's Needed
**Conditional Language Detection**:
- Pattern matching function for hedge/vague language
- Detection of 10+ conditional patterns (plans, expected, could, may, exploring, etc.)
- Return both boolean result and list of matched patterns
- Integration into ClassificationService similar to far-future
- New optional fields in ClassificationResult

**Integration Points**:
- Add `matches_conditional_language()` to `forecast_analyzer.py`
- Add `_analyze_conditional_language()` method to ClassificationService
- Extend ClassificationResult with `conditional_language` and `conditional_patterns` fields
- Update API response in `/classify` endpoint

## Architecture Design

### Module Organization
**forecast_analyzer.py** (extend existing):
- Add `matches_conditional_language(text: str) -> tuple[bool, list[str]]` function
- Pattern-based detection using regex
- Returns matched patterns for transparency
- Follows same design as `is_far_future()` function

**classifier.py** (extend existing):
- Add `_analyze_conditional_language()` private method
- Conditional execution logic (when to apply detection)
- Integration into `classify_headline()` method
- Pass results to ClassificationResult constructor

**models/classification.py** (extend existing):
- Add optional `conditional_language: bool | None = None` field
- Add optional `conditional_patterns: list[str] | None = None` field
- Maintain `exclude_none=True` for backward compatibility

**api/app.py** (no changes required):
- Existing `/classify` endpoint automatically includes new fields
- Pydantic serialization handles optional fields

### Pattern Detection Strategy
**Conditional Language Categories**:
1. **Intention verbs**: "plans to", "aims to", "intends to", "seeks to"
2. **Expectation language**: "expected to", "anticipated to"
3. **Modal uncertainty**: "could", "may", "might", "would"
4. **Exploration/consideration**: "exploring", "considering", "evaluating", "reviewing"
5. **Optionality**: "potential", "possible", "looking to"

**Detection Approach**:
- Case-insensitive pattern matching
- Word boundary checks to avoid partial matches
- Return list of actual matched patterns (not categories)
- No scoring or weighting (boolean detection only)

### Integration Logic
**When to Apply Detection**:
Option A: Always detect (regardless of temporal category)
Option B: Only for FUTURE_EVENT temporal category (like far-future)
Option C: Only when NOT far-future (complementary filtering)

**Recommended**: Option B - only for FUTURE_EVENT
- Most conditional language appears in future-oriented headlines
- Matches existing far-future pattern (conditional execution)
- Reduces false positives from past-tense conditional language

**Return Behavior**:
- If temporal_category != FUTURE_EVENT: return `None` for both fields
- If no patterns matched: return `None` for both fields
- If patterns matched: return `True` for conditional_language, list of patterns

## Implementation Phases

### Phase 1: Core Pattern Detection Function
**Description**: Implement the `matches_conditional_language()` function in `forecast_analyzer.py` with comprehensive pattern matching and test coverage.

**Core Functionality**:
- Function signature: `matches_conditional_language(text: str) -> tuple[bool, list[str]]`
- Detect 10+ conditional language patterns
- Return both boolean result and matched pattern list
- Case-insensitive matching with word boundaries

**Implementation Approach**:
- Extend `forecast_analyzer.py` module
- Add pattern matching logic using regex
- Pattern categories: intention verbs, expectations, modals, exploration language
- Return empty list if no matches, list of matched patterns otherwise

**Unit Test Requirements**:
- Test file: `tests/test_classifier.py` (add new test class)
- Positive tests for each pattern category
- Negative tests (no false positives on concrete language)
- Edge cases: multiple patterns in same headline, case variations
- Verify matched patterns list accuracy

**Acceptance Criteria**:
- `matches_conditional_language()` function implemented in `forecast_analyzer.py`
- Detects patterns: "plans to", "expected to", "aims to", "intends to", "could", "may", "might", "exploring", "considering", "evaluating"
- Returns `(True, ["pattern1", "pattern2"])` for matches
- Returns `(False, [])` for no matches
- All unit tests pass (10+ new tests)
- No changes to existing far-future detection tests

### Phase 2: ClassificationService Integration
**Description**: Add `_analyze_conditional_language()` method to ClassificationService and integrate into the classification pipeline.

**Core Functionality**:
- Private method `_analyze_conditional_language(headline: str, temporal_category: TemporalCategory) -> dict`
- Conditional execution (only for FUTURE_EVENT temporal category)
- Returns dict with `conditional_language` and `conditional_patterns` keys
- Matches integration pattern of `_analyze_far_future()` method

**Implementation Approach**:
- Add new method to ClassificationService class in `classifier.py`
- Call `forecast_analyzer.matches_conditional_language()` internally
- Apply conditional logic: if temporal_category != FUTURE_EVENT, return None values
- Build return dict with both boolean and patterns
- Invoke from `classify_headline()` method after far-future analysis
- Pass results to ClassificationResult constructor

**Unit Test Requirements**:
- Test file: `tests/test_classifier.py` (extend existing)
- Test conditional execution (FUTURE_EVENT vs others)
- Test pattern detection through service layer
- Test integration with existing classification fields
- Verify no impact on non-FUTURE_EVENT classifications

**Acceptance Criteria**:
- `_analyze_conditional_language()` method added to ClassificationService
- Only executes for FUTURE_EVENT temporal category
- Returns `{"conditional_language": None, "conditional_patterns": None}` for non-future events
- Returns `{"conditional_language": True, "conditional_patterns": [...]}` for matched patterns
- Integrates into `classify_headline()` method
- All existing unit tests continue to pass
- 5+ new unit tests for integration logic

### Phase 3: Response Model Extension
**Description**: Extend ClassificationResult Pydantic model with new optional fields for conditional language detection.

**Core Functionality**:
- Add `conditional_language: bool | None = None` field
- Add `conditional_patterns: list[str] | None = None` field
- Maintain `exclude_none=True` serialization for backward compatibility
- Update constructor calls in ClassificationService

**Implementation Approach**:
- Modify `models/classification.py` ClassificationResult model
- Add two new optional fields with None defaults
- Update `classify_headline()` to pass new fields to constructor
- No changes needed to `/classify` endpoint (auto-serialization)

**Unit Test Requirements**:
- Test file: `tests/test_models.py` (extend existing if present, or add to test_classifier.py)
- Test serialization with and without conditional fields
- Verify `exclude_none=True` behavior (fields omitted when None)
- Test backward compatibility with existing response format

**Acceptance Criteria**:
- ClassificationResult model updated with `conditional_language` and `conditional_patterns` fields
- Fields are optional with None defaults
- Serialization excludes fields when None (backward compatible)
- `/classify` endpoint returns new fields when patterns detected
- All model validation tests pass
- 3+ new tests for field serialization

### Phase 4: Integration Testing and Validation
**Description**: End-to-end integration testing through the API endpoints with real-world headline examples.

**Core Functionality**:
- Test `/classify` endpoint with various headline types
- Verify conditional language detection for FUTURE_EVENT headlines
- Confirm no detection for PAST_EVENT and GENERAL_TOPIC
- Validate backward compatibility (existing clients unaffected)

**Implementation Approach**:
- Extend integration tests in `tests/test_api.py`
- Test cases covering all pattern categories
- Test conditional execution based on temporal category
- Test response serialization and field presence/absence
- Compare with existing far-future detection behavior

**Unit Test Requirements**:
- Test file: `tests/test_api.py` (extend existing)
- 5+ integration tests for `/classify` endpoint
- Test each conditional language category
- Test combination scenarios (conditional + far-future)
- Test non-FUTURE_EVENT exclusion
- Test backward compatibility (responses without new fields)

**Acceptance Criteria**:
- All integration tests pass (5+ new tests)
- `/classify` endpoint returns `conditional_language` and `conditional_patterns` for matched FUTURE_EVENT headlines
- Fields omitted for PAST_EVENT and GENERAL_TOPIC temporal categories
- Fields omitted when no conditional language detected
- Existing API contracts preserved (backward compatible)
- No performance degradation (<100ms overhead for pattern matching)

## Testing Strategy

### Unit Tests
- `tests/test_classifier.py`: Pattern matching function and service integration
- `tests/test_models.py` or `tests/test_classifier.py`: Model fields

### Integration Tests
- `tests/test_api.py`: End-to-end API testing (5+ tests)
- Real-world headline examples from financial news
- Edge case scenarios (multiple patterns, boundary cases)

### Backward Compatibility Tests
- Verify existing API responses unchanged when no conditional language present
- Confirm `exclude_none=True` serialization working correctly
- Test with existing client expectations

## Success Metrics

### Functional Completeness
- All 10+ conditional language patterns detected correctly
- Conditional execution logic works (FUTURE_EVENT only)
- API responses include new fields when appropriate
- Backward compatibility maintained

### Test Coverage
- 23+ new tests total (10 + 5 + 3 + 5)
- All existing tests continue to pass
- Integration tests validate end-to-end behavior

### Performance
- Pattern matching adds <100ms per headline
- No impact on non-FUTURE_EVENT classifications
- No regression in existing classification performance

## Future Enhancements (Out of Scope)

### Potential Extensions
- Conditional language scoring (certainty levels)
- Detection for non-FUTURE temporal categories
- Combination with quantitative catalyst detection
- Multi-language pattern support
- Pattern weighting or prioritization

### Integration Opportunities
- Combine with routine operations filter (uncertain + routine = low signal)
- Enhance quantitative catalyst detection (uncertain guidance vs confirmed actions)
- Add to batch classification endpoint metadata

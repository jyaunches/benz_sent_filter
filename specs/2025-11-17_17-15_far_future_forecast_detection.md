# Specification: Far-Future Forecast Detection

**Created**: 2025-11-17
**Status**: Draft
**Related Bead**: benz_sent_filter-d687

## Overview & Objectives

### Problem Statement

The current sentiment classification system detects `FUTURE_EVENT` classifications but does not distinguish between near-term guidance (quarterly/annual) and far-future forecasts (multi-year projections). This causes false positives when articles contain impressive long-term revenue projections that lack immediate financial impact.

**Example False Positive**:
- Title: "Forecasts $1B Launch-Year Revenue, Sees $18B–$22B Over 5 Years"
- Issue: System reacts to impressive numbers without assessing timeline
- Market behavior: Initial reaction fades when traders realize these are speculative long-term forecasts

### Objectives

1. **Distinguish far-future forecasts** (>1 year) from near-term guidance (<1 year)
2. **Pattern-based detection** using title/summary text analysis
3. **Metadata enrichment** to flag far-future forecasts for downstream consumers
4. **No breaking changes** to existing API contracts
5. **High accuracy** (90%+ on far-future detection)

### Success Metrics

- Detect far-future forecast patterns with 90%+ accuracy
- Reduce false positives on speculative long-term forecasts by 60%+
- Near-term guidance (<1 year) does NOT trigger far-future flags
- Integration with existing temporal classification (no conflicts)

## Current State Analysis

### What Exists

**Temporal Classification** (classifier.py):
- Detects three categories: PAST_EVENT, FUTURE_EVENT, GENERAL_TOPIC
- Uses zero-shot NLI with hypothesis: "This is about a future event or forecast"
- Returns boolean classification and confidence scores

**Classification Models** (models/classification.py):
- `TemporalCategory` enum with three values
- `ClassificationScores` with past/future/general scores
- `ClassificationResult` with temporal_category field

**API Response Structure**:
- Returns temporal_category and all scores
- No metadata fields for additional flags/context

### What's Needed

**Pattern Detection**:
- Regex-based title analysis for far-future indicators
- Multi-year timeframe detection ("over 5 years", "by 2028")
- Forecast language detection ("forecasts", "projects", "estimates")

**Metadata Enhancement**:
- New optional field: `far_future_forecast: bool`
- New optional field: `forecast_timeframe: str` with extracted timeframe
- Backward compatible (optional fields)

**Integration Points**:
- Runs after basic temporal classification
- Only applies when temporal_category == FUTURE_EVENT
- Adds supplementary metadata without changing core classification

### Gap Analysis

| Feature | Current | Needed |
|---------|---------|--------|
| Basic future detection | ✓ | ✓ |
| Near vs far-future distinction | ✗ | ✓ |
| Multi-year timeframe detection | ✗ | ✓ |
| Forecast language patterns | ✗ | ✓ |
| Metadata enrichment | ✗ | ✓ |
| Confidence adjustments | ✗ | Future work |

## Architecture Design

### Detection Strategy

**Two-Phase Approach**:

1. **Temporal Classification** (existing): Detects FUTURE_EVENT using NLI
2. **Far-Future Analysis** (new): Pattern matching on title/summary when FUTURE_EVENT detected

**Pattern Categories**:

**Forecast/Projection Language**:
- "forecasts", "projects", "estimates", "expects", "targets"
- "guidance for", "outlook for", "predicts"
- "sees [value] by/over/through"

**Multi-Year Timeframes**:
- "over X years", "X-year", "through 20XX", "by 20XX"
- "cumulative", "long-term", "launch-year"
- Numeric year references >1 year from current date

**Exclusions (Near-Term)**:
- "Q1", "Q2", "Q3", "Q4", "quarter", "quarterly"
- "this year", "next year", "fiscal 20XX" (current/next fiscal year)
- "guidance" without multi-year timeframe

### Data Model Extensions

**ClassificationResult Enhancement**:
- Add optional field: `far_future_forecast: bool | None`
- Add optional field: `forecast_timeframe: str | None` (e.g., "5-year", "by 2028")

**Backward Compatibility**:
- All new fields are optional (None by default)
- Only populated when far-future patterns detected
- Existing consumers ignore unknown fields (Pydantic behavior)

### Pattern Matching Logic

**Simple Boolean Detection**:

```python
is_far_future = (
    matches_multi_year_timeframe(text) and
    not matches_quarterly_language(text)
)
```

**Detection Rationale**:
- Multi-year timeframe is the strongest signal for far-future forecasts
- Quarterly language indicates near-term guidance, excludes from far-future
- Simple boolean logic: if multi-year timeframe present and no quarterly language, it's far-future

### Integration Points

**Classifier Service**:
- Add private method `_analyze_far_future(headline, temporal_category)`
- Call from `classify_headline()` after temporal classification
- Return enriched ClassificationResult

**Configuration**:
- No additional configuration needed (uses existing settings patterns)

**Testing Strategy**:
- Unit tests for pattern matching functions
- Integration tests with real headlines
- Regression tests to ensure no impact on existing classifications

## Implementation Phases

### Phase 1: Pattern Detection Core

**Description**: Implement regex-based pattern detection functions for far-future indicators.

**Core Functionality**:
- Forecast language detection (forecasts, projects, estimates, etc.)
- Multi-year timeframe detection (over X years, by 20XX, X-year)
- Near-term exclusion detection (quarterly, Q1-Q4)
- Numeric year extraction and future year calculation

**Implementation Approach**:
- Create new module: `src/benz_sent_filter/services/forecast_analyzer.py`
- Implement pattern matching functions using regex
- Add configuration constants for patterns and thresholds
- No integration with ClassificationService yet (standalone module)

**Pattern Detection Functions**:
- `matches_multi_year_timeframe(text: str) -> tuple[bool, str | None]` (returns match + timeframe)
- `matches_quarterly_language(text: str) -> bool`
- `is_far_future(text: str) -> tuple[bool, str | None]` (returns decision + timeframe)

**Unit Test Requirements**:
- Create `tests/test_forecast_analyzer.py`
- Test `is_far_future()` with examples from appendix
- Test multi-year timeframe detection (positive/negative cases)
- Test quarterly language exclusion
- Test edge cases: malformed text, ambiguous timeframes

**Example Test Cases**:
- "Forecasts $1B Revenue Over 5 Years" → True (multi-year, no quarterly)
- "Q4 Guidance Raised to $100M" → False (quarterly exclusion)
- "Projects $500M By 2028" → True (multi-year, no quarterly)
- "Reports Q2 Revenue" → False (no multi-year)

**Acceptance Criteria**:
- Pattern functions implemented with regex
- Correctly classifies all appendix examples
- 90%+ accuracy on test suite
- No external dependencies beyond standard library (re module)
- All tests pass

### Phase 2: Data Model Extensions

**Description**: Extend Pydantic models to support far-future forecast metadata.

**Core Functionality**:
- Add optional fields to ClassificationResult
- Ensure backward compatibility (all new fields optional)
- Add validation for new fields
- Update model documentation

**Implementation Approach**:
- Modify `src/benz_sent_filter/models/classification.py`
- Add two new optional fields to ClassificationResult
- Add docstrings explaining when fields are populated
- Ensure Pydantic serialization excludes None values (existing behavior)

**New Fields**:
- `far_future_forecast: bool | None = None` - Whether headline contains far-future forecast patterns
- `forecast_timeframe: str | None = None` - Extracted timeframe (e.g., "5-year", "by 2028")

**Unit Test Requirements**:
- Modify `tests/test_models.py`
- Test ClassificationResult instantiation with new fields
- Test serialization with new fields present
- Test serialization with new fields absent (should exclude from JSON)
- Test backward compatibility (old code can parse new responses)
- Test field validation (types, constraints)

**Acceptance Criteria**:
- ClassificationResult accepts new optional fields
- Fields serialize correctly to JSON
- None values excluded from JSON output (Pydantic default)
- Existing tests pass without modification
- New field documentation clear and accurate

### Phase 3: Service Integration

**Description**: Integrate far-future analysis into ClassificationService.

**Core Functionality**:
- Add far-future analysis to classify_headline method
- Only analyze when temporal_category == FUTURE_EVENT
- Populate new metadata fields when far-future detected
- Respect feature flag (FAR_FUTURE_ENABLED)

**Implementation Approach**:
- Modify `src/benz_sent_filter/services/classifier.py`
- Add private method `_analyze_far_future(headline: str) -> dict`
- Call from `classify_headline()` after temporal classification
- Conditionally populate new fields in ClassificationResult
- Add configuration to `src/benz_sent_filter/config/settings.py`

**Configuration Settings**:
- `FAR_FUTURE_THRESHOLD = 3` - Minimum score to flag as far-future
- `FAR_FUTURE_ENABLED = True` - Feature flag to enable/disable analysis

**Analysis Logic Flow**:
1. Complete existing temporal classification
2. If temporal_category == FUTURE_EVENT:
   - Call forecast_analyzer.is_far_future(headline)
   - If True:
     - Set far_future_forecast = True
     - Set forecast_timeframe from returned value
3. Return ClassificationResult with enriched metadata

**Unit Test Requirements**:
- Modify `tests/test_classifier.py`
- Test far-future analysis with FUTURE_EVENT classifications
- Test no analysis when temporal_category != FUTURE_EVENT
- Test feature flag (enabled/disabled behavior)
- Test threshold boundary conditions
- Test metadata population accuracy
- Test backward compatibility (no new fields when not far-future)

**Acceptance Criteria**:
- Far-future analysis integrated into classify_headline
- Only runs for FUTURE_EVENT classifications
- Feature flag controls behavior
- Metadata fields correctly populated
- No performance degradation (pattern matching is fast)
- All existing tests pass

### Phase 4: API Endpoint Updates

**Description**: Update API endpoints to return enhanced classification results.

**Core Functionality**:
- Single classification endpoint returns new fields when present
- Batch classification endpoint returns new fields when present
- API documentation updated
- Response examples include far-future scenarios

**Implementation Approach**:
- No code changes to `src/benz_sent_filter/api/app.py` (Pydantic handles serialization)
- Update OpenAPI schema documentation
- Add response examples with far-future metadata
- Verify JSON serialization

**Documentation Updates**:
- Add field descriptions to OpenAPI schema
- Add example responses showing far-future forecasts
- Document when fields are populated vs absent
- Update API usage examples

**Unit Test Requirements**:
- Modify `tests/test_api.py`
- Test /classify endpoint with far-future headline
- Test /classify endpoint with near-term forecast
- Test /batch-classify with mixed headlines
- Verify JSON response structure
- Verify optional fields excluded when not applicable

**Acceptance Criteria**:
- API returns new fields when far-future detected
- API excludes fields when not far-future
- OpenAPI documentation complete and accurate
- Response examples demonstrate feature
- All API tests pass

### Phase 5: Integration Testing & Validation

**Description**: End-to-end testing with real-world headlines and validation against bead requirements.

**Core Functionality**:
- Integration tests with real model inference
- Validation against bead examples
- Performance benchmarking
- Edge case testing

**Implementation Approach**:
- Create `integration/test_far_future_integration.py`
- Test with examples from bead (TVGN, etc.)
- Test edge cases and boundary conditions
- Measure pattern matching performance
- Validate accuracy metrics

**Test Scenarios**:
- TVGN example: "Forecasts $1B Launch-Year Revenue, Sees $18B–$22B Over 5 Years"
- Near-term guidance: "Q4 Guidance Raised to $100M"
- Mixed: "Projects $500M Revenue By 2028"
- No forecast: "Reports Record Q2 Revenue"
- Edge cases: Malformed text, ambiguous timeframes

**Performance Requirements**:
- Pattern matching adds <10ms per classification
- No regression in existing classification speed
- Memory footprint unchanged

**Unit Test Requirements**:
- Create comprehensive integration test suite
- Test 20+ real-world headlines
- Test all pattern combinations
- Test performance benchmarks
- Test concurrent requests (thread safety)

**Acceptance Criteria**:
- 90%+ accuracy on far-future detection (bead requirement)
- Near-term guidance does NOT trigger false positives
- TVGN-type examples correctly flagged
- Pattern matching performance acceptable
- All integration tests pass
- No regression in existing functionality

### Phase 6: Documentation & Examples

**Description**: Update documentation with far-future forecast feature usage and examples.

**Core Functionality**:
- README updated with feature description
- API usage examples with far-future forecasts
- Pattern documentation for users
- Migration guide (if needed)

**Implementation Approach**:
- Update README.md with feature section
- Add examples to API documentation
- Document configuration options
- Add troubleshooting guide

**Documentation Sections**:
- Feature overview and use cases
- API request/response examples
- Configuration options (threshold, feature flag)
- Pattern matching behavior
- Common patterns detected
- Integration with benz_evaluator

**Example Code**:
- Python client example using far-future metadata
- cURL examples showing responses
- Filtering examples based on far_future_forecast flag

**Acceptance Criteria**:
- README includes far-future forecast section
- API documentation complete with examples
- Configuration options documented
- Integration examples provided
- User-facing documentation clear and accurate

## Non-Functional Requirements

### Performance
- Pattern matching adds <10ms per classification
- No memory overhead (regex compiled once)
- Thread-safe (no shared mutable state)

### Reliability
- Graceful degradation if pattern matching fails
- Feature flag allows disabling if issues arise
- No impact on existing classifications

### Maintainability
- Pattern configurations externalized (easy to update)
- Clear separation between pattern detection and classification
- Comprehensive test coverage (>90%)

### Scalability
- Regex patterns optimized for speed
- No external API calls (all local computation)
- Stateless design (supports horizontal scaling)

## Future Enhancements

### Post-MVP Features

**Dynamic Timeframe Calculation**:
- Calculate exact months/years from current date
- Distinguish 13-month vs 5-year forecasts
- Graduated confidence adjustments based on timeframe

**Confidence Score Adjustments**:
- Reduce confidence for far-future forecasts
- Add confidence_adjustment field
- Integration with benz_evaluator scoring

**Advanced Pattern Learning**:
- Track which patterns correlate with false positives
- Allow pattern weight tuning based on performance data
- Machine learning for pattern discovery

**Company-Specific Timeframes**:
- Different thresholds for different industries
- Biotech: FDA approval timelines (3-5 years normal)
- Tech: Product roadmaps (2-3 years normal)

## Risk Assessment

### Technical Risks

**Risk**: Regex patterns miss edge cases
- Mitigation: Comprehensive test suite, continuous monitoring
- Impact: Medium (some far-future forecasts not detected)

**Risk**: False positives on legitimate forecasts
- Mitigation: Quarterly exclusion logic, threshold tuning
- Impact: Low (can adjust thresholds)

**Risk**: Performance degradation
- Mitigation: Benchmark tests, compiled regex
- Impact: Low (pattern matching is fast)

### Integration Risks

**Risk**: Breaking changes to API consumers
- Mitigation: Optional fields, backward compatibility testing
- Impact: Very Low (Pydantic excludes None)

**Risk**: Conflicts with existing temporal classification
- Mitigation: Only enhances FUTURE_EVENT, no replacement
- Impact: Very Low (additive feature)

## Appendix

### Pattern Examples

**Far-Future Patterns (Should Detect)**:
- "Forecasts $1B Launch-Year Revenue, Sees $18B–$22B Over 5 Years"
- "Projects $500M Revenue By 2028"
- "Estimates 5-Year Cumulative Sales of $2B"
- "Guidance: Expects $100M Revenue Through 2027"
- "Targets $2B Annual Revenue by 2030"

**Near-Term Patterns (Should NOT Detect)**:
- "Q4 Guidance Raised to $100M"
- "Reports Q2 Revenue of $1B"
- "Announces $500M Contract Win"
- "Fiscal 2025 Guidance: $2B Revenue"
- "Next Quarter Expectations: $150M"

**Edge Cases**:
- "Expects $1B Revenue Upon FDA Approval" (conditional, no timeframe)
- "Long-term Growth Target: 15% CAGR" (no specific year)
- "5-Year Plan Unveiled" (plan vs forecast)
- "Q4 2027 Revenue Projected at $500M" (far quarter, specific)

### Configuration Reference

No additional configuration needed. Far-future detection uses simple pattern matching with no tunable parameters.

### Related Work

- Bead: benz_sent_filter-d687 (source requirement)
- Bead: benz_sent_filter-76c6 (vanity metrics - complementary filter)
- Bead: benz_sent_filter-1754 (routine operations - complementary filter)
- Epic: benz_sent_filter-410d (MNLS Classification API - base system)

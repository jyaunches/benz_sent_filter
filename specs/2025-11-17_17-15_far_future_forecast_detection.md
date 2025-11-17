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

### Phase 1: Pattern Detection Core [COMPLETED: 12516f4]

**Description**: Implement regex-based pattern detection functions for far-future indicators.

**Core Functionality**:
- Multi-year timeframe detection (over X years, by 20XX, X-year)
- Near-term exclusion detection (quarterly, Q1-Q4)
- Boolean far-future decision based on patterns

**Implementation Approach**:
- Create new module: `src/benz_sent_filter/services/forecast_analyzer.py`
- Implement pattern matching functions using regex
- Focus on simplicity and clarity

**Pattern Detection Functions**:
- `matches_multi_year_timeframe(text: str) -> tuple[bool, str | None]` (returns match + timeframe)
- `matches_quarterly_language(text: str) -> bool`
- `is_far_future(text: str) -> tuple[bool, str | None]` (returns decision + timeframe)

**Test Requirements**:
- Test `is_far_future()` behavior through service integration tests
- Use critical examples from appendix (lines 490-508) as test cases
- Focus on behavior, not implementation details

**Acceptance Criteria**:
- Pattern functions implemented with regex
- Correctly classifies critical appendix examples
- No external dependencies beyond standard library (re module)
- Integration tests pass

### Phase 2: Data Model Extensions [COMPLETED: 537151d]

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

**Test Requirements**:
- Test ClassificationResult with new fields via API tests
- Verify serialization behavior (present/absent fields)

**Acceptance Criteria**:
- ClassificationResult accepts new optional fields
- Fields serialize correctly to JSON
- None values excluded from JSON output (Pydantic default)
- Existing tests pass without modification

### Phase 3: Service Integration [COMPLETED: 2f39f61]

**Description**: Integrate far-future analysis into ClassificationService.

**Core Functionality**:
- Add far-future analysis to classify_headline method
- Only analyze when temporal_category == FUTURE_EVENT
- Populate new metadata fields when far-future detected

**Implementation Approach**:
- Modify `src/benz_sent_filter/services/classifier.py`
- Add private method `_analyze_far_future(headline: str) -> dict`
- Call from `classify_headline()` after temporal classification
- Conditionally populate new fields in ClassificationResult

**Configuration Settings**:
- No additional configuration needed

**Analysis Logic Flow**:
1. Complete existing temporal classification
2. If temporal_category == FUTURE_EVENT:
   - Call forecast_analyzer.is_far_future(headline)
   - If True:
     - Set far_future_forecast = True
     - Set forecast_timeframe from returned value
3. Return ClassificationResult with enriched metadata

**Test Requirements**:
- Test classifier behavior with far-future headlines
- Test FUTURE_EVENT classifications get far-future analysis
- Test other classifications do not get far-future metadata

**Acceptance Criteria**:
- Far-future analysis integrated into classify_headline
- Only runs for FUTURE_EVENT classifications
- Metadata fields correctly populated
- All existing tests pass

### Phase 4: API Endpoint Updates [COMPLETED: 9411759]

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

**Test Requirements**:
- Test /classify endpoint with far-future and near-term headlines
- Test /batch-classify with mixed headlines
- Verify JSON response structure

**Acceptance Criteria**:
- API returns new fields when far-future detected
- API excludes fields when not far-future
- OpenAPI documentation updated
- All API tests pass

### Phase 5: Integration Testing & Validation [COMPLETED: 09c70be]

**Description**: End-to-end testing with real-world headlines and validation against bead requirements.

**Core Functionality**:
- End-to-end validation with real headlines
- Verification against bead examples

**Implementation Approach**:
- Create `integration/test_far_future_integration.py`
- Test with critical examples from appendix
- Validate bead requirements

**Critical Test Cases**:
- TVGN example: "Forecasts $1B Launch-Year Revenue, Sees $18B–$22B Over 5 Years" → far_future = True
- Near-term: "Q4 Guidance Raised to $100M" → far_future = False or None
- Edge cases from appendix (lines 504-508)

**Acceptance Criteria**:
- 90%+ accuracy on far-future detection (bead requirement)
- Near-term guidance does NOT trigger false positives
- TVGN-type examples correctly flagged
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
- Add troubleshooting guide

**Documentation Sections**:
- Feature overview and use cases
- API request/response examples
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
- Integration examples provided
- User-facing documentation clear and accurate

## Non-Functional Requirements

### Performance
- Pattern matching adds <10ms per classification
- No memory overhead (regex compiled once)
- Thread-safe (no shared mutable state)

### Reliability
- Graceful degradation if pattern matching fails
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

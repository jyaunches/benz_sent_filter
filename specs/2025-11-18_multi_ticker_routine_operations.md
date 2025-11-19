# Multi-Ticker Routine Operations Endpoint

**Created**: 2025-11-18
**Status**: Draft
**Priority**: High

## Overview & Objectives

### Problem Statement

Clients consuming the sentiment filter API need to classify the same headline against multiple ticker symbols to determine routine operations status. Currently, this requires multiple full classification requests, each re-computing the expensive core classification (~2s) and company relevance checks (~500ms) for the same headline.

For a single headline with 2 tickers:
- Current: 2 full requests × ~3s each = **6 seconds total**
- Optimal: 1 core classification (~2s) + 2 routine checks (~500ms each) = **3 seconds total** (50% reduction)

### Objectives

1. **Performance**: Reduce multi-ticker query time by 40-50% by eliminating redundant model inference
2. **Efficiency**: Run core classification once, apply routine operations filter per ticker
3. **Backward Compatibility**: Maintain existing `/classify` endpoint unchanged
4. **API Design**: Provide intuitive endpoint for multi-ticker routine operations queries

### Success Metrics

- Multi-ticker requests complete in <4s for 3 tickers (vs ~9s currently)
- Zero changes required to existing `/classify` endpoint behavior
- All existing tests pass without modification

## Current State Analysis

### Existing Implementation

The `ClassificationService.classify_headline()` method (src/benz_sent_filter/services/classifier.py:134-218) performs sequential operations:

1. **Core classification** (line 151): MNLS inference with 5 candidate labels (~1.5-2s)
2. **Far-future analysis** (line 183): Regex-based pattern matching (~10ms)
3. **Routine operations** (line 186): MNLS-based detection (~300-500ms)
4. **Company relevance** (line 190): Optional MNLS inference (~500ms)

### What's Needed

A new endpoint that:
- Accepts one headline and multiple ticker symbols
- Performs core classification ONCE
- Applies routine operations filter PER ticker symbol
- Returns structured results showing routine operations status for each ticker
- Does NOT re-run core classification or company relevance checks

### Gap Analysis

**Missing Components**:
1. New API endpoint for multi-ticker routine operations
2. Service method that separates core classification from per-ticker routine analysis
3. Response model for multi-ticker routine operations results
4. Integration tests validating performance improvement

## Architecture Design

### API Design

**New Endpoint**: `POST /classify/routine-operations/multi-ticker`

**Request Schema**:
```
{
  "headline": "Bank of America announces quarterly dividend payment",
  "ticker_symbols": ["BAC", "JPM", "C"]
}
```

**Response Schema**:
```
{
  "headline": "Bank of America announces quarterly dividend payment",
  "core_classification": {
    "is_opinion": false,
    "is_straight_news": true,
    "temporal_category": "GENERAL_TOPIC",
    "scores": { ... }
  },
  "routine_operations_by_ticker": {
    "BAC": {
      "routine_operation": true,
      "routine_confidence": 0.87,
      "routine_metadata": { ... }
    },
    "JPM": {
      "routine_operation": true,
      "routine_confidence": 0.65,
      "routine_metadata": { ... }
    },
    "C": {
      "routine_operation": true,
      "routine_confidence": 0.71,
      "routine_metadata": { ... }
    }
  }
}
```

### Service Architecture

The implementation requires separating `classify_headline()` into reusable components:

1. **Core classification method**: Runs MNLS inference once, returns base classification
2. **Routine operations method**: Already exists as `_analyze_routine_operation()`, can be called independently
3. **Multi-ticker orchestration method**: Calls core once, then routine per ticker

This separation enables the new endpoint while keeping existing endpoint logic intact.

### Component Integration

**Files to Modify**:
- `src/benz_sent_filter/models/classification.py`: Add new response models
- `src/benz_sent_filter/services/classifier.py`: Add multi-ticker classification method
- `src/benz_sent_filter/api/routes.py`: Add new endpoint
- `tests/test_classifier.py`: Add unit tests for multi-ticker method
- `tests/test_models.py`: Add unit tests for new models
- `tests/test_routes.py`: Add unit tests for new endpoint
- `integration/test_multi_ticker_routine.py`: Add integration tests
- `integration/test_filter_activation_report.py`: Add multi-ticker analysis

**No Breaking Changes**: Existing `/classify` endpoint remains unchanged, uses same service methods.

## Phase 1: Core Service Method for Multi-Ticker Classification [COMPLETED: 7c01602]

### Description

Implement the core service logic that separates one-time classification from per-ticker routine operations analysis. This phase focuses on the service layer only, without API exposure.

### Core Functionality

Add a new method to `ClassificationService` that:
- Accepts one headline and a list of ticker symbols
- Performs core MNLS classification once
- Iterates through ticker symbols, running routine operations detection for each
- Returns structured data with core classification + per-ticker routine results
- Reuses existing `_analyze_routine_operation()` method for each ticker

The method should perform exactly the same core classification as `classify_headline()` but separate the per-ticker analysis loop.

### Implementation Approach

**Modify**: `src/benz_sent_filter/services/classifier.py`

Add new public method `classify_headline_multi_ticker()`:
- Extract core classification logic (lines 150-180 from existing method)
- Run core classification once
- Loop through ticker_symbols, calling `_analyze_routine_operation()` for each
- Build dictionary mapping ticker symbol to routine operations result
- Return both core classification data and ticker-specific results

The existing `classify_headline()` remains unchanged to ensure backward compatibility.

### Unit Test Requirements

**Update**: `tests/test_classifier.py`

Add new test methods covering:
1. **Basic multi-ticker**: Single headline, 3 tickers, verify routine operations run for each
2. **Empty ticker list**: Verify graceful handling
3. **Single ticker**: Verify equivalent to single-ticker routine operations
4. **Different routine results**: Headlines that trigger different routine scores per ticker
5. **Core classification consistency**: Verify core classification matches single-headline results
6. **Performance validation**: Assert multi-ticker is faster than N sequential calls (mock timing)

Mock the MNLS pipeline to control timing and verify number of inference calls.

### Acceptance Criteria

- [ ] New method `classify_headline_multi_ticker()` exists in `ClassificationService`
- [ ] Method accepts `headline: str` and `ticker_symbols: list[str]` parameters
- [ ] Core MNLS classification runs exactly once per call
- [ ] Routine operations detection runs once per ticker symbol
- [ ] Returns structured data with core classification and per-ticker routine results
- [ ] All new unit tests pass with 100% coverage of new method
- [ ] Existing tests for `classify_headline()` pass unchanged
- [ ] No changes to existing API endpoints

## Phase 2: Response Models for Multi-Ticker Results [COMPLETED: 37f483e]

### Description

Define Pydantic models for the multi-ticker routine operations response structure. These models provide type safety, validation, and API documentation.

### Core Functionality

Create response models that represent:
- Core classification results (subset of existing ClassificationResult)
- Per-ticker routine operations results
- Overall multi-ticker response structure

Models should:
- Use `exclude_none=True` for optional fields
- Provide clear field descriptions for API documentation
- Reuse existing model components where possible
- Support JSON serialization for API responses

### Implementation Approach

**Modify**: `src/benz_sent_filter/models/classification.py`

Add three new Pydantic models:

1. **CoreClassification**: Contains only core classification fields (opinion, news, temporal, scores)
   - Subset of fields from existing `ClassificationResult`
   - No company relevance, no routine operations
   - Represents the one-time classification result

2. **RoutineOperationResult**: Contains routine operations detection for one ticker
   - Fields: routine_operation, routine_confidence, routine_metadata
   - Extracted from existing `ClassificationResult` routine fields
   - Represents per-ticker routine analysis

3. **MultiTickerRoutineResponse**: Top-level response model
   - Field: headline (str)
   - Field: core_classification (CoreClassification)
   - Field: routine_operations_by_ticker (dict[str, RoutineOperationResult])
   - Combines core classification with ticker-specific results

### Unit Test Requirements

**Update**: `tests/test_models.py`

Add new test methods covering:
1. **CoreClassification validation**: Verify all required fields, optional field handling
2. **RoutineOperationResult validation**: Verify metadata structure, confidence bounds
3. **MultiTickerRoutineResponse validation**: Verify nested structure, dict key validation
4. **JSON serialization**: Verify models serialize correctly with exclude_none
5. **Field documentation**: Verify model schema includes descriptions
6. **Invalid data handling**: Verify validation errors for malformed inputs

Test both valid construction and validation error cases.

### Acceptance Criteria

- [ ] `CoreClassification` model defined with opinion, news, temporal, scores fields
- [ ] `RoutineOperationResult` model defined with routine operation fields
- [ ] `MultiTickerRoutineResponse` model defined with headline and nested results
- [ ] All models use `exclude_none=True` configuration
- [ ] All models include field descriptions for API docs
- [ ] Models serialize to JSON correctly
- [ ] All new unit tests pass with 100% coverage
- [ ] Existing model tests pass unchanged

## Phase 3: API Endpoint for Multi-Ticker Routine Operations [COMPLETED: ddae929]

### Description

Add the new REST API endpoint that exposes multi-ticker routine operations functionality to clients. This phase integrates the service method and response models into the FastAPI application.

### Core Functionality

Create new endpoint `POST /classify/routine-operations/multi-ticker` that:
- Accepts JSON request with headline and list of ticker symbols
- Validates request payload using Pydantic request model
- Calls `classify_headline_multi_ticker()` service method
- Returns structured response using `MultiTickerRoutineResponse` model
- Handles errors gracefully with appropriate HTTP status codes

The endpoint should follow existing API patterns for error handling, logging, and response formatting.

### Implementation Approach

**Modify**: `src/benz_sent_filter/api/routes.py`

Add new endpoint handler:
1. Define request model with headline and ticker_symbols fields
2. Add POST route at `/classify/routine-operations/multi-ticker`
3. Validate request using Pydantic model
4. Call service method with validated inputs
5. Map service response to `MultiTickerRoutineResponse` model
6. Return structured JSON response
7. Add error handling for invalid inputs, model failures

Follow patterns from existing `/classify` endpoint for consistency.

**Add**: OpenAPI documentation with example request/response in endpoint docstring.

### Unit Test Requirements

**Update**: `tests/test_routes.py`

Add new test methods using FastAPI TestClient:
1. **Valid multi-ticker request**: Verify 200 response with correct structure
2. **Empty ticker list**: Verify appropriate error response
3. **Missing required fields**: Verify 422 validation error
4. **Invalid ticker format**: Verify validation error handling
5. **Service exception handling**: Mock service to raise exception, verify 500 response
6. **Response schema validation**: Verify response matches OpenAPI schema
7. **Integration with existing endpoints**: Verify no impact on `/classify` endpoint

Mock the classification service to control responses and test error paths.

### Acceptance Criteria

- [ ] New endpoint `POST /classify/routine-operations/multi-ticker` exists
- [ ] Endpoint accepts request with headline and ticker_symbols
- [ ] Request validation rejects invalid payloads with 422 status
- [ ] Successful requests return 200 with `MultiTickerRoutineResponse` structure
- [ ] Service exceptions return 500 with error details
- [ ] OpenAPI documentation includes endpoint with examples
- [ ] All new unit tests pass with 100% coverage
- [ ] Existing API tests pass unchanged
- [ ] Manual testing with `curl` or similar works correctly

## Phase 4: Integration Testing and Performance Validation

### Description

Create comprehensive integration tests that validate the end-to-end functionality, measure the actual performance improvement of the multi-ticker endpoint against sequential single-ticker requests, and extend the filter activation report to analyze multi-ticker scenarios.

### Core Functionality

Integration tests should:
- Test real MNLS model inference (not mocked)
- Measure actual response times with real headlines
- Compare multi-ticker endpoint vs N sequential `/classify` calls
- Validate performance improvement meets success metrics (40-50% reduction)
- Test edge cases with production-like data
- Add multi-ticker analysis to filter activation report
- Verify backward compatibility - existing tests still pass

### Implementation Approach

**Update**: `integration/test_filter_activation_report.py`

Add new test function `test_multi_ticker_filter_activation()`:
- Create test dataset of financial services headlines with multiple related tickers:
  - Bank dividends: "Major banks announce quarterly dividend payments" → [BAC, JPM, C, WFC, GS]
  - Industry earnings: "Financial services sector reports strong Q3 earnings" → [BAC, JPM, MS, GS]
  - Regulatory news: "Fed announces new capital requirements for major banks" → [BAC, JPM, C, WFC]
- For each headline, call new `/classify/routine-operations/multi-ticker` endpoint
- Measure total time for multi-ticker call
- Compare to sequential single-ticker calls (measure individual times and sum)
- Report per-ticker routine operations results showing time savings
- Validate core classification consistency (same across all tickers)
- Print summary statistics: total headlines tested, average tickers per headline, average time saved

Add analysis section to existing `test_filter_activation_report()`:
- After processing all 55 articles, analyze multi-ticker opportunities
- Count headlines that could benefit from multi-ticker endpoint (financial services sector)
- Estimate total time savings if multi-ticker endpoint was used
- Add to summary statistics:
  ```
  MULTI-TICKER OPPORTUNITY ANALYSIS:
  - Headlines with multi-ticker potential: 12 (21.8%)
  - Estimated time savings: 67.2s total
  - Average savings per multi-ticker headline: 5.6s
  ```

**Create**: `integration/test_multi_ticker_routine.py`

Add comprehensive multi-ticker integration tests:
1. **End-to-end multi-ticker test**: Real API call with 3 tickers, verify results
2. **Performance comparison**: Time multi-ticker vs 3 sequential calls, assert improvement
3. **Consistency validation**: Verify multi-ticker core classification matches single call
4. **Per-ticker accuracy**: Verify routine operations results match individual calls
5. **Real financial headlines**: Test with actual bank dividend/earnings headlines
6. **Mixed routine results**: Headlines that are routine for some tickers, not others
7. **Edge case tests**: Empty ticker list, duplicate tickers, invalid ticker formats

**Update**: `integration/test_classification_integration.py`

Add regression tests to existing file:
- Test that existing single-ticker endpoint still works with routine operations
- Verify existing performance benchmarks still pass
- Add test for company_symbol parameter if not already covered
- Ensure batch processing with routine operations still meets performance targets

**Update**: `integration/test_company_relevance_multi.py` (if exists)

Verify no regression when routine operations filter is active:
- Company relevance detection should work identically
- Performance overhead should not increase
- Results should be consistent with/without routine operations filter

**Update**: `integration/README.md`

Document:
- Purpose of multi-ticker integration tests
- Expected performance characteristics
- How to interpret performance test results
- When to run integration tests (not in CI, requires model download)

### Unit Test Requirements

No new unit tests required for integration test phase. Validation involves:
- Running all existing integration tests to verify no regression
- Running new multi-ticker integration tests with real model
- Manual review of filter activation report output

Integration tests should be runnable with `pytest integration/test_multi_ticker_routine.py`.

### Acceptance Criteria

- [ ] New `test_multi_ticker_filter_activation()` added to filter activation report
- [ ] Filter activation report includes multi-ticker analysis section
- [ ] New `integration/test_multi_ticker_routine.py` created with comprehensive tests
- [ ] All tests in `integration/test_multi_ticker_routine.py` pass with real model
- [ ] Performance test validates 40-50% time reduction for 3-ticker queries
- [ ] Consistency test confirms core classification matches single-ticker calls
- [ ] Existing integration tests in `test_classification_integration.py` pass unchanged
- [ ] Existing integration tests in `test_filter_activation_report.py` pass unchanged
- [ ] No performance regression in existing single-ticker endpoint tests
- [ ] Multi-ticker report shows time savings vs sequential single-ticker calls
- [ ] Integration test documentation updated
- [ ] Performance results logged for benchmark tracking

## Phase 5: Documentation and API Examples

### Description

Update all documentation to include the new multi-ticker endpoint, provide usage examples, and update the CLAUDE.md file with new API patterns.

### Core Functionality

Documentation updates should:
- Explain when to use multi-ticker vs single-ticker endpoints
- Provide curl examples and Python client code
- Document performance characteristics and best practices
- Update architecture diagrams if applicable
- Add troubleshooting guidance

### Implementation Approach

**Modify**: `CLAUDE.md`

Add section under "API Design" covering:
- New `/classify/routine-operations/multi-ticker` endpoint
- Use case: same headline, multiple tickers
- Performance characteristics: 40-50% faster than sequential calls
- Request/response examples
- When to use multi-ticker vs batch endpoint

**Create**: `docs/api_examples.md` (if doesn't exist) or update existing

Add examples showing:
- curl command for multi-ticker request
- Python requests library example
- Expected response structure
- Error handling examples
- Performance comparison data

**Update**: `README.md` (if exists)

Add multi-ticker endpoint to API overview section.

### Unit Test Requirements

No new unit tests required for documentation phase. Validation involves:
- Manual review of documentation accuracy
- Testing all code examples to ensure they work
- Verifying curl commands execute successfully

### Acceptance Criteria

- [ ] CLAUDE.md updated with multi-ticker endpoint documentation
- [ ] API examples document created or updated with working examples
- [ ] All code examples tested and verified to work correctly
- [ ] Performance characteristics documented with actual measurements from Phase 5 tests
- [ ] Use case guidance clearly explains when to use each endpoint
- [ ] Troubleshooting section added for common issues
- [ ] README updated with new endpoint (if README exists)
- [ ] Integration test report findings documented as examples

## Implementation Notes

### Backward Compatibility

The existing `/classify` endpoint remains completely unchanged:
- Same request schema
- Same response schema
- Same performance characteristics
- Same service method implementation

Clients using `/classify` experience zero impact.

### Performance Optimization Opportunities

Future enhancements (not in this spec):
- Batch routine operations detection across all tickers
- Caching of company context data per ticker
- Parallel execution of per-ticker routine checks

These are deferred to maintain simplicity in initial implementation.

### Error Handling

Multi-ticker endpoint should handle:
- Empty ticker list: Return error or return core classification only
- Duplicate tickers: Deduplicate before processing
- Invalid ticker format: Validate ticker symbol format
- Service failures: Return partial results or full failure

Error handling should be consistent with existing `/classify` endpoint patterns.

### Testing Strategy

- **Unit tests**: Mock MNLS pipeline, focus on logic correctness
- **Integration tests**: Real model, focus on performance and accuracy
- **Manual testing**: Use real API calls during development

Integration tests are critical for validating performance improvements.

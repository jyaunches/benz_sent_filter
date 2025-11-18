# Specification: Routine Business Operations Filter

**Created**: 2025-11-17
**Status**: Draft
**Issue**: benz_sent_filter-1754
**Priority**: 2

## Overview & Objectives

### Problem Statement

The sentiment classification service currently processes all financial news equally, regardless of whether articles describe material events or routine business operations. This leads to false positives where articles containing large dollar amounts trigger high-priority classifications, even when the transactions are:

1. **Process announcements** rather than completed transactions (e.g., "begins marketing" vs "completes sale")
2. **Routine operations** that occur regularly in the normal course of business
3. **Financially immaterial** relative to company scale, despite impressive absolute numbers

**Example**: Fannie Mae routinely sells loan portfolios worth hundreds of millions of dollars. An article titled "Fannie Mae Begins Marketing Its Most Recent Sale Of Reperforming Loans... $560.5M" sounds significant but represents 0.014% of Fannie Mae's ~$4 trillion in total assets - a routine treasury operation, not a material event.

### Objectives

1. Detect articles describing routine business operations with 85%+ accuracy
2. Identify process announcements (early-stage) vs completed transactions
3. Assess materiality relative to company size, not absolute dollar amounts
4. Reduce false positives on routine operations by 50%+
5. Provide transparency through per-dimension confidence scores and metadata
6. Focus exclusively on financial services industry (loan sales, buybacks, dividends, refinancing)

### Success Criteria

- FNMA-type routine loan sales are correctly flagged
- Major transactions (acquisitions, large contracts, exceptional events) do NOT trigger
- Filter works without requiring company-specific configuration
- Integration maintains existing API contract
- Performance impact < 100ms per classification

## Current State Analysis

### What Exists

The benz_sent_filter service currently provides:
- MNLS-based sentiment classification for article titles
- Opinion vs News detection
- Temporal category classification (past/future/general)
- FastAPI REST endpoints for single and batch processing
- Pydantic models for request/response validation

### What's Needed

**New Capabilities**:
1. Routine operation detection logic
2. Process language pattern matching
3. Materiality assessment (relative to company context)
4. Frequency indicator detection
5. Industry-aware transaction type classification

**Integration Points**:
- Add routine_operation flag to classification response
- Include materiality metadata (process_stage, relative_size)
- Provide confidence adjustments based on routine operation detection
- Extend API models to support new fields

**Data Requirements**:
- Company context data (market cap, revenue, total assets, industry)
- Pattern dictionaries for process language, frequency indicators
- Industry-specific transaction type mappings

### Gap Analysis

**Missing Components**:
- No mechanism to assess transaction materiality
- No process language detection
- No company context integration
- No relative size calculations
- No industry-aware classification logic

**Technical Challenges**:
1. **Company Context**: Need efficient lookup for company metrics without database integration
2. **Pattern Matching**: Balance precision vs recall for process language detection
3. **Materiality Thresholds**: Industry-specific thresholds for what constitutes "routine"
4. **Performance**: Additional classification logic must not degrade response times
5. **Generalization**: Must work across industries without manual configuration

## Architecture Design

### Detection Strategy

#### 1. Process Language Detection

Identify articles describing processes/intentions rather than completed events:

**Pattern Categories**:
- **Initiation**: "begins", "starts", "initiates", "commences", "launches"
- **Marketing/Offering**: "marketing", "available for purchase", "opens bidding", "seeks bids"
- **Planning**: "files to", "plans to", "intends to", "expects to"
- **Evaluation**: "exploring options", "considering", "evaluating", "reviewing"

**Weighted Scoring**:
- Strong process indicators (e.g., "begins marketing") = +2 points
- Moderate indicators (e.g., "available for") = +1 point
- Multiple indicators compound the score

#### 2. Routine Transaction Type Detection

Financial services transaction patterns that indicate routine operations:

**Financial Services Patterns**:
- Loan portfolio sales ("sale of reperforming loans", "loan portfolio", "mortgage-backed securities")
- Regular buyback programs ("buyback program", "repurchase program", "share repurchase")
- Scheduled dividends ("quarterly dividend", "regular dividend", "dividend payment")
- Debt refinancing ("refinancing", "bond issuance", "debt offering")

**Detection Approach**:
- Pattern matching on transaction type keywords for financial services
- Frequency indicator correlation (e.g., "most recent", "another", "continues")

#### 3. Materiality Assessment

Evaluate financial significance relative to company scale:

**Threshold Levels** (configurable):
- **Market Cap Ratio**: transaction_value / market_cap < 0.01 → immaterial
- **Revenue Ratio**: transaction_value / annual_revenue < 0.05 → routine
- **Asset Ratio** (financials): transaction_value / total_assets < 0.005 → routine

**Materiality Scoring**:
- Immaterial (ratio < lower threshold): -2 points
- Borderline (ratio < upper threshold): -1 point
- Material (ratio > upper threshold): 0 points (no adjustment)

**Dollar Amount Extraction**:
- Parse financial figures from title and summary
- Support formats: "$560M", "$1.5 billion", "€100M", etc.
- Handle ranges: "between $50M and $100M" → use midpoint

#### 4. Frequency Indicator Detection

Identify language suggesting recurring/ongoing operations:

**Patterns**:
- **Recurrence**: "most recent", "latest", "another", "continues"
- **Schedule**: "quarterly", "annual", "regular", "ongoing"
- **Program**: "as part of", "in line with", "pursuant to"

**Scoring**:
- Frequency indicator present: +1 point to routine score
- Multiple indicators: +2 points

### Classification Logic

**Decision Algorithm**:

```
routine_score = 0
materiality_score = 0

# Score routine indicators
if has_process_language(title, summary):
    routine_score += 2
if has_frequency_indicators(title, summary):
    routine_score += 1
if matches_routine_transaction_type(title, company_industry):
    routine_score += 1

# Score materiality
if transaction_value AND company_context:
    ratio = calculate_materiality_ratio(transaction_value, company_context)
    if ratio < IMMATERIAL_THRESHOLD:
        materiality_score = -2
    elif ratio < ROUTINE_THRESHOLD:
        materiality_score = -1

# Final decision
if routine_score >= 2 AND materiality_score <= -1:
    flag = "routine_operation_immaterial"
    confidence_adjustment = 0.3  # Reduce confidence in materiality
```

**Per-Dimension Confidence Scores**:

Each classification dimension provides independent confidence:
- `opinion_classification.confidence`: Confidence in opinion vs news determination
- `temporal_classification.confidence`: Confidence in past/future/general categorization
- `routine_operation.confidence`: Confidence in routine operation detection

**Routine Operation Confidence Calculation**:

Base confidence: 0.5

Factors that increase confidence:
- Strong pattern matches (routine_score >= 3): +0.2
- Clear materiality assessment (materiality_score <= -2): +0.2
- Company context available: +0.15

Factors that decrease confidence:
- Conflicting signals (superlatives + routine patterns): -0.3

Final confidence clamped to [0.0, 1.0]

Example formula:
```
confidence = 0.5  # base
if routine_score >= 3:
    confidence += 0.2
if materiality_score <= -2:
    confidence += 0.2
if company_context_available:
    confidence += 0.15
if has_conflicting_signals:
    confidence -= 0.3
confidence = max(0.0, min(1.0, confidence))
```

### Data Model Extensions

**Classification Response Enhancement**:

Multi-dimensional response structure with independent confidence per dimension:

```json
{
  "opinion_classification": {
    "result": "opinion",
    "confidence": 0.85
  },
  "temporal_classification": {
    "result": "past",
    "confidence": 0.72
  },
  "routine_operation": {
    "result": true,
    "confidence": 0.91,
    "metadata": {
      "routine_score": 3,
      "materiality_score": -2,
      "materiality_ratio": 0.00014,
      "transaction_value": 560500000,
      "process_stage": "early",
      "detected_patterns": ["process_language", "routine_transaction", "frequency_indicator"]
    }
  }
}
```

**Field Definitions**:
- `routine_operation.result`: boolean flag indicating routine operation detection
- `routine_operation.confidence`: float [0.0-1.0] confidence in routine detection
- `routine_operation.metadata.routine_score`: int (0-4) pattern match score
- `routine_operation.metadata.materiality_score`: int (-2 to 0) materiality assessment
- `routine_operation.metadata.process_stage`: string ("early", "ongoing", "completed", "unknown")
  - Determined via simple keyword mapping: "begins"/"starts"/"initiates" → "early", "continues"/"ongoing" → "ongoing", "completes"/"closes"/"announces completion" → "completed"
- `routine_operation.metadata.transaction_value`: float or null (extracted dollar amount)
- `routine_operation.metadata.materiality_ratio`: float or null (transaction / company metric)
- `routine_operation.metadata.detected_patterns`: list of matched pattern types

**Company Context Data**:

Simple dictionary for company metrics used in materiality calculations:
```python
{
    "FNMA": {
        "market_cap": 4000000000,
        "annual_revenue": 25000000000,
        "total_assets": 4000000000000
    },
    "BAC": {
        "market_cap": 300000000000,
        "annual_revenue": 100000000000,
        "total_assets": 3000000000000
    }
}
```

Fields:
- `market_cap`: float (USD)
- `annual_revenue`: float (USD)
- `total_assets`: float (USD)

### Integration Approach

**Service Architecture**:

1. **RoutineOperationDetector** service class (separate module)
   - Encapsulates all detection logic
   - Stateless, thread-safe design
   - Pattern dictionaries loaded at initialization
   - Follows existing pattern: separate service like `forecast_analyzer` module

2. **Company Context Dictionary**
   - Static dictionary mapping ticker symbols to company metrics
   - Hardcoded in detector class for initial implementation
   - Future: integration with external API (FMP, etc.)

3. **Classification Pipeline Extension**
   - **Composition approach**: `ClassificationService` instantiates and calls `RoutineOperationDetector`
   - Routine detection runs in parallel with existing MNLS classification
   - Results merged into unified response with per-dimension confidence
   - No impact on existing classification logic
   - Clean separation of concerns: MNLS logic in ClassificationService, rule-based logic in RoutineOperationDetector

### Edge Cases & Handling

1. **Large Absolute Numbers**
   - Always compute relative ratios
   - Flag articles with large numbers but missing company context
   - Default to neutral (no filtering) when materiality cannot be assessed

2. **Completed vs. Process Transactions**
   - "Completes sale" should NOT trigger (completed = material event)
   - "Begins marketing" should trigger (process = routine operation)
   - Keywords: "completes", "announces completion", "closes" → exclude from routine

3. **Exceptional Events**
   - "Record", "largest ever", "unprecedented" → override routine detection
   - Even routine transaction types can be exceptional
   - Superlatives = high materiality signal

4. **Missing Company Context**
   - Cannot assess materiality without company data
   - Default: only use process language + transaction type patterns
   - Flag for manual review if high routine score but no context

5. **Financial Services Focus**
   - Loan sales, buybacks, dividends, refinancing only
   - No need for cross-industry pattern weighting
   - All patterns specific to financial services operations

6. **Special vs. Regular Dividends**
   - "Special dividend" → material, do NOT filter
   - "Quarterly dividend" → routine, filter if matches schedule
   - Keyword "special" overrides routine classification

## Implementation Phases

### Phase 1: Core Detection Engine

**Description**: Implement the foundational routine operation detection logic with pattern matching and scoring, without company context integration.

**Core Functionality**:
- Process language pattern matching (initiation, marketing, planning keywords)
- Routine transaction type detection (financial services patterns only)
- Frequency indicator detection
- Scoring algorithm that combines pattern matches
- Dollar amount extraction from title text
- Per-dimension confidence calculation for routine_operation

**Implementation Approach**:
- Create `RoutineOperationDetector` service class in `src/benz_sent_filter/services/`
- Define pattern dictionaries as **compiled regex patterns stored as class constants** (following PATTERNS.md)
- Implement pattern matching methods with regex-based detection
- Build scoring logic that aggregates pattern matches
- Add dollar amount extraction utility with support for common formats ($XXM, $XXB, etc.)
- Implement confidence calculation using formula from architecture design
- Return structured result using **single Pydantic model (`RoutineDetectionResult`) with required Phase 1 fields and optional Phase 2 fields** (follows existing `ClassificationResult` pattern with optional company fields)

**Unit Test Requirements**:
- Test each pattern category independently (process, transaction type, frequency)
- Verify scoring algorithm with various pattern combinations
- Test dollar amount extraction across formats ($500M, $1.5 billion, ranges)
- Verify edge cases: empty input, no patterns matched, multiple patterns
- Test pattern case-insensitivity
- Validate score thresholds for classification decisions
- Test confidence calculation across different routine_score values
- Verify confidence adjustments for conflicting signals (superlatives)

**Acceptance Criteria**:
- Process language detection achieves 90%+ precision on test dataset
- Frequency indicators correctly identified in 85%+ of test cases
- Dollar amount extraction handles all common formats (M, B, million, billion)
- Scoring algorithm produces consistent, reproducible results
- Confidence calculation produces values in [0.0, 1.0] range
- Confidence increases appropriately with strong pattern matches
- All unit tests pass with 100% coverage on core detection logic

### Phase 2: Materiality Assessment

**Description**: Add company context integration and relative materiality calculations to filter immaterial transactions based on company scale.

**Core Functionality**:
- Company context dictionary (market cap, revenue, assets)
- Materiality ratio calculations (transaction vs market cap, revenue, assets)
- Materiality threshold configuration (financial services only)
- Materiality scoring logic that adjusts routine detection
- Enhanced confidence calculation with materiality factors

**Implementation Approach**:
- Add static company context using **dataclass** to represent company financial data (following PATTERNS.md)
- Implement materiality calculation methods in detector
- Define materiality thresholds as class constants
- Integrate materiality_score into confidence calculation
- Extend detection result **Pydantic model** to include materiality metadata (ratio, threshold used)
- Update confidence formula to include materiality_score and company_context_available factors
- Use **NamedTuple** for intermediate calculation results (e.g., materiality ratios, threshold comparisons)

**Unit Test Requirements**:
- Test materiality ratio calculations with known values
- Verify threshold application for financial services
- Test missing company context handling (graceful degradation)
- Validate materiality scoring logic with various ratio levels
- Test company context dictionary lookup for known symbols
- Verify confidence calculation with materiality factors (+0.2 for clear materiality, +0.15 for context available)

**Acceptance Criteria**:
- Materiality ratios calculated correctly for all company sizes
- FNMA example ($560M on $4T assets) correctly flagged as immaterial with high confidence
- Missing company context handled without errors (returns null metadata, lower confidence)
- Financial services thresholds applied correctly
- Company context dictionary includes 20+ major financial services symbols
- Confidence calculation correctly incorporates materiality factors
- All materiality tests pass with 95%+ coverage

### Phase 3: API Integration

**Description**: Integrate routine operation detection into existing classification endpoints with backward-compatible API extensions.

**Core Functionality**:
- Restructure classification response to per-dimension format
- Integrate `RoutineOperationDetector` into classification service pipeline
- Return independent confidence scores for each dimension
- Include detailed metadata in routine_operation response
- Maintain backward compatibility with existing MNLS classification

**Implementation Approach**:
- Restructure `ClassificationResponse` Pydantic model to per-dimension format
- Add `opinion_classification`, `temporal_classification`, `routine_operation` fields
- Each dimension includes `result` and `confidence` fields
- `routine_operation` also includes `metadata` field with detailed scoring
- Modify classification service to invoke routine detection in parallel with MNLS
- Add routine detection to both single and batch classification endpoints
- Update API documentation with new response structure
- Ensure existing MNLS classification logic unchanged

**Unit Test Requirements**:
- Test classification response serialization with per-dimension structure
- Verify routine detection integration doesn't break existing MNLS classification
- Test independent confidence scores for each dimension
- Validate batch endpoint handles per-dimension responses correctly
- Test response structure matches documented schema
- Verify API contract with sample requests/responses

**Acceptance Criteria**:
- Response structure matches per-dimension format specification
- All three dimensions (opinion, temporal, routine_operation) included in response
- Each dimension has independent confidence score
- routine_operation.metadata includes all required fields
- API documentation updated with new response structure and examples
- No performance degradation (< 100ms overhead per request)
- Existing MNLS classification accuracy maintained

### Phase 4: Integration Testing & Validation

**Description**: Comprehensive end-to-end testing with real-world examples and validation against acceptance criteria.

**Core Functionality**:
- Integration tests with real news article examples
- Validation against FNMA and other routine operation cases
- False positive analysis (ensure major transactions not filtered)
- Performance benchmarking
- Accuracy measurement against labeled test dataset
- API documentation with examples

**Implementation Approach**:
- Create integration test suite in `integration/test_routine_operations.py`
- Build test dataset with labeled examples (routine vs material)
- Implement accuracy calculation (precision, recall, F1 score)
- Add performance benchmarking tests
- Validate edge cases from architecture design
- Create test fixtures for common scenarios (FNMA, BAC, other financial services companies)
- Update API documentation with per-dimension response examples
- Document confidence calculation factors

**Unit Test Requirements**:
- Integration tests for FNMA loan sale example (should flag as routine with high confidence)
- Tests for major acquisitions (should NOT flag as routine)
- Tests for completed transactions (should NOT flag)
- Tests for exceptional events with superlatives (should NOT flag, or flag with low confidence)
- Performance tests ensuring < 100ms overhead
- Per-dimension confidence validation tests

**Acceptance Criteria**:
- FNMA routine loan sales flagged correctly (100% success on test cases)
- Major transactions (acquisitions, large contracts) NOT flagged (0% false positives)
- Completed transactions NOT flagged as routine
- Overall accuracy 85%+ on labeled test dataset
- False positive rate < 10% on material events
- Performance overhead < 100ms per classification
- All edge cases handled correctly per architecture design
- API documentation includes per-dimension response examples with confidence scores
- At least 5 example use cases provided with sample responses

## Testing Strategy

### Unit Tests
- Pattern matching logic (90%+ coverage)
- Materiality calculations (95%+ coverage)
- Scoring algorithms (100% coverage)
- Configuration loading and validation

### Integration Tests
- End-to-end classification with routine detection
- Real-world examples (FNMA, BAC, JPM, etc.)
- Financial services validation
- Performance benchmarking
- Per-dimension confidence validation

### Regression Tests
- Ensure existing classification accuracy maintained
- Backward compatibility verification
- API contract validation

### Test Datasets
- Labeled examples for routine operations (50+ cases)
- Labeled examples for material events (50+ cases)
- Edge cases covering all identified scenarios
- Financial services coverage (banks, GSEs, insurance, asset managers)

## Performance Considerations

### Targets
- Detection overhead < 100ms per classification
- No degradation to existing classification performance
- Memory footprint < 10MB for pattern dictionaries

### Optimization Strategies
- Compile regex patterns at initialization
- Cache company context lookups
- Parallel execution with existing MNLS classification
- Lazy loading of configuration data

## Future Enhancements

### Short-term
1. Dynamic company context provider (integrate with FMP API or similar)
2. Machine learning-based pattern detection to supplement rule-based approach
3. User feedback loop to refine thresholds and patterns

### Long-term
1. Historical transaction analysis (detect unusual patterns for specific companies)
2. Sector-specific models with fine-tuned thresholds
3. Integration with benz_analyzer for cross-validation
4. Real-time threshold adjustment based on market conditions

## Dependencies

### Internal
- Existing benz_sent_filter classification service
- Pydantic models and FastAPI framework
- Configuration management infrastructure

### External
- None for initial implementation (company context uses static data)
- Future: FMP API or similar for dynamic company context

## Risks & Mitigations

### Risks
1. **False Negatives**: Missing genuinely routine operations
   - Mitigation: Comprehensive test dataset, iterative pattern refinement

2. **False Positives**: Flagging material events as routine
   - Mitigation: Conservative thresholds, superlative detection, exceptional event overrides

3. **Performance Impact**: Detection adds latency
   - Mitigation: Performance testing, optimization, parallel execution

4. **Configuration Complexity**: Too many tunable parameters
   - Mitigation: Sensible defaults, clear documentation, validation

5. **Company Context Availability**: Missing data for materiality assessment
   - Mitigation: Graceful degradation, pattern-based detection without context

### Mitigation Strategies
- Extensive testing with real-world examples
- Conservative default thresholds
- Clear documentation and examples
- Monitoring and logging for production tuning
- Feedback mechanism for continuous improvement

## Success Metrics

### Quantitative
- 85%+ accuracy on labeled test dataset
- 50%+ reduction in false positives on routine operations
- < 100ms performance overhead
- 0% degradation to existing classification accuracy
- < 10% false positive rate on material events
- Confidence scores correlate with classification accuracy

### Qualitative
- Clear, actionable metadata in responses
- Independent confidence per dimension enables use-case specific weighting
- Positive user feedback on reduced noise from routine operations
- Successful application across financial services companies

## Rollout Plan

### Phase 1: Internal Validation
- Deploy to staging environment
- Test with historical data
- Measure accuracy and performance

### Phase 2: Gradual Rollout
- Enable for subset of users
- Monitor false positive/negative rates
- Gather user feedback

### Phase 3: Full Deployment
- Enable for all users
- Monitor production metrics
- Iterate on thresholds based on feedback

### Phase 4: Optimization
- Tune thresholds based on production data
- Add new patterns as edge cases discovered
- Integrate dynamic company context provider

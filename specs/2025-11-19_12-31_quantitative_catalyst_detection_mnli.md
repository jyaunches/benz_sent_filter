# Specification: MNLI-Based Quantitative Catalyst Detection

**Created**: 2025-11-19
**Bead**: benz_sent_filter-f82f
**Related**: IMPL-016 (benz_evaluator) - "Already Priced In" Pattern Suppression
**Status**: Draft

## Overview & Objectives

### Problem Statement

The benz_analyzer system currently dismisses quantitative financial catalysts (special dividends, M&A announcements, buyback programs) based on technical "already priced in" patterns alone. This leads to false negatives where material quantitative catalysts are overlooked because price action has already occurred.

**Root Cause**: benz_analyzer lacks structured detection of whether a headline announces a specific, quantitative financial catalyst.

**Example False Negatives**:
- **UUU**: "Universal Safety Declares $1 Special Dividend..." - Dismissed due to price pattern, ignoring $1/share material catalyst
- **AHL**: "Sompo To Acquire Aspen For $3.5B, Or $37.50/Share..." - $3.5B M&A ignored due to technical patterns
- **RSKD**: "Riskified Board Authorizes Repurchase Of Up To $75M..." - $75M buyback dismissed

### Objectives

1. **Primary**: Create `/detect-quantitative-catalyst` API endpoint that identifies whether article headlines announce specific, quantitative financial catalysts
2. **Detection Capability**: Distinguish between quantitative catalysts (specific dollar amounts, prices) vs vague qualitative updates
3. **Type Classification**: Classify catalyst type (dividend, acquisition, buyback, earnings, guidance)
4. **Value Extraction**: Extract specific quantitative values from headlines ($X, percentages, per-share prices)
5. **Integration Ready**: Provide structured results for benz_analyzer to suppress "already priced in" logic when fresh catalysts detected

### Success Metrics

- 95%+ accuracy extracting dollar amounts, per-share prices from test headlines
- 90%+ accuracy classifying catalyst types on labeled test set
- <1 second response time for single headline classification
- 100% backward compatibility (new endpoint, no existing endpoint changes)
- Ready for benz_analyzer integration (Part 2 of IMPL-016)

## Current State Analysis

### What Exists

**Proven MNLI Patterns in Codebase**:

1. **Binary Classification** (`classifier.py:52-68`):
   - Pattern: Company relevance detection
   - Method: Single hypothesis test ("This article is about {company}")
   - Threshold: 0.5 for boolean conversion
   - Performance: Fast (~200ms), accurate

2. **Multi-Label Classification** (`classifier.py:150-171`):
   - Pattern: Opinion/news detection + temporal categorization
   - Method: Multiple candidate labels tested in single call
   - Scoring: Independent thresholds + argmax for category selection
   - Performance: ~300ms for 5 labels

3. **Hybrid MNLI + Regex** (`routine_detector_mnls.py`):
   - MNLI: Semantic classification ("transformational vs routine")
   - Regex: Value extraction (dollar amounts, keywords)
   - Numeric: Materiality calculations
   - **Success**: 100% accuracy on test set, clean separation of concerns

4. **Pure Regex Pattern Matching** (`forecast_analyzer.py`):
   - Used for: Far-future forecast detection
   - When appropriate: Clear syntactic patterns, no semantic ambiguity

### What's Needed

**Gap**: No mechanism to detect quantitative financial catalysts in headlines.

**Requirements**:
1. Semantic understanding to distinguish catalyst vs non-catalyst contexts
2. Type classification across 5 catalyst categories
3. Value extraction from diverse formats ($1, $3.5B, $37.50/share, 10%)
4. Confidence scoring for downstream decision-making
5. API endpoint following benz_sent_filter conventions

### Why MNLI Over Pure Regex

The original bead (benz_sent_filter-f82f) proposed pure regex approach. However, analysis of codebase patterns and test cases reveals MNLI hybrid approach is superior:

**Semantic Understanding**:
- Regex: "$1" matches both "Declares $1 Dividend" (catalyst) and "Stock Price Reaches $1" (not catalyst)
- MNLI: Understands semantic difference via hypothesis testing

**Paraphrasing Robustness**:
- Regex: Must enumerate all variants ("declares dividend", "announces dividend", "pays dividend", "distributes to shareholders")
- MNLI: Generalizes across phrasings through semantic similarity

**Context-Aware Classification**:
- Regex: "$100M" could be acquisition, buyback, asset purchase, revenue target - requires priority rules
- MNLI: Tests specific hypotheses ("announces acquisition", "announces buyback") for accurate classification

**Proven Success**:
- `routine_detector_mnls.py` achieved 100% accuracy using MNLI + regex hybrid
- All major features in benz_sent_filter use MNLI (company relevance, temporal classification, routine operations)
- Consistency with established architecture patterns

**Tradeoffs**:
- Latency: MNLI adds ~500-700ms vs <10ms for pure regex
- Acceptable: Dedicated endpoint (doesn't slow other classifications), called only when needed by benz_analyzer
- Reliability: MNLI non-determinism negligible in practice, semantic accuracy outweighs speed

## Architecture Design

### Hybrid Approach: MNLI for Detection/Classification + Regex for Value Extraction

Following the proven pattern from `routine_detector_mnls.py`, we separate concerns:

**MNLI Responsibilities** (semantic understanding):
1. Presence detection: Does headline announce quantitative catalyst?
2. Type classification: Which category (dividend, acquisition, buyback, earnings, guidance)?

**Regex Responsibilities** (pattern matching):
1. Value extraction: Extract dollar amounts, percentages, per-share prices as-is from headlines

**Numeric Logic Responsibilities** (confidence calculation):
1. Combine MNLI scores with value count
2. Penalize mismatches (MNLI says catalyst but no values extracted)
3. Boost confidence for multiple values (stronger evidence)

### Component Design

#### 1. Detector Service: `quantitative_catalyst_detector_mnls.py`

**Core Class**: `QuantitativeCatalystDetectorMNLS`

**MNLI Candidate Labels**:

```
# Presence Detection Labels
CATALYST_PRESENCE_LABELS = [
    "This announces a specific, quantitative financial catalyst with dollar amounts",
    "This is a vague or qualitative business update without specific numbers"
]

# Type Classification Labels (tested per category)
CATALYST_TYPE_LABELS = {
    "dividend": [
        "This announces a dividend payment with a specific dollar amount",
        "This does not announce a dividend payment"
    ],
    "acquisition": [
        "This announces an acquisition or merger with a specific purchase price",
        "This does not announce an acquisition or merger"
    ],
    "buyback": [
        "This announces a share buyback program with a specific dollar amount",
        "This does not announce a share buyback program"
    ],
    "earnings": [
        "This announces earnings results with specific dollar figures",
        "This does not announce earnings results"
    ],
    "guidance": [
        "This provides revenue guidance with specific dollar projections",
        "This does not provide revenue guidance"
    ]
}
```

**Detection Algorithm**:

1. **MNLI Presence Check**:
   - Test headline against presence labels
   - Extract score for "announces catalyst" label
   - If score < 0.5, return negative result immediately (fast path)

2. **Regex Value Extraction**:
   - Extract dollar amounts: `$1`, `$3.5B`, `$75M`
   - Extract per-share prices: `$37.50/share`, `$10 per share`
   - Extract percentages (context-aware): Only near financial terms (dividend, yield, EPS, earnings, revenue)
   - If MNLI indicates catalyst but no values found, penalize confidence (likely false positive)

3. **MNLI Type Classification**:
   - Test headline against each catalyst type's labels
   - Score all 5 types, select highest-scoring type
   - If best score < 0.6, return "mixed" (ambiguous type)

4. **Confidence Calculation**:
   - Base: `(presence_score * 0.5) + (type_score * 0.5)`
   - Boost: Add 0.1 if multiple values extracted (stronger evidence)
   - Cap: Maximum 1.0
   - Penalty: Multiply by 0.3 if MNLI says catalyst but no values (false positive detection)

**Key Methods**:
- `detect(headline: str) -> QuantitativeCatalystResult`: Main entry point
- `_check_presence(headline: str) -> float`: MNLI presence detection
- `_extract_values(headline: str) -> list[str]`: Regex value extraction
- `_classify_type(headline: str) -> dict`: MNLI type classification
- `_calculate_confidence(...)`: Multi-factor confidence scoring

#### 2. Data Models: `models/classification.py`

**Request Model**:
```
QuantitativeCatalystRequest:
  - headline: str (required, min_length=1)
```

**Response Model**:
```
QuantitativeCatalystResult:
  - headline: str (original text)
  - has_quantitative_catalyst: bool (detection result)
  - catalyst_type: str | None (dividend/acquisition/buyback/earnings/guidance/mixed)
  - catalyst_values: list[str] (extracted values: ["$1", "$3.5B", "10%"])
  - confidence: float (0.0-1.0, multi-factor score)
```

#### 3. Service Integration: `services/classifier.py`

**Initialization**:
- Instantiate `QuantitativeCatalystDetectorMNLS` in `ClassificationService.__init__`
- Share same MNLI pipeline instance (already loaded, no additional memory)

**Public Method**:
- `detect_quantitative_catalyst(headline: str) -> dict`: Route to detector, return serialized result

#### 4. API Endpoint: `api/app.py`

**Endpoint**: `POST /detect-quantitative-catalyst`

**Request Body**: `QuantitativeCatalystRequest`

**Response**: `QuantitativeCatalystResult`

**Pattern**: Follow existing endpoint patterns (similar to `/company-relevance`, `/routine-operations`)

**Error Handling**:
- 422 for validation errors (empty headline)
- 500 for model inference errors
- Log errors with request payload (per existing pattern)

### Integration Points

**Input**: benz_analyzer calls endpoint with article headline

**Output**: Structured detection result for use in prompt suppression logic

**No Changes Required**:
- Existing endpoints unchanged (backward compatible)
- Existing classification logic unchanged
- New optional feature, no dependencies on other services

### Performance Characteristics

**Latency Breakdown**:
- MNLI presence check: ~200ms (1 hypothesis test)
- Regex value extraction: <10ms (fast pattern matching)
- MNLI type classification: ~300-500ms (5 hypothesis tests)
- Confidence calculation: <1ms (arithmetic)
- **Total**: ~500-700ms per headline

**Optimization Opportunities** (future):
- Early exit: Skip type classification if presence score very low
- Caching: Cache results for duplicate headlines (if needed)

**Acceptable Tradeoffs**:
- Dedicated endpoint (doesn't slow down other classifications)
- Called only when needed (not every article)
- Similar latency to routine operations detector (~500ms)
- Semantic accuracy >> speed for this use case

## Implementation Phases

### Phase 1: Core Detector Service with MNLI Presence Detection

**Description**: Create foundational detector service with MNLI-based presence detection and regex value extraction. This phase establishes the core detection capability without type classification.

**Core Functionality**:
- Initialize MNLI pipeline (share instance with ClassificationService)
- Implement presence detection using binary MNLI classification
- Implement regex-based value extraction for dollar amounts, per-share prices, percentages
- Return boolean detection result with confidence score
- Handle edge cases: no values, multiple values, context-aware percentage extraction

**Implementation Approach**:

Create new service file following routine_detector_mnls.py pattern:
- File: `src/benz_sent_filter/services/quantitative_catalyst_detector_mnls.py`
- Class: `QuantitativeCatalystDetectorMNLS`
- Dependencies: transformers pipeline (shared), regex patterns
- Methods: `__init__`, `detect`, `_check_presence`, `_extract_values`, `_calculate_base_confidence`

Define MNLI labels:
- Presence labels: "announces quantitative catalyst" vs "vague update"
- Threshold: 0.5 for presence detection

Define regex patterns:
- Dollar amounts: Handle formats like $1, $3.5B, $75M, $1.9B
- Per-share prices: Handle $37.50/share, $10 per share
- Percentages: Context-aware (only near financial keywords: dividend, yield, EPS, earnings, revenue)

Confidence logic:
- Base confidence = presence_score
- Boost +0.1 if multiple values extracted
- Penalty *0.3 if MNLI indicates catalyst but no values (false positive)

**Unit Test Requirements**:

Create `tests/test_quantitative_catalyst_detector.py`:
- Test MNLI presence detection with positive cases (UUU, AHL, RSKD headlines)
- Test MNLI presence detection with negative cases (vague updates, price movements)
- Test regex dollar amount extraction: $1, $3.5B, $75M, $1.9B
- Test regex per-share price extraction: $37.50/share, $10 per share
- Test regex percentage extraction: 10% dividend (extract), 10% price gain (don't extract)
- Test confidence calculation: presence only, presence + multiple values, presence but no values
- Test edge cases: empty headline, no dollar signs, mixed formats

Test cases:
```
Positive:
- "Universal Safety Declares $1 Special Dividend..." → has_catalyst=True, values=["$1"], confidence≥0.7
- "Sompo To Acquire Aspen For $3.5B, Or $37.50/Share..." → has_catalyst=True, values=["$3.5B", "$37.50/Share"], confidence≥0.8
- "Board Authorizes Repurchase Of Up To $75M..." → has_catalyst=True, values=["$75M"], confidence≥0.7

Negative:
- "Company Updates Strategic Outlook" → has_catalyst=False, values=[], confidence=0.0
- "Stock Price Reaches $100 Milestone" → has_catalyst=False (not a catalyst, just price)
- "Plans to consider acquisition opportunities" → has_catalyst=False (vague, no specific amount)
```

**Acceptance Criteria**:
1. Detector class initializes without errors and shares MNLI pipeline
2. Presence detection returns boolean and confidence score (0.0-1.0)
3. Regex extracts dollar amounts with 95%+ accuracy on test cases
4. Regex extracts per-share prices with 95%+ accuracy
5. Percentages only extracted near financial keywords (no false positives on "stock up 10%")
6. UUU case: has_catalyst=True, values=["$1"], confidence ≥ 0.7
7. AHL case: has_catalyst=True, values=["$3.5B", "$37.50/Share"], confidence ≥ 0.8 (multiple values boost)
8. RSKD case: has_catalyst=True, values=["$75M"], confidence ≥ 0.7
9. Negative case: "Company Updates Outlook" → has_catalyst=False, confidence=0.0
10. Unit tests achieve 100% coverage of detector methods

---

### Phase 2: MNLI Type Classification

**Description**: Add multi-label MNLI classification to determine catalyst type (dividend, acquisition, buyback, earnings, guidance). Extends Phase 1 detector with semantic type identification.

**Core Functionality**:
- Define MNLI labels for 5 catalyst types
- Test each type's hypothesis against headline
- Score all types, select highest-scoring type
- Return "mixed" if no type scores above threshold (0.6)
- Integrate type classification into confidence calculation

**Implementation Approach**:

Extend detector service:
- Add `CATALYST_TYPE_LABELS` dictionary (5 types, each with positive/negative labels)
- Implement `_classify_type(headline: str) -> dict` method
- Method returns: `{"type": str, "confidence": float}`
- Test all 5 types in parallel if possible, or sequentially
- Select argmax type, return "mixed" if best_score < 0.6

Update confidence calculation:
- New formula: `(presence_score * 0.5) + (type_score * 0.5)`
- Maintains multi-value boost (+0.1)
- Maintains no-values penalty (*0.3)

Update result structure:
- Add `catalyst_type` field (str | None)
- Populate with classification result or None if no catalyst

**Unit Test Requirements**:

Extend `tests/test_quantitative_catalyst_detector.py`:
- Test dividend classification: "Declares $1 Special Dividend" → type="dividend", type_confidence≥0.8
- Test acquisition classification: "To Acquire For $3.5B" → type="acquisition", type_confidence≥0.8
- Test buyback classification: "Authorizes Repurchase Of $75M" → type="buyback", type_confidence≥0.8
- Test earnings classification: "Beats Earnings Expectations With $1 EPS" → type="earnings"
- Test guidance classification: "Raises Revenue Guidance To $500M" → type="guidance"
- Test ambiguous cases: Mixed catalyst (dividend + earnings) → type="mixed" if no clear winner
- Test type-specific confidence scoring integration
- Test that type is None when has_catalyst=False

Test cases:
```
Type Classification:
- UUU: "Declares $1 Special Dividend..." → type="dividend", confidence≥0.85
- AHL: "To Acquire Aspen For $3.5B..." → type="acquisition", confidence≥0.90
- RSKD: "Authorizes Repurchase Of Up To $75M..." → type="buyback", confidence≥0.85
- "Beats Earnings With $2 EPS, Declares $1 Dividend" → type="mixed" or highest-scoring
```

**Acceptance Criteria**:
1. Type classification method tests all 5 catalyst types
2. Returns highest-scoring type with confidence ≥ 0.6
3. Returns "mixed" if best score < 0.6 (ambiguous)
4. UUU case: type="dividend", confidence ≥ 0.85
5. AHL case: type="acquisition", confidence ≥ 0.90
6. RSKD case: type="buyback", confidence ≥ 0.85
7. Type classification adds ~300-500ms latency (acceptable)
8. Confidence calculation integrates type score: (presence * 0.5 + type * 0.5)
9. catalyst_type is None when has_catalyst=False
10. Unit tests cover all 5 types + mixed case, 100% method coverage

---

### Phase 3: Data Models and Response Structure

**Description**: Define Pydantic request/response models following benz_sent_filter conventions. Ensure clean API contract for downstream integration.

**Core Functionality**:
- Request model with headline validation
- Response model with all detection fields
- Optional fields use Pydantic patterns (default_factory, None defaults)
- Serialization follows existing patterns (exclude_none for backward compat)

**Implementation Approach**:

Create models in `src/benz_sent_filter/models/classification.py`:
- Add `QuantitativeCatalystRequest` class
  - Field: `headline: str` (required, min_length=1, description)
  - Validation: Non-empty headline

- Add `QuantitativeCatalystResult` class
  - Field: `headline: str` (original text, for context)
  - Field: `has_quantitative_catalyst: bool` (detection result)
  - Field: `catalyst_type: str | None` (type classification, None if no catalyst)
  - Field: `catalyst_values: list[str]` (extracted values, default_factory=list)
  - Field: `confidence: float` (0.0-1.0, multi-factor score)
  - Config: Use `exclude_none=True` for backward compatibility

Update detector to return model instance:
- Modify `detect()` method to return `QuantitativeCatalystResult`
- Populate all fields from detection logic
- Ensure catalyst_type is None when has_catalyst=False

**Unit Test Requirements**:

Create `tests/test_classification_models.py` or extend existing:
- Test QuantitativeCatalystRequest validation: valid headline passes
- Test QuantitativeCatalystRequest validation: empty headline fails with 422
- Test QuantitativeCatalystResult serialization: all fields present when catalyst detected
- Test QuantitativeCatalystResult serialization: catalyst_type is None when no catalyst
- Test QuantitativeCatalystResult serialization: catalyst_values empty list when no values
- Test backward compatibility: exclude_none works as expected
- Test field descriptions are meaningful for API documentation

Test cases:
```
Request Validation:
- QuantitativeCatalystRequest(headline="Valid headline") → passes
- QuantitativeCatalystRequest(headline="") → ValidationError
- QuantitativeCatalystRequest(headline="   ") → ValidationError (after strip)

Response Serialization:
- Catalyst detected: All fields populated (headline, has_catalyst=True, type, values, confidence)
- No catalyst: headline, has_catalyst=False, catalyst_type=None, catalyst_values=[], confidence=0.0
- Exclude none: catalyst_type excluded from JSON if None
```

**Acceptance Criteria**:
1. QuantitativeCatalystRequest validates headline (non-empty, min_length=1)
2. QuantitativeCatalystRequest rejects empty headlines with clear error message
3. QuantitativeCatalystResult includes all 5 fields with correct types
4. catalyst_type is str | None (None when no catalyst detected)
5. catalyst_values defaults to empty list (not None)
6. confidence is float between 0.0 and 1.0
7. Serialization excludes None values (backward compatibility)
8. Models follow existing benz_sent_filter Pydantic patterns
9. Field descriptions are clear and meaningful for API docs
10. Unit tests cover validation, serialization, edge cases with 100% coverage

---

### Phase 4: API Endpoint and Service Integration

**Description**: Create REST API endpoint and integrate detector with ClassificationService. Makes feature accessible to benz_analyzer and other consumers.

**Core Functionality**:
- POST endpoint `/detect-quantitative-catalyst`
- Request/response using Pydantic models from Phase 3
- Integration with ClassificationService for detector access
- Error handling following existing patterns (validation errors, inference errors)
- Request logging with payload (per existing pattern)

**Implementation Approach**:

Integrate detector with ClassificationService:
- File: `src/benz_sent_filter/services/classifier.py`
- In `__init__`: Initialize `self._catalyst_detector = QuantitativeCatalystDetectorMNLS()`
- Share MNLI pipeline: Pass `self._pipeline` to detector constructor
- Add method: `detect_quantitative_catalyst(headline: str) -> dict`
- Method calls detector, returns serialized result

Create API endpoint:
- File: `src/benz_sent_filter/api/app.py`
- Endpoint: `@app.post("/detect-quantitative-catalyst", response_model=QuantitativeCatalystResult)`
- Request body: `QuantitativeCatalystRequest`
- Route to: `app.state.classifier.detect_quantitative_catalyst(request.headline)`
- Error handling: 422 for validation, 500 for inference errors
- Logging: Log validation errors with payload (per validation_error_handler pattern)

Follow existing patterns:
- Similar to `/company-relevance` endpoint structure
- Similar to `/routine-operations` detector integration
- Consistent error responses across all endpoints

**Unit Test Requirements**:

Extend `tests/test_api.py`:
- Test endpoint with valid request: Returns 200 with QuantitativeCatalystResult
- Test endpoint with empty headline: Returns 422 with validation error
- Test endpoint with UUU headline: Returns has_catalyst=True, type="dividend", values=["$1"]
- Test endpoint with AHL headline: Returns has_catalyst=True, type="acquisition", values=["$3.5B", "$37.50/Share"]
- Test endpoint with RSKD headline: Returns has_catalyst=True, type="buyback", values=["$75M"]
- Test endpoint with negative case: Returns has_catalyst=False, catalyst_type=None
- Test error logging: Validation errors logged with request payload
- Test response schema: All fields present and correct types
- Test CORS headers if applicable (per existing endpoint tests)

Integration test:
- Test ClassificationService initializes detector without errors
- Test detector shares MNLI pipeline (no duplicate model loading)
- Test end-to-end: Request → endpoint → service → detector → response

Test cases:
```
API Endpoint:
- POST /detect-quantitative-catalyst {"headline": "Declares $1 Dividend"} → 200, has_catalyst=True, type="dividend"
- POST /detect-quantitative-catalyst {"headline": ""} → 422 validation error
- POST /detect-quantitative-catalyst {"headline": "Vague update"} → 200, has_catalyst=False
- POST /detect-quantitative-catalyst (missing headline) → 422 validation error

Integration:
- Service initialization: Detector created, pipeline shared
- End-to-end: Full request/response cycle with real MNLI inference
```

**Acceptance Criteria**:
1. POST /detect-quantitative-catalyst endpoint created and functional
2. Endpoint accepts QuantitativeCatalystRequest, returns QuantitativeCatalystResult
3. ClassificationService initializes detector and shares MNLI pipeline (no duplicate loading)
4. Service method detect_quantitative_catalyst routes to detector correctly
5. Validation errors return 422 with clear error messages
6. Inference errors return 500 with logged details
7. UUU test case: Endpoint returns correct detection result (dividend, $1, confidence ≥ 0.85)
8. AHL test case: Endpoint returns correct detection result (acquisition, $3.5B + $37.50/Share, confidence ≥ 0.90)
9. RSKD test case: Endpoint returns correct detection result (buyback, $75M, confidence ≥ 0.85)
10. Negative test case: "Updates Outlook" returns has_catalyst=False, catalyst_type=None, confidence=0.0
11. API tests achieve 100% coverage of endpoint and integration code
12. No regression: Existing endpoints still function correctly (run full test suite)

---

### Phase 5: Comprehensive Testing and Documentation

**Description**: Validate feature with extensive test coverage, real-world cases, and edge cases. Document API usage and integration patterns for benz_analyzer.

**Core Functionality**:
- Comprehensive test suite covering all detection scenarios
- Real-world test cases from bead (UUU, AHL, RSKD)
- Edge case handling (multiple values, ambiguous types, false positives)
- Performance validation (latency < 1s for single headline)
- API documentation with examples
- Integration guidance for benz_analyzer

**Implementation Approach**:

Expand test coverage:
- File: `tests/test_quantitative_catalyst_detector.py`
- Add real-world test cases with full headlines from bead notes
- Add edge case tests: Multiple catalysts, mixed types, vague amounts, percentages without context
- Add performance tests: Measure latency for single headline, batch of 10 headlines
- Add false positive tests: Price movements, stock milestones, non-catalyst mentions of dollar amounts
- Add false negative tests: Ensure known catalysts are detected

Test real-world cases:
- UUU (benzinga_47444642): Full headline → dividend, $1, confidence ≥ 0.85
- AHL (benzinga_47354784): Full headline → acquisition, multiple values, confidence ≥ 0.90
- RSKD (benzinga_47181321): Full headline → buyback, $75M, confidence ≥ 0.85

Edge cases:
- Multiple values: "$3.5B, Or $37.50/Share" → Extract both, boost confidence
- Mixed catalyst: "Beats earnings, raises dividend" → Type classification (mixed or highest score)
- Vague amounts: "Multi-million dollar deal" → No values extracted, has_catalyst=False
- Context-aware percentages: "Stock up 10%" → Don't extract; "10% dividend yield" → Extract
- False positive prevention: "Stock reaches $100 milestone" → has_catalyst=False

Performance validation:
- Single headline: < 1 second (target: ~500-700ms)
- Memory: No significant increase (shares MNLI pipeline)

Documentation:
- Update README.md: Add `/detect-quantitative-catalyst` endpoint description
- Document request/response models with examples
- Document confidence score interpretation (0.9+ high confidence, 0.7-0.9 medium, <0.7 low)
- Document catalyst_type values and meanings
- Document integration pattern for benz_analyzer (Part 2 of IMPL-016)

**Unit Test Requirements**:

Complete test suite in `tests/test_quantitative_catalyst_detector.py`:
- Test UUU: Full headline "Universal Safety Declares $1 Special Dividend After Feit Electric Asset Sale, Stock to Trade With Due Bills"
  - Expected: has_catalyst=True, type="dividend", values=["$1"], confidence ≥ 0.85
- Test AHL: Full headline "Sompo To Acquire Aspen For $3.5B, Or $37.50/Share And Redeem All Class A Shares"
  - Expected: has_catalyst=True, type="acquisition", values=["$3.5B", "$37.50/Share"], confidence ≥ 0.90
- Test RSKD: Full headline "Riskified Board Authorizes Repurchase Of Up To $75M Of Its Class A Ordinary Shares"
  - Expected: has_catalyst=True, type="buyback", values=["$75M"], confidence ≥ 0.85

Edge case tests:
- Test multiple values extraction and confidence boost
- Test mixed catalyst type handling
- Test vague amounts (no specific numbers) → has_catalyst=False
- Test false positives: "Stock reaches $100" → has_catalyst=False
- Test percentages without context: "Stock up 10%" → Don't extract
- Test percentages with context: "10% dividend yield" → Extract

Performance tests:
- Test single headline latency: < 1 second
- Test memory usage: No significant increase from baseline

Integration tests in `tests/test_api.py`:
- Test full end-to-end with UUU, AHL, RSKD headlines via API
- Test response format matches documentation
- Test error cases (empty headline, malformed request)

**Acceptance Criteria**:
1. UUU case passes with exact expected values (dividend, $1, confidence ≥ 0.85)
2. AHL case passes with exact expected values (acquisition, $3.5B + $37.50/Share, confidence ≥ 0.90)
3. RSKD case passes with exact expected values (buyback, $75M, confidence ≥ 0.85)
4. All edge cases handled correctly (multiple values, mixed types, vague amounts)
5. False positive rate < 5% on test set (price movements, milestones don't trigger detection)
6. False negative rate < 5% on test set (known catalysts are detected)
7. Single headline latency < 1 second (target: 500-700ms)
8. Test coverage ≥ 95% for detector, models, API endpoint
9. All acceptance criteria from previous phases still met (regression testing)
10. README.md updated with endpoint documentation, examples, integration guidance
11. API documentation includes confidence score interpretation guide
12. Documented integration pattern for benz_analyzer (IMPL-016 Part 2)

## Summary

This specification defines a comprehensive MNLI-based quantitative catalyst detection feature for benz_sent_filter. The implementation follows proven patterns from the existing codebase (particularly `routine_detector_mnls.py`) and provides a robust, semantic understanding approach superior to pure regex.

**Key Design Decisions**:
1. **MNLI hybrid approach**: Semantic detection/classification + regex value extraction
2. **Separate detector service**: Clean separation following routine operations pattern
3. **Multi-factor confidence**: Combines MNLI scores, value count, and mismatch penalties
4. **Dedicated endpoint**: `/detect-quantitative-catalyst` for focused use by benz_analyzer
5. **Backward compatible**: No changes to existing endpoints or behavior

**Success Metrics Recap**:
- 95%+ value extraction accuracy (regex)
- 90%+ type classification accuracy (MNLI)
- < 1 second response time (500-700ms target)
- 100% backward compatibility
- Ready for IMPL-016 Part 2 integration with benz_analyzer

**Next Steps**:
1. Use `/implement-phase` to execute phases sequentially
2. After completion, create bead for Part 2 (benz_analyzer integration)
3. Monitor false positive/negative rates in production
4. Consider additional catalyst types based on evaluator findings

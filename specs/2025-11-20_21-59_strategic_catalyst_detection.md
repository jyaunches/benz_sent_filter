# Specification: Strategic Catalyst Detection

**Created**: 2025-11-20
**Status**: Draft

## Overview & Objectives

### Problem Statement

The benz_analyzer system needs to identify **strategic corporate catalysts** that can significantly impact stock prices: executive changes, mergers, partnerships, product launches, rebranding, and clinical trial results. Unlike quantitative catalysts (which focus on dollar amounts), strategic catalysts are qualitative events that signal transformational business changes.

**Market Impact Evidence**:
- Executive changes: +85.9% (XFOR triple C-suite transition), +16.2% (SHCO CFO appointment), -7.4% (OPCH CFO appointment)
- Mergers: +24.3% (WKHS merger agreement)
- Product launches: +37.4% (SMX global product launch), +15.4% (CTXR AI platform)
- Partnerships: +12.3% (IMG MoU), -7.1% (WDAY partnership)
- Rebranding: +22.7% (NEHC name/ticker change)
- Clinical trials: -15.6% (PSTV Phase 1 results)

**Root Cause**: benz_sent_filter lacks strategic catalyst detection capability.

### Objectives

1. **Primary**: Create `/detect-strategic-catalyst` API endpoint that identifies whether article headlines announce strategic corporate catalysts
2. **Detection Capability**: Distinguish strategic catalysts (transformational events) from routine operations and financial results
3. **Type Classification**: Classify catalyst type across 6 categories
4. **Integration Ready**: Provide structured results for benz_analyzer to prioritize high-impact strategic events
5. **Simplicity First**: Focus on catalyst type detection only (defer sentiment, urgency, scale metadata to future iterations)

### Success Metrics

- 90%+ accuracy classifying strategic catalyst types on labeled test set (11 real-world examples)
- <1 second response time for single headline classification
- 100% backward compatibility (new endpoint, no existing endpoint changes)
- Consistent architecture with existing detectors (quantitative catalyst, routine operations)

## Current State Analysis

### What Exists

**Proven MNLI Patterns in Codebase**:

1. **Hybrid MNLI + Regex Pattern** (`quantitative_catalyst_detector_mnls.py`):
   - MNLI: Presence detection + type classification
   - Regex: Value extraction (dollar amounts, percentages)
   - Confidence: Combine MNLI scores with extracted value counts
   - **Success**: Clean separation of semantic understanding vs pattern matching

2. **Routine Operations Detector** (`routine_detector_mnls.py`):
   - MNLI: Transformational vs incremental classification
   - Materiality: Company-specific context for financial services
   - **Success**: 100% accuracy on test set

3. **Multi-Type Classification Pattern**:
   - Test multiple hypotheses per headline
   - Return highest-scoring type or "mixed" if ambiguous
   - Established in quantitative catalyst detector (5 types: dividend, acquisition, buyback, earnings, guidance)

### What's Needed

**Gap**: No mechanism to detect strategic corporate catalysts in headlines.

**Requirements**:
1. Semantic understanding to distinguish strategic catalysts from routine operations
2. Type classification across 6 catalyst categories
3. Confidence scoring for downstream decision-making
4. API endpoint following benz_sent_filter conventions

### Why MNLI Over Pure Regex

**Semantic Understanding**:
- Regex: "appoints CFO" matches both material appointment and interim appointment
- MNLI: Understands context and significance through semantic similarity

**Paraphrasing Robustness**:
- Regex: Must enumerate all variants ("appoints", "names", "welcomes", "brings on", "hires")
- MNLI: Generalizes across phrasings through semantic similarity

**Type Classification**:
- Regex: "launches" could be product launch, partnership launch, trial launch - requires priority rules
- MNLI: Tests specific hypotheses for accurate classification

**Proven Success**:
- Quantitative catalyst detector achieved high accuracy using MNLI + regex hybrid
- Routine operations detector achieved 100% accuracy using MNLI
- Consistency with established architecture patterns

## Architecture Design

### Hybrid Approach: MNLI for Detection/Classification

Following the proven pattern from `quantitative_catalyst_detector_mnls.py`, we use MNLI for semantic understanding:

**MNLI Responsibilities** (semantic understanding):
1. Presence detection: Does headline announce a strategic catalyst?
2. Type classification: Which category (executive_change, merger_agreement, strategic_partnership, product_launch, rebranding, clinical_trial_results)?

**Confidence Calculation** (numeric logic):
1. Use MNLI type classification score as confidence
2. Return "mixed" if best type score below threshold (0.6)

### Component Design

#### 1. Detector Service: `strategic_catalyst_detector_mnls.py`

**Core Class**: `StrategicCatalystDetectorMNLS`

**MNLI Candidate Labels**:

Presence Detection:
- Label 1: "This announces a specific strategic corporate event like an executive change, merger, partnership, product launch, or rebranding"
- Label 2: "This describes financial results, stock price movements, routine operations, or general market commentary"

Type Classification (6 categories):

1. **executive_change**:
   - Positive: "This announces a C-suite executive appointment, departure, or transition including CEO, CFO, President, or other senior leadership"
   - Negative: "This does not announce an executive leadership change"

2. **strategic_partnership**:
   - Positive: "This announces a strategic partnership, collaboration agreement, memorandum of understanding, or joint venture"
   - Negative: "This does not announce a strategic partnership"

3. **product_launch**:
   - Positive: "This announces a new product launch, technology platform deployment, or service introduction"
   - Negative: "This does not announce a product launch"

4. **merger_agreement**:
   - Positive: "This announces a merger agreement, acquisition announcement, or strategic combination"
   - Negative: "This does not announce a merger or acquisition"

5. **rebranding**:
   - Positive: "This announces a company name change, ticker symbol change, or corporate rebranding"
   - Negative: "This does not announce a rebranding"

6. **clinical_trial_results**:
   - Positive: "This announces clinical trial results, medical research findings, or drug efficacy data"
   - Negative: "This does not announce clinical trial results"

**Detection Logic**:

1. **Presence Check**: Test headline against presence labels
   - If presence score < 0.5, return negative result (no strategic catalyst)
   - If presence score >= 0.5, proceed to type classification

2. **Type Classification**: Test headline against all 6 type label pairs
   - Extract score for positive label from each pair
   - Select type with highest score
   - If highest score < 0.6, return type="mixed" (ambiguous)
   - Otherwise, return detected type

3. **Confidence Calculation**: Use type classification score as confidence

**Thresholds**:
- Presence detection: 0.5 (aligned with company relevance)
- Type classification: 0.6 (aligned with quantitative catalyst type classification)

#### 2. API Endpoint: `/detect-strategic-catalyst`

**Request Model** (`StrategicCatalystRequest`):
- `headline`: str (required, min_length=1)

**Response Model** (`StrategicCatalystResult`):
- `headline`: str - Original headline text
- `has_strategic_catalyst`: bool - Whether strategic catalyst detected
- `catalyst_type`: str | None - Type detected (executive_change, strategic_partnership, product_launch, merger_agreement, rebranding, clinical_trial_results, mixed) or None
- `confidence`: float - MNLI type classification score (0.0-1.0)

**Example Response**:
```json
{
  "headline": "X4 Pharmaceuticals' President And CEO Paula Ragan And CFO Adam Mostafa Have Stepped Down...",
  "has_strategic_catalyst": true,
  "catalyst_type": "executive_change",
  "confidence": 0.94
}
```

#### 3. Integration with ClassificationService

Add `detect_strategic_catalyst` method to `ClassificationService` class that:
1. Delegates to `StrategicCatalystDetectorMNLS`
2. Returns `StrategicCatalystResult`

**Pipeline Sharing**: Share existing MNLI pipeline with strategic catalyst detector to avoid loading separate model instance.

### File Structure

**New Files**:
- `src/benz_sent_filter/services/strategic_catalyst_detector_mnls.py` - Detector implementation
- `tests/test_strategic_catalyst_detector_mnls.py` - Unit tests (11 real-world examples)

**Modified Files**:
- `src/benz_sent_filter/api/app.py` - Add `/detect-strategic-catalyst` endpoint
- `src/benz_sent_filter/services/classifier.py` - Add `detect_strategic_catalyst` method, initialize detector
- `src/benz_sent_filter/models/classification.py` - Add `StrategicCatalystRequest` and `StrategicCatalystResult` models

## Implementation Phases

### Phase 1: Core Detector Implementation [COMPLETED: 74b11a8]

**Description**: Implement complete strategic catalyst detector with presence detection and type classification using MNLI. This phase delivers the full detection capability in one coherent implementation, matching the proven pattern from quantitative catalyst detector.

**Core Functionality**:
1. Create `StrategicCatalystDetectorMNLS` class with presence detection and type classification
2. Implement MNLI presence check using binary labels
3. Implement MNLI type classification across 6 catalyst categories
4. Return boolean result, catalyst type, and confidence score
5. Handle None/empty input gracefully

**Implementation Approach**:

Create `src/benz_sent_filter/services/strategic_catalyst_detector_mnls.py`:
- Define presence detection labels distinguishing strategic catalysts from routine operations
- Define CATALYST_TYPE_LABELS dict with 6 categories (executive_change, strategic_partnership, product_launch, merger_agreement, rebranding, clinical_trial_results)
- Each category has positive/negative label pair
- Implement constructor accepting optional pipeline for sharing
- Implement `_check_presence` method returning float score
- Implement `_classify_type` method testing all 6 hypotheses
- Implement `detect` method with full logic:
  - Check presence (threshold 0.5)
  - If present, classify type (threshold 0.6)
  - Return result with has_strategic_catalyst, catalyst_type, and confidence
- Use 0.5 threshold for presence detection (consistent with company relevance)
- Use 0.6 threshold for type classification (consistent with quantitative catalyst)

**Unit Test Requirements**:

Create `tests/test_strategic_catalyst_detector_mnls.py`:
- Test presence detection for positive cases (all 11 real-world examples)
- Test presence detection for negative cases (financial results, stock movements, routine operations)
- Test executive_change classification (4 examples: XFOR triple transition, SHCO CFO appointment, OPEN CEO departure, OPCH CFO appointment)
- Test merger_agreement classification (1 example: WKHS merger)
- Test strategic_partnership classification (2 examples: IMG MoU, WDAY partnership)
- Test product_launch classification (2 examples: SMX global product, CTXR AI platform)
- Test rebranding classification (1 example: NEHC name/ticker change)
- Test clinical_trial_results classification (1 example: PSTV Phase 1 results)
- Test ambiguous headlines returning "mixed" type
- Test None/empty input handling
- Test confidence score ranges (0.0-1.0)
- Verify confidence scores match MNLI type scores

**Acceptance Criteria**:
- [ ] Detector correctly identifies all 11 strategic catalyst examples as positive (has_strategic_catalyst=True)
- [ ] Detector correctly classifies all 11 examples to expected catalyst types
- [ ] Executive change examples (4) all classified as executive_change
- [ ] Merger, partnership, product launch, rebranding, clinical trial examples classified correctly
- [ ] Detector correctly rejects routine operations and financial results as negative
- [ ] Type classification completes in <1s for single headline
- [ ] Ambiguous headlines return type="mixed" with confidence < 0.6
- [ ] Confidence scores are between 0.0 and 1.0
- [ ] All unit tests pass with 90%+ type classification accuracy
- [ ] 100% coverage of detector module

### Phase 2: API Integration - Endpoint and Models

**Description**: Create REST API endpoint and integrate detector with ClassificationService.

**Core Functionality**:
1. Define Pydantic request/response models
2. Create FastAPI endpoint with validation
3. Integrate detector with ClassificationService
4. Share MNLI pipeline to avoid duplicate model loading

**Implementation Approach**:

Modify `src/benz_sent_filter/models/classification.py`:
- Add `StrategicCatalystRequest` model with headline field
- Add `StrategicCatalystResult` model with headline, has_strategic_catalyst, catalyst_type, confidence fields
- Use `model_config = ConfigDict(exclude_none=True)` for backward compatibility

Modify `src/benz_sent_filter/services/classifier.py`:
- Import `StrategicCatalystDetectorMNLS` and `StrategicCatalystResult`
- Initialize detector in `__init__` method, sharing pipeline
- Add `detect_strategic_catalyst` method delegating to detector

Modify `src/benz_sent_filter/api/app.py`:
- Import request/response models
- Add POST `/detect-strategic-catalyst` endpoint
- Use `response_model_exclude_none=True` for clean API responses
- Include docstring with example request/response

**Unit Test Requirements**:

Create `tests/test_api.py` tests (or extend existing):
- Test endpoint with valid strategic catalyst headlines
- Test endpoint with non-catalyst headlines
- Test endpoint with empty/None input (validation error)
- Test response model structure matches specification
- Test backward compatibility (no changes to existing endpoints)

**Acceptance Criteria**:
- [ ] `/detect-strategic-catalyst` endpoint returns 200 for valid requests
- [ ] Response includes all required fields (headline, has_strategic_catalyst, catalyst_type, confidence)
- [ ] catalyst_type is None when has_strategic_catalyst is False (exclude_none removes it)
- [ ] Endpoint validates request (422 for empty headline)
- [ ] Endpoint completes in <1s for single headline
- [ ] Existing API endpoints unchanged (backward compatibility)
- [ ] All integration tests pass

### Phase 3: Documentation and Testing

**Description**: Comprehensive testing with all 11 real-world examples and documentation updates.

**Core Functionality**:
1. Validate detector against all 11 real-world examples
2. Measure accuracy and performance
3. Update CLAUDE.md with new capability
4. Document API endpoint

**Implementation Approach**:

Create comprehensive test suite in `tests/test_strategic_catalyst_detector_mnls.py`:
- Test all 11 real-world examples with expected types
- Validate confidence scores are reasonable (>0.6 for clear catalysts)
- Test edge cases (multiple catalyst types in one headline)
- Performance test (measure latency for single/batch classification)

Update documentation:
- Add strategic catalyst detection to CLAUDE.md feature list
- Document 6 catalyst types
- Include example API requests/responses
- Note integration point for benz_analyzer

**Unit Test Requirements**:

End-to-end test cases:
- XFOR: Triple C-suite transition → executive_change (high confidence)
- SHCO: CFO appointment → executive_change
- OPEN: CEO departure → executive_change
- OPCH: CFO appointment → executive_change
- WKHS: Merger agreement → merger_agreement
- NEHC: Rebranding + ticker change → rebranding
- SMX: Product launch → product_launch
- CTXR: AI platform deployment → product_launch
- IMG: MoU for product development → strategic_partnership
- WDAY: Partnership → strategic_partnership
- PSTV: Phase 1 trial results → clinical_trial_results

**Acceptance Criteria**:
- [ ] All 11 real-world examples correctly classified
- [ ] 90%+ overall accuracy on test set
- [ ] Average latency <1s for single headline
- [ ] CLAUDE.md updated with strategic catalyst detection feature
- [ ] API documentation includes example requests/responses
- [ ] Zero regressions on existing tests
- [ ] 100% test coverage on strategic catalyst detector module

## Testing Strategy

### Unit Test Coverage

**Detector Logic** (`test_strategic_catalyst_detector_mnls.py`):
- Presence detection (positive and negative cases)
- Type classification (all 6 categories)
- Confidence score calculation
- Edge cases (None input, empty string, ambiguous headlines)

**API Integration** (`test_api.py`):
- Endpoint validation
- Response model structure
- Error handling
- Backward compatibility

### Test Data

**Real-World Examples** (11 cases from market data):
1. XFOR (+85.9%) - Triple C-suite transition
2. SHCO (+16.2%) - CFO appointment
3. OPEN (+16.1%) - CEO departure
4. OPCH (-7.4%) - CFO appointment
5. WKHS (+24.3%) - Merger agreement
6. NEHC (+22.7%) - Rebranding + ticker change
7. SMX (+37.4%) - Product launch (UN partnership)
8. CTXR (+15.4%) - AI platform deployment
9. IMG (+12.3%) - MoU for product development
10. WDAY (-7.1%) - Partnership
11. PSTV (-15.6%) - Phase 1 trial results

**Negative Cases**:
- Financial results: "Company reports Q3 earnings of $1.2B"
- Stock movements: "Stock rises 10% on strong volume"
- Routine operations: "Bank files quarterly MBS report"

## Success Criteria

### Functional Requirements
- [ ] Detect strategic catalysts with 90%+ accuracy on test set
- [ ] Classify catalyst type across 6 categories
- [ ] Return confidence scores (0.0-1.0)
- [ ] Handle edge cases gracefully (None, empty, ambiguous)

### Performance Requirements
- [ ] <1s response time for single headline
- [ ] Share MNLI pipeline (no duplicate model loading)
- [ ] Minimal memory overhead

### Integration Requirements
- [ ] New endpoint `/detect-strategic-catalyst` following FastAPI conventions
- [ ] Response model uses exclude_none for backward compatibility
- [ ] Zero changes to existing endpoints
- [ ] Ready for benz_analyzer integration

### Quality Requirements
- [ ] 100% test coverage on detector module
- [ ] All 11 real-world examples pass
- [ ] Zero regressions on existing tests
- [ ] Documentation updated

## Future Enhancements

**Deferred to Future Iterations**:

1. **Enhanced Metadata Extraction**:
   - Sentiment (positive/negative/neutral)
   - Urgency (immediate/dated/planned)
   - Scale (single/multiple/large)
   - Type-specific details (executive names, company names, product names)

2. **Batch Endpoint**:
   - `/detect-strategic-catalyst/batch` for multiple headlines
   - Optimized MNLI batching

3. **Mixed Type Handling**:
   - Return multiple types with scores when headline contains multiple catalysts
   - Example: "Company appoints new CEO and launches product" → both executive_change and product_launch

4. **Regex Enhancement Patterns**:
   - Extract executive titles, action verbs, company names
   - Parse dates for urgency detection
   - Count entities for scale detection

These enhancements can be added incrementally without breaking API compatibility.

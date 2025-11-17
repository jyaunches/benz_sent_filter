# Specification: Company Relevance Detection Extension

**Created**: 2025-11-17
**Status**: Draft
**Author**: System

## 1. Overview & Objectives

### Problem Statement
The benz ecosystem needs to determine if a news article headline is relevant to specific companies. Currently, the classification service can detect opinion vs news and temporal categories, but cannot assess whether a headline discusses a particular company.

This capability is essential for:
- Filtering news feeds to company-specific content
- Building company-focused sentiment dashboards
- Routing articles to appropriate analysis pipelines
- Identifying multi-company stories

### Goals
- Extend existing classification endpoints to accept optional company parameter
- Return company relevance boolean and confidence score
- Support multi-company batch relevance checking
- Reuse existing MNLS model (no new dependencies)
- Maintain backward compatibility for existing clients
- Achieve <3 second response time for single company check on CPU

### Success Criteria
- Existing endpoints continue to work without company parameter
- When company provided, response includes relevance fields
- Relevance detection achieves >80% accuracy on test fixtures
- All tests pass with >90% coverage
- Zero breaking changes to existing API contracts

## 2. Current State Analysis

### What Exists
- Classification service using `typeform/distilbert-base-uncased-mnli` for zero-shot NLI
- POST `/classify` endpoint for single headline classification (opinion/news, temporal)
- POST `/classify/batch` endpoint for multiple headlines
- Pydantic models: `ClassifyRequest`, `ClassificationResult`, `BatchClassifyRequest`
- Service method: `ClassificationService.classify_headline(headline)`
- Test coverage for existing classification dimensions

### What's Needed
- Optional company parameter in request models
- Company relevance scoring using same NLI pipeline
- Response fields for company relevance (boolean + score)
- Handling of None/null company (backward compatibility)
- Tests for company relevance detection
- Documentation updates

### Gaps
1. No company parameter in request models
2. No company relevance fields in response models
3. No service logic for company-specific NLI queries
4. No test fixtures for company relevance scenarios
5. Limited documentation about company detection capability

## 3. Architecture Design

### Model Reuse Strategy
Use the existing zero-shot classification pipeline with company-specific hypothesis templates:

**Hypothesis Template**: "This article is about {company_name}"

The model will return entailment scores indicating likelihood the headline discusses the specified company.

**Pattern Reuse**: Company relevance check follows the same pipeline calling pattern as existing opinion/news and temporal classification - just different candidate labels. Same pipeline instance, same return format, same score extraction logic.

### API Extension Approach

**Backward Compatible Design**:
- Add optional `company` field to `ClassifyRequest` and `BatchClassifyRequest`
- When `company` is None/null: existing behavior (no relevance fields in response)
- When `company` provided: include `is_about_company` and `company_score` in response
- Batch endpoint: each headline can have different company or None

**Response Schema Evolution**:
- Add optional fields: `is_about_company` (bool), `company_score` (float), `company` (str)
- Fields only present when company parameter provided
- Existing clients ignoring these fields continue to work

### Classification Logic

**Single Company Check**:
1. Run zero-shot classification with hypothesis: "This article is about {company}"
2. Extract entailment score (0.0 to 1.0)
3. Apply threshold (0.5) to generate boolean flag
4. Return both score and boolean

**Threshold Selection**: 0.5 (lower than opinion/news 0.6)
- Company mentions are often clear-cut (name appears or doesn't)
- False negatives worse than false positives for news filtering
- Raw score exposed for client-side tuning

**Edge Cases**:
- Company variations: model handles "Tesla", "TSLA", "Tesla Inc" naturally
- Multiple companies in headline: returns relevance for specified company only

### Data Flow

**With Company Parameter**:
1. Client sends POST with headline and company name
2. FastAPI validates input using Pydantic
3. Service runs existing classification (opinion/news, temporal)
4. Service runs company relevance classification (if company provided)
5. Response includes all classification results
6. Client receives unified classification with optional company relevance

**Without Company Parameter** (backward compatible):
1. Same as current behavior
2. No company relevance check performed
3. Response excludes company-related fields

## 4. Implementation Phases

### Phase 1: Extend Request/Response Models [COMPLETED: ff7c618]

**Description**: Add optional company parameter to request models and company relevance fields to response models while maintaining backward compatibility.

**Core Functionality**:
- Add optional `company` field to `ClassifyRequest` (str | None, default None)
- Add optional `company` field to each item in `BatchClassifyRequest.headlines` OR add top-level `company` field
- Add optional fields to `ClassificationResult`: `is_about_company`, `company_score`, `company`
- Ensure None company values result in response without relevance fields
- Maintain validation rules for existing fields

**Implementation Approach**:
- Modify `src/benz_sent_filter/models/classification.py`
- Update `ClassifyRequest` to add `company: str | None = None` (follows existing optional field pattern in Pydantic models)
- Update `ClassificationResult` to add three optional fields with `Field(default=None)` (same pattern as existing `Field(...)` definitions in `ClassificationScores` and `ClassificationResult`)
- Add import: `from pydantic import ConfigDict`
- Configure `ClassificationResult` with `model_config = ConfigDict(exclude_none=True)` to automatically exclude None fields from JSON serialization
- Reference existing models as template - copy-paste-modify pattern from lines 20-24 (`ClassifyRequest`) and 48-58 (`ClassificationResult`)
- For batch: add `company: str | None = None` to `BatchClassifyRequest` (same pattern as `ClassifyRequest`)
- Keep all existing field validations unchanged
- Update model exports in `__init__.py` if needed

**Unit Test Requirements**:
- Update `tests/test_models.py`
- Test `ClassifyRequest` with company parameter validates successfully
- Test `ClassifyRequest` without company parameter (None) validates successfully
- Test `ClassificationResult` serializes correctly with company fields present
- Test `ClassificationResult` serializes correctly with company fields absent (None)
- Test batch request with company parameter
- Verify JSON serialization includes/excludes fields appropriately

**Acceptance Criteria**:
- [ ] Request models accept optional company parameter
- [ ] Response models include optional company relevance fields
- [ ] Models validate correctly with and without company
- [ ] Backward compatibility maintained (None company works)
- [ ] All model tests pass

### Phase 2: Add Company Relevance Service Logic [COMPLETED: 7057a8a]

**Description**: Implement company relevance detection in the classification service using the existing NLI pipeline.

**Core Functionality**:
- Add method to run company relevance classification
- Use hypothesis template: "This article is about {company_name}"
- Extract entailment score from pipeline output
- Apply 0.5 threshold to generate boolean flag
- Return relevance score and boolean
- Handle None company gracefully (skip relevance check)

**Implementation Approach**:
- Add `COMPANY_RELEVANCE_THRESHOLD = 0.5` to `src/benz_sent_filter/config/settings.py` (follows existing `CLASSIFICATION_THRESHOLD` pattern)
- Modify `src/benz_sent_filter/services/classifier.py`
- Import `COMPANY_RELEVANCE_THRESHOLD` from config.settings
- Import `namedtuple` from `collections`
- Define `CompanyRelevance = namedtuple('CompanyRelevance', ['is_relevant', 'score'])` at module level for structured return value
- Add class constant: `COMPANY_HYPOTHESIS_TEMPLATE = "This article is about {company}"`
- Add method: `_check_company_relevance(headline: str, company: str) -> CompanyRelevance`
- Method calls existing `self._pipeline` with single hypothesis using default parameters (reuses same pipeline pattern as existing classification)
- Extract score from pipeline result (index 0 of scores list)
- Apply threshold: `is_relevant = score >= COMPANY_RELEVANCE_THRESHOLD`
- Return `CompanyRelevance(is_relevant=is_relevant, score=score)` for readable field access via `.is_relevant` and `.score` attributes
- Update `classify_headline` to check `if company is not None` before calling `_check_company_relevance`, then unpack namedtuple result: `relevance = self._check_company_relevance(headline, company)` and access via `relevance.is_relevant` and `relevance.score`
- Update `classify_batch` to handle per-headline company checks with same None guard pattern

**Unit Test Requirements**:
- Update `tests/test_classifier.py`
- Mock pipeline to return high score (0.85) for matching company headline
- Test company relevance returns `(True, 0.85)` when score above threshold
- Mock pipeline to return low score (0.15) for non-matching company
- Test company relevance returns `(False, 0.15)` when score below threshold
- Test None company skips relevance check
- Test `classify_headline` includes company fields when company provided
- Test `classify_headline` excludes company fields when company is None
- Verify existing tests still pass (no regression)

**Acceptance Criteria**:
- [ ] Service detects company relevance using NLI pipeline
- [ ] Threshold logic correctly generates boolean flag
- [ ] None/empty company handled gracefully
- [ ] Integration with existing classification works
- [ ] All service tests pass

### Phase 3: Update API Endpoints [COMPLETED: f71e9e5]

**Description**: Modify API endpoints to accept company parameter and return company relevance in responses.

**Core Functionality**:
- `/classify` endpoint accepts optional company in request body
- `/classify/batch` endpoint accepts optional company parameter
- Endpoints pass company to service classification method
- Response includes company relevance when company provided
- Response structure unchanged when company not provided (backward compatible)

**Implementation Approach**:
- Modify `src/benz_sent_filter/api/app.py`
- Update `classify_headline` route to extract company from request
- Pass company to `classifier.classify_headline(request.headline, company=request.company)`
- Update service signature: `classify_headline(headline: str, company: str | None = None)`
- Service returns `ClassificationResult` with company fields populated if company provided
- Update `classify_batch` similarly for batch processing
- Ensure validation errors (422) still work correctly
- No changes to error handling or health endpoint

**Unit Test Requirements**:
- Update `tests/test_api.py`
- Test POST `/classify` with company returns relevance fields
- Test POST `/classify` without company omits relevance fields (backward compat)
- Test POST `/classify/batch` with company for all headlines
- Test response schema matches updated Pydantic models
- Test validation error when company is provided but headline is empty
- Test existing tests continue to pass unchanged
- Verify health endpoint unaffected

**Acceptance Criteria**:
- [ ] API endpoints accept optional company parameter
- [ ] Responses include company relevance when company provided
- [ ] Backward compatibility maintained for existing clients
- [ ] Validation errors handled correctly
- [ ] All API tests pass

### Phase 4: Integration Testing & Validation

**Description**: Add integration tests with real model to validate company relevance detection accuracy.

**Core Functionality**:
- Test company relevance with real NLI model (not mocked)
- Verify accuracy on known test cases
- Test edge cases (company variations, false positives/negatives)
- Validate performance with company parameter

**Implementation Approach**:
- Update `integration/test_classification_integration.py`
- Use inline test data (no separate fixtures file)
- Test positive case: "Dell Unveils AI Data Platform..." + company="Dell" → True
- Test negative case: "Dell Unveils AI Data Platform..." + company="Tesla" → False
- Test multi-company case: Same headline + company="NVIDIA" → True
- Test performance: company check adds minimal latency (<500ms)
- Mark with `@pytest.mark.integration`

**Unit Test Requirements**:
- Test Dell headline correctly identifies Dell relevance
- Test Dell headline correctly rejects Tesla relevance
- Test Dell headline correctly identifies NVIDIA relevance (multi-company)
- Test batch processing with company parameter
- Verify no regression in existing classification dimensions

**Acceptance Criteria**:
- [ ] Integration tests with real model created
- [ ] Company relevance achieves >80% accuracy on test fixtures
- [ ] Performance target met (<3s total for single headline with company)
- [ ] Edge cases handled correctly
- [ ] Integration tests pass when run with real model

### Phase 5: Documentation & Examples

**Description**: Update documentation with company relevance API usage, examples, and best practices.

**Core Functionality**:
- Document company parameter in API reference
- Provide curl examples for company relevance
- Explain scoring and threshold
- Document backward compatibility guarantees
- Add troubleshooting for common issues

**Implementation Approach**:
- Update README.md with company relevance section
- Add example request/response showing company parameter
- Include curl command example (to check different companies, change the company field value)
- Document threshold (0.5) and when to adjust it
- Explain how to handle company name variations
- Note limitations (headline-only, no body text, single company per request)
- Add FAQ section for company detection
- Update OpenAPI schema descriptions in code docstrings

Example curl command to include:
```bash
# Check if headline is about a company (Dell, NVIDIA, Tesla, etc.)
curl -X POST http://localhost:8002/classify \
  -H "Content-Type: application/json" \
  -d '{
    "headline": "Dell Unveils AI Data Platform Updates; Launches First 2U Server With NVIDIA Blackwell GPUs",
    "company": "Dell"
  }'
```

**Unit Test Requirements**:
- No new tests required for documentation
- Verify example JSON in docs is valid
- Test example curl commands against running service

**Acceptance Criteria**:
- [ ] README updated with company relevance documentation
- [ ] Example requests/responses provided
- [ ] Curl commands tested and working
- [ ] Threshold and scoring explained
- [ ] Limitations documented
- [ ] Backward compatibility guarantees stated

## 5. Technical Decisions & Rationale

### Optional Parameter vs. New Endpoint
**Decision**: Extend existing endpoints with optional parameter
**Rationale**:
- Single API call returns all classifications
- Reduces client complexity (one request, not two)
- Backward compatible (existing clients unaffected)
- Follows REST principle of resource-based design
- Easier to maintain (one codebase path)

### Threshold: 0.5
**Decision**: Use 0.5 for company relevance (lower than 0.6 for opinion/news), configured as `COMPANY_RELEVANCE_THRESHOLD` in settings
**Rationale**:
- Centralized configuration following existing `CLASSIFICATION_THRESHOLD` pattern
- Company mentions tend to be binary (name appears or doesn't)
- False negatives costlier than false positives for news filtering
- Can tune threshold client-side using raw score, or adjust constant for global tuning
- Lower threshold captures edge cases (indirect references)

### Per-Headline vs. Batch-Level Company
**Decision**: Support batch-level company (all headlines same company)
**Rationale**:
- Simpler API for common use case (filter news for one company)
- Can extend to per-headline later if needed
- Performance optimization (single hypothesis template)
- Matches typical usage pattern

### Backward Compatibility
**Decision**: Make company parameter fully optional with None handling
**Rationale**:
- Zero breaking changes for existing integrations
- Gradual rollout possible
- Old clients continue working without changes
- New clients can adopt incrementally

## 6. Future Enhancements (Out of Scope)

- Multi-company relevance in single request (return scores for multiple companies)
- Company alias/ticker mapping (auto-expand "AAPL" to "Apple Inc")
- Named entity recognition pre-filtering (only check companies mentioned in text)
- Confidence calibration based on production feedback
- Sector/industry classification (not company-specific)
- Relevance to topics/themes (ESG, earnings, M&A)

## 7. Dependencies & Risks

### Dependencies
- External: None (reuses existing model and pipeline)
- Internal: None (extends existing service)

### Risks
1. **False Positives**: Industry terms might trigger false relevance
   - Mitigation: Threshold tuning, expose raw scores for filtering
2. **Name Variations**: "Dell" vs "DELL" vs "Dell Technologies"
   - Mitigation: Model handles variations well via NLI, document best practices
3. **Performance**: Additional pipeline call adds latency
   - Mitigation: Target <500ms overhead, acceptable for use case
4. **Multi-Company Headlines**: Headlines mentioning multiple companies (Dell + NVIDIA)
   - Mitigation: Return relevance for specified company only, client can query multiple times for different companies

### Open Questions
- Should batch endpoint support different company per headline? (Decision: No, batch-level for v1)
- What threshold provides best precision/recall tradeoff? (Decision: 0.5, tunable via raw score)
- Should we validate company name format? (Decision: No, accept any string)

## 8. Success Metrics

### Functional Metrics
- API accepts company parameter correctly
- Response includes relevance when company provided
- Backward compatibility maintained (existing tests pass)

### Accuracy Metrics
- Company relevance detection: >80% accuracy on test fixtures
- False positive rate: <20% on ambiguous headlines
- False negative rate: <10% on clear company mentions

### Performance Metrics
- Single headline + company: <3 seconds total on CPU
- Company check overhead: <500ms beyond base classification
- Batch processing: <5 seconds for 10 headlines with company

### Quality Metrics
- Test coverage maintained: >90%
- No breaking changes to existing API
- Documentation completeness: all new features documented

---

**End of Specification**

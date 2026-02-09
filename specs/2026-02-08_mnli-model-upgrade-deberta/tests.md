# Test Specification: MNLI Model Upgrade to DeBERTa-v3-large

**Created**: 2026-02-08
**Parent Spec**: spec.md
**Status**: Draft

## Test Strategy Overview

This test specification defines the validation approach for upgrading from DistilBERT-MNLI to DeBERTa-v3-large. The upgrade must maintain backward compatibility while fixing catalyst type disambiguation failures.

### Test Categories

1. **Regression Tests**: All 341 existing tests must pass
2. **Disambiguation Tests**: All 31 new tests in `test_catalyst_type_disambiguation.py` must pass
3. **Integration Tests**: End-to-end API validation
4. **Performance Tests**: Resource usage and timing validation
5. **Threshold Calibration Tests**: Score distribution analysis

## Phase 1: Model Swap - Regression Testing

**Objective**: Verify model swap doesn't break existing functionality.

### Test Plan

1. **Existing Test Suite Execution**
   ```bash
   # Run full test suite with new model
   PYTHONPATH=src pytest tests/ -v --tb=short
   ```

   **Expected Result**: All 341 tests pass without modification

   **If failures occur**: Categorize into:
   - Threshold issues (score distribution shift)
   - Label issues (model interprets labels differently)
   - Model limitations (DeBERTa fails where DistilBERT succeeded)

2. **Test Files Coverage**
   ```
   tests/test_api_endpoints.py                    # API contract validation
   tests/test_classification_service.py           # Opinion/news/temporal
   tests/test_company_relevance.py                # Company detection
   tests/test_forecast_analyzer.py                # Far-future forecast
   tests/test_quantitative_catalyst_detector.py   # Quantitative catalyst
   tests/test_routine_detector.py                 # Routine operations
   tests/test_strategic_catalyst_detector.py      # Strategic catalyst
   tests/test_classification_response_models.py   # Pydantic models
   integration/test_batch_processing.py           # Batch endpoints
   integration/test_integration.py                # Full pipeline
   integration/test_performance.py                # Timing benchmarks
   ```

3. **Threshold Calibration Data Collection**

   For any test failures, collect score distributions:
   ```python
   # Add debugging to failing tests
   print(f"DistilBERT score: {old_score}")
   print(f"DeBERTa score: {new_score}")
   print(f"Threshold: {threshold}")
   ```

   **Analysis**: If DeBERTa consistently scores 0.05-0.10 lower than DistilBERT, adjust thresholds down.

### Acceptance Criteria

- [ ] All 341 existing tests pass OR
- [ ] Failures documented with score comparisons
- [ ] Threshold adjustments proposed (if needed)

## Phase 2: Disambiguation Testing

**Objective**: Validate that DeBERTa fixes catalyst type misclassification.

### Test Plan

1. **Run Disambiguation Test Suite**
   ```bash
   PYTHONPATH=src pytest tests/test_catalyst_type_disambiguation.py -v
   ```

   **Expected Result**: All 31 tests pass (100% improvement over DistilBERT)

2. **Test Breakdown by Category**

   **Divestiture vs Acquisition** (5 tests):
   - `test_ntrb_sell_majority_stake_not_acquisition` - NTRB production case
   - `test_divest_industrial_division`
   - `test_sells_subsidiary`
   - `test_agrees_to_sell_business_unit`
   - `test_disposes_of_assets`

   **Financing vs Dividend/Buyback** (5 tests):
   - `test_indp_securities_purchase_agreement_not_dividend` - INDP production case
   - `test_convertible_note_offering_not_dividend`
   - `test_private_placement_not_dividend`
   - `test_preferred_stock_offering_not_dividend`
   - `test_atm_facility_not_buyback`

   **Revenue vs Earnings** (4 tests):
   - `test_onar_recurring_revenue_not_earnings` - ONAR production case
   - `test_contract_revenue_not_earnings`
   - `test_subscription_revenue_growth_not_earnings`
   - `test_booking_revenue_not_earnings`

   **Preserve Correct Classifications** (7 tests):
   - Ensure real acquisitions still classified as acquisition
   - Ensure real dividends still classified as dividend
   - Ensure real buybacks still classified as buyback
   - Ensure real earnings still classified as earnings
   - Ensure real guidance still classified as guidance

   **Edge Cases** (10 tests):
   - Test headlines with ambiguous keywords (sell/sale/purchase/agreement)
   - Ensure disambiguation doesn't over-correct

3. **Label Tuning Strategy** (if tests fail)

   **For divestiture disambiguation failures**:
   - Option A: Add pre-MNLI regex filter for "sell|divest|dispose" → exclude "acquisition"
   - Option B: Refine acquisition label to "announces acquiring/buying/purchasing another company"
   - Option C: Add negative examples to acquisition label

   **For financing disambiguation failures**:
   - Option A: Add "securities purchase agreement|offering|placement" → exclude "dividend"
   - Option B: Refine dividend label to emphasize "returning capital to shareholders"
   - Option C: Test if DeBERTa needs less guidance (remove overly specific language)

   **For revenue disambiguation failures**:
   - Option A: Refine earnings label to "net income/profit/EPS" vs "revenue/sales"
   - Option B: Add revenue-specific keywords to exclusion list
   - Option C: Increase TYPE_THRESHOLD for earnings (require higher confidence)

4. **Iterative Testing Workflow**
   ```bash
   # 1. Run tests
   pytest tests/test_catalyst_type_disambiguation.py -v

   # 2. Analyze failures
   pytest tests/test_catalyst_type_disambiguation.py::TestDivestitureDisambiguation -vv

   # 3. Adjust labels in quantitative_catalyst_detector_mnls.py

   # 4. Re-run
   pytest tests/test_catalyst_type_disambiguation.py -v

   # 5. Verify no regressions
   pytest tests/test_quantitative_catalyst_detector.py -v
   ```

### Acceptance Criteria

- [ ] All 31 disambiguation tests pass
- [ ] All 341 existing tests still pass (no regressions)
- [ ] Production misclassification cases (NTRB, INDP, ONAR) now correct

## Phase 3: Integration Testing

**Objective**: Validate end-to-end API behavior with new model.

### Test Plan

1. **Start Test Server**
   ```bash
   # Use port 8003 to avoid conflict with production server
   PYTHONPATH=src uvicorn benz_sent_filter.api.app:app --host 0.0.0.0 --port 8003
   ```

2. **API Endpoint Testing**

   **Test /classify**:
   ```bash
   curl -X POST http://localhost:8003/classify \
     -H "Content-Type: application/json" \
     -d '{"headline": "Company announces $1 dividend"}' | jq
   ```
   Expected: `is_opinion: false`, `temporal_category: PAST_EVENT`

   **Test /detect-quantitative-catalyst**:
   ```bash
   curl -X POST http://localhost:8003/detect-quantitative-catalyst \
     -H "Content-Type: application/json" \
     -d '{"headline": "Nutriband to sell majority stake of Pocono Pharmaceutical for $5M"}' | jq
   ```
   Expected: `catalyst_type != "acquisition"` (should be None or "mixed")

   **Test /detect-strategic-catalyst**:
   ```bash
   curl -X POST http://localhost:8003/detect-strategic-catalyst \
     -H "Content-Type: application/json" \
     -d '{"headline": "Company appoints new CEO"}' | jq
   ```
   Expected: `has_strategic_catalyst: true`, `catalyst_subtype: "executive_changes"`

3. **Backward Compatibility Schema Check**
   ```python
   # Verify response schemas unchanged
   from benz_sent_filter.models.classification import ClassificationResult
   result = ClassificationResult(...)
   assert "is_opinion" in result.model_dump()
   assert "is_straight_news" in result.model_dump()
   # No new required fields
   ```

4. **Batch Processing Test**
   ```bash
   curl -X POST http://localhost:8003/classify/batch \
     -H "Content-Type: application/json" \
     -d '{
       "headlines": [
         "Company announces $1 dividend",
         "Stock rises 10%",
         "CEO resigns"
       ]
     }' | jq
   ```
   Expected: Array of 3 results, all valid

### Acceptance Criteria

- [ ] All 7 endpoints return valid responses
- [ ] No API contract changes (schema backward compatible)
- [ ] Production misclassification cases return correct results via API

## Phase 4: Performance Testing

**Objective**: Validate resource usage and timing acceptable for deployment.

### Test Plan

1. **Startup Time Measurement**
   ```bash
   time PYTHONPATH=src python -c "from benz_sent_filter.services.classifier import ClassificationService; s = ClassificationService()"
   ```
   **Expected**: 45-90 seconds (vs 15-30s for DistilBERT)
   **Acceptance**: < 120 seconds

2. **Memory Usage**
   ```bash
   # Monitor memory during startup
   /usr/bin/time -l python -c "from benz_sent_filter.services.classifier import ClassificationService; s = ClassificationService()"
   ```
   **Expected**: ~1.5GB (vs ~250MB for DistilBERT)
   **Acceptance**: < 2GB

3. **Inference Timing**
   ```python
   import time
   from benz_sent_filter.services.classifier import ClassificationService

   service = ClassificationService()
   headline = "Company announces $1 dividend"

   start = time.time()
   result = service.classify(headline)
   duration = time.time() - start

   print(f"Inference time: {duration*1000:.1f}ms")
   ```
   **Expected**: 400-600ms per headline (vs 200-300ms for DistilBERT)
   **Acceptance**: < 1000ms (1 second)

4. **Batch Processing Timing**
   ```python
   headlines = ["test headline"] * 10
   start = time.time()
   results = service.classify_batch(headlines)
   duration = time.time() - start

   print(f"Batch time: {duration:.1f}s for {len(headlines)} headlines")
   print(f"Per-headline avg: {duration/len(headlines)*1000:.1f}ms")
   ```
   **Expected**: < 10 seconds for 10 headlines
   **Acceptance**: < 15 seconds for 10 headlines

### Acceptance Criteria

- [ ] Startup time < 120 seconds
- [ ] Memory usage < 2GB
- [ ] Single headline inference < 1000ms
- [ ] Batch of 10 < 15 seconds
- [ ] Resource requirements documented for deployment

## Phase 5: Score Distribution Analysis

**Objective**: Understand how DeBERTa's score distributions differ from DistilBERT.

### Test Plan

1. **Collect Score Data**
   ```python
   # Run on sample headlines and collect scores
   test_headlines = [
       "Company announces $1 dividend",
       "Stock rises 10%",
       "Company acquires competitor for $100M",
       "Nutriband to sell majority stake for $5M",
   ]

   for headline in test_headlines:
       result = detector.detect(headline)
       print(f"{headline[:50]}")
       print(f"  DistilBERT: {old_score:.3f}")
       print(f"  DeBERTa: {result.confidence:.3f}")
       print(f"  Difference: {result.confidence - old_score:.3f}")
   ```

2. **Threshold Recommendations**

   If DeBERTa scores consistently differ by pattern:
   - Lower by 0.05-0.10: Reduce PRESENCE_THRESHOLD and TYPE_THRESHOLD by 0.05
   - Higher by 0.05-0.10: Can keep current thresholds or increase slightly
   - Same distribution: No threshold changes needed

3. **Document Findings**
   ```markdown
   ## Score Distribution Comparison

   | Headline Type | DistilBERT Avg | DeBERTa Avg | Delta |
   |--------------|----------------|-------------|-------|
   | Real dividend | 0.87 | 0.82 | -0.05 |
   | Price move | 0.23 | 0.18 | -0.05 |
   | Divestiture | 0.91 (wrong) | 0.45 | -0.46 |

   **Recommendation**: Reduce TYPE_THRESHOLD from 0.6 to 0.55
   ```

### Acceptance Criteria

- [ ] Score distributions analyzed for 20+ test headlines
- [ ] Threshold adjustments documented (if needed)
- [ ] New thresholds validated against full test suite

## Test Execution Checklist

### Pre-Implementation
- [ ] Review test strategy
- [ ] Ensure `test_catalyst_type_disambiguation.py` exists
- [ ] Baseline current test results with DistilBERT

### Phase 1 (Model Swap)
- [ ] Update model name in settings.py
- [ ] Run full test suite
- [ ] Document any failures
- [ ] Collect score distributions
- [ ] Adjust thresholds if needed
- [ ] Re-run full test suite

### Phase 2 (Disambiguation)
- [ ] Run disambiguation test suite
- [ ] For failures: analyze and categorize
- [ ] Tune labels or add pre-filters
- [ ] Iterate until all 31 tests pass
- [ ] Verify no regressions

### Phase 3 (Integration)
- [ ] Start test server on port 8003
- [ ] Test all 7 endpoints with production cases
- [ ] Verify backward compatibility
- [ ] Test batch processing
- [ ] Shutdown test server

### Phase 4 (Performance)
- [ ] Measure startup time
- [ ] Measure memory usage
- [ ] Measure inference timing
- [ ] Measure batch timing
- [ ] Document resource requirements

### Phase 5 (Score Analysis)
- [ ] Collect score data for 20+ headlines
- [ ] Compare DistilBERT vs DeBERTa distributions
- [ ] Document threshold recommendations
- [ ] Validate recommendations against full suite

## Success Criteria Summary

This upgrade is validated when:

1. **Regression**: All 341 existing tests pass
2. **Disambiguation**: All 31 new tests pass
3. **Production**: NTRB, INDP, ONAR cases now classify correctly
4. **API**: All 7 endpoints work, no contract changes
5. **Performance**: Startup < 120s, inference < 1s, memory < 2GB
6. **Documentation**: Thresholds documented, findings summarized

## Risk Mitigation

### Risk: DeBERTa has fundamentally different score distribution
**Mitigation**: Phase 5 score analysis provides data-driven threshold adjustments

### Risk: DeBERTa is too slow for production
**Mitigation**: Phase 4 performance testing validates timing before deployment

### Risk: Label tuning breaks existing tests
**Mitigation**: Run full test suite after every label change

### Risk: Disambiguation over-corrects (breaks real acquisitions/dividends)
**Mitigation**: TestDisambiguationPreservesCorrectClassifications + edge case tests

## Appendix: Test Data Sources

### Existing Test Coverage
- 341 total tests across 11 test files
- Coverage: API endpoints, services, models, integration, performance

### New Disambiguation Tests
- 31 tests in `test_catalyst_type_disambiguation.py`
- 3 production misclassification cases (NTRB, INDP, ONAR)
- 5 divestiture tests, 5 financing tests, 4 revenue tests
- 7 preserve-correct tests, 10 edge case tests

### Sample Headlines for Manual Testing
```python
PRODUCTION_CASES = [
    "Nutriband to sell majority stake of Pocono Pharmaceutical for $5M",  # NTRB
    "Indaptus Therapeutics enters $6M securities purchase agreement with David Lazar",  # INDP
    "Onar says new December clients add over $400,000 in recurring revenue",  # ONAR
]

POSITIVE_CONTROLS = [
    "Sompo To Acquire Aspen For $3.5B, Or $37.50/Share",  # Real acquisition
    "Universal Safety Declares $1 Special Dividend",  # Real dividend
    "Riskified Board Authorizes Repurchase Of Up To $75M",  # Real buyback
]
```

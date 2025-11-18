# Test Specification: Routine Business Operations Filter

**Created**: 2025-11-17
**Spec File**: specs/2025-11-17_17-30_routine_operations_filter.md
**Issue**: benz_sent_filter-1754

## Overview

This test specification provides comprehensive testing guidance for all implementation phases of the routine operations filter feature. Tests are organized by phase to support incremental TDD implementation via the `/implement-phase` workflow.

## Test File Structure

```
tests/
  test_routine_detector.py              # Phase 1 & 2 unit tests
  test_routine_integration.py           # Phase 3 unit tests (API integration)

integration/
  test_routine_operations.py            # Phase 4 integration tests
```

---

## Phase 1: Core Detection Engine - Test Guide

### Existing Tests to Modify

None - this is a new service class.

### New Tests to Create

**File**: `tests/test_routine_detector.py`

#### 1. Service Initialization Tests

**`test_routine_detector_initialization_success`**
- **Input**: None (default initialization)
- **Expected**: RoutineOperationDetector instance created, **compiled regex patterns loaded as class constants**
- **Covers**: Basic service initialization, pattern dictionary availability

**`test_routine_detector_has_process_language_patterns`**
- **Input**: Check detector.PROCESS_LANGUAGE_PATTERNS
- **Expected**: Dictionary with keys: "initiation", "marketing", "planning", "evaluation" - each value is a **compiled regex pattern (re.Pattern)**
- **Covers**: Process language pattern dictionary structure, compiled patterns

**`test_routine_detector_has_transaction_type_patterns`**
- **Input**: Check detector.FINANCIAL_SERVICES_PATTERNS
- **Expected**: Dictionary with patterns for loan sales, buybacks, dividends, refinancing
- **Covers**: Transaction type pattern dictionary structure

**`test_routine_detector_has_frequency_patterns`**
- **Input**: Check detector.FREQUENCY_PATTERNS
- **Expected**: Dictionary with keys: "recurrence", "schedule", "program"
- **Covers**: Frequency indicator pattern dictionary structure

#### 2. Process Language Detection Tests

**`test_detect_process_language_strong_initiation_pattern`**
- **Input**: "Fannie Mae Begins Marketing Its Most Recent Sale"
- **Expected**: Detected, score +2, pattern type "process_language"
- **Covers**: Strong process indicator detection (initiation category)

**`test_detect_process_language_marketing_pattern`**
- **Input**: "Loan Portfolio Available for Purchase"
- **Expected**: Detected, score +1, pattern type "process_language"
- **Covers**: Moderate process indicator detection (marketing category)

**`test_detect_process_language_planning_pattern`**
- **Input**: "Bank Plans to Issue Bonds Next Quarter"
- **Expected**: Detected, score +1, pattern type "process_language"
- **Covers**: Planning language detection

**`test_detect_process_language_evaluation_pattern`**
- **Input**: "Company Exploring Options for Debt Refinancing"
- **Expected**: Detected, score +1, pattern type "process_language"
- **Covers**: Evaluation language detection

**`test_detect_process_language_case_insensitive`**
- **Input**: "BEGINS MARKETING", "begins marketing", "Begins Marketing"
- **Expected**: All variations detected
- **Covers**: Case-insensitive pattern matching

**`test_detect_process_language_multiple_patterns`**
- **Input**: "Bank Begins Marketing and Plans to Launch Sale"
- **Expected**: Detected, compound score (multiple patterns), multiple pattern types
- **Covers**: Multiple process indicators in single headline

**`test_detect_process_language_completed_transaction_excluded`**
- **Input**: "Completes Sale of Loan Portfolio"
- **Expected**: NOT detected (completion keywords exclude routine)
- **Covers**: Edge case - completed transactions not flagged as process

**`test_detect_process_language_no_pattern_match`**
- **Input**: "Bank Reports Q2 Earnings of $1B"
- **Expected**: NOT detected, score 0
- **Covers**: Headlines without process language

#### 3. Routine Transaction Type Detection Tests

**`test_detect_routine_transaction_loan_portfolio_sale`**
- **Input**: "Sale of Reperforming Loans"
- **Expected**: Detected, score +1, pattern type "routine_transaction"
- **Covers**: Loan portfolio sale pattern (financial services)

**`test_detect_routine_transaction_buyback_program`**
- **Input**: "Share Repurchase Program Announced"
- **Expected**: Detected, score +1, pattern type "routine_transaction"
- **Covers**: Buyback program pattern

**`test_detect_routine_transaction_quarterly_dividend`**
- **Input**: "Quarterly Dividend Payment of $0.50"
- **Expected**: Detected, score +1, pattern type "routine_transaction"
- **Covers**: Scheduled dividend pattern

**`test_detect_routine_transaction_debt_refinancing`**
- **Input**: "Bond Issuance for Debt Refinancing"
- **Expected**: Detected, score +1, pattern type "routine_transaction"
- **Covers**: Refinancing pattern

**`test_detect_routine_transaction_special_dividend_excluded`**
- **Input**: "Special Dividend of $5.00 Announced"
- **Expected**: NOT detected (special dividend is exceptional, not routine)
- **Covers**: Edge case - special dividends excluded

**`test_detect_routine_transaction_no_match`**
- **Input**: "Acquisition of Competitor for $10B"
- **Expected**: NOT detected, score 0
- **Covers**: Non-routine transactions excluded

#### 4. Frequency Indicator Detection Tests

**`test_detect_frequency_indicator_recurrence`**
- **Input**: "Most Recent Sale of Reperforming Loans"
- **Expected**: Detected, score +1, pattern type "frequency_indicator"
- **Covers**: Recurrence pattern ("most recent", "latest", "another")

**`test_detect_frequency_indicator_schedule`**
- **Input**: "Quarterly Dividend Payment"
- **Expected**: Detected, score +1, pattern type "frequency_indicator"
- **Covers**: Schedule pattern ("quarterly", "annual", "regular")

**`test_detect_frequency_indicator_program`**
- **Input**: "As Part of Ongoing Buyback Program"
- **Expected**: Detected, score +1, pattern type "frequency_indicator"
- **Covers**: Program pattern ("as part of", "pursuant to")

**`test_detect_frequency_indicator_multiple_patterns`**
- **Input**: "Latest Quarterly Dividend Payment"
- **Expected**: Detected, compound score +2 (multiple indicators)
- **Covers**: Multiple frequency indicators

**`test_detect_frequency_indicator_no_match`**
- **Input**: "First-Ever Dividend Payment"
- **Expected**: NOT detected, score 0
- **Covers**: Non-recurring events excluded

#### 5. Dollar Amount Extraction Tests

**`test_extract_dollar_amount_millions_abbreviation`**
- **Input**: "$560M"
- **Expected**: 560000000.0
- **Covers**: Millions format with abbreviation

**`test_extract_dollar_amount_billions_abbreviation`**
- **Input**: "$1.5B"
- **Expected**: 1500000000.0
- **Covers**: Billions format with abbreviation

**`test_extract_dollar_amount_millions_word`**
- **Input**: "$500 million"
- **Expected**: 500000000.0
- **Covers**: Millions format with word

**`test_extract_dollar_amount_billions_word`**
- **Input**: "$2.3 billion"
- **Expected**: 2300000000.0
- **Covers**: Billions format with word

**`test_extract_dollar_amount_euro_symbol`**
- **Input**: "€100M"
- **Expected**: 100000000.0
- **Covers**: Euro currency symbol support

**`test_extract_dollar_amount_range_midpoint`**
- **Input**: "Between $50M and $100M"
- **Expected**: 75000000.0 (midpoint)
- **Covers**: Range handling

**`test_extract_dollar_amount_no_amount`**
- **Input**: "No financial figures mentioned"
- **Expected**: None
- **Covers**: Headlines without dollar amounts

**`test_extract_dollar_amount_multiple_amounts_first`**
- **Input**: "$500M initial, $1B total"
- **Expected**: 500000000.0 (first amount extracted)
- **Covers**: Multiple amounts - extract first

#### 6. Scoring Algorithm Tests

**`test_scoring_algorithm_process_plus_frequency`**
- **Input**: Headline with process language (+2) and frequency indicator (+1)
- **Expected**: routine_score = 3, detected_patterns = ["process_language", "frequency_indicator"]
- **Covers**: Additive scoring from multiple pattern categories

**`test_scoring_algorithm_all_patterns`**
- **Input**: Headline with process (+2), transaction type (+1), frequency (+1)
- **Expected**: routine_score = 4, detected_patterns = ["process_language", "routine_transaction", "frequency_indicator"]
- **Covers**: Maximum possible routine_score

**`test_scoring_algorithm_single_pattern`**
- **Input**: Headline with only frequency indicator (+1)
- **Expected**: routine_score = 1, detected_patterns = ["frequency_indicator"]
- **Covers**: Single pattern detection

**`test_scoring_algorithm_no_patterns`**
- **Input**: "Bank Reports Q2 Earnings"
- **Expected**: routine_score = 0, detected_patterns = []
- **Covers**: Zero score for non-routine headlines

**`test_scoring_algorithm_consistent_reproducible`**
- **Input**: Same headline tested multiple times
- **Expected**: Identical routine_score and patterns each time
- **Covers**: Reproducibility requirement

#### 7. Confidence Calculation Tests (Phase 1 - Base Confidence)

**`test_confidence_calculation_base_value`**
- **Input**: routine_score = 0, no materiality, no context
- **Expected**: confidence = 0.5
- **Covers**: Base confidence value

**`test_confidence_calculation_strong_patterns_boost`**
- **Input**: routine_score = 3, no materiality, no context
- **Expected**: confidence = 0.7 (0.5 + 0.2)
- **Covers**: +0.2 boost for routine_score >= 3

**`test_confidence_calculation_weak_patterns_no_boost`**
- **Input**: routine_score = 2, no materiality, no context
- **Expected**: confidence = 0.5 (no boost for score < 3)
- **Covers**: No boost for weak patterns

**`test_confidence_calculation_conflicting_signals_penalty`**
- **Input**: routine_score = 3, headline contains "record-breaking" (superlative)
- **Expected**: confidence = 0.4 (0.7 - 0.3 penalty)
- **Covers**: -0.3 penalty for conflicting signals

**`test_confidence_calculation_superlative_detection`**
- **Input**: Headlines with "largest ever", "unprecedented", "record"
- **Expected**: Superlative detected, confidence reduced
- **Covers**: Superlative detection logic

**`test_confidence_calculation_clamped_to_range`**
- **Input**: Edge cases that would produce values outside [0.0, 1.0]
- **Expected**: Confidence clamped to [0.0, 1.0]
- **Covers**: Confidence range enforcement

#### 8. Edge Case Tests

**`test_edge_case_empty_headline`**
- **Input**: ""
- **Expected**: routine_score = 0, confidence = 0.5, transaction_value = None
- **Covers**: Empty input handling

**`test_edge_case_none_headline`**
- **Input**: None
- **Expected**: Appropriate error or zero score
- **Covers**: None input handling

**`test_edge_case_very_long_headline`**
- **Input**: Headline > 500 characters
- **Expected**: Pattern matching still works
- **Covers**: Long text handling

**`test_edge_case_special_characters`**
- **Input**: "Fannie Mae Begins Marketing... $560M!!!"
- **Expected**: Patterns detected despite special characters
- **Covers**: Special character robustness

### Test Implementation Notes

- **Fixtures**: Create `sample_fnma_headline`, `sample_routine_dividend`, `sample_major_acquisition` in conftest.py
- **Mocks**: No external dependencies in Phase 1 (no MNLS model, no API calls)
- **Coverage Target**: 100% coverage on core detection logic
- **Test Organization**: Group by pattern category (process, transaction, frequency) for clarity
- **Model Structure**: `RoutineDetectionResult` Pydantic model with required Phase 1 fields (routine_score, confidence, detected_patterns, transaction_value, process_stage) and optional Phase 2 fields (materiality_score, materiality_ratio). Test that Phase 1 returns None for Phase 2 fields.

---

## Phase 2: Materiality Assessment - Test Guide

### Existing Tests to Modify

**File**: `tests/test_routine_detector.py`

- Extend confidence calculation tests to include materiality factors
- Add company context dictionary tests

### New Tests to Create

**File**: `tests/test_routine_detector.py` (continued)

#### 1. Company Context Dictionary Tests

**`test_company_context_dictionary_has_fnma`**
- **Input**: Check detector.COMPANY_CONTEXT["FNMA"]
- **Expected**: **CompanyContext dataclass instance** with market_cap, annual_revenue, total_assets attributes
- **Covers**: FNMA company context availability, dataclass structure

**`test_company_context_dictionary_has_bac`**
- **Input**: Check detector.COMPANY_CONTEXT["BAC"]
- **Expected**: **CompanyContext dataclass instance** with required financial metrics
- **Covers**: BAC company context availability, dataclass structure

**`test_company_context_dictionary_20_plus_symbols`**
- **Input**: len(detector.COMPANY_CONTEXT)
- **Expected**: >= 20 symbols
- **Covers**: Acceptance criteria - 20+ financial services symbols

**`test_company_context_lookup_known_symbol`**
- **Input**: detector.get_company_context("FNMA")
- **Expected**: Returns FNMA context dict
- **Covers**: Successful company context lookup

**`test_company_context_lookup_unknown_symbol`**
- **Input**: detector.get_company_context("UNKNOWN")
- **Expected**: Returns None (graceful degradation)
- **Covers**: Missing company context handling

#### 2. Materiality Ratio Calculation Tests

**`test_calculate_materiality_ratio_market_cap`**
- **Input**: transaction_value=560500000, market_cap=4000000000
- **Expected**: **MaterialityRatio NamedTuple** with ratio = 0.140125 (transaction / market_cap), metric_type = "market_cap"
- **Covers**: Market cap ratio calculation, NamedTuple structure

**`test_calculate_materiality_ratio_revenue`**
- **Input**: transaction_value=560500000, annual_revenue=25000000000
- **Expected**: ratio = 0.02242 (transaction / revenue)
- **Covers**: Revenue ratio calculation

**`test_calculate_materiality_ratio_assets_fnma_example`**
- **Input**: transaction_value=560500000, total_assets=4000000000000
- **Expected**: ratio = 0.00014 (0.014% - FNMA example)
- **Covers**: Asset ratio calculation, FNMA realistic scenario

**`test_calculate_materiality_ratio_zero_company_metric`**
- **Input**: transaction_value=100M, market_cap=0
- **Expected**: ratio = None or error handling
- **Covers**: Division by zero protection

**`test_calculate_materiality_ratio_none_transaction_value`**
- **Input**: transaction_value=None, market_cap=4B
- **Expected**: ratio = None
- **Covers**: Missing transaction value handling

#### 3. Materiality Threshold Tests

**`test_materiality_threshold_immaterial_market_cap`**
- **Input**: ratio = 0.005 (0.5%), threshold = 0.01
- **Expected**: immaterial = True
- **Covers**: Market cap immaterial threshold (< 1%)

**`test_materiality_threshold_routine_revenue`**
- **Input**: ratio = 0.03 (3%), threshold = 0.05
- **Expected**: routine = True
- **Covers**: Revenue routine threshold (< 5%)

**`test_materiality_threshold_routine_assets`**
- **Input**: ratio = 0.00014 (0.014%), threshold = 0.005
- **Expected**: routine = True (FNMA example)
- **Covers**: Asset routine threshold (< 0.5% for financials)

**`test_materiality_threshold_material_above_threshold`**
- **Input**: ratio = 0.15 (15%), threshold = 0.01
- **Expected**: material = True (routine = False)
- **Covers**: Material transactions not flagged as routine

#### 4. Materiality Scoring Tests

**`test_materiality_scoring_immaterial_negative_two`**
- **Input**: ratio = 0.00014 (well below threshold)
- **Expected**: materiality_score = -2
- **Covers**: Immaterial scoring (clear immateriality)

**`test_materiality_scoring_borderline_negative_one`**
- **Input**: ratio = 0.008 (borderline immaterial)
- **Expected**: materiality_score = -1
- **Covers**: Borderline materiality scoring

**`test_materiality_scoring_material_zero`**
- **Input**: ratio = 0.15 (clearly material)
- **Expected**: materiality_score = 0 (no adjustment)
- **Covers**: Material transaction scoring

**`test_materiality_scoring_missing_context_zero`**
- **Input**: No company context available
- **Expected**: materiality_score = 0 (neutral, no assessment)
- **Covers**: Graceful degradation without context

#### 5. Enhanced Confidence Calculation Tests

**`test_confidence_with_clear_materiality_boost`**
- **Input**: routine_score=3, materiality_score=-2, context available
- **Expected**: confidence = 0.5 + 0.2 (patterns) + 0.2 (materiality) + 0.15 (context) = 1.05 → 1.0 (clamped)
- **Covers**: All positive factors combined, clamping to 1.0

**`test_confidence_with_context_available_boost`**
- **Input**: routine_score=2, materiality_score=0, context available
- **Expected**: confidence = 0.5 + 0.15 (context) = 0.65
- **Covers**: +0.15 boost for company context availability

**`test_confidence_with_borderline_materiality_no_boost`**
- **Input**: routine_score=3, materiality_score=-1 (borderline)
- **Expected**: confidence = 0.7 (only pattern boost, no materiality boost for -1)
- **Covers**: Materiality boost only for clear immateriality (-2)

**`test_confidence_without_context_no_boost`**
- **Input**: routine_score=3, no context available
- **Expected**: confidence = 0.7 (no context boost)
- **Covers**: No context availability boost when context missing

**`test_confidence_fnma_realistic_scenario`**
- **Input**: FNMA loan sale, routine_score=3, materiality_score=-2, context available
- **Expected**: confidence >= 0.85 (high confidence for clear routine operation)
- **Covers**: Acceptance criteria - FNMA example with high confidence

#### 6. Integration with Detection Logic

**`test_detect_with_materiality_fnma_loan_sale`**
- **Input**: "Fannie Mae Begins Marketing Its Most Recent Sale Of Reperforming Loans... $560.5M", symbol="FNMA"
- **Expected**:
  - routine_score = 3 (process + frequency + transaction type)
  - materiality_score = -2 (immaterial)
  - materiality_ratio = 0.00014
  - transaction_value = 560500000
  - confidence >= 0.85
  - result = True (routine operation)
- **Covers**: Full FNMA example from spec

**`test_detect_with_materiality_missing_context`**
- **Input**: "Company X Begins Marketing Loan Sale $560M", symbol="UNKNOWN"
- **Expected**:
  - routine_score = 2 or 3 (patterns detected)
  - materiality_score = 0 (no context)
  - materiality_ratio = None
  - confidence = 0.5-0.7 (lower due to missing context)
- **Covers**: Graceful degradation without company context

**`test_detect_with_materiality_large_material_transaction`**
- **Input**: "Bank Acquires Competitor for $50B", symbol="BAC" (market cap ~$300B)
- **Expected**:
  - routine_score = 0 (no routine patterns)
  - materiality_score = 0 (material ratio ~16%)
  - result = False (not routine)
- **Covers**: Material transactions not flagged

### Test Implementation Notes

- **Company Context Data**: Create realistic test data for FNMA, BAC, JPM, WFC, C, GS in company context dictionary
- **Threshold Constants**: Define as class constants for easy tuning
- **Fixtures**: Add `company_context_fnma`, `company_context_unknown` fixtures
- **Coverage Target**: 95%+ coverage on materiality logic

---

## Phase 3: API Integration - Test Guide

### Existing Tests to Modify

**File**: `tests/test_api.py`

- Update classification response assertions to expect per-dimension structure
- Verify routine_operation field included in responses

**File**: `tests/test_models.py`

- Update ClassificationResponse model tests for new structure

### New Tests to Create

**File**: `tests/test_routine_integration.py`

#### 1. Response Model Tests

**`test_classification_response_per_dimension_structure`**
- **Input**: Create ClassificationResponse **Pydantic model** with opinion, temporal, routine_operation dimensions
- **Expected**: JSON serialization matches per-dimension format from spec, Pydantic validation passes
- **Covers**: Response model structure validation, Pydantic model usage

**`test_opinion_classification_dimension`**
- **Input**: Opinion classification data
- **Expected**:
  ```json
  {
    "result": "opinion",
    "confidence": 0.85
  }
  ```
- **Covers**: Opinion dimension structure

**`test_temporal_classification_dimension`**
- **Input**: Temporal classification data
- **Expected**:
  ```json
  {
    "result": "past",
    "confidence": 0.72
  }
  ```
- **Covers**: Temporal dimension structure

**`test_routine_operation_dimension_with_metadata`**
- **Input**: Routine operation detection result
- **Expected**:
  ```json
  {
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
  ```
- **Covers**: Routine operation dimension with full metadata

**`test_routine_operation_metadata_optional_fields_null`**
- **Input**: Routine detection without company context
- **Expected**: materiality_ratio = null, transaction_value = null in metadata
- **Covers**: Nullable metadata fields

**`test_response_model_pydantic_validation`**
- **Input**: Invalid response data (missing required fields)
- **Expected**: Pydantic ValidationError
- **Covers**: Response model validation

#### 2. Classification Service Integration Tests

**`test_classification_service_invokes_routine_detector`**
- **Input**: Headline with routine patterns
- **Expected**: RoutineOperationDetector.detect() called via composition (detector is instance attribute of ClassificationService)
- **Covers**: Service integration (routine detector invoked), composition pattern

**`test_classification_service_parallel_execution`**
- **Input**: Headline (measure execution time with/without routine detection)
- **Expected**: No significant serial slowdown (parallel execution working)
- **Covers**: Performance - parallel execution

**`test_classification_service_preserves_mnls_results`**
- **Input**: Headline
- **Expected**: Opinion and temporal classifications unchanged from baseline
- **Covers**: Existing MNLS classification logic unaffected

**`test_classification_service_merges_routine_results`**
- **Input**: Headline with routine patterns
- **Expected**: Response includes all three dimensions (opinion, temporal, routine_operation)
- **Covers**: Results merging into unified response

**`test_classification_service_routine_detection_with_company_symbol`**
- **Input**: Headline, company_symbol="FNMA"
- **Expected**: Routine detection uses company context for materiality
- **Covers**: Company symbol passed to routine detector

#### 3. API Endpoint Tests

**`test_single_classification_endpoint_includes_routine_operation`**
- **Input**: POST /classify {"headline": "FNMA Begins Marketing Loan Sale $560M"}
- **Expected**: Response includes routine_operation dimension with metadata
- **Covers**: Single classification endpoint integration

**`test_single_classification_endpoint_per_dimension_confidence`**
- **Input**: POST /classify {"headline": "..."}
- **Expected**: Each dimension has independent confidence score
- **Covers**: Per-dimension confidence in API response

**`test_batch_classification_endpoint_includes_routine_operation`**
- **Input**: POST /classify/batch {"headlines": [...]}
- **Expected**: All results include routine_operation dimension
- **Covers**: Batch endpoint integration

**`test_batch_classification_endpoint_maintains_order`**
- **Input**: Batch with 3 headlines (routine, material, neutral)
- **Expected**: Results in same order, correct routine detection for each
- **Covers**: Batch processing order and correctness

**`test_api_response_json_schema_matches_spec`**
- **Input**: API response JSON
- **Expected**: Schema validation passes against spec format
- **Covers**: API contract validation

**`test_api_response_backward_compatibility`**
- **Input**: Existing MNLS classification request
- **Expected**: Response includes new fields, existing logic intact
- **Covers**: Backward compatibility

#### 4. Performance Tests

**`test_single_classification_performance_under_100ms`**
- **Input**: Single headline classification
- **Expected**: Overhead from routine detection < 100ms
- **Covers**: Performance acceptance criteria

**`test_batch_classification_performance_scales_linearly`**
- **Input**: Batches of 10, 50, 100 headlines
- **Expected**: Time scales roughly linearly, routine detection doesn't cause quadratic slowdown
- **Covers**: Batch performance scaling

#### 5. Edge Case Integration Tests

**`test_routine_detection_with_none_company_symbol`**
- **Input**: Headline, company_symbol=None
- **Expected**: Routine detection runs without context (materiality_ratio=null)
- **Covers**: Missing company symbol handling

**`test_routine_detection_with_unknown_symbol`**
- **Input**: Headline, company_symbol="UNKNOWN"
- **Expected**: Routine detection runs, materiality_ratio=null, lower confidence
- **Covers**: Unknown company symbol handling

**`test_api_error_handling_routine_detector_failure`**
- **Input**: Mock RoutineOperationDetector to raise exception
- **Expected**: API returns 500 error with appropriate message
- **Covers**: Error handling in routine detection integration

### Test Implementation Notes

- **Mocks**: Mock RoutineOperationDetector for some API tests to isolate API layer
- **Integration**: Some tests should use real detector to verify end-to-end flow
- **API Client**: Use FastAPI TestClient for endpoint tests
- **Fixtures**: Add `api_client`, `routine_detector_mock` fixtures
- **Coverage Target**: 95%+ on API integration layer

---

## Phase 4: Integration Testing & Validation - Test Guide

### Existing Tests to Modify

None - these are new end-to-end integration tests.

### New Tests to Create

**File**: `integration/test_routine_operations.py`

#### 1. Real-World Example Tests

**`test_fnma_loan_sale_routine_detection_high_confidence`**
- **Input**: "Fannie Mae Begins Marketing Its Most Recent Sale Of Reperforming Loans... $560.5M"
- **Expected**:
  - routine_operation.result = True
  - routine_operation.confidence >= 0.85
  - routine_score = 3
  - materiality_score = -2
  - process_stage = "early"
- **Covers**: FNMA example from spec (acceptance criteria - 100% success)

**`test_bac_regular_buyback_routine_detection`**
- **Input**: "Bank of America Announces Another Quarterly Share Repurchase Program"
- **Expected**:
  - routine_operation.result = True
  - detected_patterns includes "routine_transaction", "frequency_indicator"
- **Covers**: Regular buyback program detection

**`test_jpm_quarterly_dividend_routine_detection`**
- **Input**: "JPMorgan Chase Declares Quarterly Dividend of $1.00 Per Share"
- **Expected**:
  - routine_operation.result = True
  - detected_patterns includes "routine_transaction", "frequency_indicator"
- **Covers**: Scheduled dividend detection

**`test_gs_debt_offering_routine_detection`**
- **Input**: "Goldman Sachs Files to Issue $2B in Senior Notes"
- **Expected**:
  - routine_operation.result = True (if immaterial)
  - detected_patterns includes "routine_transaction"
- **Covers**: Debt refinancing pattern

#### 2. False Positive Prevention Tests

**`test_major_acquisition_not_flagged_as_routine`**
- **Input**: "JPMorgan Acquires First Republic Bank for $50B"
- **Expected**:
  - routine_operation.result = False
  - routine_score = 0 (no routine patterns)
- **Covers**: Acceptance criteria - major acquisitions NOT flagged (0% false positives)

**`test_large_contract_win_not_flagged`**
- **Input**: "Bank Wins $10B Government Contract"
- **Expected**:
  - routine_operation.result = False
- **Covers**: Large contracts not flagged as routine

**`test_exceptional_dividend_not_flagged`**
- **Input**: "Special Dividend of $10 Per Share Announced"
- **Expected**:
  - routine_operation.result = False ("special" keyword excludes)
- **Covers**: Special dividends excluded from routine

**`test_record_transaction_not_flagged`**
- **Input**: "Bank Announces Record-Breaking $100B Merger"
- **Expected**:
  - routine_operation.result = False or low confidence (superlative detected)
- **Covers**: Superlative detection prevents false positives

**`test_completed_transaction_not_flagged`**
- **Input**: "Fannie Mae Completes Sale of $500M Loan Portfolio"
- **Expected**:
  - routine_operation.result = False (completed transactions are material)
- **Covers**: Completion keywords exclude routine classification

#### 3. Edge Case Validation Tests

**`test_large_absolute_value_immaterial_relative`**
- **Input**: "FNMA Begins Marketing $800M Loan Portfolio" (0.02% of assets)
- **Expected**:
  - routine_operation.result = True
  - materiality_ratio < 0.005 (immaterial despite large absolute value)
- **Covers**: Edge case - large absolute numbers, small relative

**`test_missing_company_context_pattern_based_detection`**
- **Input**: "Unknown Bank Begins Marketing Quarterly Dividend"
- **Expected**:
  - routine_operation.result = True (based on patterns only)
  - materiality_ratio = null
  - confidence < 0.7 (lower without context)
- **Covers**: Edge case - missing company context

**`test_conflicting_signals_low_confidence`**
- **Input**: "FNMA Begins Marketing Record-Breaking $1B Loan Sale"
- **Expected**:
  - routine_operation.result = True or False
  - confidence reduced due to "record-breaking" superlative
- **Covers**: Edge case - conflicting signals

**`test_special_vs_regular_dividend`**
- **Input**: ["Regular Dividend $0.50", "Special Dividend $5.00"]
- **Expected**:
  - Regular: routine = True
  - Special: routine = False
- **Covers**: Edge case - special dividend distinction

#### 4. Accuracy Measurement Tests

**`test_accuracy_on_labeled_routine_dataset`**
- **Input**: 50+ labeled routine operation examples
- **Expected**: Accuracy >= 85% (true positives)
- **Covers**: Acceptance criteria - 85%+ accuracy on labeled dataset

**`test_accuracy_on_labeled_material_dataset`**
- **Input**: 50+ labeled material event examples
- **Expected**: False positive rate < 10%
- **Covers**: Acceptance criteria - < 10% false positive rate

**`test_precision_recall_f1_metrics`**
- **Input**: Combined labeled dataset (routine + material)
- **Expected**: Calculate precision, recall, F1 score
- **Covers**: Overall classification quality metrics

**`test_confidence_score_correlation`**
- **Input**: Labeled dataset with known correct/incorrect classifications
- **Expected**: Higher confidence correlates with higher accuracy
- **Covers**: Success metric - confidence scores correlate with accuracy

#### 5. Performance Benchmarking Tests

**`test_single_classification_latency_under_100ms`**
- **Input**: 100 sequential single classifications
- **Expected**: Average overhead < 100ms per classification
- **Covers**: Acceptance criteria - < 100ms performance overhead

**`test_batch_classification_throughput`**
- **Input**: Batch of 1000 headlines
- **Expected**: Total time < 100 seconds (< 100ms per headline)
- **Covers**: Batch processing performance

**`test_memory_footprint_pattern_dictionaries`**
- **Input**: Measure RoutineOperationDetector memory usage
- **Expected**: < 10MB for pattern dictionaries
- **Covers**: Performance consideration - memory footprint

#### 6. Cross-Company Validation Tests

**`test_validation_across_gses`**
- **Input**: Examples from FNMA, FHLMC (Freddie Mac)
- **Expected**: Both correctly identify routine loan sales
- **Covers**: GSE coverage

**`test_validation_across_banks`**
- **Input**: Examples from JPM, BAC, WFC, C, GS
- **Expected**: Routine operations correctly identified for all major banks
- **Covers**: Large bank coverage

**`test_validation_insurance_companies`**
- **Input**: Examples from insurance/asset managers (if relevant)
- **Expected**: Routine operations in insurance context
- **Covers**: Financial services diversity

### Test Implementation Notes

- **Test Dataset**: Build labeled dataset with 50+ routine examples, 50+ material examples
- **Test Fixtures**: Load test dataset from JSON/YAML file for repeatability
- **Metrics Calculation**: Implement precision, recall, F1 helpers
- **Performance**: Use pytest-benchmark for timing measurements
- **Documentation Examples**: Select 5 best examples for API documentation
- **Coverage Target**: End-to-end validation of all spec acceptance criteria

---

## Test Data Fixtures

### Routine Operation Examples (True Positives)

```python
ROUTINE_OPERATION_EXAMPLES = [
    {
        "headline": "Fannie Mae Begins Marketing Its Most Recent Sale Of Reperforming Loans... $560.5M",
        "symbol": "FNMA",
        "expected_routine": True,
        "expected_confidence": ">= 0.85",
        "expected_patterns": ["process_language", "routine_transaction", "frequency_indicator"]
    },
    {
        "headline": "Bank of America Announces Quarterly Dividend of $0.25 Per Share",
        "symbol": "BAC",
        "expected_routine": True,
        "expected_patterns": ["routine_transaction", "frequency_indicator"]
    },
    {
        "headline": "Wells Fargo Continues Share Repurchase Program",
        "symbol": "WFC",
        "expected_routine": True,
        "expected_patterns": ["frequency_indicator", "routine_transaction"]
    },
    # ... 47 more examples
]
```

### Material Event Examples (True Negatives - Should NOT Flag)

```python
MATERIAL_EVENT_EXAMPLES = [
    {
        "headline": "JPMorgan Acquires First Republic Bank for $50B",
        "symbol": "JPM",
        "expected_routine": False,
        "reason": "Major acquisition"
    },
    {
        "headline": "Goldman Sachs Announces Record Q4 Earnings",
        "symbol": "GS",
        "expected_routine": False,
        "reason": "Earnings announcement, superlative"
    },
    {
        "headline": "Citigroup Completes $10B Asset Sale",
        "symbol": "C",
        "expected_routine": False,
        "reason": "Completed transaction (material event)"
    },
    # ... 47 more examples
]
```

---

## Test Execution Strategy

### Phase-by-Phase Execution

1. **Phase 1**: Run `pytest tests/test_routine_detector.py -k "not materiality"` - Core detection only
2. **Phase 2**: Run `pytest tests/test_routine_detector.py` - Full detector with materiality
3. **Phase 3**: Run `pytest tests/test_routine_integration.py tests/test_api.py` - API integration
4. **Phase 4**: Run `pytest integration/test_routine_operations.py` - End-to-end validation

### Coverage Targets

- **Phase 1**: 100% coverage on core detection methods
- **Phase 2**: 95%+ coverage on materiality logic
- **Phase 3**: 95%+ coverage on API integration
- **Phase 4**: Validation of all acceptance criteria (not coverage-based)

### Continuous Testing

```bash
# Watch mode for TDD
pytest tests/test_routine_detector.py --watch

# Full test suite with coverage
pytest --cov=benz_sent_filter --cov-report=html

# Integration tests only
pytest integration/
```

---

## Success Criteria Validation Matrix

| Acceptance Criteria | Test Coverage |
|---------------------|---------------|
| FNMA loan sales correctly flagged | `test_fnma_loan_sale_routine_detection_high_confidence` |
| Major transactions NOT flagged | `test_major_acquisition_not_flagged_as_routine`, etc. |
| 85%+ accuracy | `test_accuracy_on_labeled_routine_dataset` |
| < 10% false positives | `test_accuracy_on_labeled_material_dataset` |
| < 100ms overhead | `test_single_classification_latency_under_100ms` |
| Per-dimension confidence | `test_single_classification_endpoint_per_dimension_confidence` |
| 20+ company symbols | `test_company_context_dictionary_20_plus_symbols` |

---

*This test specification provides comprehensive guidance for TDD implementation of the routine operations filter across all phases.*

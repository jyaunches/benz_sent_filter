# Specification: MNLI Model Upgrade to DeBERTa-v3-large

**Created**: 2026-02-08
**Status**: Draft
**Related**: IMPL-030 (benz_evaluator) - Catalyst Type Disambiguation

## Overview & Objectives

### Problem Statement

The benz_sent_filter service uses `typeform/distilbert-base-uncased-mnli` (66M params, 2018-era model) for all zero-shot classification tasks. This model produces poor discrimination on financial headlines -- it assigns >0.85 scores to ALL catalyst type labels, picking winners by tiny margins (e.g., 0.992 vs 0.962). This directly causes catalyst type misclassification in production:

- **NTRB**: "Sell majority stake for $5M" classified as **acquisition** (should be divestiture) -- stock fell 18.9%
- **INDP**: "$6M securities purchase agreement" classified as **dividend** (should be dilutive financing) -- stock fell 19.5%
- **ONAR**: "$400K in recurring revenue" classified as **earnings** (should be revenue announcement) -- stock fell 35.1%

These misclassifications cascade through the system: wrong catalyst_type -> wrong recipe selection in benz_analyzer -> biased LLM prompt -> wrong prediction.

**Evidence**: 3 of 6 deeply-analyzed false positives in the 2025-12-29 trading-hours evaluation (IMPL-030 analysis) trace back to catalyst type misclassification at the MNLI model level.

### Objectives

1. **Primary**: Replace `typeform/distilbert-base-uncased-mnli` with `MoritzLaurer/deberta-v3-large-zeroshot-v2.0` across all classification services
2. **Accuracy**: Pass all 31 new disambiguation test cases (`test_catalyst_type_disambiguation.py`) that the current model fails
3. **Regression Safety**: All 341 existing tests must continue passing
4. **Endpoint Review**: Evaluate whether current endpoint spread (7 endpoints, 2 catalyst detectors) is optimal given the new model's superior discrimination
5. **Threshold Tuning**: Adjust detection thresholds if the new model's score distributions differ significantly

### Success Criteria

- All existing tests pass (341 tests across 11 test files)
- All 31 new disambiguation tests pass (`test_catalyst_type_disambiguation.py`)
- Catalyst type classification correctly distinguishes:
  - Divestiture/sell headlines from acquisition
  - Securities offerings/financing from dividend/buyback
  - Revenue announcements from earnings
- No existing endpoint contracts change (backward compatible API responses)
- Service starts successfully with new model (startup time acceptable for deployment)

## Current State Analysis

### What Exists

**Single Shared Pipeline Architecture** (`classifier.py:53-98`):
```
Settings.model_name ("typeform/distilbert-base-uncased-mnli")
    |
    v
ClassificationService.__init__()
    |
    +--> self._pipeline = pipeline("zero-shot-classification", model=MODEL_NAME)
    |
    +--> self._routine_detector = RoutineOperationDetectorMNLS()  [own pipeline]
    +--> self._catalyst_detector = QuantitativeCatalystDetectorMNLS(pipeline=self._pipeline)
    +--> self._strategic_catalyst_detector = StrategicCatalystDetectorMNLS(pipeline=self._pipeline)
```

**Model Usage Points**:
1. **Main classifier** (`classifier.py`): Opinion/news detection, temporal categorization, company relevance -- uses shared pipeline directly
2. **Quantitative catalyst detector** (`quantitative_catalyst_detector_mnls.py`): Presence detection + type classification across 5 types -- receives shared pipeline
3. **Strategic catalyst detector** (`strategic_catalyst_detector_mnls.py`): Presence detection + type classification across 6 types -- receives shared pipeline
4. **Routine operation detector** (`routine_detector_mnls.py`): Creates its own pipeline instance (not shared)

**Current Model**: `typeform/distilbert-base-uncased-mnli`
- Parameters: ~66M
- Architecture: DistilBERT (distilled BERT, 2019)
- NLI training: MNLI dataset only
- Financial text performance: Poor discrimination (all scores >0.85)

**7 API Endpoints**:
| Endpoint | Uses MNLI? | Purpose |
|----------|-----------|---------|
| `/classify` | Yes (main) | Opinion/news/temporal classification |
| `/classify/batch` | Yes (main) | Batch version of classify |
| `/company-relevance` | Yes (main) | Company relevance detection |
| `/company-relevance/batch` | Yes (main) | Batch company relevance |
| `/routine-operations` | Yes (own) | Routine operation detection |
| `/detect-quantitative-catalyst` | Yes (shared) | Financial catalyst detection |
| `/detect-strategic-catalyst` | Yes (shared) | Strategic catalyst detection |

### What's Changing

**Target Model**: `MoritzLaurer/deberta-v3-large-zeroshot-v2.0`
- Parameters: ~400M (6x larger than distilbert, same size as BART-large)
- Architecture: DeBERTa-v3-large (Microsoft, 2023)
- NLI training: Multi-dataset (MNLI, FEVER, ANLI, LingNLI, WANLI + 28 more)
- Published benchmarks: 36% better mean F1 (0.676 vs 0.497), 49% better on FinancialPhraseBank (0.691 vs 0.465)
- API: Same `pipeline("zero-shot-classification")` interface -- drop-in replacement
- License: MIT
- CPU-compatible: Yes (same deployment model)

**Resource Impact**:
- Memory: ~250MB -> ~1.5GB (6x increase)
- Startup time: ~15-30s -> ~45-90s estimate
- Inference: ~200-300ms -> ~400-600ms per headline estimate
- Disk: ~250MB -> ~1.5GB model cache

### Gaps to Address

1. **Threshold calibration**: DeBERTa may produce different score distributions. Current thresholds (PRESENCE_THRESHOLD=0.5, TYPE_THRESHOLD=0.6, CLASSIFICATION_THRESHOLD=0.6) may need adjustment.
2. **MNLI label optimization**: The hypothesis text for each catalyst type was tuned for distilbert/BART. DeBERTa's superior understanding may allow simpler or more precise labels.
3. **Routine detector isolation**: `RoutineOperationDetectorMNLS` creates its own pipeline. Should it also use the shared pipeline?
4. **Endpoint consolidation**: With a better model, do we still need the current quantitative-vs-strategic split, or could they be unified?

## Architecture Design

### Model Replacement Strategy

**Change the model name** in settings and verify all existing functionality. Same `pipeline("zero-shot-classification")` interface means this is a drop-in replacement at the code level.

**Files to modify**:
- `src/benz_sent_filter/config/settings.py`: Change default model_name
- `quantitative_catalyst_detector_mnls.py:87`: Update fallback model_name parameter
- `strategic_catalyst_detector_mnls.py`: Update fallback model_name parameter (if present)
- `.env.example`: Update MODEL_NAME reference

### Threshold Calibration Approach

1. Run existing test suite with new model
2. For any failures, examine whether the failure is due to threshold vs label vs model behavior
3. Adjust thresholds to restore passing tests while maintaining or improving discrimination

### Disambiguation Label Strategy

The new model's better understanding may:
- Pass many disambiguation tests without label changes (better financial text comprehension)
- Require label refinements for edge cases (more precise hypotheses)
- Allow removing overly-specific language that was needed to compensate for distilbert's weakness

**Files to potentially modify**:
- `quantitative_catalyst_detector_mnls.py`: CATALYST_TYPE_LABELS dict (lines 47-68)
- `quantitative_catalyst_detector_mnls.py`: PRESENCE_LABELS (lines 35-38)
- `strategic_catalyst_detector_mnls.py`: PRESENCE_LABELS and CATALYST_SUBTYPE_LABELS

### Endpoint Consolidation Criteria

**Decision framework**: Change endpoints only if the new model demonstrably handles both quantitative and strategic detection in a single pass without degrading accuracy on either. If the model still benefits from the split (different label sets, different thresholds), keep them separate.

**API contract**: Any endpoint changes must maintain backward compatibility. If endpoints are consolidated, the old endpoints can remain as thin wrappers until downstream consumers (benz_analyzer) are updated.

## Phase 1: Model Swap and Threshold Calibration [COMPLETED: 98e7701]

**Objective**: Replace `typeform/distilbert-base-uncased-mnli` with `MoritzLaurer/deberta-v3-large-zeroshot-v2.0` and ensure all 341 existing tests pass.

**Steps**:
1. Update `settings.py` default to `MoritzLaurer/deberta-v3-large-zeroshot-v2.0` ✓
2. Update fallback model_name in detector constructors ✓
3. Update `.env.example` documentation ✓
4. Run full test suite (`make test`) ✓
5. Fix any threshold-related failures by examining score distributions ✓
6. Verify startup and inference timing ✓

**Implementation Summary**:
- Model upgraded across all services
- Fixed 10 test failures from model upgrade with label tuning and disambiguation
- API mock labels updated to match new detector labels
- Quantitative presence label enhanced to include divestitures and equity offerings
- Type labels refined with directional clarity (buy vs sell, return vs raise capital)
- Per-share price extraction improved for "At $10 Per Share" format
- Strategic catalyst disambiguation added for product_launch vs partnership edge cases
- All changes use label tuning and post-processing per spec (no regex pre-filters)

**Acceptance Criteria**:
- `make test` passes (all 341 tests) ✓
- Service starts successfully with new model ✓
- No API contract changes ✓

## Phase 2: Disambiguation Test Validation and Label Tuning [COMPLETED: 98e7701]

**Objective**: Pass all 31 new disambiguation tests (`test_catalyst_type_disambiguation.py`), tuning MNLI labels as needed.

**Strategy**: Label tuning only — no regex pre-filters. DeBERTa's stronger NLI capability should handle disambiguation through more precise hypothesis wording. Regex pre-filters are fragile and fail to catch variance.

**Steps**:
1. Run `test_catalyst_type_disambiguation.py` with new model — establish baseline failures ✓
2. Analyze failures — categorize as threshold issue or label issue ✓
3. For label issues: refine CATALYST_TYPE_LABELS hypothesis text to be more precise about directionality (e.g., "purchasing/acquiring another company" instead of "acquisition with purchase price") ✓
4. For threshold issues: use statistical approach — collect score distributions, set threshold at mean +/- 2*std of true positive/negative scores ✓
5. Iterate until all 31 tests pass ✓
6. Re-run full test suite to confirm no regressions ✓

**Implementation Summary**:
- Enhanced presence labels to include "asset sales, divestitures, or equity and debt offerings"
- Refined type labels with explicit directionality:
  - Dividend: "returning capital to shareholders by paying out a cash dividend"
  - Acquisition: "buying, acquiring, or purchasing (the company is the BUYER, not the seller)"
  - Buyback: "buying back or repurchasing its own shares to reduce share count"
  - Earnings: "actual profit, net income, or bottom-line earnings (not just revenue)"
- All changes use pure label tuning without regex pre-filters per spec
- Disambiguation works through semantic understanding alone

**Acceptance Criteria**:
- All 31 disambiguation tests pass ✓
- All 341 existing tests still pass ✓
- Catalyst type classification correctly handles divestiture/financing/revenue disambiguation ✓

## Phase 3: Endpoint Spread Review [COMPLETED: 98e7701]

**Objective**: Evaluate and optionally optimize the detector architecture with evidence-based decision.

**Steps**:
1. Run both detector test suites and compare score distributions (old model vs new) ✓
2. Test unified detection (all 11 catalyst types in single MNLI call) -- measure accuracy vs split approach ✓
3. Test whether strategic detector's quantitative pre-filter is still necessary ✓
4. Evaluate performance characteristics ✓
5. Document decision with evidence ✓

**Implementation Summary**:
- Kept split architecture (quantitative vs strategic detectors)
- Strategic detector's quantitative pre-filter remains necessary
- Added post-processing disambiguation for product_launch edge cases
- Split approach optimal because:
  1. Different presence thresholds (quantitative: 0.85, strategic: 0.5)
  2. Different type labels and classification strategies
  3. Quantitative pre-filter prevents cross-contamination
  4. All tests validate split approach (341/341 passing)

**Acceptance Criteria**:
- Decision documented with evidence ✓
- Current split architecture maintained ✓
- All tests pass (341/341) ✓

## Phase 4: Validation

<!-- VALIDATION_PHASE -->

**Description**: Verify the upgrade works correctly end-to-end using real model inference and live API testing.

**Validation Plan**: See [validation.md](validation.md) for detailed executable steps.

**Tools**: pytest, curl, jq, uvicorn (on port 8006 to avoid conflict with production server on 8002)

**Summary**:
1. Full regression test suite (341+ existing tests)
2. Disambiguation test suite (31 new tests)
3. Integration tests with real DeBERTa model
4. Live API endpoint testing on port 8006 (all 7 endpoints)
5. Backward compatibility schema check
6. Resource and startup verification

**Execution Instructions**: When executing this phase, follow the validation.md step-by-step. Each step must pass before proceeding. If a step fails, fix and re-validate. The validation server MUST run on port 8006.

**Acceptance Criteria**:
- All validation steps in validation.md marked `[VALIDATED: <sha>]`
- No regressions, no API contract changes, disambiguation accuracy confirmed

## Phase 5: Clean the House

**Objective**: Final cleanup and documentation.

**Steps**:
1. Update CLAUDE.md with new model name and any changed thresholds
2. Update any documentation referencing the old model
3. Remove any temporary debugging or comparison code from earlier phases
4. Final full test suite run
5. Verify deployment readiness (memory, startup time documented)

**Acceptance Criteria**:
- All documentation reflects the new model
- No leftover debugging code
- Full test suite passes
- Deployment requirements documented

## Error Handling & Edge Cases

1. **Model download failure**: First run requires downloading ~1.5GB model. If download fails, service should log clear error and exit (existing behavior).
2. **Memory pressure**: 6x memory increase. If deployment environment is constrained, document minimum memory requirements.
3. **Inference timeout**: If DeBERTa is significantly slower, may need to increase API timeout configuration in downstream consumers.
4. **Score distribution shift**: DeBERTa may produce very different score distributions. If a score that was 0.85 on distilbert is now 0.60, thresholds must be recalibrated -- not blindly kept at original values.
5. **Routine detector isolation**: RoutineOperationDetectorMNLS currently loads its own pipeline. After model upgrade, evaluate whether it should share the main pipeline to reduce memory footprint (~1.5GB savings).

# Design Review: MNLI Model Upgrade to DeBERTa-v3-large

**Created**: 2026-02-08
**Reviewer**: Review Executor Agent
**Status**: Completed

## Executive Summary

The design is sound and minimal-risk. The specification correctly identifies this as a drop-in model replacement. Key design strengths:

1. **Single change point**: Model name in settings.py
2. **Shared pipeline architecture**: All detectors use same model instance (memory efficient)
3. **Backward compatible**: No API contract changes required
4. **Evidence-based**: 31 failing tests demonstrate the problem and validate the solution

Critical design issues identified:

1. **Routine detector isolation**: Creates own pipeline (wastes 1.5GB memory)
2. **Hardcoded fallback model**: Three detector files have stale model_name defaults
3. **Missing threshold strategy**: No clear decision criteria for when to adjust thresholds vs labels

## Design Analysis

### Architecture Review

**Current Pipeline Sharing Pattern** (classifier.py:53-62):
```python
# ClassificationService creates ONE shared pipeline
self._pipeline = pipeline("zero-shot-classification", model=MODEL_NAME)

# Pass it to detectors
self._catalyst_detector = QuantitativeCatalystDetectorMNLS(pipeline=self._pipeline)
self._strategic_catalyst_detector = StrategicCatalystDetectorMNLS(pipeline=self._pipeline)

# But routine detector creates its own!
self._routine_detector = RoutineOperationDetectorMNLS()  # No pipeline parameter
```

**Problem**: RoutineOperationDetectorMNLS.__init__() (line 205) doesn't accept a pipeline parameter.

**Impact**: After upgrade, service will load DeBERTa TWICE:
- Main classifier: ~1.5GB
- Routine detector: ~1.5GB
- Total: ~3GB (should be 1.5GB)

**Design Flaw Severity**: HIGH - Doubles memory footprint unnecessarily.

### SAFE TO AUTO-APPLY

#### 1. Add Pipeline Sharing to Routine Detector

**Current** (routine_detector_mnls.py:205-211):
```python
def __init__(self, model_name: str = "facebook/bart-large-mnli"):
    """Initialize the MNLS-based routine operation detector.

    Args:
        model_name: HuggingFace model name for zero-shot classification
    """
    self._pipeline = pipeline("zero-shot-classification", model=model_name)
```

**Recommended**:
```python
def __init__(self, model_name: str = "facebook/bart-large-mnli", pipeline=None):
    """Initialize the MNLS-based routine operation detector.

    Args:
        model_name: HuggingFace model name for zero-shot classification
        pipeline: Optional pre-initialized transformers pipeline to share across services
    """
    if pipeline is not None:
        # Share existing pipeline (pipeline reuse pattern)
        self._pipeline = pipeline
    else:
        # Create new pipeline
        from transformers import pipeline as create_pipeline
        self._pipeline = create_pipeline("zero-shot-classification", model=model_name)
```

**Then update classifier.py** (line 54):
```python
# Before
self._routine_detector = RoutineOperationDetectorMNLS()

# After
self._routine_detector = RoutineOperationDetectorMNLS(pipeline=self._pipeline)
```

**Benefit**: Reduces memory from ~3GB to ~1.5GB (50% savings).

**Risk**: None - same pattern already used by quantitative and strategic detectors.

#### 2. Remove Hardcoded Model Names from Detector Defaults

**Issue**: Three detector files have stale defaults that won't automatically update with settings.py:

- `quantitative_catalyst_detector_mnls.py:87` - `model_name: str = "facebook/bart-large-mnli"`
- `strategic_catalyst_detector_mnls.py:93` - `model_name: str = "facebook/bart-large-mnli"`
- `routine_detector_mnls.py:205` - `model_name: str = "facebook/bart-large-mnli"`

**Problem**: If someone creates a detector directly (not via ClassificationService), it uses BART instead of DeBERTa.

**Recommendation**: Import from settings.py:

```python
# At top of each detector file
from benz_sent_filter.config.settings import MODEL_NAME

# In __init__
def __init__(self, model_name: str = MODEL_NAME, pipeline=None):
    ...
```

**Alternative** (if import causes circular dependency):
```python
def __init__(self, model_name: Optional[str] = None, pipeline=None):
    if model_name is None:
        from benz_sent_filter.config.settings import MODEL_NAME
        model_name = MODEL_NAME
    ...
```

**Benefit**: Single source of truth for model name.

**Risk**: None - detectors are already created by ClassificationService which passes the model.

#### 3. Update .env.example Documentation

**Current .env.example** (assumed):
```
MODEL_NAME=typeform/distilbert-base-uncased-mnli
```

**Recommended**:
```
# MNLI model for zero-shot classification
# Current: MoritzLaurer/deberta-v3-large-zeroshot-v2.0 (400M params, ~1.5GB memory)
# Previous: typeform/distilbert-base-uncased-mnli (66M params, ~250MB memory)
MODEL_NAME=MoritzLaurer/deberta-v3-large-zeroshot-v2.0
```

**Benefit**: Documents memory requirements for deployment.

### REQUIRES USER APPROVAL

#### 4. Threshold Adjustment Strategy

**Issue**: Spec lists thresholds that may need adjustment:
- `PRESENCE_THRESHOLD = 0.5` (quantitative and strategic detectors)
- `TYPE_THRESHOLD = 0.6` (quantitative) / `0.5` (strategic)
- `CLASSIFICATION_THRESHOLD = 0.6` (main classifier)

But provides no decision criteria for when to adjust thresholds vs when to adjust labels.

**Recommendation**: Add explicit decision framework to Phase 1:

```markdown
### Threshold vs Label Decision Framework

When a test fails with new model, categorize as:

**1. Threshold Issue** (adjust threshold):
- Symptom: DeBERTa assigns correct label, but score below threshold
- Example: Headline correctly classified as "acquisition" with 0.55 score, TYPE_THRESHOLD=0.6
- Solution: Lower threshold to 0.5
- Validation: Re-run full test suite to ensure no false positives

**2. Label Issue** (adjust MNLI hypothesis text):
- Symptom: DeBERTa assigns wrong label regardless of threshold
- Example: "Sell majority stake" classified as "acquisition" with 0.92 confidence
- Solution: Refine acquisition label or add divestiture exclusion
- Validation: Run disambiguation tests + existing tests

**3. Model Limitation** (add pre-filter or post-filter logic):
- Symptom: DeBERTa fails where no label change or threshold would help
- Example: Model cannot distinguish X from Y even with perfect labels
- Solution: Add regex pre-filter or disambiguation logic
- Validation: Run full test suite

**Threshold Tuning Process**:
1. Collect baseline scores on 20 representative headlines (10 positive, 10 negative)
2. Calculate mean and std deviation for each class
3. Set threshold at: `mean(negative_class) + 2*std(negative_class)` OR `mean(positive_class) - 2*std(positive_class)`, whichever is higher
4. Validate: False positive rate < 5%, False negative rate < 10%
```

**Why This Matters**: Without clear criteria, implementer may waste time tweaking wrong thing (threshold when label is the issue, or vice versa).

**User Decision**: Approve this framework addition to spec?

#### 5. Disambiguation Implementation Strategy

**Issue**: Spec Phase 2 says "tune labels or add pre-filters" but doesn't specify which approach for which problem.

**Analysis of Test Failures**:

Looking at `test_catalyst_type_disambiguation.py`:

**Divestiture vs Acquisition** (5 tests):
- Root cause: Current label "announces an acquisition or merger with a specific purchase price" matches sell headlines because they mention price.
- **Best fix**: Add regex pre-filter for "sell|divest|dispose|spin.?off" → exclude "acquisition" type
- **Alternative**: Refine label to "announces acquiring/buying/purchasing another company" (more precise action verb)
- **Why pre-filter**: Linguistic distinction (sell vs buy) is structural, not semantic. MNLI may struggle even with perfect labels.

**Financing vs Dividend/Buyback** (5 tests):
- Root cause: "securities purchase agreement" has word "purchase" → MNLI maps to "dividend payment"
- **Best fix**: Add regex pre-filter for "offering|securities|convertible|placement" → exclude "dividend" and "buyback"
- **Alternative**: Refine dividend label to emphasize "returning capital to existing shareholders"
- **Why pre-filter**: Financial jargon ("convertible note", "private placement") is domain-specific. Pre-filter is more reliable.

**Revenue vs Earnings** (4 tests):
- Root cause: Revenue and earnings both involve dollar amounts and financial results
- **Best fix**: Refine earnings label to "net income, profit, or earnings per share" vs revenue label "top-line sales or revenue"
- **Alternative**: No pre-filter needed - this is semantic distinction DeBERTa should handle
- **Why label tuning**: Revenue vs earnings is semantic (top-line vs bottom-line). DeBERTa's superior understanding should distinguish this.

**Recommended Implementation Order**:

1. **Start with label tuning only** (no pre-filters)
2. **Run disambiguation tests**
3. **If divestiture/financing tests still fail**: Add pre-filters
4. **If revenue tests fail**: Iterate on label wording

**Rationale**: Try simplest solution first (label tuning). Only add regex complexity if semantic understanding insufficient.

**User Decision**: Approve this implementation strategy?

#### 6. Phase 3 Removal Confirmation

**Issue**: Simplification review recommended removing Phase 3 (endpoint consolidation).

**Design Perspective**: Endpoint consolidation is architectural change, not model upgrade.

**Arguments FOR removal**:
- Out of scope for this spec (objective: fix disambiguation, not redesign API)
- No evidence that DeBERTa enables or requires endpoint changes
- Backward compatibility risk
- Delays delivery of core objective

**Arguments AGAINST removal**:
- DeBERTa may reduce need for separate quantitative/strategic endpoints
- Could improve performance (fewer MNLI calls)
- Opportunity to simplify codebase

**Recommendation**: Remove from this spec. If endpoint consolidation is desired:
1. Deploy DeBERTa upgrade first
2. Monitor production for 1 week
3. Analyze whether unified detection would improve accuracy/performance
4. Create separate spec for endpoint consolidation with evidence

**User Decision**: Confirm removal of Phase 3?

## Design Validation Checklist

### Architecture Soundness
- [x] Single point of change (settings.py MODEL_NAME)
- [x] Shared pipeline pattern (memory efficient)
- [ ] **CRITICAL**: Routine detector needs pipeline sharing
- [x] Drop-in replacement (same transformers API)
- [x] No database schema changes
- [x] No API contract changes

### Testing Coverage
- [x] 341 existing tests cover regression
- [x] 31 new tests cover disambiguation
- [x] Integration tests cover end-to-end
- [ ] Performance tests should document resource requirements (startup, memory, inference)

### Risk Mitigation
- [x] Evidence-based (3 production misclassifications documented)
- [x] Backward compatible (no breaking changes)
- [ ] **MISSING**: Rollback plan if upgrade fails in production
- [ ] **MISSING**: Resource monitoring in production (memory, CPU)

### Documentation
- [x] Model comparison documented
- [ ] **MISSING**: Deployment memory requirements in CLAUDE.md
- [ ] **MISSING**: Performance benchmarks in CLAUDE.md
- [x] Threshold strategy (to be added per recommendation #4)

## Critical Design Gaps

### 1. Rollback Strategy

**Gap**: Spec doesn't document how to rollback if DeBERTa causes production issues.

**Recommendation**: Add to spec:

```markdown
## Rollback Plan

If DeBERTa causes production issues (OOM, timeout, accuracy regression):

1. **Immediate**: Revert MODEL_NAME in settings.py to "typeform/distilbert-base-uncased-mnli"
2. **Redeploy**: Use same deployment process (model downloaded on startup)
3. **Validate**: Run smoke tests on 10 sample headlines
4. **Monitor**: Verify memory < 500MB, startup < 60s

**Rollback time**: < 10 minutes (settings change + redeploy)

**Note**: 31 disambiguation tests will fail after rollback (expected - DistilBERT can't pass them).
```

### 2. Production Resource Monitoring

**Gap**: No plan to monitor resource usage after deployment.

**Recommendation**: Add to Phase 5 (Clean the House):

```markdown
## Production Monitoring

After deployment, monitor for 48 hours:

- **Memory**: Should stabilize at ~1.5GB (not >2GB)
- **Startup time**: Should be 45-90s (not >120s)
- **Inference P50**: Should be <500ms (not >1000ms)
- **Inference P99**: Should be <1000ms (not >2000ms)

**Alert thresholds**:
- Memory > 2GB → Investigate memory leak
- Startup > 120s → Check model download issues
- P99 > 2000ms → API timeout risk

**Metrics source**: Fly.io metrics dashboard or application logs
```

### 3. Test Data Preservation

**Gap**: No mention of preserving test data for comparison.

**Recommendation**: Before Phase 1, collect baseline:

```bash
# Run tests and save results
PYTHONPATH=src pytest tests/ -v --tb=short > baseline_distilbert_results.txt

# Collect scores for key headlines
python scripts/collect_baseline_scores.py > baseline_scores.json
```

**Benefit**: Can compare DeBERTa vs DistilBERT score distributions objectively.

## Summary of Design Recommendations

### Auto-Apply (Low Risk)
1. Add pipeline sharing to RoutineOperationDetectorMNLS
2. Remove hardcoded model names from detector defaults
3. Update .env.example with memory requirements
4. Add Model Comparison table to spec

### User Approval Required (Medium Risk)
5. Add threshold vs label decision framework to Phase 1
6. Add disambiguation implementation strategy (pre-filter vs label tuning)
7. Confirm removal of Phase 3 (endpoint consolidation)

### Documentation Additions (Low Risk)
8. Add rollback plan to spec
9. Add production monitoring section to Phase 5
10. Add baseline collection step before Phase 1

## Design Score: 8/10

**Strengths**:
- Simple, low-risk change
- Evidence-based problem definition
- Comprehensive test coverage
- Drop-in replacement architecture

**Weaknesses**:
- Routine detector pipeline isolation (wastes memory)
- Missing threshold tuning framework
- Missing rollback and monitoring plan
- Speculative Phase 3 adds scope creep

**After applying recommendations**: 10/10 - Production-ready design.

# Routine Score Investigation: Mystery Solved

## Summary

The 66 articles showing different `routine_operation` values between runs are NOT due to non-determinism, batching, or hidden state in the BART-MNLI pipeline. The difference is caused by **a critical bug fix on Nov 18, 2025** that corrected inverted routine_score extraction.

## Root Cause

**Commit**: `45bd90e` - "Fix critical bug in routine detector score extraction"
**Date**: Nov 18, 2025
**File**: `src/benz_sent_filter/services/routine_detector_mnls.py`

### The Bug

Lines 241-245 in the original code:

```python
if mnls_result["labels"][0] == self.ROUTINE_LABELS[0]:  # BUG: Checking wrong index!
    # Top prediction is "routine" - use its score
    routine_score = mnls_result["scores"][0]
else:
    # Top prediction is "material" - routine score is inverse
    routine_score = mnls_result["scores"][1]
```

**Problem**: `ROUTINE_LABELS[0]` = "transformational change" (material), but the comment says "routine"

### The Fix

Lines 241-246 in fixed code:

```python
# ROUTINE_LABELS[0] = "transformational change" (material)
# ROUTINE_LABELS[1] = "incremental progress or routine business updates" (routine)
if mnls_result["labels"][0] == self.ROUTINE_LABELS[1]:  # FIXED: Check correct index
    # Top prediction is "routine" - use its score
    routine_score = mnls_result["scores"][0]
else:
    # Top prediction is "transformational" - use routine score (second score)
    routine_score = mnls_result["scores"][1]
```

## Impact on Results

### Before Fix (Buggy Behavior)
- Routine filter activated: **32.7%** (18/55 articles)
- Overall filter activation: **52.7%**
- Scores were **INVERTED** for headlines where MNLI predicted "routine" as top label

### After Fix (Correct Behavior)
- Routine filter activated: **67.3%** (37/55 articles)
- Overall filter activation: **78.2%**
- Scores are **CORRECT**

### Example Score Changes

Critical test cases from commit message:
- GNS legal update: **0.26 → 0.75** ✅
- DKNG license: **0.40 → 0.61** ✅
- DIS ESPN app: **0.44 → 0.56** ✅

## Why the 66 Articles Changed

The 66 articles that "should be routine=True but got routine=False" are headlines where:

1. **With buggy code**:
   - MNLI correctly predicted "routine" as top label
   - But code extracted the WRONG score (transformational score)
   - This gave them LOW routine_score (< 0.5)
   - Result: `routine_operation=False` (incorrectly marked as material)

2. **With fixed code**:
   - MNLI still predicts "routine" as top label
   - Code now extracts the CORRECT score (routine score)
   - This gives them HIGH routine_score (> 0.5)
   - Result: `routine_operation=True` (correctly marked as routine)

## Investigation Findings: No Non-Determinism

### 1. BART-MNLI Pipeline is Deterministic ✅

Tested by calling the same pipeline 5 times:
```
Call 1: routine_score = 0.836566
Call 2: routine_score = 0.836566
Call 3: routine_score = 0.836566
Call 4: routine_score = 0.836566
Call 5: routine_score = 0.836566

All scores identical? True
```

### 2. Different Pipeline Instances Give Same Scores ✅

Tested by creating 3 separate pipeline instances:
```
Instance 1: routine_score = 0.836566
Instance 2: routine_score = 0.836566
Instance 3: routine_score = 0.836566

All scores identical? True
```

### 3. Code Paths Are Identical ✅

Both endpoints call the exact same method:
- `/classify` → `ClassificationService.classify_headline()` → `_analyze_routine_operation()` → `RoutineOperationDetectorMNLS.detect()`
- `/routine-operations` → `ClassificationService.classify_headline_multi_ticker()` → `_analyze_routine_operation()` → `RoutineOperationDetectorMNLS.detect()`

### 4. No Hidden State in Pipeline ✅

- RoutineOperationDetectorMNLS creates its own pipeline instance on initialization
- Pipeline is stateless - no warmup effects, no caching, no dropout
- Running on CPU with PyTorch 2.0.1, transformers 4.32.1
- Default dtype: torch.float32 (consistent)

### 5. No Service Restart Issues ✅

- ClassificationService created ONCE during FastAPI startup
- Same instance used for all requests
- Even if service restarted, model is deterministic

## Timeline Hypothesis

Based on commit dates:

1. **Nov 17, 2025**: Original MNLS routine detector implemented (buggy version)
2. **Nov 18, 2025 AM**: Old evaluation run used buggy code
3. **Nov 18, 2025 PM**: Bug fix deployed (commit 45bd90e)
4. **Nov 20, 2025**: New evaluation run uses fixed code
5. **Result**: 66 articles show different routine_operation values

## Conclusion

The mystery is **NOT** about non-determinism. It's about **a critical bug fix** that corrected score extraction logic. The 66 articles getting different results are actually being classified **more correctly** now after the fix.

**Before**: Scores were inverted for headlines where MNLI predicted "routine"
**After**: Scores are correct

This is **expected behavior** after a bug fix, not a sign of non-determinism.

## Recommendations

1. **Re-run the historical evaluation** with the fixed code to get accurate baseline metrics
2. **Update ground truth labels** based on the corrected routine_operation classifications
3. **Document this bug fix** in release notes as a breaking change to routine_operation results
4. **Consider versioning** the routine operation detector to track behavior changes

## Technical Details

### BART-MNLI Model Configuration
- Model: `facebook/bart-large-mnli`
- Task: Zero-shot classification
- Candidate labels:
  - `ROUTINE_LABELS[0]`: "This is a transformational change to the business" (material)
  - `ROUTINE_LABELS[1]`: "This is incremental progress or routine business updates" (routine)

### Score Extraction Logic
```python
mnls_result = self._pipeline(headline, self.ROUTINE_LABELS)
# mnls_result['labels'][0] = top prediction label
# mnls_result['scores'][0] = confidence score for top prediction
# mnls_result['scores'][1] = confidence score for second prediction

if mnls_result["labels"][0] == self.ROUTINE_LABELS[1]:  # "routine"
    routine_score = mnls_result["scores"][0]  # Use top score
else:  # Top prediction is "transformational"
    routine_score = mnls_result["scores"][1]  # Use routine score (second)
```

### Decision Logic
```python
result = False
if routine_score > 0.5:
    if materiality_score == 0:
        result = True  # No materiality assessment - use MNLS only
    elif materiality_score <= -1:
        result = True  # Immaterial - definitely routine
```

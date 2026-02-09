# Specification Simplification Review

**Created**: 2026-02-08
**Reviewer**: Review Executor Agent
**Status**: Completed

## Executive Summary

The specification is well-structured and comprehensive. Identified areas for simplification:

1. **Consolidate redundant model information** (mentioned 3 times)
2. **Merge overlapping phase descriptions** (Phase 1 & Phase 2 could be sequential steps)
3. **Remove speculative endpoint consolidation** (Phase 3) - defer until evidence shows it's needed
4. **Simplify validation phase** (Phase 4) - link to external doc rather than duplicate instructions

## Detailed Recommendations

### SAFE TO AUTO-APPLY

#### 1. Consolidate Model Information

**Issue**: Model specs repeated in "Current State" (lines 64-69), "What's Changing" (lines 83-96), and implicitly in Phase descriptions.

**Recommendation**: Create single "Model Comparison" table, reference it throughout.

```markdown
## Model Comparison

| Aspect | DistilBERT-MNLI (Current) | DeBERTa-v3-large (Target) |
|--------|---------------------------|---------------------------|
| Parameters | 66M | 400M (6x larger) |
| Architecture | DistilBERT (2019) | DeBERTa-v3 (2023) |
| Training | MNLI only | 33 NLI datasets |
| Memory | ~250MB | ~1.5GB |
| Startup | 15-30s | 45-90s (est) |
| Inference | 200-300ms | 400-600ms (est) |
| API | `pipeline("zero-shot-classification")` | Same (drop-in) |

**Performance Evidence**:
- Mean F1: 0.497 → 0.676 (+36%)
- FinancialPhraseBank F1: 0.465 → 0.691 (+49%)
```

**Impact**: Reduces duplication, easier to reference.

#### 2. Simplify "Gaps to Address" Section

**Issue**: Lines 98-104 list gaps that are actually addressed in phases. Redundant.

**Recommendation**: Remove this section. Gaps are clear from phase objectives.

**Rationale**: Each gap is already a phase objective:
- Gap 1 (thresholds) → Phase 1 objective
- Gap 2 (labels) → Phase 2 objective
- Gap 3 (routine detector) → Phase 5 (cleanup)
- Gap 4 (endpoints) → Phase 3 (review)

#### 3. Consolidate Phase 1 and Phase 2

**Issue**: Phases 1 & 2 are sequential parts of the same workflow:
- Phase 1: "Make old tests pass"
- Phase 2: "Make new tests pass"

Both involve threshold/label tuning on the same codebase.

**Recommendation**: Merge into single "Model Upgrade and Validation" phase:

```markdown
## Phase 1: Model Upgrade and Validation

**Objective**: Replace DistilBERT with DeBERTa and pass all tests (341 existing + 31 new).

**Steps**:
1. Update model name in settings.py, detector constructors, .env.example
2. Run existing test suite (341 tests) → fix threshold issues if needed
3. Run disambiguation test suite (31 tests) → tune labels for divestiture/financing/revenue
4. Iterate: adjust thresholds/labels until all 372 tests pass
5. Verify startup time and memory usage acceptable

**Acceptance Criteria**:
- All 372 tests pass (341 existing + 31 new)
- Service starts successfully (< 120s, < 2GB memory)
- No API contract changes
- Production cases (NTRB, INDP, ONAR) classify correctly
```

**Impact**: Simpler workflow, clearer that this is iterative tuning, not two separate phases.

#### 4. Simplify Validation Phase (Phase 4)

**Issue**: Lines 196-216 duplicate instructions that belong in validation.md.

**Recommendation**: Reduce to summary with link:

```markdown
## Phase 2: Integration and Performance Validation

**Objective**: Verify end-to-end functionality and production readiness.

**What to validate**:
- Integration tests with real model
- Live API testing (all 7 endpoints on port 8003)
- Performance benchmarks (startup, inference, memory)
- Backward compatibility

**Execution**: Follow step-by-step instructions in [validation.md](validation.md)

**Acceptance Criteria**: All validation steps marked `[VALIDATED: <sha>]`
```

**Impact**: Spec stays high-level, validation.md has detailed steps.

### REQUIRES USER APPROVAL

#### 5. Remove or Defer Phase 3 (Endpoint Consolidation)

**Issue**: Phase 3 (lines 177-193) proposes evaluating endpoint consolidation, but provides no evidence this is needed.

**Concerns**:
1. **Scope creep**: Spec is about model upgrade, not API redesign
2. **Speculative**: "If model X does Y, then maybe consolidate" - no data suggesting this
3. **Risk**: Endpoint changes introduce backward compatibility complexity
4. **Timeline**: Adds uncertainty to delivery

**Recommendation Option A (Aggressive)**: Remove Phase 3 entirely.

**Rationale**:
- Focus on single objective: fix catalyst type disambiguation
- Defer endpoint optimization until there's evidence it's needed
- Reduce scope, reduce risk

**Recommendation Option B (Conservative)**: Defer to post-deployment analysis.

```markdown
## Post-Deployment Analysis (Optional)

After the upgrade is deployed and stable, optionally evaluate:
1. Whether DeBERTa's improved discrimination allows endpoint consolidation
2. Performance benefits of unified detection
3. API evolution strategy

**Decision point**: Only pursue if monitoring shows clear benefit and no regression risk.
```

**Impact**: Removes speculative work, focuses on core objective.

## Summary of Changes

### Auto-Apply Changes

1. **Add Model Comparison table** (replaces 3 scattered descriptions)
2. **Remove "Gaps to Address" section** (redundant with phase objectives)
3. **Merge Phase 1 + Phase 2** into "Phase 1: Model Upgrade and Validation"
4. **Simplify Phase 4** (link to validation.md, remove duplicate instructions)
5. **Renumber remaining phases** (Phase 5 becomes Phase 3)

### User Decision Required

6. **Phase 3 Endpoint Consolidation**: Remove entirely OR defer to post-deployment?

## Resulting Structure (After Simplification)

```markdown
# Specification: MNLI Model Upgrade to DeBERTa-v3-large

## Overview & Objectives
- Problem Statement (with evidence)
- Objectives (5 clear goals)
- Success Criteria (5 clear criteria)

## Model Comparison
- Single table comparing DistilBERT vs DeBERTa

## Current State Analysis
- Architecture diagram (simplified)
- 7 API endpoints (table)
- Files to modify (clear list)

## Phase 1: Model Upgrade and Validation
- Merged threshold calibration + disambiguation
- Clear iterative workflow
- 372 total tests

## Phase 2: Integration and Performance Validation
- Link to validation.md
- Summary only

## Phase 3: Clean the House
- Documentation updates
- Final verification

## Error Handling & Edge Cases
- (unchanged)
```

**Line count reduction**: ~250 lines → ~180 lines (28% shorter)

**Clarity improvement**:
- 1 model comparison (not 3)
- 3 phases (not 5)
- 1 validation doc (not 2)

## Recommendation

**Auto-apply all safe changes** (items 1-5).

**For Phase 3 Endpoint Consolidation**: Recommend complete removal. Rationale:
- Not needed to achieve stated objectives
- Introduces scope creep and risk
- Can be addressed in future spec if evidence emerges
- DRY principle: don't design for speculative future needs

The spec's objective is "fix catalyst type disambiguation by upgrading model" - endpoint consolidation is a separate objective that should be its own spec if pursued.

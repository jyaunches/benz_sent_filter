# Validation: MNLI Model Upgrade to DeBERTa-v3-large

**Spec**: `specs/2026-02-08_mnli-model-upgrade-deberta/spec.md`
**Created**: 2026-02-08
**Tools**: pytest, httpx, curl, jq, make
**Model**: Real inference (MoritzLaurer/deberta-v3-large-zeroshot-v2.0)
**Validation Port**: 8006 (verified free; 8002-8005 in use)

---

## Validation Step 1: Full Regression Test Suite [STATUS: pending]

**What to verify**: All 341 existing tests pass with the new DeBERTa model — no regressions in opinion/news detection, temporal classification, company relevance, routine operations, quantitative catalysts, or strategic catalysts.

**Tool**: pytest (via make)

**Action**:
```bash
PYTHONPATH=src uv run pytest tests/ -v --tb=short 2>&1 | tail -80
```

**Expected**:
- All existing tests pass (341+)
- No failures related to threshold changes, label mismatches, or score distribution shifts
- If failures occur: categorize as threshold vs label vs model behavior issue and fix before proceeding

**Failure loop**:
1. Identify failing test(s) and root cause (threshold, label, or model behavior)
2. Adjust thresholds or labels in source code
3. Re-run `make test` until green
4. Do NOT proceed to Step 2 until this passes

---

## Validation Step 2: Disambiguation Test Suite [STATUS: pending]

**What to verify**: All 31 new disambiguation tests pass — DeBERTa correctly distinguishes divestiture from acquisition, securities offerings from dividends, and revenue announcements from earnings.

**Tool**: pytest

**Action**:
```bash
PYTHONPATH=src uv run pytest tests/test_catalyst_type_disambiguation.py -v --tb=long
```

**Expected**:
- All 31 tests pass across 5 test classes:
  - `TestDivestitureDisambiguation` (5 tests): sell/divest headlines NOT classified as acquisition
  - `TestFinancingDisambiguation` (5 tests): securities offerings NOT classified as dividend/buyback
  - `TestRevenueDisambiguation` (4 tests): revenue announcements NOT classified as earnings
  - `TestDisambiguationPreservesCorrectClassifications` (8 tests): real acquisitions/dividends/buybacks/earnings still correctly classified
  - `TestDisambiguationEdgeCases` (9 tests): tricky headlines don't over-correct

**Failure loop**:
1. For each failing test, inspect the MNLI scores returned
2. If threshold issue: adjust PRESENCE_THRESHOLD or TYPE_THRESHOLD using statistical approach (score distribution mean +/- 2*std)
3. If label issue: refine CATALYST_TYPE_LABELS hypothesis text to be more precise (e.g., "purchasing/acquiring" instead of "acquisition with purchase price")
4. Prefer label tuning over regex pre-filters — DeBERTa's stronger NLI should handle disambiguation via better-worded hypotheses
5. After each fix, re-run BOTH this test file AND `make test` to confirm no regressions
6. Do NOT proceed until all 31 pass AND all 341 existing tests still pass

---

## Validation Step 3: Integration Tests with Real Model [STATUS: pending]

**What to verify**: Real model inference produces correct results on realistic financial headlines (not mocked).

**Tool**: pytest

**Action**:
```bash
PYTHONPATH=src uv run pytest integration/ -v --tb=long
```

**Expected**:
- All 27 integration tests pass with real DeBERTa model loaded
- Model loads successfully (may take 45-90s on first run for download)
- Inference times acceptable (<1s per headline on CPU)

**Failure loop**:
1. If model download fails: check network, disk space (~1.5GB needed)
2. If inference timeouts: note timing but do not block — document in Phase 4
3. If accuracy failures: trace back to threshold/label issues and fix, re-run

---

## Validation Step 4: Live API Endpoint Testing [STATUS: pending]

**What to verify**: All 7 API endpoints return correct responses with the new model when the server is running.

**Tool**: curl, jq, background server process

**Setup** (start validation server on port 8006):
```bash
PORT=8006 PYTHONPATH=src uv run uvicorn benz_sent_filter.api.app:app --host 0.0.0.0 --port 8006 &
VALIDATION_PID=$!
sleep 60  # Allow model download/loading time
```

**Action 4a — Health check**:
```bash
curl -s http://localhost:8006/health | jq .
```
Expected: `{"status": "healthy"}` (or equivalent)

**Action 4b — Classify endpoint (opinion vs news)**:
```bash
curl -s -X POST http://localhost:8006/classify \
  -H "Content-Type: application/json" \
  -d '{"headline": "Why the Fed Is Wrong About Interest Rates"}' | jq .
```
Expected: `is_opinion: true`, `is_straight_news: false`, valid `temporal_category`

**Action 4c — Classify with company relevance**:
```bash
curl -s -X POST http://localhost:8006/classify \
  -H "Content-Type: application/json" \
  -d '{"headline": "Tesla Shares Surge After Record Q4 Earnings", "company": "Tesla"}' | jq .
```
Expected: `is_about_company: true`, `company_score > 0.5`

**Action 4d — Quantitative catalyst detection (the core fix)**:
```bash
curl -s -X POST http://localhost:8006/detect-quantitative-catalyst \
  -H "Content-Type: application/json" \
  -d '{"headline": "Company to sell majority stake for $5M"}' | jq .
```
Expected: Should NOT classify as `acquisition` — this is the NTRB misclassification case

**Action 4e — Quantitative catalyst (real dividend)**:
```bash
curl -s -X POST http://localhost:8006/detect-quantitative-catalyst \
  -H "Content-Type: application/json" \
  -d '{"headline": "Company declares $0.50 quarterly dividend"}' | jq .
```
Expected: `has_quantitative_catalyst: true`, `catalyst_type: "dividend"`

**Action 4f — Strategic catalyst detection**:
```bash
curl -s -X POST http://localhost:8006/detect-strategic-catalyst \
  -H "Content-Type: application/json" \
  -d '{"headline": "X4 Pharmaceuticals CEO and CFO Step Down"}' | jq .
```
Expected: `has_strategic_catalyst: true`, `catalyst_subtype: "executive_changes"`

**Action 4g — Routine operations**:
```bash
curl -s -X POST http://localhost:8006/routine-operations \
  -H "Content-Type: application/json" \
  -d '{"headlines": [{"headline": "FNMA monthly volume summary for December", "company_symbol": "FNMA"}]}' | jq .
```
Expected: `routine_operation: true`

**Action 4h — Batch classify**:
```bash
curl -s -X POST http://localhost:8006/classify/batch \
  -H "Content-Type: application/json" \
  -d '{"headlines": [{"headline": "Fed Raises Interest Rates by 0.25%"}, {"headline": "Why Investors Should Sell Everything Now"}]}' | jq .
```
Expected: Two results, first is news/past, second is opinion

**Teardown**:
```bash
kill $VALIDATION_PID 2>/dev/null
```

**Failure loop**:
1. If server fails to start: check model download, memory (~1.5GB), port availability
2. If endpoint returns wrong classification: trace to threshold/label issue, fix, restart server, re-test
3. If timeout: note inference latency, document but do not block unless >5s per headline

---

## Validation Step 5: Backward Compatibility Check [STATUS: pending]

**What to verify**: API response schemas are unchanged — no fields added, removed, or renamed.

**Tool**: pytest (existing test_api.py covers this), curl diff

**Action**:
```bash
# The API test suite validates all response schemas
PYTHONPATH=src uv run pytest tests/test_api.py -v --tb=short
```

**Expected**:
- All ~89 API tests pass
- Response fields match documented contract in CLAUDE.md
- No `exclude_none` behavior changes (optional fields still omitted when None)

---

## Validation Step 6: Resource and Startup Verification [STATUS: pending]

**What to verify**: Service starts within acceptable time and memory usage is documented.

**Tool**: bash, time

**Action**:
```bash
# Time the server startup (on port 8006 to avoid conflict)
time (PORT=8006 PYTHONPATH=src timeout 120 uv run python -c "
from benz_sent_filter.services.classifier import ClassificationService
import time
start = time.time()
svc = ClassificationService()
elapsed = time.time() - start
print(f'Model loaded in {elapsed:.1f}s')
print(f'Model: {svc._pipeline.model.name_or_path}')
")
```

**Expected**:
- Model loads within 120s (first run may be slower due to download)
- Model name confirms `deberta-v3-large-zeroshot-v2.0`
- Document actual startup time and memory for deployment planning

---

## Execution Instructions

When executing this validation phase, Claude MUST:
1. Execute each validation step **in order** (Steps 1-6)
2. If a validation step fails:
   - Identify the root cause
   - Fix the issue in the implementation
   - Re-run the failing validation step
   - Re-run any earlier steps that may be affected by the fix
   - Continue this loop until the step passes
3. Only mark a step `[VALIDATED: <git-sha>]` when it passes
4. Only mark this phase complete when ALL 6 validation steps pass
5. The validation server MUST run on port **8006** (not 8002) to avoid disrupting the production server
6. Report any issues that could not be resolved

## Acceptance Criteria

- [ ] All 341+ existing tests pass (Step 1)
- [ ] All 31 disambiguation tests pass (Step 2)
- [ ] Integration tests pass with real model (Step 3)
- [ ] All 7 API endpoints return correct results via live server on port 8006 (Step 4)
- [ ] API response schemas unchanged (Step 5)
- [ ] Startup time and memory documented (Step 6)
- [ ] Any issues found were fixed and re-validated

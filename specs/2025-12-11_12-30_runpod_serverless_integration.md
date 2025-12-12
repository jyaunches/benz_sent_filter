# Specification: RunPod Serverless GPU Integration

**Created**: 2025-12-11
**Status**: Draft

## Overview & Objectives

### Problem Statement

The benz_sent_filter service currently runs MNLI inference on CPU with the following performance:
- Single headline: ~2 seconds
- Batch of 10: ~10 seconds
- Maximum throughput: ~30 headlines/minute

**Traffic Requirements** (Benzinga article bursts):
- Peak: 339 articles in a single minute
- Typical large bursts: 50-100 articles at :10 and :40 past the hour
- Peak hours: 6:00 AM - 11:00 AM EST

**Current Gap**: CPU inference cannot handle peak bursts within acceptable latency.

**Solution**: Integrate with RunPod Serverless to run GPU inference with automatic scaling and pay-per-second billing.

### Objectives

1. **Primary**: Add RunPod serverless handler to benz_sent_filter for GPU inference
2. **Preserve Existing**: Keep FastAPI deployment working for Fly.io (dual deployment)
3. **Minimal Changes**: Wrap existing `ClassificationService` - no rewrite
4. **Cost Efficient**: Pay only for actual inference time (~$30-60/month vs $95 for VM)
5. **Auto-scaling**: Let RunPod handle scaling during burst traffic

### Success Metrics

- GPU inference: < 100ms per headline (20x improvement)
- Batch of 100: < 1 second
- Handle 339 article burst in < 10 seconds
- Zero code changes to core `ClassificationService`
- Docker image builds and deploys to RunPod successfully

## Current State Analysis

### What Exists

**Core Classification Service** (`services/classifier.py`):
- `ClassificationService` class loads DistilBERT-MNLI model
- Methods: `classify_headline()`, `classify_batch()`, `detect_quantitative_catalyst()`, `detect_strategic_catalyst()`, etc.
- Uses `transformers` pipeline with shared model instance

**FastAPI Application** (`api/app.py`):
- Wraps `ClassificationService` with REST endpoints
- Endpoints: `/classify`, `/classify/batch`, `/routine-operations`, `/detect-quantitative-catalyst`, `/detect-strategic-catalyst`, etc.
- Deployed to Fly.io on CPU

**Existing Dockerfile** (CPU-optimized):
- Python 3.11-slim base
- CPU-only PyTorch
- Downloads model on startup

### What's Needed

1. **RunPod Handler**: Thin wrapper that calls `ClassificationService`
2. **GPU Dockerfile**: CUDA-enabled base image with model pre-embedded
3. **Local Testing**: Ability to test handler locally before deployment
4. **Documentation**: Setup and deployment instructions

### Why RunPod Serverless

| Feature | RunPod Serverless | Lambda Labs VM |
|---------|-------------------|----------------|
| **Scaling** | Automatic | Manual (build yourself) |
| **Billing** | Per-second | Per-hour |
| **Cold starts** | 500ms-2s (FlashBoot) | None (VM always on) |
| **Cost estimate** | $30-60/month | $95/month |
| **Infrastructure** | Managed | You manage |

## Architecture Design

### Dual Deployment Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         benz_sent_filter                                 │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│   src/benz_sent_filter/                                                  │
│   ├── services/classifier.py      ◄── Core logic (unchanged)            │
│   ├── api/app.py                  ◄── FastAPI (Fly.io)                  │
│   └── runpod_handler.py           ◄── NEW: RunPod handler               │
│                                                                          │
│   Dockerfile                      ◄── Fly.io (CPU)                      │
│   Dockerfile.runpod               ◄── NEW: RunPod (GPU)                 │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
                    │                               │
                    ▼                               ▼
         ┌──────────────────┐            ┌──────────────────┐
         │     Fly.io       │            │  RunPod Server-  │
         │   (CPU, 24/7)    │            │  less (GPU, on-  │
         │                  │            │  demand scaling) │
         └──────────────────┘            └──────────────────┘
```

### RunPod Handler Design

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         RunPod Worker Flow                               │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│   Worker Startup (once):                                                 │
│   ┌─────────────────────────────────────────────┐                       │
│   │  1. Import ClassificationService            │                       │
│   │  2. Load model (GPU via torch.cuda)         │                       │
│   │  3. Keep in memory for all jobs             │                       │
│   └─────────────────────────────────────────────┘                       │
│                                                                          │
│   Per Request:                                                           │
│   ┌─────────────────────────────────────────────┐                       │
│   │  1. Receive job {"input": {...}}            │                       │
│   │  2. Route to appropriate method             │                       │
│   │  3. Return result                           │                       │
│   └─────────────────────────────────────────────┘                       │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

### Request/Response Format

**RunPod Request Format**:
```json
{
  "input": {
    "operation": "classify",
    "headline": "Apple announces new iPhone",
    "company": "Apple"
  }
}
```

**Supported Operations**:
- `classify` - Single headline classification
- `classify_batch` - Multiple headlines
- `routine_operations` - Multi-ticker routine analysis
- `company_relevance` - Company relevance check
- `detect_quantitative_catalyst` - Quantitative catalyst detection
- `detect_strategic_catalyst` - Strategic catalyst detection

**RunPod Response Format**:
```json
{
  "output": {
    "is_opinion": false,
    "is_straight_news": true,
    "temporal_category": "past_event",
    "scores": {...}
  }
}
```

### GPU Detection

The `ClassificationService` will automatically use GPU when available:

```
Transformers pipeline behavior:
- If CUDA available → uses GPU (device=0)
- If no CUDA → uses CPU

No code changes needed - transformers handles this automatically.
```

## Configuration Design

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `RUNPOD_DEBUG` | Enable debug logging | `false` |
| `TRANSFORMERS_CACHE` | Model cache directory | `/app/.cache` |

### RunPod Endpoint Settings (configured in RunPod console)

```yaml
# Recommended settings for benz_sent_filter
endpoint_name: benz-sent-filter
gpu_type: "NVIDIA RTX A4000"  # 16GB VRAM, sufficient for DistilBERT
active_workers: 1              # Keep 1 warm during peak hours
max_workers: 3                 # Handle burst traffic
idle_timeout: 60               # Keep workers warm between bursts
queue_delay: 2                 # Spin up workers if queue > 2s
flashboot: enabled             # Reduce cold starts to ~500ms
```

### Estimated Costs

| Configuration | Monthly Cost | Cold Starts |
|---------------|--------------|-------------|
| 0 active workers | ~$15-30 | Yes, at burst boundaries |
| 1 active worker (peak hours only) | ~$50-60 | Minimal |
| 1 active worker (24/7) | ~$200 | None |

## Implementation Phases

### Phase 1: RunPod Handler

**Description**: Create the RunPod serverless handler that wraps ClassificationService.

**Core Functionality**:
- Handler function that processes RunPod job format
- Operation routing (classify, classify_batch, etc.)
- Model loading at worker startup (outside handler)
- Error handling with proper RunPod error format

**Dependencies**: Existing `ClassificationService`

**Files to Create**:
- `src/benz_sent_filter/runpod_handler.py`

**Handler Structure**:

The handler must:
1. Load `ClassificationService` once at module level (worker startup)
2. Accept job dict with `input` key
3. Route based on `operation` field
4. Return results directly (RunPod handles JSON serialization)
5. Let exceptions propagate (RunPod marks job as FAILED)

**Supported Operations**:

| Operation | Input Fields | Maps To |
|-----------|--------------|---------|
| `classify` | `headline`, `company?` | `classify_headline()` |
| `classify_batch` | `headlines`, `company?` | `classify_batch()` |
| `routine_operations` | `headline`, `ticker_symbols` | `classify_headline_multi_ticker()` |
| `company_relevance` | `headline`, `company` | `check_company_relevance()` |
| `company_relevance_batch` | `headlines`, `company` | `check_company_relevance_batch()` |
| `detect_quantitative_catalyst` | `headline` | `detect_quantitative_catalyst()` |
| `detect_strategic_catalyst` | `headline` | `detect_strategic_catalyst()` |

**Unit Test Requirements**:

Tests to Write:

1. **test_handler_classify_single_headline**
   - Input: `{"input": {"operation": "classify", "headline": "Test headline"}}`
   - Expected: Dict with `is_opinion`, `is_straight_news`, `temporal_category`, `scores`

2. **test_handler_classify_with_company**
   - Input: `{"input": {"operation": "classify", "headline": "Apple news", "company": "Apple"}}`
   - Expected: Result includes `is_about_company`, `company_score`

3. **test_handler_classify_batch**
   - Input: `{"input": {"operation": "classify_batch", "headlines": ["H1", "H2"]}}`
   - Expected: List of classification results

4. **test_handler_routine_operations**
   - Input: `{"input": {"operation": "routine_operations", "headline": "...", "ticker_symbols": ["BAC"]}}`
   - Expected: Dict with `core_classification`, `routine_operations_by_ticker`

5. **test_handler_detect_quantitative_catalyst**
   - Input: `{"input": {"operation": "detect_quantitative_catalyst", "headline": "..."}}`
   - Expected: Dict with `has_quantitative_catalyst`, `catalyst_type`

6. **test_handler_detect_strategic_catalyst**
   - Input: `{"input": {"operation": "detect_strategic_catalyst", "headline": "..."}}`
   - Expected: Dict with `has_strategic_catalyst`, `catalyst_subtype`

7. **test_handler_invalid_operation**
   - Input: `{"input": {"operation": "invalid"}}`
   - Expected: Error dict with message

8. **test_handler_missing_required_field**
   - Input: `{"input": {"operation": "classify"}}` (no headline)
   - Expected: Error dict with message

**Acceptance Criteria**:
- Handler loads ClassificationService at module level
- All 7 operations route correctly to ClassificationService methods
- Results are JSON-serializable (Pydantic models converted to dicts)
- Invalid operations return clear error messages
- Missing required fields return clear error messages

---

### Phase 2: GPU Dockerfile

**Description**: Create Docker image optimized for RunPod GPU deployment.

**Core Functionality**:
- CUDA-enabled base image
- Pre-embedded model weights (fast cold starts)
- RunPod handler as entrypoint
- Minimal image size

**Dependencies**: Phase 1 (handler exists)

**Files to Create**:
- `Dockerfile.runpod`

**Dockerfile Requirements**:

1. **Base Image**: `runpod/pytorch:2.2.0-py3.10-cuda12.1.1-devel-ubuntu22.04`
   - Pre-configured CUDA and PyTorch
   - Compatible with RunPod infrastructure

2. **Dependencies**:
   - Install project dependencies via pip
   - Pin versions for reproducibility

3. **Model Pre-download**:
   - Download `typeform/distilbert-base-uncased-mnli` during build
   - Embeds model in image (~500MB addition)
   - Eliminates download time on cold start

4. **Entrypoint**: `python -u runpod_handler.py`
   - `-u` for unbuffered output (better logging)

**Unit Test Requirements**:

Tests to Write:

1. **test_dockerfile_builds_successfully**
   - Run: `docker build -f Dockerfile.runpod -t test .`
   - Expected: Build completes without errors

2. **test_dockerfile_has_cuda**
   - Run: Container with `python -c "import torch; print(torch.cuda.is_available())"`
   - Expected: Returns `True` (when run on GPU host)

3. **test_dockerfile_has_model_cached**
   - Run: Container, check `~/.cache/huggingface/` or `/app/.cache`
   - Expected: Model files present

4. **test_dockerfile_handler_starts**
   - Run: Container entrypoint
   - Expected: Handler starts without import errors

**Acceptance Criteria**:
- Image builds with `docker build --platform linux/amd64 -f Dockerfile.runpod`
- Image size < 10GB
- Model weights embedded in image
- Handler starts successfully in container
- CUDA available when run on GPU host

---

### Phase 3: Local Testing

**Description**: Enable local testing of RunPod handler without deploying.

**Core Functionality**:
- Local HTTP server mode via `--rp_serve_api` flag
- Test with curl or Python requests
- Debug mode for troubleshooting

**Dependencies**: Phase 1 (handler exists)

**Files to Create/Modify**:
- Update `runpod_handler.py` if needed for local testing
- Add `scripts/test_runpod_local.py` for integration testing

**Local Testing Commands**:

```bash
# Start local server (CPU mode for development)
python src/benz_sent_filter/runpod_handler.py --rp_serve_api --rp_api_port 8080

# Test classify endpoint
curl -X POST http://localhost:8080/runsync \
  -H "Content-Type: application/json" \
  -d '{"input": {"operation": "classify", "headline": "Apple announces new iPhone"}}'

# Test batch endpoint
curl -X POST http://localhost:8080/runsync \
  -H "Content-Type: application/json" \
  -d '{"input": {"operation": "classify_batch", "headlines": ["H1", "H2", "H3"]}}'
```

**Unit Test Requirements**:

Tests to Write:

1. **test_local_server_starts**
   - Run handler with `--rp_serve_api`
   - Expected: Server starts on specified port

2. **test_local_server_responds_to_runsync**
   - Send POST to `/runsync` with valid input
   - Expected: Returns classification result

3. **test_local_server_handles_errors**
   - Send invalid request
   - Expected: Returns error response, doesn't crash

**Acceptance Criteria**:
- `python runpod_handler.py --rp_serve_api` starts local server
- Can test all operations via curl
- Error responses are informative
- Server handles multiple sequential requests

---

### Phase 4: Deployment Documentation

**Description**: Document the complete deployment process for RunPod.

**Core Functionality**:
- Step-by-step deployment guide
- RunPod console configuration
- Monitoring and troubleshooting
- Cost optimization tips

**Dependencies**: Phases 1-3 complete

**Files to Create**:
- `docs/RUNPOD_DEPLOYMENT.md`

**Documentation Sections**:

1. **Prerequisites**
   - Docker Hub account
   - RunPod account with payment method
   - Local Docker installation

2. **Building and Pushing Image**
   ```bash
   docker build --platform linux/amd64 -f Dockerfile.runpod -t username/benz-sent-filter:v1.0.0 .
   docker push username/benz-sent-filter:v1.0.0
   ```

3. **Creating RunPod Endpoint**
   - Navigate to Serverless → New Endpoint
   - Select GPU type (RTX A4000 recommended)
   - Configure scaling (active workers, max workers, idle timeout)
   - Set environment variables

4. **Testing Deployment**
   ```bash
   curl -X POST "https://api.runpod.ai/v2/YOUR_ENDPOINT_ID/runsync" \
     -H "Authorization: Bearer $RUNPOD_API_KEY" \
     -H "Content-Type: application/json" \
     -d '{"input": {"operation": "classify", "headline": "Test"}}'
   ```

5. **Monitoring**
   - RunPod dashboard metrics
   - Worker logs
   - Cost tracking

6. **Troubleshooting**
   - Common errors and solutions
   - Cold start optimization
   - Memory issues

**Acceptance Criteria**:
- Documentation covers complete deployment flow
- Includes copy-paste commands
- Screenshots of RunPod console where helpful
- Troubleshooting section addresses common issues

---

### Phase 5: Client Integration Guide

**Description**: Document how benz_analyzer (or other clients) should call the RunPod endpoint.

**Core Functionality**:
- Python client example
- Async/sync request patterns
- Error handling
- Batch optimization

**Dependencies**: Phase 4 (deployment works)

**Files to Create**:
- Add section to `docs/RUNPOD_DEPLOYMENT.md` or create `docs/RUNPOD_CLIENT.md`

**Client Patterns**:

1. **Synchronous Request** (`/runsync`):
   - Waits for result
   - Best for single headlines
   - Timeout: 30s default

2. **Asynchronous Request** (`/run`):
   - Returns job ID immediately
   - Poll `/status/{job_id}` for result
   - Best for large batches

3. **Recommended Client Code**:
   ```python
   import requests

   RUNPOD_ENDPOINT = "https://api.runpod.ai/v2/YOUR_ENDPOINT_ID"
   RUNPOD_API_KEY = "your_api_key"

   def classify_headline(headline: str, company: str = None) -> dict:
       response = requests.post(
           f"{RUNPOD_ENDPOINT}/runsync",
           headers={"Authorization": f"Bearer {RUNPOD_API_KEY}"},
           json={"input": {"operation": "classify", "headline": headline, "company": company}},
           timeout=30
       )
       response.raise_for_status()
       return response.json()["output"]
   ```

**Acceptance Criteria**:
- Client example works with deployed endpoint
- Documents both sync and async patterns
- Includes error handling best practices
- Shows batch optimization for high throughput

---

### Phase 6: Clean the House

**Description**: Post-implementation cleanup and documentation maintenance.

**Tasks**:

1. **Remove Dead Code**:
   - Check for any unused imports in new files
   - Ensure no debugging code left in handler

2. **Update Related Documentation**:
   - Update `CLAUDE.md` with RunPod deployment info
   - Update `README.md` with GPU deployment option
   - Add RunPod to deployment section

3. **Update INTEGRATION.md**:
   - Use `agent: implementation-writer` to update INTEGRATION.md
   - Document RunPod endpoint as alternative to Fly.io

**Acceptance Criteria**:
- No commented-out code blocks remain
- CLAUDE.md includes RunPod deployment info
- README.md mentions GPU deployment option
- INTEGRATION.md documents RunPod API contract

## Appendix A: RunPod API Reference

### Request Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/runsync` | POST | Synchronous execution (waits for result) |
| `/run` | POST | Asynchronous execution (returns job ID) |
| `/status/{job_id}` | GET | Check job status |
| `/cancel/{job_id}` | POST | Cancel running job |
| `/health` | GET | Endpoint health metrics |

### Request Format

```json
{
  "input": {
    "operation": "string",
    // operation-specific fields
  }
}
```

### Response Format (Success)

```json
{
  "id": "job-id",
  "status": "COMPLETED",
  "output": { /* operation result */ },
  "delayTime": 123,
  "executionTime": 456
}
```

### Response Format (Error)

```json
{
  "id": "job-id",
  "status": "FAILED",
  "error": "Error message"
}
```

## Appendix B: GPU Performance Expectations

### DistilBERT MNLI on RTX A4000 (16GB)

| Operation | Expected Time |
|-----------|---------------|
| Single headline | 30-50ms |
| Batch of 10 | 50-100ms |
| Batch of 100 | 200-500ms |

### Cold Start Times

| Scenario | Time |
|----------|------|
| FlashBoot enabled | 500ms - 1s |
| FlashBoot disabled | 5-15s |
| Model not cached | 30-60s |

### Throughput Capacity

Single RTX A4000 worker:
- ~1,200-2,000 headlines/minute (batched)
- Far exceeds your peak of 339/minute

## Appendix C: Cost Estimates

### Scenario: Peak Hours Only (6-11 AM EST, weekdays)

| Configuration | Calculation | Monthly |
|---------------|-------------|---------|
| 0 active, inference only | ~5 min actual GPU/day × $0.00019/sec × 22 days | ~$12 |
| 1 active worker | 5.5 hrs × $0.19/hr × 0.7 discount × 22 days | ~$16 |
| Burst scaling (extra workers) | ~10 min/day × $0.19/hr × 22 days | ~$7 |
| **Total estimate** | | **$25-35** |

Note: Actual costs depend on traffic patterns. Monitor RunPod dashboard for accurate billing.

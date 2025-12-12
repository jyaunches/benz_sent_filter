# RunPod Serverless GPU Deployment Guide

This guide covers deploying benz_sent_filter to RunPod Serverless for GPU-accelerated MNLI inference.

## Prerequisites

1. **Docker Hub Account**: For pushing the container image
2. **RunPod Account**: With payment method configured
3. **Local Docker**: For building the image

## Quick Start

### 1. Build the Docker Image

```bash
cd /path/to/benz_sent_filter

# Build for linux/amd64 (required for RunPod)
docker build --platform linux/amd64 -f Dockerfile.runpod -t YOUR_DOCKERHUB_USERNAME/benz-sent-filter:v1.0.0 .
```

### 2. Push to Docker Hub

```bash
docker login
docker push YOUR_DOCKERHUB_USERNAME/benz-sent-filter:v1.0.0
```

### 3. Create RunPod Endpoint

1. Go to [RunPod Console](https://www.runpod.io/console/serverless)
2. Click **New Endpoint**
3. Select **Custom** (import from Docker Registry)
4. Enter your image: `docker.io/YOUR_USERNAME/benz-sent-filter:v1.0.0`
5. Configure settings (see below)
6. Click **Deploy**

### Recommended Endpoint Settings

| Setting | Value | Notes |
|---------|-------|-------|
| **GPU Type** | RTX A4000 (16GB) | Sufficient for DistilBERT |
| **Active Workers** | 1 | Keep 1 warm during peak hours |
| **Max Workers** | 3 | Handle burst traffic |
| **Idle Timeout** | 60 seconds | Keep workers warm between bursts |
| **FlashBoot** | Enabled | Faster cold starts |

### 4. Test Your Deployment

```bash
export RUNPOD_API_KEY="your_api_key"
export RUNPOD_ENDPOINT_ID="your_endpoint_id"

curl -X POST "https://api.runpod.ai/v2/$RUNPOD_ENDPOINT_ID/runsync" \
  -H "Authorization: Bearer $RUNPOD_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "input": {
      "operation": "classify",
      "headline": "Apple announces new iPhone"
    }
  }'
```

## Local Testing

Before deploying, test the handler locally:

```bash
# Start local RunPod server (CPU mode)
cd /path/to/benz_sent_filter
python src/benz_sent_filter/runpod_handler.py --rp_serve_api --rp_api_port 8080

# In another terminal, run tests
./scripts/test_runpod_local.sh
```

## API Reference

### Request Format

All requests use POST to `/runsync` (synchronous) or `/run` (asynchronous):

```json
{
  "input": {
    "operation": "<operation_name>",
    // ... operation-specific fields
  }
}
```

### Supported Operations

#### 1. `classify` - Single Headline Classification

```json
{
  "input": {
    "operation": "classify",
    "headline": "Apple announces new iPhone",
    "company": "Apple"  // optional
  }
}
```

**Response:**
```json
{
  "is_opinion": false,
  "is_straight_news": true,
  "temporal_category": "past_event",
  "scores": {
    "opinion_score": 0.12,
    "news_score": 0.88,
    "past_score": 0.75,
    "future_score": 0.15,
    "general_score": 0.10
  },
  "headline": "Apple announces new iPhone",
  "is_about_company": true,
  "company_score": 0.92,
  "company": "Apple"
}
```

#### 2. `classify_batch` - Multiple Headlines

```json
{
  "input": {
    "operation": "classify_batch",
    "headlines": ["Headline 1", "Headline 2"],
    "company": "Apple"  // optional
  }
}
```

#### 3. `routine_operations` - Multi-Ticker Analysis

```json
{
  "input": {
    "operation": "routine_operations",
    "headline": "Bank announces quarterly dividend",
    "ticker_symbols": ["BAC", "JPM", "C"]
  }
}
```

**Response:**
```json
{
  "core_classification": {
    "is_opinion": false,
    "is_straight_news": true,
    "temporal_category": "past_event",
    "scores": {...}
  },
  "routine_operations_by_ticker": {
    "BAC": {"routine_operation": true, "routine_confidence": 0.87, ...},
    "JPM": {"routine_operation": true, "routine_confidence": 0.65, ...},
    "C": {"routine_operation": true, "routine_confidence": 0.71, ...}
  }
}
```

#### 4. `company_relevance` - Check Company Relevance

```json
{
  "input": {
    "operation": "company_relevance",
    "headline": "Apple announces new iPhone",
    "company": "Apple"
  }
}
```

#### 5. `company_relevance_batch` - Batch Company Relevance

```json
{
  "input": {
    "operation": "company_relevance_batch",
    "headlines": ["Apple news", "Tesla news"],
    "company": "Apple"
  }
}
```

#### 6. `detect_quantitative_catalyst` - Detect Financial Catalysts

```json
{
  "input": {
    "operation": "detect_quantitative_catalyst",
    "headline": "Company announces $1 dividend"
  }
}
```

**Response:**
```json
{
  "headline": "Company announces $1 dividend",
  "has_quantitative_catalyst": true,
  "catalyst_type": "dividend",
  "catalyst_values": ["$1"],
  "confidence": 0.87
}
```

#### 7. `detect_strategic_catalyst` - Detect Strategic Events

```json
{
  "input": {
    "operation": "detect_strategic_catalyst",
    "headline": "CEO and CFO Step Down"
  }
}
```

**Response:**
```json
{
  "headline": "CEO and CFO Step Down",
  "has_strategic_catalyst": true,
  "catalyst_subtype": "executive_changes",
  "confidence": 0.94
}
```

## Client Integration (Python)

```python
import requests
from typing import Optional

class RunPodSentFilterClient:
    """Client for benz_sent_filter on RunPod Serverless."""

    def __init__(self, endpoint_id: str, api_key: str):
        self.base_url = f"https://api.runpod.ai/v2/{endpoint_id}"
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }

    def classify(self, headline: str, company: Optional[str] = None) -> dict:
        """Classify a single headline."""
        payload = {
            "input": {
                "operation": "classify",
                "headline": headline
            }
        }
        if company:
            payload["input"]["company"] = company

        response = requests.post(
            f"{self.base_url}/runsync",
            headers=self.headers,
            json=payload,
            timeout=30
        )
        response.raise_for_status()
        return response.json()["output"]

    def classify_batch(self, headlines: list[str], company: Optional[str] = None) -> list[dict]:
        """Classify multiple headlines."""
        payload = {
            "input": {
                "operation": "classify_batch",
                "headlines": headlines
            }
        }
        if company:
            payload["input"]["company"] = company

        response = requests.post(
            f"{self.base_url}/runsync",
            headers=self.headers,
            json=payload,
            timeout=60
        )
        response.raise_for_status()
        return response.json()["output"]

    def detect_quantitative_catalyst(self, headline: str) -> dict:
        """Detect quantitative financial catalyst."""
        response = requests.post(
            f"{self.base_url}/runsync",
            headers=self.headers,
            json={
                "input": {
                    "operation": "detect_quantitative_catalyst",
                    "headline": headline
                }
            },
            timeout=30
        )
        response.raise_for_status()
        return response.json()["output"]

    def detect_strategic_catalyst(self, headline: str) -> dict:
        """Detect strategic corporate catalyst."""
        response = requests.post(
            f"{self.base_url}/runsync",
            headers=self.headers,
            json={
                "input": {
                    "operation": "detect_strategic_catalyst",
                    "headline": headline
                }
            },
            timeout=30
        )
        response.raise_for_status()
        return response.json()["output"]


# Usage
client = RunPodSentFilterClient(
    endpoint_id="YOUR_ENDPOINT_ID",
    api_key="YOUR_API_KEY"
)

result = client.classify("Apple announces new iPhone", company="Apple")
print(result)
```

## Cost Optimization

### Scaling Configuration

For your traffic pattern (bursts at :10 and :40 past the hour, peak 6-11 AM EST):

```yaml
# Recommended settings
active_workers: 1          # Always-warm worker
max_workers: 3             # Handle 339 article bursts
idle_timeout: 60           # Keep burst workers warm
queue_delay: 2             # Fast scaling
```

### Cost Estimates

| Configuration | Monthly Cost |
|---------------|--------------|
| 0 active workers (pure serverless) | ~$15-30 |
| 1 active worker (peak hours only) | ~$50-60 |
| 1 active worker (24/7) | ~$200 |

### Scheduled Scaling (Optional)

To minimize costs, scale active workers via API:

```bash
# Scale up at 5:45 AM EST (before peak)
curl -X PATCH "https://api.runpod.ai/v2/endpoint/$ENDPOINT_ID" \
  -H "Authorization: Bearer $API_KEY" \
  -d '{"activeWorkers": 1}'

# Scale down at 11:30 AM EST (after peak)
curl -X PATCH "https://api.runpod.ai/v2/endpoint/$ENDPOINT_ID" \
  -H "Authorization: Bearer $API_KEY" \
  -d '{"activeWorkers": 0}'
```

## Monitoring

### RunPod Dashboard

- View worker status, queue depth, and costs at https://www.runpod.io/console/serverless
- Monitor cold starts and execution times
- Set up billing alerts

### Health Check

```bash
curl "https://api.runpod.ai/v2/$ENDPOINT_ID/health" \
  -H "Authorization: Bearer $API_KEY"
```

## Troubleshooting

### Cold Start Timeout

If workers timeout during cold start:
1. Verify model is embedded in Docker image (check `TRANSFORMERS_CACHE`)
2. Increase worker timeout in RunPod console
3. Enable FlashBoot for faster cold starts

### Out of Memory

If GPU runs out of memory:
1. Use larger GPU type (A4000 → A6000)
2. Reduce batch sizes in requests
3. Check for memory leaks in handler

### Handler Errors

View worker logs in RunPod console:
1. Go to endpoint → Logs
2. Filter by worker ID or time range
3. Check for Python exceptions

### Connection Timeouts

If requests timeout:
1. Check endpoint is active (not paused)
2. Verify API key is valid
3. Increase client timeout (default 30s may be too short for cold start)

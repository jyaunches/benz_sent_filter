# Filter Pipeline Sequence Test Script

## Purpose

This script simulates the exact sequence of API calls made by `benz_analyzer`'s filter pipeline to `benz_sent_filter` during article processing.

## Background

Created to debug timeout issues reported in bead `benz_sent_filter-c1fb` after the benz_analyzer headline classification filter refactor (2025-11-22).

## What It Does

Replicates the filter pipeline execution order from `benz_analyzer/src/analyzer_core/api.py`:

1. **OpinionFilter** → `POST /classify`
   - Checks for opinion content, temporal classification, far-future forecasts

2. **RoutineOperationFilter** → `POST /routine-operations`
   - Per-ticker routine operation detection (earnings, dividends, splits)

3. **QuantitativeCatalystFilter** → `POST /detect-quantitative-catalyst`
   - Detects quantitative financial catalysts ($23B, $2.227, etc.)

4. **StrategicCatalystFilter** → `POST /detect-strategic-catalyst`
   - Detects strategic catalysts (M&A, executive changes, partnerships)

## Usage

```bash
cd /Users/jyaunches/Development/benzbout/benz_sent_filter

# Default (localhost:8002)
./test_filter_pipeline_sequence.sh

# Custom URL
BENZ_SENT_FILTER_URL=http://localhost:8002 ./test_filter_pipeline_sequence.sh
```

## Requirements

- `benz_sent_filter` service running
- `jq` installed for JSON parsing (`brew install jq` on macOS)
- `curl` for HTTP requests

## Test Article

Uses real test data from IMPL-025 dataset:
- **Headline**: "EchoStar To Sell 3.45 GHz And 600 MHz Spectrum Licenses To AT&T For $23B..."
- **Tickers**: ["SATS", "T"]
- **Expected**: Quantitative catalyst ($23B), M&A transaction

## Expected Behavior

All endpoints should:
- Respond within <1 second (not timeout at 5s)
- Return populated data structures (not empty/default values)
- Show correct classifications:
  - `/classify`: `is_opinion=false`, `temporal_category` not "unknown"
  - `/routine-operations`: Per-ticker results with `routine_operation` booleans
  - `/detect-quantitative-catalyst`: Detect $23B acquisition value
  - `/detect-strategic-catalyst`: Detect M&A transaction type

## Debugging with This Script

If you see timeouts or empty responses:

1. **Check service is running**: `ps aux | grep benz_sent_filter`
2. **Check service logs**: Look for incoming requests
3. **Verify endpoint implementation**: Each endpoint should be defined in `src/sentiment_filter/api.py`
4. **Check model loading**: Ensure NLI models loaded without errors on startup

## Output Format

The script shows:
- Request payload (JSON formatted)
- Response data (JSON formatted)
- Key fields extracted for readability
- Summary of filter decisions
- Pipeline decision (reject or pass with recipe hints)

## Related Beads

- **benz_sent_filter-c1fb**: API endpoints timing out after refactor
- **benz_analyzer-dd6d**: Missing catalyst_filter regression (already fixed)

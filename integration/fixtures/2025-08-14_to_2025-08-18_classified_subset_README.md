# Classified & Evaluated Subset - Aug 14-18, 2025

## Overview

This subset contains **55 articles** that successfully passed benz_analyzer's pre-filtering stage, were classified by the LLM, and were successfully evaluated against ground truth data.

**Source Run**: `2025-11-17_19-06_RUN_2025-08-14_to_2025-08-18_market-hours_min-vol-2000000`
**Original Dataset**: `2025-08-14_to_2025-08-18_market-hours_min-vol-2000000.json` (1,146 articles)

## Key Statistics

### Dataset Size
- **Original articles**: 1,146 (1.8MB)
- **Pre-filtered articles**: 1,089 (95.0% filtered out by benz_analyzer)
- **Successfully classified**: 59 articles (4 couldn't be evaluated due to missing ground truth)
- **Successfully evaluated**: 55 articles (in this subset)
- **Subset file size**: 79KB (95.6% smaller than original)

### Evaluation Performance
- **Overall Accuracy**: 45.5% (25 correct / 55 total)
- **Total Ticker Sentiments Evaluated**: 55 (1:1 ratio with articles)

### Confusion Matrix Distribution
| Category | Count | Percentage |
|----------|-------|------------|
| True Neutral | 13 | 23.6% |
| False Neutral | 15 | 27.3% |
| False Negative | 10 | 18.2% |
| True Negative | 7 | 12.7% |
| False Positive | 5 | 9.1% |
| True Positive | 5 | 9.1% |

### Timing Category Distribution
Articles categorized by when they were published relative to price movements:
- **pre_move**: Articles published before significant movement occurred
- **during_move**: Articles published while movement was ongoing
- **post_move_reporting**: Articles published after peak movement

## File Structure

Each article in the subset maintains the original eval data format plus an additional `evaluation` field:

```json
{
  "eval_id": "benzinga_47123967_XOS",
  "prompt_context": { ... },
  "ground_truth": { ... },
  "metadata": { ... },
  "evaluation": [
    {
      "ticker": "XOS",
      "gt_actual_movement": "LOSER",
      "predicted_sentiment": "NEGATIVE",
      "confusion_category": "True Negative",
      "is_correct": true,
      "timing_category": "during_move"
    }
  ]
}
```

### Evaluation Field Schema
- `ticker`: Stock ticker symbol
- `gt_actual_movement`: Ground truth classification (GAINER, LOSER, NEUTRAL)
- `predicted_sentiment`: LLM prediction (POSITIVE, NEGATIVE, NEUTRAL)
- `confusion_category`: Confusion matrix category
  - True Positive: Predicted POSITIVE, Actual GAINER
  - True Negative: Predicted NEGATIVE, Actual LOSER
  - True Neutral: Predicted NEUTRAL, Actual NEUTRAL
  - False Positive: Predicted POSITIVE, but Actual was LOSER/NEUTRAL
  - False Negative: Predicted NEGATIVE, but Actual was GAINER/NEUTRAL
  - False Neutral: Predicted NEUTRAL, but Actual was GAINER/LOSER
- `is_correct`: Boolean indicating if prediction matched ground truth
- `timing_category`: Temporal context (pre_move, during_move, post_move_reporting)

## Use Cases

### 1. Fast Development Iterations
```bash
# Test code changes without processing full dataset
news-analyzer evaluate eval_data/2025-08-14_to_2025-08-18_classified_subset.json
```

### 2. Confusion Matrix Analysis
```bash
# Extract all False Positives
cat eval_data/2025-08-14_to_2025-08-18_classified_subset.json | \
  jq '.[] | select(.evaluation[0].confusion_category == "False Positive")'

# Group by confusion category
cat eval_data/2025-08-14_to_2025-08-18_classified_subset.json | \
  jq 'group_by(.evaluation[0].confusion_category) |
      map({category: .[0].evaluation[0].confusion_category, count: length})'
```

### 3. Timing Analysis
```bash
# Analyze accuracy by timing category
cat eval_data/2025-08-14_to_2025-08-18_classified_subset.json | \
  jq 'group_by(.evaluation[0].timing_category) |
      map({
        timing: .[0].evaluation[0].timing_category,
        total: length,
        correct: [.[] | select(.evaluation[0].is_correct)] | length
      })'
```

### 4. Cost Optimization Testing
Use this subset for rapid iteration without incurring full dataset API costs:
- 55 articles vs 1,146 = 95% cost reduction
- Average test run: ~$0.50 vs ~$10 for full dataset
- Iteration time: <2 minutes vs ~20 minutes

### 5. Pattern Investigation
```bash
# Find all earnings-related false positives
cat eval_data/2025-08-14_to_2025-08-18_classified_subset.json | \
  jq '.[] | select(
    .evaluation[0].confusion_category == "False Positive" and
    (.prompt_context.title | test("earnings|EPS"; "i"))
  )'
```

## Why These 55 Articles?

These articles represent the complete evaluation dataset from the Aug 14-18 run:

1. **Passed Pre-Filters**: These articles weren't filtered out by benz_analyzer's cost-saving pre-filters
   - Not blocked by ticker count limits
   - Not flagged by channel filters
   - Not caught by low-impact pattern detection

2. **Successfully Classified**: The LLM generated sentiment predictions for these articles

3. **Evaluable Ground Truth**: These articles have complete temporal context data
   - `article_timing_category` is not "unknown"
   - `move_after_article_pct` is available
   - Sufficient intraday data coverage

**Excluded Articles**:
- 4 articles were classified but couldn't be evaluated (timing_category: "unknown")
  - benzinga_47129923_MIAX
  - benzinga_47154649_WKHS
  - benzinga_47162642_TNXP
  - benzinga_47166971_TNXP

## Ticker Distribution

55 unique tickers with single-ticker articles (no multi-ticker articles in this subset).

**Top Tickers**: All tickers appear exactly once in this subset.

## Data Quality Notes

1. **Sparse Data**: Many articles have `data_issues.price_data: ["sparse_data"]` with coverage ~40%
2. **Timing Context**: Articles span all three timing categories (pre_move, during_move, post_move_reporting)
3. **Market Conditions**: Aug 14-18, 2025 period with VIX ranging 15.1-15.2 (moderate volatility)

## Regeneration

To recreate this subset from a different evaluation run:

```python
import json

# Load evaluation details
with open('reports/<run_id>/evaluation_details.json') as f:
    eval_details = json.load(f)

# Get evaluated article IDs
eval_ids = {d['article_id'] for d in eval_details}

# Filter original eval data
with open('eval_data/<original>.json') as f:
    original = json.load(f)

subset = [article for article in original if article['eval_id'] in eval_ids]

# Add evaluation data...
```

## Related Files
- **Full evaluation results**: `reports/2025-11-17_19-06_RUN_2025-08-14_to_2025-08-18_market-hours_min-vol-2000000/evaluation_results.json`
- **Evaluation details**: `reports/2025-11-17_19-06_RUN_2025-08-14_to_2025-08-18_market-hours_min-vol-2000000/evaluation_details.json`
- **HTML report**: `reports/2025-11-17_19-06_RUN_2025-08-14_to_2025-08-18_market-hours_min-vol-2000000/evaluation_report.xlsx`

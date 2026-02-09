"""
Comprehensive threshold analysis with more test cases.
"""
import sys
sys.path.insert(0, "src")

from transformers import pipeline
from benz_sent_filter.services.quantitative_catalyst_detector_mnls import QuantitativeCatalystDetectorMNLS
import statistics

model_pipeline = pipeline("zero-shot-classification", model="MoritzLaurer/deberta-v3-large-zeroshot-v2.0")
PRESENCE_LABELS = QuantitativeCatalystDetectorMNLS.PRESENCE_LABELS

# Comprehensive positive test cases (should detect as catalyst)
positive_cases = [
    # Earnings
    "Company Reports Q4 Earnings of $1.5M",
    "Firm Posts Net Income of $800K in Q3",
    # Revenue (these should still be detected as quantitative catalysts)
    # Include ACTUAL test headlines with conversational structure
    "Onar says new December clients add over $400,000 in recurring revenue",  # ONAR actual headline
    "Company reports $50M in new contract revenue for Q4",
    "SaaS company adds $2M in annual recurring subscription revenue",
    "Company announces $15M in new booking revenue from enterprise clients",
    # Guidance
    "Company Raises Full-Year Revenue Guidance to $100M",
    "Firm Lowers Q3 Earnings Guidance to $50M",
    # Dividends
    "UUU Announces $0.50 Special Dividend",
    "Company Declares $1.25 Quarterly Dividend",
    # Acquisitions
    "Company Announces $10M Acquisition of Competitor",
    "Firm Completes $500M Merger with Rival",
    # Buybacks
    "Company Authorizes $100M Share Buyback Program",
    "Firm Completes $25M Stock Repurchase",
]

# Comprehensive negative test cases (should NOT detect as catalyst)
negative_cases = [
    # Stock price movements
    "Company stock rises 10% on market optimism",
    "Shares fall 5% on sector weakness",
    # Analyst opinions
    "Analyst upgrades stock to Buy rating",
    "Morgan Stanley initiates coverage with Outperform rating",
    # General updates
    "CEO discusses long-term vision in interview",
    "Company announces new board member appointment",
    # Vague language (no specific amounts)
    "Company announces plans for potential acquisition",
    "Firm exploring strategic alternatives",
    # Operational updates without financial impact
    "Company launches new marketing campaign",
    "Firm opens new office in Austin",
]

print("=== ANALYZING THRESHOLD ===\n")

positive_scores = []
for headline in positive_cases:
    result = model_pipeline(headline, PRESENCE_LABELS, multi_label=False)
    score = result['scores'][0] if result['labels'][0] == PRESENCE_LABELS[0] else result['scores'][1]
    positive_scores.append(score)
    if score < 0.98:  # Flag any unexpectedly low scores
        print(f"LOW POSITIVE: {headline[:60]}... → {score:.4f}")

negative_scores = []
for headline in negative_cases:
    result = model_pipeline(headline, PRESENCE_LABELS, multi_label=False)
    score = result['scores'][0] if result['labels'][0] == PRESENCE_LABELS[0] else result['scores'][1]
    negative_scores.append(score)
    if score > 0.95:  # Flag any unexpectedly high scores
        print(f"HIGH NEGATIVE: {headline[:60]}... → {score:.4f}")

print(f"\n=== STATISTICS ===")
print(f"Positive (should detect): n={len(positive_scores)}")
print(f"  Mean: {statistics.mean(positive_scores):.4f}")
print(f"  Min: {min(positive_scores):.4f}")
print(f"  Max: {max(positive_scores):.4f}")
print(f"  StdDev: {statistics.stdev(positive_scores):.4f}")

print(f"\nNegative (should reject): n={len(negative_scores)}")
print(f"  Mean: {statistics.mean(negative_scores):.4f}")
print(f"  Min: {min(negative_scores):.4f}")
print(f"  Max: {max(negative_scores):.4f}")
print(f"  StdDev: {statistics.stdev(negative_scores):.4f}")

# Statistical threshold calculation (mean + 2*std of negatives)
threshold_stat = statistics.mean(negative_scores) + 2 * statistics.stdev(negative_scores)
print(f"\n=== THRESHOLD RECOMMENDATIONS ===")
print(f"Current threshold: 0.5")
print(f"Mean of means: {(statistics.mean(positive_scores) + statistics.mean(negative_scores)) / 2:.4f}")
print(f"Statistical (neg_mean + 2*neg_std): {threshold_stat:.4f}")
print(f"Max negative score: {max(negative_scores):.4f}")
print(f"Min positive score: {min(positive_scores):.4f}")
print(f"Recommended (conservative): {(max(negative_scores) + min(positive_scores)) / 2:.4f}")

# Test different thresholds
print(f"\n=== THRESHOLD PERFORMANCE ===")
for threshold in [0.50, 0.60, 0.70, 0.80, 0.85, 0.89, 0.90, 0.95, 0.97, 0.98]:
    tp = sum(1 for s in positive_scores if s >= threshold)
    fn = len(positive_scores) - tp
    tn = sum(1 for s in negative_scores if s < threshold)
    fp = len(negative_scores) - tn
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0
    print(f"  {threshold:.2f}: TP={tp:2d} FN={fn:2d} TN={tn:2d} FP={fp:2d} | P={precision:.3f} R={recall:.3f} F1={f1:.3f}")

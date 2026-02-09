"""
Diagnostic script to examine presence detection scores from DeBERTa model.
This will help determine the right presence threshold.
"""
import sys
sys.path.insert(0, "src")

from transformers import pipeline
from benz_sent_filter.services.quantitative_catalyst_detector_mnls import QuantitativeCatalystDetectorMNLS

# Initialize DeBERTa model
model_pipeline = pipeline("zero-shot-classification", model="MoritzLaurer/deberta-v3-large-zeroshot-v2.0")

# Presence labels from quantitative detector (use actual values from class)
PRESENCE_LABELS = QuantitativeCatalystDetectorMNLS.PRESENCE_LABELS

# Test headlines that should have catalyst
positive_headlines = [
    "ONAR Announces $400K in Recurring Revenue",
    "Company Reports Q4 Earnings of $1.5M",
    "Firm Posts Net Income of $800K in Q3",
    "Company Raises Full-Year Revenue Guidance to $100M",
    "UUU Announces $0.50 Special Dividend",
    "Company Announces $10M Acquisition of Competitor",
]

# Test headlines that should NOT have catalyst
negative_headlines = [
    "Company stock rises 10% on market optimism",
    "Analyst upgrades stock to Buy rating",
    "CEO discusses long-term vision in interview",
]

print("=== POSITIVE EXAMPLES (should have catalyst) ===\n")
for headline in positive_headlines:
    result = model_pipeline(headline, PRESENCE_LABELS, multi_label=False)
    catalyst_score = result['scores'][0]  # First label is the "has catalyst" label
    print(f"{headline}")
    print(f"  Catalyst score: {catalyst_score:.4f}")
    print(f"  Predicted: {result['labels'][0][:50]}...")
    print()

print("\n=== NEGATIVE EXAMPLES (should NOT have catalyst) ===\n")
for headline in negative_headlines:
    result = model_pipeline(headline, PRESENCE_LABELS, multi_label=False)
    catalyst_score = result['scores'][0]
    print(f"{headline}")
    print(f"  Catalyst score: {catalyst_score:.4f}")
    print(f"  Predicted: {result['labels'][0][:50]}...")
    print()

# Calculate statistics
print("\n=== STATISTICS ===")
positive_scores = []
for headline in positive_headlines:
    result = model_pipeline(headline, PRESENCE_LABELS, multi_label=False)
    positive_scores.append(result['scores'][0])

negative_scores = []
for headline in negative_headlines:
    result = model_pipeline(headline, PRESENCE_LABELS, multi_label=False)
    negative_scores.append(result['scores'][0])

import statistics
print(f"Positive examples (should detect):")
print(f"  Mean: {statistics.mean(positive_scores):.4f}")
print(f"  Min: {min(positive_scores):.4f}")
print(f"  Max: {max(positive_scores):.4f}")
if len(positive_scores) > 1:
    print(f"  StdDev: {statistics.stdev(positive_scores):.4f}")

print(f"\nNegative examples (should NOT detect):")
print(f"  Mean: {statistics.mean(negative_scores):.4f}")
print(f"  Min: {min(negative_scores):.4f}")
print(f"  Max: {max(negative_scores):.4f}")
if len(negative_scores) > 1:
    print(f"  StdDev: {statistics.stdev(negative_scores):.4f}")

print(f"\nCurrent threshold: 0.5")
print(f"Suggested threshold (mean of means): {(statistics.mean(positive_scores) + statistics.mean(negative_scores)) / 2:.4f}")

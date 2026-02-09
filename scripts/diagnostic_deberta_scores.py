"""
Diagnostic script to examine DeBERTa score distributions on failing test cases.
This will help determine if we need threshold adjustments or label tuning.
"""
import sys
sys.path.insert(0, "src")

from benz_sent_filter.services.quantitative_catalyst_detector_mnls import QuantitativeCatalystDetectorMNLS
from benz_sent_filter.services.strategic_catalyst_detector_mnls import StrategicCatalystDetectorMNLS

# Initialize detectors
quant_detector = QuantitativeCatalystDetectorMNLS()
strategic_detector = StrategicCatalystDetectorMNLS()

print("=== QUANTITATIVE CATALYST DETECTOR FAILURES ===\n")

# Earnings vs Revenue disambiguation failures
revenue_headlines = [
    ("ONAR recurring revenue", "ONAR Announces $400K in Recurring Revenue"),
    ("Contract revenue", "Company Secures $2M Contract Revenue"),
    ("Subscription revenue", "SaaS Company Reports 50% Subscription Revenue Growth"),
    ("Booking revenue", "Platform Announces $5M in New Booking Revenue"),
]

print("Revenue announcements (should NOT be 'earnings'):")
for name, headline in revenue_headlines:
    result = quant_detector.detect(headline)
    print(f"\n{name}: {headline}")
    print(f"  has_catalyst: {result.has_quantitative_catalyst}")
    print(f"  catalyst_type: {result.catalyst_type}")
    print(f"  confidence: {result.confidence:.3f}")
    if hasattr(result, 'type_scores'):
        print(f"  type_scores: {result.type_scores}")

# Real earnings that should still be classified as earnings
earnings_headlines = [
    ("Real earnings Q4", "Company Reports Q4 Earnings of $1.5M"),
    ("Net income earnings", "Firm Posts Net Income of $800K in Q3"),
]

print("\n\nReal earnings announcements (SHOULD be 'earnings'):")
for name, headline in earnings_headlines:
    result = quant_detector.detect(headline)
    print(f"\n{name}: {headline}")
    print(f"  has_catalyst: {result.has_quantitative_catalyst}")
    print(f"  catalyst_type: {result.catalyst_type}")
    print(f"  confidence: {result.confidence:.3f}")
    if hasattr(result, 'type_scores'):
        print(f"  type_scores: {result.type_scores}")

# Guidance test
guidance_headline = "Company Raises Full-Year Revenue Guidance to $100M"
print(f"\n\nGuidance headline (SHOULD be 'guidance'):")
print(f"{guidance_headline}")
result = quant_detector.detect(guidance_headline)
print(f"  has_catalyst: {result.has_quantitative_catalyst}")
print(f"  catalyst_type: {result.catalyst_type}")
print(f"  confidence: {result.confidence:.3f}")
if hasattr(result, 'type_scores'):
    print(f"  type_scores: {result.type_scores}")

print("\n\n=== STRATEGIC CATALYST DETECTOR FAILURES ===\n")

# Clinical trial failures
clinical_headlines = [
    ("PSTV results", "Positron Announces Positive Phase 1 Clinical Trial Results"),
    ("Clinical trial type", "Company Announces Positive Phase 2 Clinical Trial Results"),
]

print("Clinical trial headlines (should be 'clinical_trial', not 'mixed'):")
for name, headline in clinical_headlines:
    result = strategic_detector.detect(headline)
    print(f"\n{name}: {headline}")
    print(f"  has_catalyst: {result.has_strategic_catalyst}")
    print(f"  catalyst_subtype: {result.catalyst_subtype}")
    print(f"  confidence: {result.confidence:.3f}")

# Product launch failures
product_headlines = [
    ("SMX product launch", "SMX (SECURITY MATTERS) PLC Partners with UN to Launch Global Product Authentication Platform"),
    ("Product launch type", "Company Launches New Product Platform"),
]

print("\n\nProduct launch headlines (should be 'product_launch', not 'mixed'):")
for name, headline in product_headlines:
    result = strategic_detector.detect(headline)
    print(f"\n{name}: {headline}")
    print(f"  has_catalyst: {result.has_strategic_catalyst}")
    print(f"  catalyst_subtype: {result.catalyst_subtype}")
    print(f"  confidence: {result.confidence:.3f}")

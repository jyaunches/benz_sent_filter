"""Test strategic catalyst detection with problem headlines."""
import sys
sys.path.insert(0, "src")

from benz_sent_filter.services.strategic_catalyst_detector_mnls import StrategicCatalystDetectorMNLS

detector = StrategicCatalystDetectorMNLS()

# Problem headlines from failures
test_cases = [
    ("SMX product launch", "SMX (SECURITY MATTERS) PLC Partners with UN to Launch Global Product Authentication Platform", "product_launch"),
    ("Citius AI launch", "Citius Pharmaceuticals Launches AI Platform for Drug Development", "product_launch"),
    ("PSTV clinical trial", "Positron Announces Positive Phase 1 Clinical Trial Results", "clinical_trial"),
    ("Generic clinical trial", "Company Announces Positive Phase 2 Clinical Trial Results", "clinical_trial"),
    ("Generic product launch", "Company Launches New Product Platform", "product_launch"),
]

print("Testing Strategic Catalyst Detection:\n")
for name, headline, expected_type in test_cases:
    result = detector.detect(headline)
    status = "✓" if result.catalyst_subtype == expected_type else "✗"
    print(f"{status} {name}")
    print(f"  Headline: {headline[:70]}...")
    print(f"  Expected: {expected_type}")
    print(f"  Got: {result.catalyst_subtype}")
    print(f"  Has catalyst: {result.has_strategic_catalyst}")
    print(f"  Confidence: {result.confidence:.3f}")
    print()

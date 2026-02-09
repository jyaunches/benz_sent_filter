"""Test clinical trial presence detection scores."""
import sys
sys.path.insert(0, "src")

from transformers import pipeline
from benz_sent_filter.services.strategic_catalyst_detector_mnls import StrategicCatalystDetectorMNLS

model_pipeline = pipeline("zero-shot-classification", model="MoritzLaurer/deberta-v3-large-zeroshot-v2.0")
PRESENCE_LABELS = StrategicCatalystDetectorMNLS.PRESENCE_LABELS

test_headlines = [
    "Positron Announces Positive Phase 1 Clinical Trial Results",
    "Company Announces Positive Phase 2 Clinical Trial Results",
    "Biotech Reports Promising Phase 3 Trial Data",
    "Firm Shares Negative Clinical Study Outcomes",
]

print("Clinical Trial Presence Scores:\n")
for headline in test_headlines:
    result = model_pipeline(headline, PRESENCE_LABELS, multi_label=False)
    score = result['scores'][0] if result['labels'][0] == PRESENCE_LABELS[0] else result['scores'][1]
    predicted = result['labels'][0][:60]
    print(f"{headline[:70]}...")
    print(f"  Score: {score:.4f}")
    print(f"  Threshold: 0.5")
    print(f"  Pass? {score >= 0.5}")
    print(f"  Predicted: {predicted}...")
    print()

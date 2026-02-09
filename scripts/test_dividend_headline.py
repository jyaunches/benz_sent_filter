"""Test the failing dividend headline."""
import sys
sys.path.insert(0, "src")

from transformers import pipeline
from benz_sent_filter.services.quantitative_catalyst_detector_mnls import QuantitativeCatalystDetectorMNLS

model_pipeline = pipeline("zero-shot-classification", model="MoritzLaurer/deberta-v3-large-zeroshot-v2.0")
PRESENCE_LABELS = QuantitativeCatalystDetectorMNLS.PRESENCE_LABELS

headline = "Universal Security Instruments Increases Quarterly Dividend to $1 Per Share"

result = model_pipeline(headline, PRESENCE_LABELS, multi_label=False)
score = result['scores'][0] if result['labels'][0] == PRESENCE_LABELS[0] else result['scores'][1]
predicted = result['labels'][0][:70]

print(f"Headline: {headline}")
print(f"Score: {score:.4f}")
print(f"Threshold: 0.85")
print(f"Pass? {score >= 0.85}")
print(f"Predicted: {predicted}...")
print()

# Also test with detector
detector = QuantitativeCatalystDetectorMNLS()
result = detector.detect(headline)
print("Detector result:")
print(f"  has_catalyst: {result.has_quantitative_catalyst}")
print(f"  catalyst_type: {result.catalyst_type}")
print(f"  confidence: {result.confidence:.3f}")

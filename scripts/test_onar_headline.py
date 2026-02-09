"""Test ONAR headline specifically."""
import sys
sys.path.insert(0, "src")

from transformers import pipeline
from benz_sent_filter.services.quantitative_catalyst_detector_mnls import QuantitativeCatalystDetectorMNLS

model_pipeline = pipeline("zero-shot-classification", model="MoritzLaurer/deberta-v3-large-zeroshot-v2.0")
PRESENCE_LABELS = QuantitativeCatalystDetectorMNLS.PRESENCE_LABELS

test_headlines = [
    "Onar says new December clients add over $400,000 in recurring revenue",
    "Company reports $50M in new contract revenue for Q4",
    "SaaS company adds $2M in annual recurring subscription revenue",
    "Company announces $15M in new booking revenue from enterprise clients",
]

print("Testing revenue announcements with DeBERTa:\n")
for headline in test_headlines:
    result = model_pipeline(headline, PRESENCE_LABELS, multi_label=False)
    score = result['scores'][0] if result['labels'][0] == PRESENCE_LABELS[0] else result['scores'][1]
    predicted = result['labels'][0][:60]
    print(f"{headline[:70]}...")
    print(f"  Score: {score:.4f}")
    print(f"  Predicted: {predicted}...")
    print(f"  PASS threshold (0.98)? {score >= 0.98}")
    print()

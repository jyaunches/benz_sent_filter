"""Strategic catalyst detector using MNLI zero-shot classification.

This module provides an MNLI-based detector that identifies whether article
headlines announce strategic corporate catalysts (executive changes, mergers,
partnerships, product launches, rebranding, clinical trials) using semantic
understanding.

Pure MNLI approach:
- MNLI: Presence detection (semantic understanding)
- MNLI: Type classification (6 catalyst categories)
- Confidence: MNLI type classification score
"""

from typing import Optional

from transformers import pipeline

from benz_sent_filter.models.classification import StrategicCatalystResult


class StrategicCatalystDetectorMNLS:
    """MNLI-based detector for strategic corporate catalysts.

    Uses zero-shot classification to detect whether a headline announces
    a strategic corporate catalyst and classify its type across 6 categories.

    Pure MNLI approach - no regex patterns needed for strategic catalysts.
    """

    # MNLI candidate labels for presence detection
    # Optimized to distinguish strategic catalysts from financial results and routine operations
    PRESENCE_LABELS = [
        "This announces a specific strategic corporate event like an executive change, merger, partnership, product launch, or rebranding",
        "This describes financial results, stock price movements, routine operations, or general market commentary",
    ]

    # Presence detection threshold
    PRESENCE_THRESHOLD = 0.5  # Aligned with company relevance detection

    # Type classification threshold
    TYPE_THRESHOLD = 0.6  # Aligned with quantitative catalyst type classification

    # MNLI labels for catalyst type classification
    CATALYST_TYPE_LABELS = {
        "executive_change": [
            "This announces a C-suite executive appointment, departure, or transition including CEO, CFO, President, or other senior leadership",
            "This does not announce an executive leadership change",
        ],
        "strategic_partnership": [
            "This announces a strategic partnership, collaboration agreement, memorandum of understanding, or joint venture",
            "This does not announce a strategic partnership",
        ],
        "product_launch": [
            "This announces a new product launch, technology platform deployment, or service introduction",
            "This does not announce a product launch",
        ],
        "merger_agreement": [
            "This announces a merger agreement, acquisition announcement, or strategic combination",
            "This does not announce a merger or acquisition",
        ],
        "rebranding": [
            "This announces a company name change, ticker symbol change, or corporate rebranding",
            "This does not announce a rebranding",
        ],
        "clinical_trial_results": [
            "This announces clinical trial results, medical research findings, or drug efficacy data",
            "This does not announce clinical trial results",
        ],
    }

    def __init__(self, model_name: str = "facebook/bart-large-mnli", pipeline=None):
        """Initialize the MNLI-based strategic catalyst detector.

        Args:
            model_name: HuggingFace model name for zero-shot classification
            pipeline: Optional pre-initialized transformers pipeline to share across services
        """
        if pipeline is not None:
            # Share existing pipeline (pipeline reuse pattern)
            self._pipeline = pipeline
        else:
            # Create new pipeline
            from transformers import pipeline as create_pipeline

            self._pipeline = create_pipeline("zero-shot-classification", model=model_name)

    def detect(self, headline: Optional[str]) -> StrategicCatalystResult:
        """Detect strategic catalyst in headline.

        Args:
            headline: News article headline to analyze

        Returns:
            StrategicCatalystResult with detection details
        """
        # Handle None/empty input
        if not headline:
            return StrategicCatalystResult(
                headline=headline or "",
                has_strategic_catalyst=False,
                catalyst_type=None,
                confidence=0.0,
            )

        # Step 1: MNLI presence check
        presence_score = self._check_presence(headline)

        # Fast path: If MNLI says not a catalyst, return negative result
        if presence_score < self.PRESENCE_THRESHOLD:
            return StrategicCatalystResult(
                headline=headline,
                has_strategic_catalyst=False,
                catalyst_type=None,
                confidence=presence_score,
            )

        # Step 2: Classify catalyst type using MNLI
        type_result = self._classify_type(headline)
        catalyst_type = type_result["type"]
        type_score = type_result["confidence"]

        # Step 3: Use type classification score as confidence
        confidence = type_score

        # Final decision: Has catalyst if presence detected
        has_catalyst = True

        return StrategicCatalystResult(
            headline=headline,
            has_strategic_catalyst=has_catalyst,
            catalyst_type=catalyst_type,
            confidence=confidence,
        )

    def _check_presence(self, headline: str) -> float:
        """Check if headline announces a strategic catalyst using MNLI.

        Args:
            headline: Headline text to check

        Returns:
            Float score (0.0-1.0) indicating confidence that headline
            announces a strategic catalyst
        """
        result = self._pipeline(headline, self.PRESENCE_LABELS)

        # Extract score for "announces catalyst" label (first label)
        if result["labels"][0] == self.PRESENCE_LABELS[0]:
            # Top prediction is "catalyst" - use its score
            return result["scores"][0]
        else:
            # Top prediction is "not catalyst" - return catalyst score (second)
            return result["scores"][1]

    def _classify_type(self, headline: str) -> dict:
        """Classify catalyst type using MNLI.

        Tests headline against all 6 catalyst type labels and returns
        the highest-scoring type. Returns "mixed" if best score < threshold.

        Args:
            headline: Headline text to classify

        Returns:
            Dict with:
                - type: str (executive_change/strategic_partnership/product_launch/
                         merger_agreement/rebranding/clinical_trial_results/mixed)
                - confidence: float (0.0-1.0, score of best type)
        """
        type_scores = {}

        # Test each catalyst type
        for catalyst_type, labels in self.CATALYST_TYPE_LABELS.items():
            result = self._pipeline(headline, labels)

            # Extract score for positive label (first label)
            if result["labels"][0] == labels[0]:
                # Top prediction is this type - use its score
                score = result["scores"][0]
            else:
                # Top prediction is negative - use type score (second)
                score = result["scores"][1]

            type_scores[catalyst_type] = score

        # Find highest-scoring type
        best_type = max(type_scores, key=type_scores.get)
        best_score = type_scores[best_type]

        # If best score below threshold, return "mixed" (ambiguous)
        if best_score < self.TYPE_THRESHOLD:
            return {"type": "mixed", "confidence": best_score}

        return {"type": best_type, "confidence": best_score}

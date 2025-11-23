"""Strategic catalyst detector using MNLI zero-shot classification.

This module provides an MNLI-based detector that identifies whether article
headlines announce strategic corporate catalysts (executive changes, mergers,
partnerships, product launches, rebranding, clinical trials) using semantic
understanding.

Pure MNLI approach:
- MNLI: Presence detection (semantic understanding)
- MNLI: Type classification (6 catalyst categories)
- Confidence: MNLI type classification score

Quantitative Pre-Filter:
- Regex: Reject headlines with dollar amounts + financial keywords
- Purpose: Prevent quantitative catalysts from being detected as strategic
"""

import re
from typing import Optional

from transformers import pipeline

from benz_sent_filter.models.classification import StrategicCatalystResult


class StrategicCatalystDetectorMNLS:
    """MNLI-based detector for strategic corporate catalysts.

    Uses zero-shot classification to detect whether a headline announces
    a strategic corporate catalyst and classify its type across 6 categories.

    Hybrid approach:
    - Regex: Pre-filter to reject quantitative catalysts (dollar amounts + financial keywords)
    - MNLI: Semantic detection and type classification for strategic catalysts
    """

    # Quantitative catalyst pre-filter patterns (reused from quantitative_catalyst_detector_mnls)
    DOLLAR_PATTERN = re.compile(
        r"\$(\d+(?:,\d{3})*(?:\.\d+)?)\s*([BMK])?\b(?:/[Ss]hare|\s+[Pp]er\s+[Ss]hare)?",
        re.IGNORECASE,
    )
    PERCENTAGE_PATTERN = re.compile(r"\b(\d+(?:\.\d+)?)\s*%", re.IGNORECASE)
    FINANCIAL_KEYWORDS = re.compile(
        r"\b(dividend|yield|growth|return|margin|beat|miss|eps|earnings|revenue|guidance)\b",
        re.IGNORECASE,
    )

    # MNLI candidate labels for presence detection
    # Optimized to distinguish strategic catalysts from financial results and routine operations
    PRESENCE_LABELS = [
        "This announces a specific strategic corporate event like an executive change, merger, partnership, product launch, or rebranding",
        "This describes financial results, stock price movements, routine operations, or general market commentary",
    ]

    # Presence detection threshold
    PRESENCE_THRESHOLD = 0.5  # Aligned with company relevance detection

    # Type classification threshold
    TYPE_THRESHOLD = 0.5  # Lowered to match presence detection threshold for better recall

    # MNLI labels for catalyst type classification
    # Tuned for semantic clarity with action-oriented verbs and distinctive features
    # Key principle: Avoid semantic overlap, use action verbs, include distinctive keywords
    CATALYST_TYPE_LABELS = {
        "m&a": [
            "This announces a merger where companies combine into one entity or an acquisition where one company purchases and takes control of another company",
            "This does not announce a merger, acquisition, or companies combining into a single entity",
        ],
        "executive_changes": [
            "This announces that a C-suite executive (CEO, CFO, President, or COO) is joining, leaving, stepping down from, or being appointed to their leadership position",
            "This does not announce executive appointments, departures, or C-suite leadership transitions",
        ],
        "partnership": [
            "This announces that two or more separate companies are signing an agreement to collaborate, partner, or work together on a joint project while remaining independent companies",
            "This does not announce a partnership, collaboration agreement, or companies working together while staying separate",
        ],
        "product_launch": [
            "This announces that a single company is launching, releasing, or making available a new finished product, service, or platform that is ready for customers to use now",
            "This does not announce a product launch, release, or new offering becoming available to customers",
        ],
        "corporate_restructuring": [
            "This announces a company is changing its corporate name, rebranding its identity, changing its ticker symbol, or restructuring its corporate structure",
            "This does not announce a name change, rebranding, ticker change, or corporate restructuring",
        ],
        "clinical_trial": [
            "This announces positive or negative results, outcomes, or data from a completed Phase 1, Phase 2, or Phase 3 clinical trial or medical study",
            "This does not announce clinical trial results, medical study outcomes, or research findings from completed trials",
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
                catalyst_subtype=None,
                confidence=0.0,
            )

        # Step 0: Quantitative pre-filter - reject headlines with financial values
        # Check for dollar amounts, percentages, and financial keywords
        has_dollar_amount = bool(self.DOLLAR_PATTERN.search(headline))
        has_percentage = bool(self.PERCENTAGE_PATTERN.search(headline))
        has_financial_keyword = bool(self.FINANCIAL_KEYWORDS.search(headline))

        # Reject headlines with quantitative financial indicators:
        # - Any dollar amount (signals quantitative catalyst like acquisition value, dividend amount)
        # - Percentage + financial keyword (signals quantitative results like earnings growth)
        # - Financial keyword alone (signals financial results like earnings, revenue reports)
        if has_dollar_amount or (has_percentage and has_financial_keyword) or has_financial_keyword:
            return StrategicCatalystResult(
                headline=headline,
                has_strategic_catalyst=False,
                catalyst_subtype=None,
                confidence=0.0,
            )

        # Step 1: MNLI presence check
        presence_score = self._check_presence(headline)

        # Fast path: If MNLI says not a catalyst, return negative result
        if presence_score < self.PRESENCE_THRESHOLD:
            return StrategicCatalystResult(
                headline=headline,
                has_strategic_catalyst=False,
                catalyst_subtype=None,
                confidence=presence_score,
            )

        # Step 2: Classify catalyst type using MNLI
        type_result = self._classify_type(headline)
        catalyst_subtype = type_result["type"]
        type_score = type_result["confidence"]

        # Step 3: Use type classification score as confidence
        confidence = type_score

        # Final decision: Has catalyst if presence detected
        has_catalyst = True

        return StrategicCatalystResult(
            headline=headline,
            has_strategic_catalyst=has_catalyst,
            catalyst_subtype=catalyst_subtype,
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

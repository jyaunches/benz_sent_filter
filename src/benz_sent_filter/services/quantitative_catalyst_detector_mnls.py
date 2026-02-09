"""Quantitative catalyst detector using MNLI zero-shot classification.

This module provides an MNLI-based detector that identifies whether article
headlines announce specific, quantitative financial catalysts (dividends,
acquisitions, buybacks, earnings, guidance) using semantic understanding.

Hybrid approach:
- MNLI: Presence detection (semantic understanding)
- Regex: Value extraction (dollar amounts, per-share prices, percentages)
- Numeric: Confidence calculation
"""

import re
import time
from typing import Optional

from loguru import logger
from transformers import pipeline

from benz_sent_filter.models.classification import QuantitativeCatalystResult


class QuantitativeCatalystDetectorMNLS:
    """MNLI-based detector for quantitative financial catalysts.

    Uses zero-shot classification to detect whether a headline announces
    a specific, quantitative financial catalyst. Combines MNLI semantic
    understanding with regex-based value extraction.

    Phase 1: Presence detection only (no type classification yet).
    """

    # MNLI candidate labels for presence detection
    # Optimized to distinguish quantitative catalysts from vague updates and price movements
    # Tuned for DeBERTa-v3-large model - more precise language to avoid false negatives
    # Includes both capital-returning (dividends, buybacks, divestitures) and capital-deploying/raising (acquisitions, equity offerings) events
    # Includes revenue announcements (recurring revenue, contract revenue, booking revenue)
    PRESENCE_LABELS = [
        "This announces a corporate financial event with specific dollar amounts such as dividends, acquisitions, buybacks, earnings results, revenue guidance, revenue announcements, asset sales, divestitures, or equity and debt offerings",
        "This describes general commentary, stock price changes, analyst opinions, or vague business updates without specific financial transactions",
    ]

    # Presence detection threshold
    # Tuned for DeBERTa-v3-large based on score distribution analysis:
    # - Positive cases (catalysts): min=0.8999 (ONAR conversational headline), mean=0.9910
    # - Negative cases (non-catalysts): max=0.2850, mean=0.0593
    # - 0.85 provides perfect separation with safety margin above max negative (0.2850)
    PRESENCE_THRESHOLD = 0.85

    # Type classification threshold
    TYPE_THRESHOLD = 0.6  # Minimum score to assign specific type

    # MNLI labels for catalyst type classification
    # Tuned for DeBERTa-v3-large to distinguish directionality and transaction types
    # Key improvements: directional clarity (buying vs selling, returning vs raising capital)
    CATALYST_TYPE_LABELS = {
        "dividend": [
            "This announces that the company is returning capital to shareholders by paying out a cash dividend or distribution",
            "This does not announce a dividend payment or capital return to shareholders",
        ],
        "acquisition": [
            "This announces that the company is buying, acquiring, or purchasing another company, assets, or business (the company is the BUYER, not the seller)",
            "This is not about the company buying or acquiring another entity (it could be about selling assets or something else entirely)",
        ],
        "buyback": [
            "This announces that the company is buying back or repurchasing its own shares from shareholders to reduce share count",
            "This is not about the company buying back its own shares",
        ],
        "earnings": [
            "This announces actual profit, net income, or bottom-line earnings results from a completed reporting period (not just revenue or top-line growth)",
            "This is not about actual profit or net income from a completed period",
        ],
        "guidance": [
            "This provides forward-looking financial projections, forecasts, or guidance for future periods",
            "This is not about forward-looking financial projections or guidance",
        ],
    }

    # Regex patterns for value extraction
    # Dollar amounts: $1, $3.5B, $75M, $1.9B, $560.5M
    # Use word boundary after B/M/K to avoid matching "$100 Milestone" as "$100M"
    DOLLAR_PATTERN = re.compile(
        r"\$(\d+(?:,\d{3})*(?:\.\d+)?)\s*([BMK])?\b(?:/[Ss]hare|\s+[Pp]er\s+[Ss]hare)?",
        re.IGNORECASE,
    )

    # Percentage pattern (context-aware - only near financial keywords)
    PERCENTAGE_PATTERN = re.compile(r"\b(\d+(?:\.\d+)?)\s*%", re.IGNORECASE)

    # Financial context keywords for percentage extraction
    FINANCIAL_KEYWORDS = re.compile(
        r"\b(dividend|yield|growth|return|margin|beat|miss|eps|earnings|revenue|guidance)\b",
        re.IGNORECASE,
    )

    def __init__(self, model_name: str = "MoritzLaurer/deberta-v3-large-zeroshot-v2.0", pipeline=None):
        """Initialize the MNLI-based quantitative catalyst detector.

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

    def detect(self, headline: Optional[str]) -> QuantitativeCatalystResult:
        """Detect quantitative catalyst in headline.

        Args:
            headline: News article headline to analyze

        Returns:
            QuantitativeCatalystResult with detection details
        """
        logger.debug(
            "Starting quantitative catalyst detection",
            headline_length=len(headline) if headline else 0,
        )
        start_time = time.time()

        # Handle None/empty input
        if not headline:
            logger.warning("Empty headline provided for quantitative catalyst detection")
            return QuantitativeCatalystResult(
                headline=headline or "",
                has_quantitative_catalyst=False,
                catalyst_type=None,
                catalyst_values=[],
                confidence=0.0,
            )

        # Step 1: MNLI presence check
        logger.debug("Running MNLI presence detection")
        presence_score = self._check_presence(headline)
        logger.debug(
            "MNLI presence detection completed", presence_score=round(presence_score, 3)
        )

        # Fast path: If MNLI says not a catalyst, return negative result
        if presence_score < self.PRESENCE_THRESHOLD:
            duration = time.time() - start_time
            logger.info(
                "Quantitative catalyst not detected (presence score below threshold)",
                presence_score=round(presence_score, 3),
                threshold=self.PRESENCE_THRESHOLD,
                duration_ms=round(duration * 1000, 2),
            )
            return QuantitativeCatalystResult(
                headline=headline,
                has_quantitative_catalyst=False,
                catalyst_type=None,
                catalyst_values=[],
                confidence=0.0,
            )

        # Step 2: Extract values using regex
        logger.debug("Extracting quantitative values")
        catalyst_values = self._extract_values(headline)
        logger.debug(
            "Value extraction completed",
            value_count=len(catalyst_values),
            values=catalyst_values,
        )

        # Step 3: Classify catalyst type (Phase 2)
        logger.debug("Classifying catalyst type")
        type_result = self._classify_type(headline)
        catalyst_type = type_result["type"]
        type_score = type_result["confidence"]
        logger.debug(
            "Type classification completed",
            catalyst_type=catalyst_type,
            type_score=round(type_score, 3),
        )

        # Step 4: Calculate confidence
        confidence = self._calculate_confidence(
            presence_score, type_score, catalyst_values, headline
        )

        # Final decision: Has catalyst if presence score high AND values extracted
        has_catalyst = presence_score >= self.PRESENCE_THRESHOLD and len(
            catalyst_values
        ) > 0

        # Edge case: MNLI says catalyst but no values found
        # This might be a false positive - penalize confidence
        if presence_score >= self.PRESENCE_THRESHOLD and len(catalyst_values) == 0:
            has_catalyst = False
            catalyst_type = None
            confidence = presence_score * 0.3  # Penalize
            logger.warning(
                "Catalyst detected but no values extracted - likely false positive",
                presence_score=round(presence_score, 3),
            )

        duration = time.time() - start_time
        logger.info(
            "Quantitative catalyst detection completed",
            has_catalyst=has_catalyst,
            catalyst_type=catalyst_type,
            value_count=len(catalyst_values),
            confidence=round(confidence, 3),
            duration_ms=round(duration * 1000, 2),
        )

        return QuantitativeCatalystResult(
            headline=headline,
            has_quantitative_catalyst=has_catalyst,
            catalyst_type=catalyst_type if has_catalyst else None,
            catalyst_values=catalyst_values,
            confidence=confidence,
        )

    def _check_presence(self, headline: str) -> float:
        """Check if headline announces a quantitative catalyst using MNLI.

        Args:
            headline: Headline text to check

        Returns:
            Float score (0.0-1.0) indicating confidence that headline
            announces a quantitative catalyst
        """
        result = self._pipeline(headline, self.PRESENCE_LABELS)

        # Extract score for "announces catalyst" label (first label)
        if result["labels"][0] == self.PRESENCE_LABELS[0]:
            # Top prediction is "catalyst" - use its score
            return result["scores"][0]
        else:
            # Top prediction is "vague update" - return catalyst score (second)
            return result["scores"][1]

    def _extract_values(self, headline: str) -> list[str]:
        """Extract quantitative values from headline using regex.

        Extracts:
        - Dollar amounts: $1, $3.5B, $75M
        - Per-share prices: $37.50/share, $10 per share
        - Percentages: Only when near financial keywords

        Args:
            headline: Headline text to extract from

        Returns:
            List of extracted values as strings (e.g., ["$1", "$3.5B", "10%"])
        """
        values = []

        # Extract dollar amounts (including per-share prices)
        for match in self.DOLLAR_PATTERN.finditer(headline):
            amount = match.group(1)
            unit = match.group(2) or ""  # B, M, K or empty

            # Get the full matched text to preserve formatting
            full_match = match.group(0)

            # Standardize the format
            if unit:
                values.append(f"${amount}{unit}")
            elif "/share" in full_match.lower() or "per share" in full_match.lower():
                # Preserve per-share notation
                if "/share" in full_match.lower():
                    values.append(f"${amount}/Share")
                else:
                    values.append(f"${amount}/Share")
            else:
                # Check if "per share" appears within 5 words after the dollar amount
                # This handles "Tender Offer At $10 Per Share" where regex doesn't capture it
                match_end = match.end()
                remaining = headline[match_end:match_end+30]  # Look ahead up to 30 chars
                if re.search(r'\s+per\s+share', remaining, re.IGNORECASE):
                    values.append(f"${amount}/Share")
                else:
                    values.append(f"${amount}")

        # Extract percentages only if near financial keywords
        if self.FINANCIAL_KEYWORDS.search(headline):
            for match in self.PERCENTAGE_PATTERN.finditer(headline):
                pct_value = match.group(1)
                values.append(f"{pct_value}%")

        return values

    def _classify_type(self, headline: str) -> dict:
        """Classify catalyst type using MNLI.

        Tests headline against all 5 catalyst type labels and returns
        the highest-scoring type. Returns "mixed" if best score < threshold.

        Args:
            headline: Headline text to classify

        Returns:
            Dict with:
                - type: str (dividend/acquisition/buyback/earnings/guidance/mixed)
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

    def _calculate_confidence(
        self,
        presence_score: float,
        type_score: float,
        catalyst_values: list[str],
        headline: str,
    ) -> float:
        """Calculate confidence score for detection.

        Combines:
        - MNLI presence score (50% weight)
        - MNLI type score (50% weight)
        - Number of values extracted (boost for multiple values)

        Args:
            presence_score: MNLI presence score (0.0-1.0)
            type_score: MNLI type classification score (0.0-1.0)
            catalyst_values: List of extracted values
            headline: Original headline text

        Returns:
            Confidence score (0.0-1.0)
        """
        # Base confidence: weighted average of presence and type scores
        confidence = (presence_score * 0.5) + (type_score * 0.5)

        # Boost confidence if multiple values extracted (stronger evidence)
        if len(catalyst_values) > 1:
            confidence = min(confidence + 0.1, 1.0)

        return confidence

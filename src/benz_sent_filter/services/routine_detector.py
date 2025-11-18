"""Routine business operations detector using pattern matching.

This module provides the RoutineOperationDetector service class that identifies
routine business operations (loan sales, buybacks, dividends, refinancing) using
regex pattern matching, scoring algorithms, and materiality assessment.
"""

import re
from typing import Optional

from pydantic import BaseModel


class RoutineDetectionResult(BaseModel):
    """Result model for routine operation detection.

    Phase 1 fields (required):
        routine_score: int (0-4) pattern match score
        confidence: float [0.0-1.0] confidence in routine detection
        detected_patterns: list of matched pattern types
        transaction_value: float or None (extracted dollar amount)
        process_stage: str ("early", "ongoing", "completed", "unknown")
        result: bool - final routine operation classification

    Phase 2 fields (optional, added later):
        materiality_score: int (-2 to 0) materiality assessment
        materiality_ratio: float or None (transaction / company metric)
    """

    routine_score: int
    confidence: float
    detected_patterns: list[str]
    transaction_value: Optional[float] = None
    process_stage: str
    result: bool
    materiality_score: Optional[int] = None
    materiality_ratio: Optional[float] = None


class RoutineOperationDetector:
    """Detector for routine business operations in financial services.

    Uses compiled regex patterns to identify:
    - Process language (initiation, marketing, planning, evaluation)
    - Routine transaction types (loan sales, buybacks, dividends, refinancing)
    - Frequency indicators (recurrence, schedule, program)
    - Dollar amounts
    - Superlatives and override keywords

    Scoring algorithm combines pattern matches and applies explicit overrides
    for exceptional events (superlatives, completions, special events).
    """

    # Process language patterns (compiled regex)
    PROCESS_LANGUAGE_PATTERNS = {
        "initiation": re.compile(
            r"\b(begins?|starts?|initiates?|commences?|launches?)\b",
            re.IGNORECASE,
        ),
        "marketing": re.compile(
            r"\b(marketing|available for purchase|opens? bidding|seeks? bids?)\b",
            re.IGNORECASE,
        ),
        "planning": re.compile(
            r"\b(files? to|plans? to|intends? to|expects? to)\b",
            re.IGNORECASE,
        ),
        "evaluation": re.compile(
            r"\b(exploring options?|considering|evaluating|reviewing)\b",
            re.IGNORECASE,
        ),
    }

    # Financial services transaction type patterns
    FINANCIAL_SERVICES_PATTERNS = {
        "loan_sales": re.compile(
            r"\b(sale of (?:re)?performing loans?|loan portfolio|mortgage-backed securities|mbs)\b",
            re.IGNORECASE,
        ),
        "buyback": re.compile(
            r"\b(buyback|repurchase program|share repurchase)\b",
            re.IGNORECASE,
        ),
        "dividend": re.compile(
            r"\b(dividend payment|dividend)\b",
            re.IGNORECASE,
        ),
        "refinancing": re.compile(
            r"\b(refinancing|bond issuance|debt offering)\b",
            re.IGNORECASE,
        ),
    }

    # Frequency indicator patterns
    FREQUENCY_PATTERNS = {
        "recurrence": re.compile(
            r"\b(most recent|latest|another|continues?)\b",
            re.IGNORECASE,
        ),
        "schedule": re.compile(
            r"\b(quarterly|annual|regular|ongoing)\b",
            re.IGNORECASE,
        ),
        "program": re.compile(
            r"\b(as part of|in line with|pursuant to)\b",
            re.IGNORECASE,
        ),
    }

    # Override patterns
    SUPERLATIVE_PATTERN = re.compile(
        r"\b(record|largest|unprecedented|historic|biggest|highest|never before)\b",
        re.IGNORECASE,
    )

    COMPLETION_PATTERN = re.compile(
        r"\b(completes?|announces? completion|closes?)\b",
        re.IGNORECASE,
    )

    SPECIAL_KEYWORD_PATTERN = re.compile(
        r"\bspecial\b",
        re.IGNORECASE,
    )

    # Process stage detection patterns
    EARLY_STAGE_PATTERN = re.compile(
        r"\b(begins?|starts?|initiates?)\b",
        re.IGNORECASE,
    )

    ONGOING_STAGE_PATTERN = re.compile(
        r"\b(continues?|ongoing)\b",
        re.IGNORECASE,
    )

    COMPLETED_STAGE_PATTERN = re.compile(
        r"\b(completes?|announces? completion|closes?)\b",
        re.IGNORECASE,
    )

    def detect(self, headline: Optional[str]) -> RoutineDetectionResult:
        """Detect routine business operations in a headline.

        Args:
            headline: News article headline to analyze

        Returns:
            RoutineDetectionResult with scores, patterns, and final classification
        """
        # Handle None/empty input
        if not headline:
            return RoutineDetectionResult(
                routine_score=0,
                confidence=0.5,
                detected_patterns=[],
                transaction_value=None,
                process_stage="unknown",
                result=False,
            )

        # Initialize scoring
        routine_score = 0
        detected_patterns = []

        # Detect process language
        process_score = self._detect_process_language(headline)
        if process_score > 0:
            routine_score += process_score
            detected_patterns.append("process_language")

        # Detect routine transaction types
        if self._detect_routine_transaction(headline):
            routine_score += 1
            detected_patterns.append("routine_transaction")

        # Detect frequency indicators
        frequency_score = self._detect_frequency_indicators(headline)
        if frequency_score > 0:
            routine_score += frequency_score
            detected_patterns.append("frequency_indicator")

        # Extract transaction value
        transaction_value = self._extract_dollar_amount(headline)

        # Detect process stage
        process_stage = self._detect_process_stage(headline)

        # Calculate confidence
        confidence = self._calculate_confidence(routine_score, headline)

        # Final decision with explicit overrides
        result = self._make_final_decision(routine_score, headline)

        return RoutineDetectionResult(
            routine_score=routine_score,
            confidence=confidence,
            detected_patterns=detected_patterns,
            transaction_value=transaction_value,
            process_stage=process_stage,
            result=result,
        )

    def _detect_process_language(self, text: str) -> int:
        """Detect process language patterns.

        Returns:
            Score contribution (0-2)
        """
        score = 0

        # Check initiation patterns (strong indicator, +2)
        if self.PROCESS_LANGUAGE_PATTERNS["initiation"].search(text):
            score = max(score, 2)

        # Check marketing patterns (+1)
        if self.PROCESS_LANGUAGE_PATTERNS["marketing"].search(text):
            score = max(score, 1)

        # Check planning patterns (+1)
        if self.PROCESS_LANGUAGE_PATTERNS["planning"].search(text):
            score = max(score, 1)

        # Check evaluation patterns (+1)
        if self.PROCESS_LANGUAGE_PATTERNS["evaluation"].search(text):
            score = max(score, 1)

        return score

    def _detect_routine_transaction(self, text: str) -> bool:
        """Detect routine transaction type patterns.

        Returns:
            True if routine transaction type detected
        """
        for pattern in self.FINANCIAL_SERVICES_PATTERNS.values():
            if pattern.search(text):
                return True
        return False

    def _detect_frequency_indicators(self, text: str) -> int:
        """Detect frequency indicator patterns.

        Returns:
            Score contribution (0-2)
        """
        matches = 0

        for pattern in self.FREQUENCY_PATTERNS.values():
            if pattern.search(text):
                matches += 1

        # Multiple indicators compound the score
        return min(matches, 2)

    def _extract_dollar_amount(self, text: str) -> Optional[float]:
        """Extract dollar amount from text.

        Supports formats:
        - $560M, $1.5B
        - $500 million, $2.3 billion
        - €100M (euro symbol)
        - "Between $50M and $100M" (returns midpoint)

        Returns:
            Amount in dollars or None if not found
        """
        # Pattern for ranges: "between $X and $Y"
        range_pattern = re.compile(
            r"between\s+[\$€](\d+(?:\.\d+)?)\s*([MB])\s+and\s+[\$€](\d+(?:\.\d+)?)\s*([MB])",
            re.IGNORECASE,
        )
        range_match = range_pattern.search(text)
        if range_match:
            val1 = float(range_match.group(1))
            unit1 = range_match.group(2).upper()
            val2 = float(range_match.group(3))
            unit2 = range_match.group(4).upper()

            mult1 = 1_000_000 if unit1 == "M" else 1_000_000_000
            mult2 = 1_000_000 if unit2 == "M" else 1_000_000_000

            return (val1 * mult1 + val2 * mult2) / 2

        # Pattern for single amounts with abbreviation: $560M, $1.5B, €100M
        abbr_pattern = re.compile(
            r"[\$€](\d+(?:\.\d+)?)\s*([MB])\b",
            re.IGNORECASE,
        )
        abbr_match = abbr_pattern.search(text)
        if abbr_match:
            value = float(abbr_match.group(1))
            unit = abbr_match.group(2).upper()
            multiplier = 1_000_000 if unit == "M" else 1_000_000_000
            return value * multiplier

        # Pattern for amounts with words: $500 million, $2.3 billion
        word_pattern = re.compile(
            r"[\$€](\d+(?:\.\d+)?)\s+(million|billion)\b",
            re.IGNORECASE,
        )
        word_match = word_pattern.search(text)
        if word_match:
            value = float(word_match.group(1))
            unit = word_match.group(2).lower()
            multiplier = 1_000_000 if unit == "million" else 1_000_000_000
            return value * multiplier

        return None

    def _detect_process_stage(self, text: str) -> str:
        """Detect process stage from keywords.

        Returns:
            "early", "ongoing", "completed", or "unknown"
        """
        if self.EARLY_STAGE_PATTERN.search(text):
            return "early"
        if self.ONGOING_STAGE_PATTERN.search(text):
            return "ongoing"
        if self.COMPLETED_STAGE_PATTERN.search(text):
            return "completed"
        return "unknown"

    def _calculate_confidence(
        self, routine_score: int, headline: str
    ) -> float:
        """Calculate confidence in routine operation detection.

        Base confidence: 0.5

        Factors that increase confidence:
        - Strong pattern matches (routine_score >= 3): +0.2
        - Clear materiality (materiality_score <= -2): +0.2 (Phase 2)
        - Company context available: +0.15 (Phase 2)

        Factors that decrease confidence:
        - Conflicting signals (superlatives + routine patterns): -0.3

        Returns:
            Confidence clamped to [0.0, 1.0]
        """
        confidence = 0.5

        # Strong pattern boost
        if routine_score >= 3:
            confidence += 0.2

        # Conflicting signals penalty
        if self.SUPERLATIVE_PATTERN.search(headline):
            confidence -= 0.3

        # Clamp to valid range
        return max(0.0, min(1.0, confidence))

    def _make_final_decision(
        self, routine_score: int, headline: str
    ) -> bool:
        """Make final routine operation classification decision.

        Base threshold rule:
        - routine_score >= 2 AND materiality_score <= -1 -> routine

        Explicit overrides (priority order):
        - Superlatives -> NOT routine
        - Completion keywords -> NOT routine
        - Special keywords -> NOT routine

        Args:
            routine_score: Aggregated pattern match score
            headline: Headline text for override checks

        Returns:
            True if routine operation, False otherwise
        """
        # Check explicit overrides first
        if self.SUPERLATIVE_PATTERN.search(headline):
            return False

        if self.COMPLETION_PATTERN.search(headline):
            return False

        if self.SPECIAL_KEYWORD_PATTERN.search(headline):
            return False

        # Base threshold rule (Phase 1 without materiality)
        # In Phase 1, we only have routine_score
        # Phase 2 will add materiality_score condition
        if routine_score >= 2:
            return True

        return False

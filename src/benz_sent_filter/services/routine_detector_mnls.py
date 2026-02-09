"""Routine business operations detector using MNLS zero-shot classification.

This module provides an MNLS-based RoutineOperationDetector that uses
zero-shot NLI classification to identify routine business operations
combined with materiality assessment.
"""

import re
import time
from dataclasses import dataclass
from typing import Optional

from loguru import logger
from pydantic import BaseModel
from transformers import pipeline


@dataclass
class CompanyContext:
    """Company financial context for materiality assessment.

    Attributes:
        market_cap: Market capitalization in USD
        annual_revenue: Annual revenue in USD
        total_assets: Total assets in USD
    """

    market_cap: float
    annual_revenue: float
    total_assets: float


class RoutineDetectionResult(BaseModel):
    """Result model for routine operation detection.

    Fields:
        routine_score: MNLS confidence score (renamed for compatibility)
        confidence: Same as routine_score (for API compatibility)
        detected_patterns: Always ["mnls_classification"]
        transaction_value: Extracted dollar amount or None
        process_stage: Detected from keywords
        result: Final routine operation classification
        materiality_score: Materiality assessment score
        materiality_ratio: Transaction / company metric ratio
    """

    routine_score: float  # MNLS score (0.0-1.0)
    confidence: float  # Same as routine_score
    detected_patterns: list[str]
    transaction_value: Optional[float] = None
    process_stage: str
    result: bool
    materiality_score: Optional[int] = None
    materiality_ratio: Optional[float] = None


class RoutineOperationDetectorMNLS:
    """MNLS-based detector for routine business operations.

    Uses zero-shot classification to answer: "Is this a routine business
    operation or a material business event?"

    Combines MNLS semantic understanding with materiality assessment
    based on transaction size relative to company metrics.
    """

    # Materiality thresholds
    IMMATERIAL_THRESHOLD_MARKET_CAP = 0.01  # 1% of market cap
    ROUTINE_THRESHOLD_REVENUE = 0.05  # 5% of revenue
    ROUTINE_THRESHOLD_ASSETS = 0.005  # 0.5% of assets (for financials)

    # MNLS candidate labels (materiality from investor perspective)
    # Tuned to distinguish between material events and routine business operations
    # Material: ONE-TIME transformational corporate events (strategic deals, partnerships, major milestones)
    # Routine: RECURRING predictable activities (quarterly dividends, regular filings, standard operations)
    # Key distinction: Emphasize "happens once" vs "happens every quarter/year"
    ROUTINE_LABELS = [
        "This announces a major one-time business transaction or milestone like selling company assets, acquiring another business, winning government contracts or being selected for military programs, announcing significant clinical trial successes with complete responses or positive outcomes, securing gigawatt-scale energy deployment deals, raising significant capital, or completing multi-billion dollar transactions",
        "This announces a recurring scheduled event that happens every quarter or every year like quarterly dividend payments, annual shareholder meetings, regular earnings reports, or routine SEC compliance filings",
    ]

    # Company context dictionary (same as pattern-based version)
    COMPANY_CONTEXT = {
        "FNMA": CompanyContext(
            market_cap=4_000_000_000,
            annual_revenue=25_000_000_000,
            total_assets=4_000_000_000_000,
        ),
        "BAC": CompanyContext(
            market_cap=300_000_000_000,
            annual_revenue=100_000_000_000,
            total_assets=3_000_000_000_000,
        ),
        "JPM": CompanyContext(
            market_cap=450_000_000_000,
            annual_revenue=150_000_000_000,
            total_assets=3_800_000_000_000,
        ),
        "WFC": CompanyContext(
            market_cap=180_000_000_000,
            annual_revenue=85_000_000_000,
            total_assets=1_900_000_000_000,
        ),
        "C": CompanyContext(
            market_cap=100_000_000_000,
            annual_revenue=75_000_000_000,
            total_assets=2_400_000_000_000,
        ),
        "GS": CompanyContext(
            market_cap=110_000_000_000,
            annual_revenue=48_000_000_000,
            total_assets=1_600_000_000_000,
        ),
        "MS": CompanyContext(
            market_cap=150_000_000_000,
            annual_revenue=54_000_000_000,
            total_assets=1_200_000_000_000,
        ),
        "USB": CompanyContext(
            market_cap=75_000_000_000,
            annual_revenue=24_000_000_000,
            total_assets=650_000_000_000,
        ),
        "PNC": CompanyContext(
            market_cap=65_000_000_000,
            annual_revenue=20_000_000_000,
            total_assets=560_000_000_000,
        ),
        "TFC": CompanyContext(
            market_cap=55_000_000_000,
            annual_revenue=18_000_000_000,
            total_assets=530_000_000_000,
        ),
        "BK": CompanyContext(
            market_cap=45_000_000_000,
            annual_revenue=16_000_000_000,
            total_assets=430_000_000_000,
        ),
        "STT": CompanyContext(
            market_cap=28_000_000_000,
            annual_revenue=12_000_000_000,
            total_assets=300_000_000_000,
        ),
        "COF": CompanyContext(
            market_cap=55_000_000_000,
            annual_revenue=32_000_000_000,
            total_assets=470_000_000_000,
        ),
        "AXP": CompanyContext(
            market_cap=150_000_000_000,
            annual_revenue=52_000_000_000,
            total_assets=240_000_000_000,
        ),
        "SCHW": CompanyContext(
            market_cap=120_000_000_000,
            annual_revenue=20_000_000_000,
            total_assets=460_000_000_000,
        ),
        "BLK": CompanyContext(
            market_cap=130_000_000_000,
            annual_revenue=19_000_000_000,
            total_assets=180_000_000_000,
        ),
        "FHLMC": CompanyContext(
            market_cap=3_500_000_000,
            annual_revenue=22_000_000_000,
            total_assets=3_200_000_000_000,
        ),
        "AIG": CompanyContext(
            market_cap=48_000_000_000,
            annual_revenue=50_000_000_000,
            total_assets=580_000_000_000,
        ),
        "PRU": CompanyContext(
            market_cap=38_000_000_000,
            annual_revenue=58_000_000_000,
            total_assets=900_000_000_000,
        ),
        "MET": CompanyContext(
            market_cap=50_000_000_000,
            annual_revenue=68_000_000_000,
            total_assets=750_000_000_000,
        ),
        "ALL": CompanyContext(
            market_cap=40_000_000_000,
            annual_revenue=52_000_000_000,
            total_assets=130_000_000_000,
        ),
    }

    # Process stage patterns (keep for metadata)
    EARLY_STAGE_PATTERN = re.compile(
        r"\b(begins?|starts?|initiates?|launches?|files?\s+to|announces?\s+plans?)\b",
        re.IGNORECASE,
    )
    ONGOING_STAGE_PATTERN = re.compile(
        r"\b(continues?|ongoing|pursuing|proceeding with)\b",
        re.IGNORECASE,
    )
    COMPLETED_STAGE_PATTERN = re.compile(
        r"\b(completes?|completed|closes?|closed|finalizes?|finalized)\b",
        re.IGNORECASE,
    )

    def __init__(self, model_name: str = "MoritzLaurer/deberta-v3-large-zeroshot-v2.0"):
        """Initialize the MNLS-based routine operation detector.

        Args:
            model_name: HuggingFace model name for zero-shot classification
        """
        self._pipeline = pipeline("zero-shot-classification", model=model_name)

    def detect(
        self, headline: Optional[str], company_symbol: Optional[str] = None
    ) -> RoutineDetectionResult:
        """Detect routine business operations using MNLS zero-shot classification.

        Args:
            headline: News article headline to analyze
            company_symbol: Optional company ticker symbol for materiality assessment

        Returns:
            RoutineDetectionResult with MNLS scores and materiality assessment
        """
        logger.debug(
            "Starting routine operation detection",
            headline_length=len(headline) if headline else 0,
            company_symbol=company_symbol,
        )
        start_time = time.time()

        # Handle None/empty input
        if not headline:
            logger.warning("Empty headline provided for routine detection")
            return RoutineDetectionResult(
                routine_score=0.5,
                confidence=0.5,
                detected_patterns=[],
                transaction_value=None,
                process_stage="unknown",
                result=False,
            )

        # Use MNLS to classify routine vs material
        mnls_result = self._pipeline(headline, self.ROUTINE_LABELS)

        # Extract routine score (confidence that it's routine)
        # mnls_result['labels'][0] is the top prediction
        # mnls_result['scores'][0] is the confidence for top prediction
        # ROUTINE_LABELS[0] = "significant strategic corporate event" (material)
        # ROUTINE_LABELS[1] = "routine recurring business activity" (routine)
        if mnls_result["labels"][0] == self.ROUTINE_LABELS[1]:
            # Top prediction is "routine" - use its score
            routine_score = mnls_result["scores"][0]
        else:
            # Top prediction is "material" - use routine score (second score)
            routine_score = mnls_result["scores"][1]

        # Extract transaction value (keep helper from pattern matching)
        transaction_value = self._extract_dollar_amount(headline)

        # Detect process stage (keep helper for metadata)
        process_stage = self._detect_process_stage(headline)

        # Materiality assessment (same logic as pattern-based)
        materiality_score = 0
        materiality_ratio = None

        if company_symbol:
            company_context = self.COMPANY_CONTEXT.get(company_symbol)
            if company_context and transaction_value:
                # Calculate materiality ratio
                if company_context.total_assets > 0:
                    materiality_ratio = transaction_value / company_context.total_assets
                    metric_type = "assets"
                elif company_context.annual_revenue > 0:
                    materiality_ratio = transaction_value / company_context.annual_revenue
                    metric_type = "revenue"
                elif company_context.market_cap > 0:
                    materiality_ratio = transaction_value / company_context.market_cap
                    metric_type = "market_cap"

                # Score materiality
                if materiality_ratio is not None:
                    if materiality_ratio < 0.005:  # < 0.5%
                        materiality_score = -2
                    elif materiality_ratio < 0.05:  # < 5%
                        materiality_score = -1
                    else:
                        materiality_score = 0

        # Final decision: combine MNLS score with materiality
        # Priority order:
        # 1. Strong immateriality evidence (materiality_score <= -2) → routine
        # 2. MNLS score > 0.5 → routine
        # 3. Otherwise → material
        result = False
        if materiality_score <= -2:
            # Very immaterial transaction - definitely routine regardless of MNLI
            result = True
        elif routine_score > 0.5:
            # MNLI says routine
            result = True

        duration = time.time() - start_time
        logger.info(
            "Routine operation detection completed",
            is_routine=result,
            routine_score=round(routine_score, 3),
            has_transaction_value=transaction_value is not None,
            transaction_value=transaction_value,
            process_stage=process_stage,
            materiality_score=materiality_score,
            company_symbol=company_symbol,
            duration_ms=round(duration * 1000, 2),
        )

        return RoutineDetectionResult(
            routine_score=routine_score,
            confidence=routine_score,
            detected_patterns=["mnls_classification"],
            transaction_value=transaction_value,
            process_stage=process_stage,
            result=result,
            materiality_score=materiality_score if company_symbol else None,
            materiality_ratio=materiality_ratio,
        )

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

"""Classification service using zero-shot NLI."""

from collections import namedtuple

from transformers import pipeline

from benz_sent_filter.config.settings import (
    CLASSIFICATION_THRESHOLD,
    COMPANY_RELEVANCE_THRESHOLD,
    MODEL_NAME,
)
from benz_sent_filter.models.classification import (
    ClassificationResult,
    ClassificationScores,
    QuantitativeCatalystResult,
    StrategicCatalystResult,
    TemporalCategory,
)
from benz_sent_filter.services import forecast_analyzer
from benz_sent_filter.services.quantitative_catalyst_detector_mnls import (
    QuantitativeCatalystDetectorMNLS,
)
from benz_sent_filter.services.routine_detector_mnls import RoutineOperationDetectorMNLS
from benz_sent_filter.services.strategic_catalyst_detector_mnls import (
    StrategicCatalystDetectorMNLS,
)

# Named tuple for structured company relevance results
CompanyRelevance = namedtuple("CompanyRelevance", ["is_relevant", "score"])


class ClassificationService:
    """Service for classifying headlines using zero-shot NLI.

    Loads DistilBERT-MNLI model at initialization and provides methods
    for single and batch headline classification.
    """

    # All candidate labels in one list (maintains order for score extraction)
    CANDIDATE_LABELS = [
        "This is an opinion piece or editorial",  # index 0 - opinion
        "This is a factual news report",  # index 1 - news
        "This is about a past event that already happened",  # index 2 - past
        "This is about a future event or forecast",  # index 3 - future
        "This is a general topic or analysis",  # index 4 - general
    ]

    # Company relevance hypothesis template
    COMPANY_HYPOTHESIS_TEMPLATE = "This article is about {company}"

    def __init__(self):
        """Initialize the classification service and load the NLI model.

        Raises:
            RuntimeError: If model fails to load
        """
        self._pipeline = pipeline("zero-shot-classification", model=MODEL_NAME)
        self._routine_detector = RoutineOperationDetectorMNLS()
        # Share pipeline with quantitative catalyst detector to avoid loading BART-MNLI separately
        self._catalyst_detector = QuantitativeCatalystDetectorMNLS(pipeline=self._pipeline)
        # Share pipeline with strategic catalyst detector
        self._strategic_catalyst_detector = StrategicCatalystDetectorMNLS(pipeline=self._pipeline)

    def _check_company_relevance(
        self, headline: str, company: str
    ) -> CompanyRelevance:
        """Check if headline is about the specified company.

        Args:
            headline: Headline text to check
            company: Company name to check relevance for

        Returns:
            CompanyRelevance namedtuple with is_relevant (bool) and score (float)
        """
        hypothesis = self.COMPANY_HYPOTHESIS_TEMPLATE.format(company=company)
        result = self._pipeline(headline, candidate_labels=[hypothesis])
        score = result["scores"][0]
        is_relevant = score >= COMPANY_RELEVANCE_THRESHOLD
        return CompanyRelevance(is_relevant=is_relevant, score=score)

    def _analyze_far_future(
        self, headline: str, temporal_category: TemporalCategory
    ) -> dict:
        """Analyze if headline contains far-future forecast patterns.

        Only performs analysis for FUTURE_EVENT classifications. Returns
        dictionary with far_future_forecast and forecast_timeframe keys.

        Args:
            headline: Headline text to analyze
            temporal_category: Temporal category from classification

        Returns:
            Dict with far_future_forecast (bool | None) and forecast_timeframe (str | None)
        """
        # Only analyze far-future for FUTURE_EVENT classifications
        if temporal_category != TemporalCategory.FUTURE_EVENT:
            return {"far_future_forecast": None, "forecast_timeframe": None}

        # Check for far-future patterns
        is_far_future, timeframe = forecast_analyzer.is_far_future(headline)

        if is_far_future:
            return {"far_future_forecast": True, "forecast_timeframe": timeframe}
        else:
            return {"far_future_forecast": None, "forecast_timeframe": None}

    def _analyze_conditional_language(
        self, headline: str, temporal_category: TemporalCategory
    ) -> dict:
        """Analyze if headline contains conditional or hedging language patterns.

        Only performs analysis for FUTURE_EVENT classifications. Returns
        dictionary with conditional_language and conditional_patterns keys.

        Args:
            headline: Headline text to analyze
            temporal_category: Temporal category from classification

        Returns:
            Dict with conditional_language (bool | None) and conditional_patterns (list[str] | None)
        """
        # Only analyze conditional language for FUTURE_EVENT classifications
        if temporal_category != TemporalCategory.FUTURE_EVENT:
            return {"conditional_language": None, "conditional_patterns": None}

        # Check for conditional language patterns
        has_conditional, patterns = forecast_analyzer.matches_conditional_language(headline)

        if has_conditional:
            return {"conditional_language": True, "conditional_patterns": patterns}
        else:
            return {"conditional_language": None, "conditional_patterns": None}

    def _analyze_routine_operation(
        self, headline: str, company_symbol: str | None = None
    ) -> dict:
        """Analyze if headline describes a routine business operation.

        Args:
            headline: Headline text to analyze
            company_symbol: Optional company ticker symbol for materiality assessment

        Returns:
            Dict with routine_operation, routine_confidence, and routine_metadata keys
        """
        # Detect routine operations
        detection_result = self._routine_detector.detect(
            headline, company_symbol=company_symbol
        )

        # Build metadata dict from detection result
        metadata = {
            "routine_score": detection_result.routine_score,
            "detected_patterns": detection_result.detected_patterns,
            "transaction_value": detection_result.transaction_value,
            "process_stage": detection_result.process_stage,
        }

        # Add materiality fields if available
        if detection_result.materiality_score is not None:
            metadata["materiality_score"] = detection_result.materiality_score
        if detection_result.materiality_ratio is not None:
            metadata["materiality_ratio"] = detection_result.materiality_ratio

        return {
            "routine_operation": detection_result.result,
            "routine_confidence": detection_result.confidence,
            "routine_metadata": metadata,
        }

    def classify_headline(
        self, headline: str, company: str | None = None
    ) -> ClassificationResult:
        """Classify a single headline.

        Args:
            headline: Headline text to classify
            company: Optional company name to check relevance

        Returns:
            ClassificationResult with boolean flags, scores, and temporal category

        Raises:
            RuntimeError: If inference fails
        """
        # Make one pipeline call with all 5 candidate labels
        result = self._pipeline(headline, candidate_labels=self.CANDIDATE_LABELS)

        # Extract scores by index (same order as CANDIDATE_LABELS)
        scores = result["scores"]
        opinion_score = scores[0]
        news_score = scores[1]
        past_score = scores[2]
        future_score = scores[3]
        general_score = scores[4]

        # Apply threshold to opinion/news scores for boolean flags
        is_opinion = opinion_score >= CLASSIFICATION_THRESHOLD
        is_straight_news = news_score >= CLASSIFICATION_THRESHOLD

        # Determine temporal category from highest temporal score
        temporal_scores = [
            (past_score, TemporalCategory.PAST_EVENT),
            (future_score, TemporalCategory.FUTURE_EVENT),
            (general_score, TemporalCategory.GENERAL_TOPIC),
        ]
        _, temporal_category = max(temporal_scores, key=lambda x: x[0])

        # Build structured result
        classification_scores = ClassificationScores(
            opinion_score=opinion_score,
            news_score=news_score,
            past_score=past_score,
            future_score=future_score,
            general_score=general_score,
        )

        # Analyze far-future patterns
        far_future_metadata = self._analyze_far_future(headline, temporal_category)

        # Analyze conditional language patterns
        conditional_metadata = self._analyze_conditional_language(headline, temporal_category)

        # Check company relevance if company provided
        if company is not None:
            relevance = self._check_company_relevance(headline, company)
            return ClassificationResult(
                is_opinion=is_opinion,
                is_straight_news=is_straight_news,
                temporal_category=temporal_category,
                scores=classification_scores,
                headline=headline,
                is_about_company=relevance.is_relevant,
                company_score=relevance.score,
                company=company,
                far_future_forecast=far_future_metadata["far_future_forecast"],
                forecast_timeframe=far_future_metadata["forecast_timeframe"],
                conditional_language=conditional_metadata["conditional_language"],
                conditional_patterns=conditional_metadata["conditional_patterns"],
            )
        else:
            return ClassificationResult(
                is_opinion=is_opinion,
                is_straight_news=is_straight_news,
                temporal_category=temporal_category,
                scores=classification_scores,
                headline=headline,
                far_future_forecast=far_future_metadata["far_future_forecast"],
                forecast_timeframe=far_future_metadata["forecast_timeframe"],
                conditional_language=conditional_metadata["conditional_language"],
                conditional_patterns=conditional_metadata["conditional_patterns"],
            )

    def classify_headline_multi_ticker(
        self, headline: str, ticker_symbols: list[str]
    ) -> dict:
        """Classify a headline once, then analyze routine operations for multiple tickers.

        This method optimizes multi-ticker routine operations queries by:
        - Running core MNLS classification once
        - Analyzing routine operations separately for each ticker
        - Avoiding redundant model inference

        Args:
            headline: Headline text to classify
            ticker_symbols: List of ticker symbols to analyze routine operations for

        Returns:
            Dict with structure:
            {
                "core_classification": {
                    "is_opinion": bool,
                    "is_straight_news": bool,
                    "temporal_category": str,
                    "scores": {
                        "opinion_score": float,
                        "news_score": float,
                        "past_score": float,
                        "future_score": float,
                        "general_score": float
                    }
                },
                "routine_operations_by_ticker": {
                    "SYMBOL1": {
                        "routine_operation": bool,
                        "routine_confidence": float,
                        "routine_metadata": dict
                    },
                    ...
                }
            }
        """
        # Perform core classification once
        result = self._pipeline(headline, candidate_labels=self.CANDIDATE_LABELS)

        # Extract scores by index
        scores = result["scores"]
        opinion_score = scores[0]
        news_score = scores[1]
        past_score = scores[2]
        future_score = scores[3]
        general_score = scores[4]

        # Apply threshold to opinion/news scores
        is_opinion = opinion_score >= CLASSIFICATION_THRESHOLD
        is_straight_news = news_score >= CLASSIFICATION_THRESHOLD

        # Determine temporal category from highest temporal score
        temporal_scores = [
            (past_score, TemporalCategory.PAST_EVENT),
            (future_score, TemporalCategory.FUTURE_EVENT),
            (general_score, TemporalCategory.GENERAL_TOPIC),
        ]
        _, temporal_category = max(temporal_scores, key=lambda x: x[0])

        # Build core classification dict
        core_classification = {
            "is_opinion": is_opinion,
            "is_straight_news": is_straight_news,
            "temporal_category": temporal_category.value,
            "scores": {
                "opinion_score": opinion_score,
                "news_score": news_score,
                "past_score": past_score,
                "future_score": future_score,
                "general_score": general_score,
            },
        }

        # Analyze routine operations for each ticker
        routine_operations_by_ticker = {}
        for ticker in ticker_symbols:
            routine_result = self._analyze_routine_operation(headline, company_symbol=ticker)
            routine_operations_by_ticker[ticker] = routine_result

        return {
            "core_classification": core_classification,
            "routine_operations_by_ticker": routine_operations_by_ticker,
        }

    def classify_batch(
        self, headlines: list[str], company: str | None = None
    ) -> list[ClassificationResult]:
        """Classify multiple headlines.

        Uses simple list comprehension for sequential processing.
        No batch optimization - prioritizes simplicity over performance.

        Args:
            headlines: List of headline texts to classify
            company: Optional company name to check relevance for all headlines

        Returns:
            List of ClassificationResult objects in same order as input
        """
        return [
            self.classify_headline(headline, company=company) for headline in headlines
        ]

    def check_company_relevance(self, headline: str, company: str) -> dict:
        """Check if a headline is relevant to a specific company.

        Args:
            headline: Headline text to analyze
            company: Company name to check relevance against

        Returns:
            Dict with headline, company, is_about_company, and company_score
        """
        relevance = self._check_company_relevance(headline, company)

        return {
            "headline": headline,
            "company": company,
            "is_about_company": relevance.is_relevant,
            "company_score": relevance.score,
        }

    def check_company_relevance_batch(self, headlines: list[str], company: str) -> list[dict]:
        """Check company relevance for multiple headlines.

        Args:
            headlines: List of headline texts to analyze
            company: Company name to check relevance against

        Returns:
            List of dicts with relevance results
        """
        return [self.check_company_relevance(headline, company) for headline in headlines]

    def detect_quantitative_catalyst(self, headline: str) -> QuantitativeCatalystResult:
        """Detect quantitative financial catalysts in headline.

        Uses shared MNLI pipeline for efficient inference. Detects presence,
        classifies type (dividend/acquisition/buyback/earnings/guidance), and
        extracts quantitative values.

        Args:
            headline: Headline text to analyze

        Returns:
            QuantitativeCatalystResult with detection details
        """
        return self._catalyst_detector.detect(headline)

    def detect_strategic_catalyst(self, headline: str) -> StrategicCatalystResult:
        """Detect strategic corporate catalysts in headline.

        Uses shared MNLI pipeline for efficient inference. Detects presence
        and classifies type (executive_change/merger_agreement/strategic_partnership/
        product_launch/rebranding/clinical_trial_results).

        Args:
            headline: Headline text to analyze

        Returns:
            StrategicCatalystResult with detection details
        """
        return self._strategic_catalyst_detector.detect(headline)

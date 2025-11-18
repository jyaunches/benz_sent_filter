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
    TemporalCategory,
)
from benz_sent_filter.services import forecast_analyzer
from benz_sent_filter.services.routine_detector_mnls import RoutineOperationDetectorMNLS

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
        self, headline: str, company: str | None = None, company_symbol: str | None = None
    ) -> ClassificationResult:
        """Classify a single headline.

        Args:
            headline: Headline text to classify
            company: Optional company name to check relevance
            company_symbol: Optional company ticker symbol for materiality assessment

        Returns:
            ClassificationResult with boolean flags, scores, temporal category, and routine operation detection

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

        # Analyze routine operations
        routine_metadata = self._analyze_routine_operation(headline, company_symbol)

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
                routine_operation=routine_metadata["routine_operation"],
                routine_confidence=routine_metadata["routine_confidence"],
                routine_metadata=routine_metadata["routine_metadata"],
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
                routine_operation=routine_metadata["routine_operation"],
                routine_confidence=routine_metadata["routine_confidence"],
                routine_metadata=routine_metadata["routine_metadata"],
            )

    def classify_batch(
        self, headlines: list[str], company: str | None = None, company_symbol: str | None = None
    ) -> list[ClassificationResult]:
        """Classify multiple headlines.

        Uses simple list comprehension for sequential processing.
        No batch optimization - prioritizes simplicity over performance.

        Args:
            headlines: List of headline texts to classify
            company: Optional company name to check relevance for all headlines
            company_symbol: Optional company ticker symbol for materiality assessment

        Returns:
            List of ClassificationResult objects in same order as input
        """
        return [
            self.classify_headline(headline, company=company, company_symbol=company_symbol) for headline in headlines
        ]

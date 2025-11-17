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
            )

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

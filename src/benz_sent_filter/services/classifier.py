"""Classification service using zero-shot NLI."""

from transformers import pipeline

from benz_sent_filter.config.settings import CLASSIFICATION_THRESHOLD, MODEL_NAME
from benz_sent_filter.models.classification import (
    ClassificationResult,
    ClassificationScores,
    TemporalCategory,
)


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

    def __init__(self):
        """Initialize the classification service and load the NLI model.

        Raises:
            RuntimeError: If model fails to load
        """
        self._pipeline = pipeline("zero-shot-classification", model=MODEL_NAME)

    def classify_headline(self, headline: str) -> ClassificationResult:
        """Classify a single headline.

        Args:
            headline: Headline text to classify

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

        return ClassificationResult(
            is_opinion=is_opinion,
            is_straight_news=is_straight_news,
            temporal_category=temporal_category,
            scores=classification_scores,
            headline=headline,
        )

    def classify_batch(self, headlines: list[str]) -> list[ClassificationResult]:
        """Classify multiple headlines.

        Uses simple list comprehension for sequential processing.
        No batch optimization - prioritizes simplicity over performance.

        Args:
            headlines: List of headline texts to classify

        Returns:
            List of ClassificationResult objects in same order as input
        """
        return [self.classify_headline(headline) for headline in headlines]

"""Tests for data models."""

import pytest
from pydantic import ValidationError


def test_temporal_category_enum_values():
    """Test TemporalCategory enum has correct members and values."""
    from benz_sent_filter.models.classification import TemporalCategory

    # Test enum has three members with UPPERCASE names
    assert hasattr(TemporalCategory, "PAST_EVENT")
    assert hasattr(TemporalCategory, "FUTURE_EVENT")
    assert hasattr(TemporalCategory, "GENERAL_TOPIC")

    # Test member values are lowercase strings (for API serialization)
    assert TemporalCategory.PAST_EVENT.value == "past_event"
    assert TemporalCategory.FUTURE_EVENT.value == "future_event"
    assert TemporalCategory.GENERAL_TOPIC.value == "general_topic"

    # Test all three members exist
    assert len(TemporalCategory) == 3


def test_classify_request_valid_headline():
    """Test ClassifyRequest validates successfully with valid headline."""
    from benz_sent_filter.models.classification import ClassifyRequest

    request = ClassifyRequest(headline="Valid headline text")
    assert request.headline == "Valid headline text"


def test_classify_request_empty_headline_rejected():
    """Test ClassifyRequest rejects empty headline."""
    from benz_sent_filter.models.classification import ClassifyRequest

    with pytest.raises(ValidationError) as exc_info:
        ClassifyRequest(headline="")

    errors = exc_info.value.errors()
    assert any("headline" in str(error["loc"]) for error in errors)


def test_batch_classify_request_valid():
    """Test BatchClassifyRequest validates successfully with valid headlines."""
    from benz_sent_filter.models.classification import BatchClassifyRequest

    request = BatchClassifyRequest(headlines=["headline1", "headline2"])
    assert len(request.headlines) == 2
    assert request.headlines[0] == "headline1"
    assert request.headlines[1] == "headline2"


def test_batch_classify_request_empty_list_rejected():
    """Test BatchClassifyRequest rejects empty headlines list."""
    from benz_sent_filter.models.classification import BatchClassifyRequest

    with pytest.raises(ValidationError) as exc_info:
        BatchClassifyRequest(headlines=[])

    errors = exc_info.value.errors()
    assert any("headlines" in str(error["loc"]) for error in errors)


def test_classification_scores_all_fields():
    """Test ClassificationScores has all required score fields."""
    from benz_sent_filter.models.classification import ClassificationScores

    scores = ClassificationScores(
        opinion_score=0.8,
        news_score=0.2,
        past_score=0.1,
        future_score=0.7,
        general_score=0.2,
    )

    assert isinstance(scores.opinion_score, float)
    assert isinstance(scores.news_score, float)
    assert isinstance(scores.past_score, float)
    assert isinstance(scores.future_score, float)
    assert isinstance(scores.general_score, float)

    assert scores.opinion_score == 0.8
    assert scores.news_score == 0.2
    assert scores.past_score == 0.1
    assert scores.future_score == 0.7
    assert scores.general_score == 0.2


def test_classification_result_structure():
    """Test ClassificationResult has all required fields with correct types."""
    from benz_sent_filter.models.classification import (
        ClassificationResult,
        ClassificationScores,
        TemporalCategory,
    )

    scores = ClassificationScores(
        opinion_score=0.8,
        news_score=0.2,
        past_score=0.1,
        future_score=0.7,
        general_score=0.2,
    )

    result = ClassificationResult(
        is_opinion=True,
        is_straight_news=False,
        temporal_category=TemporalCategory.FUTURE_EVENT,
        scores=scores,
        headline="Test headline",
    )

    assert isinstance(result.is_opinion, bool)
    assert isinstance(result.is_straight_news, bool)
    assert isinstance(result.temporal_category, TemporalCategory)
    assert isinstance(result.scores, ClassificationScores)
    assert isinstance(result.headline, str)

    assert result.is_opinion is True
    assert result.is_straight_news is False
    assert result.temporal_category == TemporalCategory.FUTURE_EVENT
    assert result.headline == "Test headline"


def test_batch_classification_result_structure():
    """Test BatchClassificationResult contains list of ClassificationResult objects."""
    from benz_sent_filter.models.classification import (
        BatchClassificationResult,
        ClassificationResult,
        ClassificationScores,
        TemporalCategory,
    )

    scores = ClassificationScores(
        opinion_score=0.8,
        news_score=0.2,
        past_score=0.1,
        future_score=0.7,
        general_score=0.2,
    )

    result1 = ClassificationResult(
        is_opinion=True,
        is_straight_news=False,
        temporal_category=TemporalCategory.FUTURE_EVENT,
        scores=scores,
        headline="Headline 1",
    )

    result2 = ClassificationResult(
        is_opinion=False,
        is_straight_news=True,
        temporal_category=TemporalCategory.PAST_EVENT,
        scores=scores,
        headline="Headline 2",
    )

    batch_result = BatchClassificationResult(results=[result1, result2])

    assert isinstance(batch_result.results, list)
    assert len(batch_result.results) == 2
    assert all(isinstance(r, ClassificationResult) for r in batch_result.results)
    assert batch_result.results[0].headline == "Headline 1"
    assert batch_result.results[1].headline == "Headline 2"

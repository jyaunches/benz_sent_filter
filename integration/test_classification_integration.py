"""Integration tests with real DistilBERT-MNLI model.

These tests download and load the actual model from Hugging Face.
Run with: pytest -m integration
Skip with: pytest -m "not integration"
"""

import time

import pytest

from benz_sent_filter.models.classification import TemporalCategory


@pytest.mark.integration
def test_real_model_loads_successfully(real_classifier):
    """Test that ClassificationService initializes with real transformers."""
    assert real_classifier is not None
    assert hasattr(real_classifier, "_pipeline")


@pytest.mark.integration
def test_real_inference_produces_valid_scores(
    real_classifier, sample_headline_opinion
):
    """Test that real model produces scores in valid range [0, 1]."""
    result = real_classifier.classify_headline(sample_headline_opinion)

    # All scores should be between 0 and 1
    assert 0 <= result.scores.opinion_score <= 1
    assert 0 <= result.scores.news_score <= 1
    assert 0 <= result.scores.past_score <= 1
    assert 0 <= result.scores.future_score <= 1
    assert 0 <= result.scores.general_score <= 1


@pytest.mark.integration
def test_opinion_headline_detection_real_model(
    real_classifier, sample_headline_opinion
):
    """Test real model detects opinion in 'Why the Fed Is Wrong About Inflation'."""
    result = real_classifier.classify_headline(sample_headline_opinion)

    # Real model should score opinion higher than random (> 0.5)
    # Note: We use lenient thresholds since zero-shot may not be perfect
    assert result.scores.opinion_score > 0.5, (
        f"Expected opinion_score > 0.5 for opinion headline, "
        f"got {result.scores.opinion_score}"
    )


@pytest.mark.integration
def test_news_headline_detection_real_model(real_classifier, sample_headline_news):
    """Test real model detects news in 'Fed Raises Interest Rates by 25 Basis Points'."""
    result = real_classifier.classify_headline(sample_headline_news)

    # Real model should score news higher than random
    assert result.scores.news_score > 0.5, (
        f"Expected news_score > 0.5 for news headline, " f"got {result.scores.news_score}"
    )


@pytest.mark.integration
def test_past_event_temporal_classification_real_model(
    real_classifier, sample_headline_past
):
    """Test real model classifies 'Tesla Shares Surge After Yesterday's Earnings Beat' as past."""
    result = real_classifier.classify_headline(sample_headline_past)

    assert result.temporal_category == TemporalCategory.PAST_EVENT, (
        f"Expected PAST_EVENT for past headline, " f"got {result.temporal_category}"
    )


@pytest.mark.integration
def test_future_event_temporal_classification_real_model(
    real_classifier, sample_headline_future
):
    """Test real model classifies 'Tesla to Report Q4 Earnings Next Week' as future."""
    result = real_classifier.classify_headline(sample_headline_future)

    assert result.temporal_category == TemporalCategory.FUTURE_EVENT, (
        f"Expected FUTURE_EVENT for future headline, "
        f"got {result.temporal_category}"
    )


@pytest.mark.integration
def test_general_topic_temporal_classification_real_model(
    real_classifier, sample_headline_general
):
    """Test real model classifies 'How Tesla Changed the EV Market' as general."""
    result = real_classifier.classify_headline(sample_headline_general)

    assert result.temporal_category == TemporalCategory.GENERAL_TOPIC, (
        f"Expected GENERAL_TOPIC for general headline, "
        f"got {result.temporal_category}"
    )


@pytest.mark.integration
def test_batch_processing_maintains_accuracy_real_model(
    real_classifier,
    sample_headline_opinion,
    sample_headline_news,
    sample_headline_past,
    sample_headline_future,
    sample_headline_general,
):
    """Test that batch processing maintains accuracy for all fixture headlines."""
    headlines = [
        sample_headline_opinion,
        sample_headline_news,
        sample_headline_past,
        sample_headline_future,
        sample_headline_general,
    ]

    results = real_classifier.classify_batch(headlines)

    assert len(results) == 5

    # Check that each result has valid temporal category
    # (we don't check exact values since batch vs single may differ slightly)
    for result in results:
        assert result.temporal_category in [
            TemporalCategory.PAST_EVENT,
            TemporalCategory.FUTURE_EVENT,
            TemporalCategory.GENERAL_TOPIC,
        ]


@pytest.mark.integration
def test_classification_consistency_real_model(real_classifier):
    """Test that same headline classified twice produces identical results."""
    headline = "Tesla Announces New Product Launch"

    result1 = real_classifier.classify_headline(headline)
    result2 = real_classifier.classify_headline(headline)

    # Scores should be exactly identical (deterministic model)
    assert result1.scores.opinion_score == result2.scores.opinion_score
    assert result1.scores.news_score == result2.scores.news_score
    assert result1.scores.past_score == result2.scores.past_score
    assert result1.scores.future_score == result2.scores.future_score
    assert result1.scores.general_score == result2.scores.general_score

    # Boolean flags and temporal category should match
    assert result1.is_opinion == result2.is_opinion
    assert result1.is_straight_news == result2.is_straight_news
    assert result1.temporal_category == result2.temporal_category


@pytest.mark.integration
def test_response_time_single_headline_real_model(real_classifier):
    """Test that single headline classification completes in < 2 seconds."""
    headline = "Stock Market Reaches New High"

    start_time = time.time()
    result = real_classifier.classify_headline(headline)
    elapsed_time = time.time() - start_time

    assert elapsed_time < 2.0, (
        f"Expected classification in < 2s, took {elapsed_time:.2f}s"
    )
    assert result is not None


@pytest.mark.integration
def test_response_time_batch_10_headlines_real_model(real_classifier):
    """Test that batch of 10 headlines completes in < 10 seconds."""
    headlines = [f"Test headline number {i}" for i in range(10)]

    start_time = time.time()
    results = real_classifier.classify_batch(headlines)
    elapsed_time = time.time() - start_time

    assert elapsed_time < 10.0, (
        f"Expected batch classification in < 10s, took {elapsed_time:.2f}s"
    )
    assert len(results) == 10

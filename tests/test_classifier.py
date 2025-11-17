"""Tests for classification service."""

import pytest


def test_service_initialization_success(mock_transformers_pipeline):
    """Test ClassificationService initializes successfully with mocked pipeline."""
    mock_transformers_pipeline({
        "This is an opinion piece or editorial": 0.5,
        "This is a factual news report": 0.5,
        "This is about a past event that already happened": 0.3,
        "This is about a future event or forecast": 0.3,
        "This is a general topic or analysis": 0.4,
    })

    from benz_sent_filter.services.classifier import ClassificationService

    service = ClassificationService()
    assert service is not None


def test_service_initialization_model_load_failure(monkeypatch):
    """Test ClassificationService raises error when model fails to load."""
    import sys

    # Remove cached module to force reimport with new mock
    if "benz_sent_filter.services.classifier" in sys.modules:
        del sys.modules["benz_sent_filter.services.classifier"]
    if "benz_sent_filter.services" in sys.modules:
        del sys.modules["benz_sent_filter.services"]

    def _mock_pipeline_fail(task, model):
        raise RuntimeError("Model download failed")

    monkeypatch.setattr("transformers.pipeline", _mock_pipeline_fail)

    from benz_sent_filter.services.classifier import ClassificationService

    with pytest.raises(RuntimeError, match="Model download failed"):
        ClassificationService()


def test_classify_headline_opinion_detection(
    mock_transformers_pipeline, sample_headline_opinion
):
    """Test classify_headline detects opinion headlines correctly."""
    import sys

    # Clear module cache to ensure fresh import with current mock
    if "benz_sent_filter.services.classifier" in sys.modules:
        del sys.modules["benz_sent_filter.services.classifier"]

    mock_transformers_pipeline({
        "This is an opinion piece or editorial": 0.75,
        "This is a factual news report": 0.25,
        "This is about a past event that already happened": 0.1,
        "This is about a future event or forecast": 0.1,
        "This is a general topic or analysis": 0.2,
    })

    from benz_sent_filter.services.classifier import ClassificationService

    service = ClassificationService()
    result = service.classify_headline(sample_headline_opinion)

    assert result.is_opinion is True
    assert result.scores.opinion_score == 0.75
    assert result.headline == sample_headline_opinion


def test_classify_headline_news_detection(
    mock_transformers_pipeline, sample_headline_news
):
    """Test classify_headline detects news headlines correctly."""
    import sys

    # Clear module cache to ensure fresh import with current mock
    if "benz_sent_filter.services.classifier" in sys.modules:
        del sys.modules["benz_sent_filter.services.classifier"]

    mock_transformers_pipeline({
        "This is an opinion piece or editorial": 0.2,
        "This is a factual news report": 0.85,
        "This is about a past event that already happened": 0.7,
        "This is about a future event or forecast": 0.1,
        "This is a general topic or analysis": 0.2,
    })

    from benz_sent_filter.services.classifier import ClassificationService

    service = ClassificationService()
    result = service.classify_headline(sample_headline_news)

    assert result.is_straight_news is True
    assert result.scores.news_score == 0.85
    assert result.headline == sample_headline_news


def test_classify_headline_threshold_boundary_below(mock_transformers_pipeline):
    """Test threshold logic: score 0.59 results in False."""
    import sys

    # Clear module cache to ensure fresh import with current mock
    if "benz_sent_filter.services.classifier" in sys.modules:
        del sys.modules["benz_sent_filter.services.classifier"]

    mock_transformers_pipeline({
        "This is an opinion piece or editorial": 0.59,
        "This is a factual news report": 0.41,
        "This is about a past event that already happened": 0.3,
        "This is about a future event or forecast": 0.3,
        "This is a general topic or analysis": 0.4,
    })

    from benz_sent_filter.services.classifier import ClassificationService

    service = ClassificationService()
    result = service.classify_headline("Test headline")

    assert result.is_opinion is False  # 0.59 < 0.6
    assert result.scores.opinion_score == 0.59


def test_classify_headline_threshold_boundary_at(mock_transformers_pipeline):
    """Test threshold logic: score 0.60 results in True."""
    import sys

    # Clear module cache to ensure fresh import with current mock
    if "benz_sent_filter.services.classifier" in sys.modules:
        del sys.modules["benz_sent_filter.services.classifier"]

    mock_transformers_pipeline({
        "This is an opinion piece or editorial": 0.60,
        "This is a factual news report": 0.40,
        "This is about a past event that already happened": 0.3,
        "This is about a future event or forecast": 0.3,
        "This is a general topic or analysis": 0.4,
    })

    from benz_sent_filter.services.classifier import ClassificationService

    service = ClassificationService()
    result = service.classify_headline("Test headline")

    assert result.is_opinion is True  # 0.60 >= 0.6
    assert result.scores.opinion_score == 0.60


def test_classify_headline_past_event_temporal(
    mock_transformers_pipeline, sample_headline_past
):
    """Test temporal classification detects past events correctly."""
    import sys

    # Clear module cache to ensure fresh import with current mock
    if "benz_sent_filter.services.classifier" in sys.modules:
        del sys.modules["benz_sent_filter.services.classifier"]

    mock_transformers_pipeline({
        "This is an opinion piece or editorial": 0.2,
        "This is a factual news report": 0.7,
        "This is about a past event that already happened": 0.8,
        "This is about a future event or forecast": 0.1,
        "This is a general topic or analysis": 0.1,
    })

    from benz_sent_filter.models.classification import TemporalCategory
    from benz_sent_filter.services.classifier import ClassificationService

    service = ClassificationService()
    result = service.classify_headline(sample_headline_past)

    assert result.temporal_category == TemporalCategory.PAST_EVENT
    assert result.scores.past_score == 0.8


def test_classify_headline_future_event_temporal(
    mock_transformers_pipeline, sample_headline_future
):
    """Test temporal classification detects future events correctly."""
    import sys

    # Clear module cache to ensure fresh import with current mock
    if "benz_sent_filter.services.classifier" in sys.modules:
        del sys.modules["benz_sent_filter.services.classifier"]

    mock_transformers_pipeline({
        "This is an opinion piece or editorial": 0.2,
        "This is a factual news report": 0.6,
        "This is about a past event that already happened": 0.1,
        "This is about a future event or forecast": 0.75,
        "This is a general topic or analysis": 0.15,
    })

    from benz_sent_filter.models.classification import TemporalCategory
    from benz_sent_filter.services.classifier import ClassificationService

    service = ClassificationService()
    result = service.classify_headline(sample_headline_future)

    assert result.temporal_category == TemporalCategory.FUTURE_EVENT
    assert result.scores.future_score == 0.75


def test_classify_headline_general_topic_temporal(
    mock_transformers_pipeline, sample_headline_general
):
    """Test temporal classification detects general topics correctly."""
    import sys

    # Clear module cache to ensure fresh import with current mock
    if "benz_sent_filter.services.classifier" in sys.modules:
        del sys.modules["benz_sent_filter.services.classifier"]

    mock_transformers_pipeline({
        "This is an opinion piece or editorial": 0.4,
        "This is a factual news report": 0.5,
        "This is about a past event that already happened": 0.2,
        "This is about a future event or forecast": 0.1,
        "This is a general topic or analysis": 0.7,
    })

    from benz_sent_filter.models.classification import TemporalCategory
    from benz_sent_filter.services.classifier import ClassificationService

    service = ClassificationService()
    result = service.classify_headline(sample_headline_general)

    assert result.temporal_category == TemporalCategory.GENERAL_TOPIC
    assert result.scores.general_score == 0.7


def test_classify_headline_all_scores_present(mock_transformers_pipeline):
    """Test that all 5 scores are present in the result."""
    import sys

    # Clear module cache to ensure fresh import with current mock
    if "benz_sent_filter.services.classifier" in sys.modules:
        del sys.modules["benz_sent_filter.services.classifier"]

    mock_transformers_pipeline({
        "This is an opinion piece or editorial": 0.3,
        "This is a factual news report": 0.4,
        "This is about a past event that already happened": 0.2,
        "This is about a future event or forecast": 0.5,
        "This is a general topic or analysis": 0.6,
    })

    from benz_sent_filter.services.classifier import ClassificationService

    service = ClassificationService()
    result = service.classify_headline("Test headline")

    assert result.scores.opinion_score == 0.3
    assert result.scores.news_score == 0.4
    assert result.scores.past_score == 0.2
    assert result.scores.future_score == 0.5
    assert result.scores.general_score == 0.6


def test_classify_headline_original_headline_preserved(mock_transformers_pipeline):
    """Test that the original headline is preserved in the result."""
    test_headline = "Test Headline Text"
    mock_transformers_pipeline({
        "This is an opinion piece or editorial": 0.5,
        "This is a factual news report": 0.5,
        "This is about a past event that already happened": 0.3,
        "This is about a future event or forecast": 0.3,
        "This is a general topic or analysis": 0.4,
    })

    from benz_sent_filter.services.classifier import ClassificationService

    service = ClassificationService()
    result = service.classify_headline(test_headline)

    assert result.headline == test_headline


def test_classify_batch_multiple_headlines(mock_transformers_pipeline):
    """Test batch classification returns correct number of results."""
    import sys

    # Clear module cache to ensure fresh import with current mock
    if "benz_sent_filter.services.classifier" in sys.modules:
        del sys.modules["benz_sent_filter.services.classifier"]

    mock_transformers_pipeline({
        "This is an opinion piece or editorial": 0.5,
        "This is a factual news report": 0.5,
        "This is about a past event that already happened": 0.3,
        "This is about a future event or forecast": 0.3,
        "This is a general topic or analysis": 0.4,
    })

    from benz_sent_filter.services.classifier import ClassificationService

    service = ClassificationService()
    headlines = ["headline1", "headline2", "headline3"]
    results = service.classify_batch(headlines)

    assert len(results) == 3
    assert all(hasattr(r, "is_opinion") for r in results)


def test_classify_batch_maintains_order(mock_transformers_pipeline):
    """Test that batch results maintain input order."""
    import sys

    # Clear module cache to ensure fresh import with current mock
    if "benz_sent_filter.services.classifier" in sys.modules:
        del sys.modules["benz_sent_filter.services.classifier"]

    mock_transformers_pipeline({
        "This is an opinion piece or editorial": 0.5,
        "This is a factual news report": 0.5,
        "This is about a past event that already happened": 0.3,
        "This is about a future event or forecast": 0.3,
        "This is a general topic or analysis": 0.4,
    })

    from benz_sent_filter.services.classifier import ClassificationService

    service = ClassificationService()
    headlines = ["First headline", "Second headline", "Third headline"]
    results = service.classify_batch(headlines)

    assert results[0].headline == "First headline"
    assert results[1].headline == "Second headline"
    assert results[2].headline == "Third headline"


def test_classify_headline_inference_error(monkeypatch):
    """Test that inference errors are properly raised."""
    import sys

    # Remove cached module to force reimport with new mock
    if "benz_sent_filter.services.classifier" in sys.modules:
        del sys.modules["benz_sent_filter.services.classifier"]
    if "benz_sent_filter.services" in sys.modules:
        del sys.modules["benz_sent_filter.services"]

    def _mock_pipeline(task, model):
        def pipeline_fn(text, candidate_labels):
            raise RuntimeError("Inference failed")

        return pipeline_fn

    monkeypatch.setattr("transformers.pipeline", _mock_pipeline)

    from benz_sent_filter.services.classifier import ClassificationService

    service = ClassificationService()

    with pytest.raises(RuntimeError, match="Inference failed"):
        service.classify_headline("Test headline")

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


# Phase 2: Company Relevance Service Logic Tests


def test_check_company_relevance_high_score_above_threshold(
    mock_transformers_pipeline,
):
    """Test company relevance returns namedtuple with is_relevant=True when score above threshold."""
    import sys

    # Clear module cache to ensure fresh import with current mock
    if "benz_sent_filter.services.classifier" in sys.modules:
        del sys.modules["benz_sent_filter.services.classifier"]

    mock_transformers_pipeline({
        "This is an opinion piece or editorial": 0.2,
        "This is a factual news report": 0.7,
        "This is about a past event that already happened": 0.2,
        "This is about a future event or forecast": 0.3,
        "This is a general topic or analysis": 0.5,
        "This article is about Dell": 0.85,
    })

    from benz_sent_filter.services.classifier import ClassificationService

    service = ClassificationService()
    relevance = service._check_company_relevance("Dell Unveils AI Platform", "Dell")

    assert relevance.is_relevant is True
    assert relevance.score == 0.85


def test_check_company_relevance_low_score_below_threshold(
    mock_transformers_pipeline,
):
    """Test company relevance returns namedtuple with is_relevant=False when score below threshold."""
    import sys

    # Clear module cache to ensure fresh import with current mock
    if "benz_sent_filter.services.classifier" in sys.modules:
        del sys.modules["benz_sent_filter.services.classifier"]

    mock_transformers_pipeline({
        "This is an opinion piece or editorial": 0.2,
        "This is a factual news report": 0.7,
        "This is about a past event that already happened": 0.2,
        "This is about a future event or forecast": 0.3,
        "This is a general topic or analysis": 0.5,
        "This article is about Tesla": 0.15,
    })

    from benz_sent_filter.services.classifier import ClassificationService

    service = ClassificationService()
    relevance = service._check_company_relevance("Dell Unveils AI Platform", "Tesla")

    assert relevance.is_relevant is False
    assert relevance.score == 0.15


def test_check_company_relevance_threshold_boundary_at_point_five(
    mock_transformers_pipeline,
):
    """Test company relevance returns is_relevant=True at threshold boundary (0.50)."""
    import sys

    # Clear module cache to ensure fresh import with current mock
    if "benz_sent_filter.services.classifier" in sys.modules:
        del sys.modules["benz_sent_filter.services.classifier"]

    mock_transformers_pipeline({
        "This is an opinion piece or editorial": 0.2,
        "This is a factual news report": 0.7,
        "This is about a past event that already happened": 0.2,
        "This is about a future event or forecast": 0.3,
        "This is a general topic or analysis": 0.5,
        "This article is about Test Company": 0.50,
    })

    from benz_sent_filter.services.classifier import ClassificationService

    service = ClassificationService()
    relevance = service._check_company_relevance("Test headline", "Test Company")

    assert relevance.is_relevant is True  # 0.50 >= COMPANY_RELEVANCE_THRESHOLD (0.5)
    assert relevance.score == 0.50


def test_check_company_relevance_threshold_boundary_below_point_five(
    mock_transformers_pipeline,
):
    """Test company relevance returns is_relevant=False below threshold boundary (0.49)."""
    import sys

    # Clear module cache to ensure fresh import with current mock
    if "benz_sent_filter.services.classifier" in sys.modules:
        del sys.modules["benz_sent_filter.services.classifier"]

    mock_transformers_pipeline({
        "This is an opinion piece or editorial": 0.2,
        "This is a factual news report": 0.7,
        "This is about a past event that already happened": 0.2,
        "This is about a future event or forecast": 0.3,
        "This is a general topic or analysis": 0.5,
        "This article is about Test Company": 0.49,
    })

    from benz_sent_filter.services.classifier import ClassificationService

    service = ClassificationService()
    relevance = service._check_company_relevance("Test headline", "Test Company")

    assert relevance.is_relevant is False  # 0.49 < COMPANY_RELEVANCE_THRESHOLD (0.5)
    assert relevance.score == 0.49


def test_check_company_relevance_uses_correct_hypothesis_template(
    mock_transformers_pipeline, monkeypatch
):
    """Test company relevance uses correct hypothesis template."""
    import sys

    # Clear module cache to ensure fresh import with current mock
    if "benz_sent_filter.services.classifier" in sys.modules:
        del sys.modules["benz_sent_filter.services.classifier"]

    # Track pipeline calls to verify hypothesis
    pipeline_calls = []

    def track_calls_pipeline(task, model):
        def pipeline_fn(text, candidate_labels):
            pipeline_calls.append({"text": text, "labels": candidate_labels})
            scores = [0.85 if "NVIDIA" in label else 0.2 for label in candidate_labels]
            return {"labels": candidate_labels, "scores": scores}

        return pipeline_fn

    monkeypatch.setattr("transformers.pipeline", track_calls_pipeline)

    from benz_sent_filter.services.classifier import ClassificationService

    service = ClassificationService()
    service._check_company_relevance("Test headline", "NVIDIA")

    # Verify that "This article is about NVIDIA" was passed to pipeline
    assert any(
        "This article is about NVIDIA" in call["labels"] for call in pipeline_calls
    )


def test_classify_headline_with_company_includes_relevance_fields(
    mock_transformers_pipeline,
):
    """Test classify_headline includes company relevance fields when company provided."""
    import sys

    # Clear module cache to ensure fresh import with current mock
    if "benz_sent_filter.services.classifier" in sys.modules:
        del sys.modules["benz_sent_filter.services.classifier"]

    mock_transformers_pipeline({
        "This is an opinion piece or editorial": 0.2,
        "This is a factual news report": 0.75,
        "This is about a past event that already happened": 0.7,
        "This is about a future event or forecast": 0.1,
        "This is a general topic or analysis": 0.2,
        "This article is about Dell": 0.85,
    })

    from benz_sent_filter.services.classifier import ClassificationService

    service = ClassificationService()
    result = service.classify_headline("Dell Unveils AI Platform", company="Dell")

    # Verify company relevance fields present
    assert result.is_about_company is True
    assert result.company_score == 0.85
    assert result.company == "Dell"

    # Verify existing classification still works
    assert result.is_straight_news is True
    assert result.headline == "Dell Unveils AI Platform"


def test_classify_headline_with_none_company_excludes_relevance_fields(
    mock_transformers_pipeline,
):
    """Test classify_headline excludes company fields when company is None."""
    import sys

    # Clear module cache to ensure fresh import with current mock
    if "benz_sent_filter.services.classifier" in sys.modules:
        del sys.modules["benz_sent_filter.services.classifier"]

    mock_transformers_pipeline({
        "This is an opinion piece or editorial": 0.2,
        "This is a factual news report": 0.75,
        "This is about a past event that already happened": 0.7,
        "This is about a future event or forecast": 0.1,
        "This is a general topic or analysis": 0.2,
    })

    from benz_sent_filter.services.classifier import ClassificationService

    service = ClassificationService()
    result = service.classify_headline("Dell Unveils AI Platform", company=None)

    # Verify company fields are None
    assert result.is_about_company is None
    assert result.company_score is None
    assert result.company is None

    # Verify existing classification still works
    assert result.is_straight_news is True


def test_classify_batch_with_company_all_headlines(mock_transformers_pipeline):
    """Test classify_batch includes company relevance for all headlines when company provided."""
    import sys

    # Clear module cache to ensure fresh import with current mock
    if "benz_sent_filter.services.classifier" in sys.modules:
        del sys.modules["benz_sent_filter.services.classifier"]

    mock_transformers_pipeline({
        "This is an opinion piece or editorial": 0.2,
        "This is a factual news report": 0.7,
        "This is about a past event that already happened": 0.2,
        "This is about a future event or forecast": 0.3,
        "This is a general topic or analysis": 0.5,
        "This article is about Dell": 0.80,
    })

    from benz_sent_filter.services.classifier import ClassificationService

    service = ClassificationService()
    results = service.classify_batch(["h1", "h2", "h3"], company="Dell")

    # Verify 3 results returned
    assert len(results) == 3

    # Verify all have company relevance fields populated
    for result in results:
        assert result.is_about_company is True
        assert result.company_score == 0.80
        assert result.company == "Dell"


def test_classify_batch_with_none_company_no_relevance_checks(
    mock_transformers_pipeline,
):
    """Test classify_batch excludes company fields when company is None."""
    import sys

    # Clear module cache to ensure fresh import with current mock
    if "benz_sent_filter.services.classifier" in sys.modules:
        del sys.modules["benz_sent_filter.services.classifier"]

    mock_transformers_pipeline({
        "This is an opinion piece or editorial": 0.2,
        "This is a factual news report": 0.7,
        "This is about a past event that already happened": 0.2,
        "This is about a future event or forecast": 0.3,
        "This is a general topic or analysis": 0.5,
    })

    from benz_sent_filter.services.classifier import ClassificationService

    service = ClassificationService()
    results = service.classify_batch(["h1", "h2"], company=None)

    # Verify 2 results returned
    assert len(results) == 2

    # Verify company fields are None
    for result in results:
        assert result.is_about_company is None
        assert result.company_score is None
        assert result.company is None


# ============================================================================
# Far-Future Forecast Detection Tests (Phase 1)
# ============================================================================


def test_forecast_analyzer_detects_multi_year_forecast():
    """Test that multi-year forecasts are detected correctly."""
    from benz_sent_filter.services.forecast_analyzer import is_far_future

    # Should detect: "Over 5 Years"
    headline = "Forecasts $1B Launch-Year Revenue, Sees $18B-$22B Over 5 Years"
    is_far, timeframe = is_far_future(headline)

    assert is_far is True
    assert timeframe is not None
    assert "5" in timeframe.lower() or "year" in timeframe.lower()


def test_forecast_analyzer_detects_by_year_pattern():
    """Test that 'by YYYY' patterns are detected as far-future."""
    from benz_sent_filter.services.forecast_analyzer import is_far_future

    # Should detect: "By 2028"
    headline = "Projects $500M Revenue By 2028"
    is_far, timeframe = is_far_future(headline)

    assert is_far is True
    assert timeframe is not None
    assert "2028" in timeframe


def test_forecast_analyzer_detects_x_year_pattern():
    """Test that 'X-year' patterns are detected as far-future."""
    from benz_sent_filter.services.forecast_analyzer import is_far_future

    # Should detect: "5-Year"
    headline = "Estimates 5-Year Cumulative Sales of $2B"
    is_far, timeframe = is_far_future(headline)

    assert is_far is True
    assert timeframe is not None
    assert "5" in timeframe and "year" in timeframe.lower()


def test_forecast_analyzer_excludes_quarterly_guidance():
    """Test that quarterly guidance is NOT flagged as far-future."""
    from benz_sent_filter.services.forecast_analyzer import is_far_future

    # Should NOT detect: "Q4 Guidance"
    headline = "Q4 Guidance Raised to $100M"
    is_far, timeframe = is_far_future(headline)

    assert is_far is False
    assert timeframe is None


def test_forecast_analyzer_excludes_quarterly_results():
    """Test that quarterly results are NOT flagged as far-future."""
    from benz_sent_filter.services.forecast_analyzer import is_far_future

    # Should NOT detect: "Q2 Revenue"
    headline = "Reports Q2 Revenue of $1B"
    is_far, timeframe = is_far_future(headline)

    assert is_far is False
    assert timeframe is None


def test_forecast_analyzer_excludes_immediate_contracts():
    """Test that immediate contract wins are NOT flagged as far-future."""
    from benz_sent_filter.services.forecast_analyzer import is_far_future

    # Should NOT detect: No timeframe indicators
    headline = "Announces $500M Contract Win"
    is_far, timeframe = is_far_future(headline)

    assert is_far is False
    assert timeframe is None


def test_forecast_analyzer_excludes_fiscal_year_guidance():
    """Test that fiscal year guidance is NOT flagged as far-future."""
    from benz_sent_filter.services.forecast_analyzer import is_far_future

    # Should NOT detect: "Fiscal 2025" (near-term)
    headline = "Fiscal 2025 Guidance: $2B Revenue"
    is_far, timeframe = is_far_future(headline)

    assert is_far is False
    assert timeframe is None


def test_forecast_analyzer_detects_through_year_pattern():
    """Test that 'through YYYY' patterns are detected as far-future."""
    from benz_sent_filter.services.forecast_analyzer import is_far_future

    # Should detect: "Through 2027"
    headline = "Guidance: Expects $100M Revenue Through 2027"
    is_far, timeframe = is_far_future(headline)

    assert is_far is True
    assert timeframe is not None
    assert "2027" in timeframe


# ============================================================================
# Far-Future Forecast Detection Tests (Phase 3: Service Integration)
# ============================================================================


def test_classify_headline_future_event_with_far_future_pattern(
    mock_transformers_pipeline,
):
    """Test classify_headline detects far-future patterns in FUTURE_EVENT headlines."""
    import sys

    # Clear module cache
    if "benz_sent_filter.services.classifier" in sys.modules:
        del sys.modules["benz_sent_filter.services.classifier"]

    mock_transformers_pipeline({
        "This is an opinion piece or editorial": 0.2,
        "This is a factual news report": 0.75,
        "This is about a past event that already happened": 0.1,
        "This is about a future event or forecast": 0.7,
        "This is a general topic or analysis": 0.2,
    })

    from benz_sent_filter.services.classifier import ClassificationService
    from benz_sent_filter.models.classification import TemporalCategory

    service = ClassificationService()
    result = service.classify_headline("Projects $500M Revenue By 2028")

    # Verify temporal classification is FUTURE_EVENT
    assert result.temporal_category == TemporalCategory.FUTURE_EVENT

    # Verify far-future fields populated
    assert result.far_future_forecast is True
    assert result.forecast_timeframe is not None
    assert "2028" in result.forecast_timeframe


def test_classify_headline_future_event_without_far_future_pattern(
    mock_transformers_pipeline,
):
    """Test classify_headline does NOT flag near-term FUTURE_EVENT as far-future."""
    import sys

    # Clear module cache
    if "benz_sent_filter.services.classifier" in sys.modules:
        del sys.modules["benz_sent_filter.services.classifier"]

    mock_transformers_pipeline({
        "This is an opinion piece or editorial": 0.2,
        "This is a factual news report": 0.75,
        "This is about a past event that already happened": 0.1,
        "This is about a future event or forecast": 0.7,
        "This is a general topic or analysis": 0.2,
    })

    from benz_sent_filter.services.classifier import ClassificationService
    from benz_sent_filter.models.classification import TemporalCategory

    service = ClassificationService()
    result = service.classify_headline("Q4 Guidance Raised to $100M")

    # Verify temporal classification is FUTURE_EVENT (guidance is about future)
    assert result.temporal_category == TemporalCategory.FUTURE_EVENT

    # Verify far-future fields NOT populated (quarterly is near-term)
    assert result.far_future_forecast is None
    assert result.forecast_timeframe is None


def test_classify_headline_past_event_no_far_future_analysis(
    mock_transformers_pipeline,
):
    """Test classify_headline does NOT analyze far-future for PAST_EVENT headlines."""
    import sys

    # Clear module cache
    if "benz_sent_filter.services.classifier" in sys.modules:
        del sys.modules["benz_sent_filter.services.classifier"]

    mock_transformers_pipeline({
        "This is an opinion piece or editorial": 0.2,
        "This is a factual news report": 0.75,
        "This is about a past event that already happened": 0.7,
        "This is about a future event or forecast": 0.1,
        "This is a general topic or analysis": 0.2,
    })

    from benz_sent_filter.services.classifier import ClassificationService
    from benz_sent_filter.models.classification import TemporalCategory

    service = ClassificationService()
    result = service.classify_headline("Reports Q2 Revenue of $1B")

    # Verify temporal classification is PAST_EVENT
    assert result.temporal_category == TemporalCategory.PAST_EVENT

    # Verify far-future fields NOT populated (only analyzed for FUTURE_EVENT)
    assert result.far_future_forecast is None
    assert result.forecast_timeframe is None


def test_classify_headline_far_future_with_company_relevance(
    mock_transformers_pipeline,
):
    """Test classify_headline populates both far-future and company fields."""
    import sys

    # Clear module cache
    if "benz_sent_filter.services.classifier" in sys.modules:
        del sys.modules["benz_sent_filter.services.classifier"]

    mock_transformers_pipeline({
        "This is an opinion piece or editorial": 0.2,
        "This is a factual news report": 0.75,
        "This is about a past event that already happened": 0.1,
        "This is about a future event or forecast": 0.7,
        "This is a general topic or analysis": 0.2,
        "This article is about Dell": 0.85,
    })

    from benz_sent_filter.services.classifier import ClassificationService
    from benz_sent_filter.models.classification import TemporalCategory

    service = ClassificationService()
    result = service.classify_headline(
        "Dell Projects $10B Revenue By 2027", company="Dell"
    )

    # Verify temporal classification
    assert result.temporal_category == TemporalCategory.FUTURE_EVENT

    # Verify far-future fields populated
    assert result.far_future_forecast is True
    assert result.forecast_timeframe is not None
    assert "2027" in result.forecast_timeframe

    # Verify company fields also populated
    assert result.is_about_company is True
    assert result.company_score == 0.85
    assert result.company == "Dell"


# Phase 1: Multi-Ticker Classification Tests


def test_classify_headline_multi_ticker_basic(mock_transformers_pipeline):
    """Test multi-ticker classification with 3 tickers."""
    import sys

    # Clear module cache
    if "benz_sent_filter.services.classifier" in sys.modules:
        del sys.modules["benz_sent_filter.services.classifier"]

    mock_transformers_pipeline({
        "This is an opinion piece or editorial": 0.2,
        "This is a factual news report": 0.85,
        "This is about a past event that already happened": 0.3,
        "This is about a future event or forecast": 0.3,
        "This is a general topic or analysis": 0.4,
        "This article describes a routine business operation like quarterly dividends, regular loan portfolio sales, scheduled buybacks, or normal refinancing": 0.75,
    })

    from benz_sent_filter.services.classifier import ClassificationService

    service = ClassificationService()
    result = service.classify_headline_multi_ticker(
        "Bank announces quarterly dividend payment",
        ticker_symbols=["BAC", "JPM", "C"]
    )

    # Verify core classification exists
    assert "core_classification" in result
    core = result["core_classification"]
    assert core["is_opinion"] is False
    assert core["is_straight_news"] is True

    # Verify per-ticker routine operations
    assert "routine_operations_by_ticker" in result
    ticker_results = result["routine_operations_by_ticker"]
    assert len(ticker_results) == 3
    assert "BAC" in ticker_results
    assert "JPM" in ticker_results
    assert "C" in ticker_results

    # Each ticker should have routine operation result
    for ticker in ["BAC", "JPM", "C"]:
        assert "routine_operation" in ticker_results[ticker]
        assert "routine_confidence" in ticker_results[ticker]
        assert "routine_metadata" in ticker_results[ticker]


def test_classify_headline_multi_ticker_empty_list(mock_transformers_pipeline):
    """Test multi-ticker classification with empty ticker list."""
    import sys

    # Clear module cache
    if "benz_sent_filter.services.classifier" in sys.modules:
        del sys.modules["benz_sent_filter.services.classifier"]

    mock_transformers_pipeline({
        "This is an opinion piece or editorial": 0.2,
        "This is a factual news report": 0.85,
        "This is about a past event that already happened": 0.3,
        "This is about a future event or forecast": 0.3,
        "This is a general topic or analysis": 0.4,
    })

    from benz_sent_filter.services.classifier import ClassificationService

    service = ClassificationService()
    result = service.classify_headline_multi_ticker(
        "Bank announces quarterly dividend payment",
        ticker_symbols=[]
    )

    # Core classification should still exist
    assert "core_classification" in result
    assert result["core_classification"]["is_straight_news"] is True

    # Routine operations dict should be empty
    assert "routine_operations_by_ticker" in result
    assert len(result["routine_operations_by_ticker"]) == 0


def test_classify_headline_multi_ticker_single_ticker(mock_transformers_pipeline):
    """Test multi-ticker with single ticker matches single-ticker behavior."""
    import sys

    # Clear module cache
    if "benz_sent_filter.services.classifier" in sys.modules:
        del sys.modules["benz_sent_filter.services.classifier"]

    mock_transformers_pipeline({
        "This is an opinion piece or editorial": 0.2,
        "This is a factual news report": 0.85,
        "This is about a past event that already happened": 0.3,
        "This is about a future event or forecast": 0.3,
        "This is a general topic or analysis": 0.4,
        "This article describes a routine business operation like quarterly dividends, regular loan portfolio sales, scheduled buybacks, or normal refinancing": 0.65,
    })

    from benz_sent_filter.services.classifier import ClassificationService

    service = ClassificationService()

    # Multi-ticker call with one ticker
    multi_result = service.classify_headline_multi_ticker(
        "Bank announces dividend",
        ticker_symbols=["BAC"]
    )

    # Single-ticker call
    single_result = service.classify_headline(
        "Bank announces dividend",
        company_symbol="BAC"
    )

    # Core classification should match
    assert multi_result["core_classification"]["is_straight_news"] == single_result.is_straight_news
    assert multi_result["core_classification"]["temporal_category"] == single_result.temporal_category.value

    # Routine operation result should match
    multi_routine = multi_result["routine_operations_by_ticker"]["BAC"]
    assert multi_routine["routine_operation"] == single_result.routine_operation
    assert multi_routine["routine_confidence"] == single_result.routine_confidence


def test_classify_headline_multi_ticker_different_routine_results(mock_transformers_pipeline):
    """Test that routine operations are analyzed separately for each ticker."""
    import sys

    # Clear module cache
    if "benz_sent_filter.services.classifier" in sys.modules:
        del sys.modules["benz_sent_filter.services.classifier"]

    mock_transformers_pipeline({
        "This is an opinion piece or editorial": 0.2,
        "This is a factual news report": 0.85,
        "This is about a past event that already happened": 0.3,
        "This is about a future event or forecast": 0.3,
        "This is a general topic or analysis": 0.4,
        "This is a transformational change to the business": 0.4,
        "This is incremental progress or routine business updates": 0.6,
    })

    from benz_sent_filter.services.classifier import ClassificationService

    service = ClassificationService()
    result = service.classify_headline_multi_ticker(
        "Company announces quarterly dividend",
        ticker_symbols=["AAPL", "BAC", "JPM"]
    )

    ticker_results = result["routine_operations_by_ticker"]

    # All tickers should have results
    assert len(ticker_results) == 3
    assert "AAPL" in ticker_results
    assert "BAC" in ticker_results
    assert "JPM" in ticker_results

    # Each ticker should have routine operation fields
    for ticker in ["AAPL", "BAC", "JPM"]:
        assert "routine_operation" in ticker_results[ticker]
        assert "routine_confidence" in ticker_results[ticker]
        assert "routine_metadata" in ticker_results[ticker]
        # Verify metadata has expected structure
        metadata = ticker_results[ticker]["routine_metadata"]
        assert "routine_score" in metadata
        assert "detected_patterns" in metadata
        assert "process_stage" in metadata


def test_classify_headline_multi_ticker_core_classification_consistency(mock_transformers_pipeline):
    """Test that core classification is identical to single-headline results."""
    import sys

    # Clear module cache
    if "benz_sent_filter.services.classifier" in sys.modules:
        del sys.modules["benz_sent_filter.services.classifier"]

    mock_transformers_pipeline({
        "This is an opinion piece or editorial": 0.15,
        "This is a factual news report": 0.88,
        "This is about a past event that already happened": 0.65,
        "This is about a future event or forecast": 0.2,
        "This is a general topic or analysis": 0.15,
        "This article describes a routine business operation like quarterly dividends, regular loan portfolio sales, scheduled buybacks, or normal refinancing": 0.45,
    })

    from benz_sent_filter.services.classifier import ClassificationService

    service = ClassificationService()

    headline = "Fed Raised Interest Rates Yesterday"

    # Get multi-ticker result
    multi_result = service.classify_headline_multi_ticker(
        headline,
        ticker_symbols=["BAC", "JPM"]
    )

    # Get single classification result (no company)
    single_result = service.classify_headline(headline)

    # Core classification fields should match exactly
    core = multi_result["core_classification"]
    assert core["is_opinion"] == single_result.is_opinion
    assert core["is_straight_news"] == single_result.is_straight_news
    assert core["temporal_category"] == single_result.temporal_category.value
    assert core["scores"]["opinion_score"] == single_result.scores.opinion_score
    assert core["scores"]["news_score"] == single_result.scores.news_score
    assert core["scores"]["past_score"] == single_result.scores.past_score
    assert core["scores"]["future_score"] == single_result.scores.future_score
    assert core["scores"]["general_score"] == single_result.scores.general_score


def test_classify_headline_multi_ticker_performance_validation(monkeypatch):
    """Test multi-ticker is faster than N sequential calls by counting inference calls."""
    import sys

    # Clear module cache
    if "benz_sent_filter.services.classifier" in sys.modules:
        del sys.modules["benz_sent_filter.services.classifier"]

    # Counter to track pipeline calls
    call_count = {"count": 0}

    def _counting_mock_pipeline(task, model):
        def pipeline_fn(text, candidate_labels):
            call_count["count"] += 1
            scores = [0.5 for _ in candidate_labels]
            return {"labels": candidate_labels, "scores": scores}
        return pipeline_fn

    monkeypatch.setattr("transformers.pipeline", _counting_mock_pipeline)

    from benz_sent_filter.services.classifier import ClassificationService

    service = ClassificationService()

    # Multi-ticker call with 3 tickers
    call_count["count"] = 0
    service.classify_headline_multi_ticker(
        "Bank announces dividend",
        ticker_symbols=["BAC", "JPM", "C"]
    )
    multi_ticker_calls = call_count["count"]

    # Sequential single-ticker calls (3 times)
    call_count["count"] = 0
    for ticker in ["BAC", "JPM", "C"]:
        service.classify_headline("Bank announces dividend", company_symbol=ticker)
    sequential_calls = call_count["count"]

    # Multi-ticker should make fewer calls than sequential
    # Expected: Multi-ticker = 1 core + 3 routine = ~4-5 calls
    # Sequential = (1 core + 1 routine) × 3 = ~6 calls
    assert multi_ticker_calls < sequential_calls, (
        f"Multi-ticker ({multi_ticker_calls} calls) should be faster than "
        f"sequential ({sequential_calls} calls)"
    )

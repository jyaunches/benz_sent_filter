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


# Phase 1: Company Relevance Detection - Request Model Tests


def test_classify_request_with_company_parameter():
    """Test ClassifyRequest validates successfully with company parameter."""
    from benz_sent_filter.models.classification import ClassifyRequest

    request = ClassifyRequest(headline="Test headline", company="Dell")
    assert request.headline == "Test headline"
    assert request.company == "Dell"


def test_classify_request_without_company_parameter_defaults_none():
    """Test ClassifyRequest without company parameter defaults to None."""
    from benz_sent_filter.models.classification import ClassifyRequest

    request = ClassifyRequest(headline="Test headline")
    assert request.headline == "Test headline"
    assert request.company is None


def test_classify_request_with_none_company_explicit():
    """Test ClassifyRequest with explicit None company parameter."""
    from benz_sent_filter.models.classification import ClassifyRequest

    request = ClassifyRequest(headline="Test headline", company=None)
    assert request.headline == "Test headline"
    assert request.company is None


def test_classification_result_with_company_fields_present():
    """Test ClassificationResult serializes correctly with company fields present."""
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
        headline="Dell Unveils AI Platform",
        is_about_company=True,
        company_score=0.85,
        company="Dell",
    )

    # Test field access
    assert result.is_about_company is True
    assert result.company_score == 0.85
    assert result.company == "Dell"

    # Test serialization includes company fields
    result_dict = result.model_dump()
    assert "is_about_company" in result_dict
    assert "company_score" in result_dict
    assert "company" in result_dict
    assert result_dict["is_about_company"] is True
    assert result_dict["company_score"] == 0.85
    assert result_dict["company"] == "Dell"


def test_classification_result_with_company_fields_none():
    """Test ClassificationResult with company fields set to None."""
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
        is_about_company=None,
        company_score=None,
        company=None,
    )

    # Test field access
    assert result.is_about_company is None
    assert result.company_score is None
    assert result.company is None


def test_classification_result_json_excludes_none_company_fields():
    """Test ClassificationResult JSON serialization excludes None company fields."""
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

    # Create result without company fields (defaults to None)
    result = ClassificationResult(
        is_opinion=True,
        is_straight_news=False,
        temporal_category=TemporalCategory.FUTURE_EVENT,
        scores=scores,
        headline="Test headline",
    )

    # Test serialization excludes None fields due to exclude_none=True
    result_dict = result.model_dump(exclude_none=True)
    assert "is_about_company" not in result_dict
    assert "company_score" not in result_dict
    assert "company" not in result_dict

    # Verify existing fields still present
    assert "is_opinion" in result_dict
    assert "headline" in result_dict


def test_batch_classify_request_with_company_parameter():
    """Test BatchClassifyRequest with company parameter."""
    from benz_sent_filter.models.classification import BatchClassifyRequest

    request = BatchClassifyRequest(headlines=["h1", "h2"], company="Tesla")
    assert len(request.headlines) == 2
    assert request.company == "Tesla"


def test_batch_classify_request_without_company_defaults_none():
    """Test BatchClassifyRequest without company defaults to None."""
    from benz_sent_filter.models.classification import BatchClassifyRequest

    request = BatchClassifyRequest(headlines=["h1", "h2"])
    assert len(request.headlines) == 2
    assert request.company is None


# ============================================================================
# Far-Future Forecast Detection Tests (Phase 2: Data Model Extensions)
# ============================================================================


def test_classification_result_with_far_future_fields_present():
    """Test ClassificationResult accepts and serializes far-future forecast fields."""
    from benz_sent_filter.models.classification import (
        ClassificationResult,
        ClassificationScores,
        TemporalCategory,
    )

    scores = ClassificationScores(
        opinion_score=0.2,
        news_score=0.8,
        past_score=0.1,
        future_score=0.7,
        general_score=0.2,
    )

    result = ClassificationResult(
        is_opinion=False,
        is_straight_news=True,
        temporal_category=TemporalCategory.FUTURE_EVENT,
        scores=scores,
        headline="Projects $500M Revenue By 2028",
        far_future_forecast=True,
        forecast_timeframe="by 2028",
    )

    # Test field access
    assert result.far_future_forecast is True
    assert result.forecast_timeframe == "by 2028"

    # Test serialization includes far-future fields
    result_dict = result.model_dump()
    assert "far_future_forecast" in result_dict
    assert "forecast_timeframe" in result_dict
    assert result_dict["far_future_forecast"] is True
    assert result_dict["forecast_timeframe"] == "by 2028"


def test_classification_result_with_far_future_fields_none():
    """Test ClassificationResult with far-future fields set to None."""
    from benz_sent_filter.models.classification import (
        ClassificationResult,
        ClassificationScores,
        TemporalCategory,
    )

    scores = ClassificationScores(
        opinion_score=0.2,
        news_score=0.8,
        past_score=0.7,
        future_score=0.1,
        general_score=0.2,
    )

    result = ClassificationResult(
        is_opinion=False,
        is_straight_news=True,
        temporal_category=TemporalCategory.PAST_EVENT,
        scores=scores,
        headline="Reports Q2 Revenue of $1B",
        far_future_forecast=None,
        forecast_timeframe=None,
    )

    # Test field access
    assert result.far_future_forecast is None
    assert result.forecast_timeframe is None


def test_classification_result_json_excludes_none_far_future_fields():
    """Test ClassificationResult JSON serialization excludes None far-future fields."""
    from benz_sent_filter.models.classification import (
        ClassificationResult,
        ClassificationScores,
        TemporalCategory,
    )

    scores = ClassificationScores(
        opinion_score=0.2,
        news_score=0.8,
        past_score=0.7,
        future_score=0.1,
        general_score=0.2,
    )

    # Create result without far-future fields (defaults to None)
    result = ClassificationResult(
        is_opinion=False,
        is_straight_news=True,
        temporal_category=TemporalCategory.PAST_EVENT,
        scores=scores,
        headline="Reports Q2 Revenue of $1B",
    )

    # Test serialization excludes None fields due to exclude_none=True
    result_dict = result.model_dump(exclude_none=True)
    assert "far_future_forecast" not in result_dict
    assert "forecast_timeframe" not in result_dict

    # Verify existing fields still present
    assert "is_opinion" in result_dict
    assert "headline" in result_dict
    assert "temporal_category" in result_dict


def test_classification_result_far_future_without_company_fields():
    """Test ClassificationResult with far-future fields but no company fields."""
    from benz_sent_filter.models.classification import (
        ClassificationResult,
        ClassificationScores,
        TemporalCategory,
    )

    scores = ClassificationScores(
        opinion_score=0.2,
        news_score=0.8,
        past_score=0.1,
        future_score=0.7,
        general_score=0.2,
    )

    result = ClassificationResult(
        is_opinion=False,
        is_straight_news=True,
        temporal_category=TemporalCategory.FUTURE_EVENT,
        scores=scores,
        headline="Estimates 5-Year Cumulative Sales of $2B",
        far_future_forecast=True,
        forecast_timeframe="5-year",
    )

    # Test far-future fields present
    assert result.far_future_forecast is True
    assert result.forecast_timeframe == "5-year"

    # Test company fields default to None
    assert result.is_about_company is None
    assert result.company_score is None
    assert result.company is None

    # Test serialization
    result_dict = result.model_dump()
    assert result_dict["far_future_forecast"] is True
    assert result_dict["forecast_timeframe"] == "5-year"


def test_classification_result_all_optional_fields_present():
    """Test ClassificationResult with all optional fields (company + far-future) present."""
    from benz_sent_filter.models.classification import (
        ClassificationResult,
        ClassificationScores,
        TemporalCategory,
    )

    scores = ClassificationScores(
        opinion_score=0.2,
        news_score=0.8,
        past_score=0.1,
        future_score=0.7,
        general_score=0.2,
    )

    result = ClassificationResult(
        is_opinion=False,
        is_straight_news=True,
        temporal_category=TemporalCategory.FUTURE_EVENT,
        scores=scores,
        headline="Dell Projects $10B Revenue By 2027",
        is_about_company=True,
        company_score=0.90,
        company="Dell",
        far_future_forecast=True,
        forecast_timeframe="by 2027",
    )

    # Test all optional fields present
    assert result.is_about_company is True
    assert result.company_score == 0.90
    assert result.company == "Dell"
    assert result.far_future_forecast is True
    assert result.forecast_timeframe == "by 2027"

    # Test serialization includes all fields
    result_dict = result.model_dump()
    assert result_dict["is_about_company"] is True
    assert result_dict["company"] == "Dell"
    assert result_dict["far_future_forecast"] is True
    assert result_dict["forecast_timeframe"] == "by 2027"


# ============================================================================
# Phase 2: Multi-Ticker Response Models
# ============================================================================


def test_core_classification_model_all_required_fields():
    """Test CoreClassification model has all required core classification fields."""
    from benz_sent_filter.models.classification import CoreClassification

    core = CoreClassification(
        is_opinion=False,
        is_straight_news=True,
        temporal_category="past_event",
        scores={
            "opinion_score": 0.2,
            "news_score": 0.85,
            "past_score": 0.7,
            "future_score": 0.1,
            "general_score": 0.2,
        },
    )

    assert core.is_opinion is False
    assert core.is_straight_news is True
    assert core.temporal_category == "past_event"
    assert core.scores["opinion_score"] == 0.2
    assert core.scores["news_score"] == 0.85


def test_routine_operation_result_model_structure():
    """Test RoutineOperationResult model has all required routine operation fields."""
    from benz_sent_filter.models.classification import RoutineOperationResult

    routine = RoutineOperationResult(
        routine_operation=True,
        routine_confidence=0.87,
        routine_metadata={
            "routine_score": 0.87,
            "detected_patterns": ["mnls_classification"],
            "process_stage": "completed",
            "transaction_value": None,
        },
    )

    assert routine.routine_operation is True
    assert routine.routine_confidence == 0.87
    assert "routine_score" in routine.routine_metadata
    assert "detected_patterns" in routine.routine_metadata
    assert routine.routine_metadata["process_stage"] == "completed"


def test_multi_ticker_routine_response_basic_structure():
    """Test MultiTickerRoutineResponse with headline and per-ticker results."""
    from benz_sent_filter.models.classification import (
        CoreClassification,
        MultiTickerRoutineResponse,
        RoutineOperationResult,
    )

    core = CoreClassification(
        is_opinion=False,
        is_straight_news=True,
        temporal_category="general_topic",
        scores={
            "opinion_score": 0.2,
            "news_score": 0.85,
            "past_score": 0.3,
            "future_score": 0.3,
            "general_score": 0.4,
        },
    )

    bac_routine = RoutineOperationResult(
        routine_operation=True,
        routine_confidence=0.87,
        routine_metadata={
            "routine_score": 0.87,
            "detected_patterns": ["mnls_classification"],
            "process_stage": "completed",
        },
    )

    jpm_routine = RoutineOperationResult(
        routine_operation=True,
        routine_confidence=0.65,
        routine_metadata={
            "routine_score": 0.65,
            "detected_patterns": ["mnls_classification"],
            "process_stage": "completed",
        },
    )

    response = MultiTickerRoutineResponse(
        headline="Bank announces quarterly dividend payment",
        core_classification=core,
        routine_operations_by_ticker={"BAC": bac_routine, "JPM": jpm_routine},
    )

    assert response.headline == "Bank announces quarterly dividend payment"
    assert response.core_classification.is_straight_news is True
    assert len(response.routine_operations_by_ticker) == 2
    assert "BAC" in response.routine_operations_by_ticker
    assert "JPM" in response.routine_operations_by_ticker
    assert response.routine_operations_by_ticker["BAC"].routine_operation is True


def test_multi_ticker_routine_response_json_serialization():
    """Test MultiTickerRoutineResponse serializes correctly to JSON."""
    from benz_sent_filter.models.classification import (
        CoreClassification,
        MultiTickerRoutineResponse,
        RoutineOperationResult,
    )

    core = CoreClassification(
        is_opinion=False,
        is_straight_news=True,
        temporal_category="general_topic",
        scores={
            "opinion_score": 0.2,
            "news_score": 0.85,
            "past_score": 0.3,
            "future_score": 0.3,
            "general_score": 0.4,
        },
    )

    bac_routine = RoutineOperationResult(
        routine_operation=True,
        routine_confidence=0.87,
        routine_metadata={"routine_score": 0.87},
    )

    response = MultiTickerRoutineResponse(
        headline="Test headline",
        core_classification=core,
        routine_operations_by_ticker={"BAC": bac_routine},
    )

    # Test JSON serialization
    response_dict = response.model_dump()
    assert "headline" in response_dict
    assert "core_classification" in response_dict
    assert "routine_operations_by_ticker" in response_dict
    assert response_dict["headline"] == "Test headline"
    assert response_dict["core_classification"]["is_straight_news"] is True
    assert "BAC" in response_dict["routine_operations_by_ticker"]


def test_multi_ticker_routine_response_empty_ticker_dict():
    """Test MultiTickerRoutineResponse with empty ticker dictionary."""
    from benz_sent_filter.models.classification import (
        CoreClassification,
        MultiTickerRoutineResponse,
    )

    core = CoreClassification(
        is_opinion=False,
        is_straight_news=True,
        temporal_category="general_topic",
        scores={
            "opinion_score": 0.2,
            "news_score": 0.85,
            "past_score": 0.3,
            "future_score": 0.3,
            "general_score": 0.4,
        },
    )

    response = MultiTickerRoutineResponse(
        headline="Test headline",
        core_classification=core,
        routine_operations_by_ticker={},
    )

    assert response.headline == "Test headline"
    assert len(response.routine_operations_by_ticker) == 0


def test_multi_ticker_routine_request_model_validation():
    """Test MultiTickerRoutineRequest validates headline and ticker_symbols."""
    from benz_sent_filter.models.classification import MultiTickerRoutineRequest

    request = MultiTickerRoutineRequest(
        headline="Bank announces dividend",
        ticker_symbols=["BAC", "JPM", "C"],
    )

    assert request.headline == "Bank announces dividend"
    assert len(request.ticker_symbols) == 3
    assert "BAC" in request.ticker_symbols


def test_multi_ticker_routine_request_empty_headline_rejected():
    """Test MultiTickerRoutineRequest rejects empty headline."""
    from benz_sent_filter.models.classification import MultiTickerRoutineRequest

    with pytest.raises(ValidationError) as exc_info:
        MultiTickerRoutineRequest(
            headline="",
            ticker_symbols=["BAC"],
        )

    errors = exc_info.value.errors()
    assert any("headline" in str(error["loc"]) for error in errors)

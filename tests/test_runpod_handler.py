"""Tests for RunPod serverless handler."""

import sys
from unittest.mock import MagicMock

import pytest


@pytest.fixture
def handler_module(mock_transformers_pipeline, monkeypatch):
    """Import handler module with mocked transformers pipeline and runpod."""
    # Mock runpod module before import
    mock_runpod = MagicMock()
    monkeypatch.setitem(sys.modules, "runpod", mock_runpod)
    monkeypatch.setitem(sys.modules, "runpod.serverless", mock_runpod.serverless)

    # Set up mock scores
    mock_transformers_pipeline(
        {
            "This is an opinion piece or editorial": 0.3,
            "This is a factual news report": 0.7,
            "This is about a past event that already happened": 0.6,
            "This is about a future event or forecast": 0.2,
            "This is a general topic or analysis": 0.2,
        }
    )

    # Clear module cache to force fresh import with mocked pipeline
    modules_to_clear = [
        "benz_sent_filter.runpod_handler",
        "benz_sent_filter.services.classifier",
        "benz_sent_filter.services.routine_detector_mnls",
        "benz_sent_filter.services.quantitative_catalyst_detector_mnls",
        "benz_sent_filter.services.strategic_catalyst_detector_mnls",
    ]
    for module_name in modules_to_clear:
        if module_name in sys.modules:
            del sys.modules[module_name]

    # Import handler module (triggers service initialization)
    from benz_sent_filter import runpod_handler

    return runpod_handler


def test_handler_classify_single_headline(handler_module):
    """Test handler processes classify operation for single headline."""
    job = {"input": {"operation": "classify", "headline": "Apple announces new iPhone"}}

    result = handler_module.handler(job)

    assert isinstance(result, dict)
    assert "is_opinion" in result
    assert "is_straight_news" in result
    assert "temporal_category" in result
    assert "scores" in result
    assert result["is_straight_news"] is True
    assert result["temporal_category"] == "past_event"


def test_handler_classify_with_company(handler_module):
    """Test handler processes classify operation with company parameter."""
    job = {
        "input": {
            "operation": "classify",
            "headline": "Apple announces new iPhone",
            "company": "Apple",
        }
    }

    result = handler_module.handler(job)

    assert isinstance(result, dict)
    assert "is_about_company" in result
    assert "company_score" in result
    assert isinstance(result["is_about_company"], bool)
    assert isinstance(result["company_score"], float)


def test_handler_classify_batch(handler_module):
    """Test handler processes classify_batch operation."""
    job = {
        "input": {
            "operation": "classify_batch",
            "headlines": [
                "Apple announces new iPhone",
                "Tesla reports record earnings",
                "Why the Fed is wrong about inflation",
            ],
        }
    }

    result = handler_module.handler(job)

    assert isinstance(result, list)
    assert len(result) == 3
    for item in result:
        assert "is_opinion" in item
        assert "is_straight_news" in item
        assert "temporal_category" in item


def test_handler_routine_operations(handler_module):
    """Test handler processes routine_operations operation."""
    job = {
        "input": {
            "operation": "routine_operations",
            "headline": "Bank of America processes mortgage application",
            "ticker_symbols": ["BAC"],
        }
    }

    result = handler_module.handler(job)

    assert isinstance(result, dict)
    assert "core_classification" in result
    assert "routine_operations_by_ticker" in result
    assert isinstance(result["core_classification"], dict)
    assert isinstance(result["routine_operations_by_ticker"], dict)
    assert "BAC" in result["routine_operations_by_ticker"]


def test_handler_company_relevance(handler_module):
    """Test handler processes company_relevance operation."""
    job = {
        "input": {
            "operation": "company_relevance",
            "headline": "Apple announces new iPhone",
            "company": "Apple",
        }
    }

    result = handler_module.handler(job)

    assert isinstance(result, dict)
    assert "is_about_company" in result
    assert "company_score" in result
    assert "company" in result
    assert result["company"] == "Apple"


def test_handler_company_relevance_batch(handler_module):
    """Test handler processes company_relevance_batch operation."""
    job = {
        "input": {
            "operation": "company_relevance_batch",
            "headlines": [
                "Apple announces new iPhone",
                "Tesla reports earnings",
            ],
            "company": "Apple",
        }
    }

    result = handler_module.handler(job)

    assert isinstance(result, list)
    assert len(result) == 2
    for item in result:
        assert "is_about_company" in item
        assert "company_score" in item


def test_handler_detect_quantitative_catalyst(handler_module):
    """Test handler processes detect_quantitative_catalyst operation."""
    job = {
        "input": {
            "operation": "detect_quantitative_catalyst",
            "headline": "Company declares $1.50 quarterly dividend",
        }
    }

    result = handler_module.handler(job)

    assert isinstance(result, dict)
    assert "has_quantitative_catalyst" in result
    assert "headline" in result
    # These fields may or may not be present depending on detection
    assert isinstance(result["has_quantitative_catalyst"], bool)


def test_handler_detect_strategic_catalyst(handler_module):
    """Test handler processes detect_strategic_catalyst operation."""
    job = {
        "input": {
            "operation": "detect_strategic_catalyst",
            "headline": "Company appoints new CEO",
        }
    }

    result = handler_module.handler(job)

    assert isinstance(result, dict)
    assert "has_strategic_catalyst" in result
    assert "headline" in result
    assert isinstance(result["has_strategic_catalyst"], bool)


def test_handler_invalid_operation(handler_module):
    """Test handler raises error for invalid operation."""
    job = {"input": {"operation": "invalid_operation"}}

    with pytest.raises(ValueError, match="Invalid operation: invalid_operation"):
        handler_module.handler(job)


def test_handler_missing_operation(handler_module):
    """Test handler raises error when operation field is missing."""
    job = {"input": {}}

    with pytest.raises(ValueError, match="Missing required field 'operation'"):
        handler_module.handler(job)


def test_handler_missing_headline_classify(handler_module):
    """Test handler raises error when headline is missing for classify operation."""
    job = {"input": {"operation": "classify"}}

    with pytest.raises(
        ValueError, match="Missing required field 'headline' for classify operation"
    ):
        handler_module.handler(job)


def test_handler_missing_headlines_batch(handler_module):
    """Test handler raises error when headlines is missing for batch operation."""
    job = {"input": {"operation": "classify_batch"}}

    with pytest.raises(
        ValueError,
        match="Missing required field 'headlines' for classify_batch operation",
    ):
        handler_module.handler(job)


def test_handler_missing_ticker_symbols(handler_module):
    """Test handler raises error when ticker_symbols is missing for routine_operations."""
    job = {
        "input": {
            "operation": "routine_operations",
            "headline": "Test headline",
        }
    }

    with pytest.raises(
        ValueError,
        match="Missing required field 'ticker_symbols' for routine_operations operation",
    ):
        handler_module.handler(job)


def test_handler_missing_company_relevance(handler_module):
    """Test handler raises error when company is missing for company_relevance."""
    job = {
        "input": {
            "operation": "company_relevance",
            "headline": "Test headline",
        }
    }

    with pytest.raises(
        ValueError,
        match="Missing required field 'company' for company_relevance operation",
    ):
        handler_module.handler(job)

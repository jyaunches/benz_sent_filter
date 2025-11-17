"""Tests for the API endpoints."""

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client(mock_transformers_pipeline):
    """Create a test client for the FastAPI app."""
    import sys

    # Clear module cache before importing app
    if "benz_sent_filter.api.app" in sys.modules:
        del sys.modules["benz_sent_filter.api.app"]
    if "benz_sent_filter.services.classifier" in sys.modules:
        del sys.modules["benz_sent_filter.services.classifier"]

    # Set up mock with default scores
    mock_transformers_pipeline({
        "This is an opinion piece or editorial": 0.7,
        "This is a factual news report": 0.3,
        "This is about a past event that already happened": 0.2,
        "This is about a future event or forecast": 0.3,
        "This is a general topic or analysis": 0.5,
    })

    from benz_sent_filter.api.app import app

    # Use context manager to trigger startup/shutdown events
    with TestClient(app) as client:
        yield client


def test_health_check(client):
    """Test the health check endpoint."""
    response = client.get("/health")
    assert response.status_code == 200

    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "benz_sent_filter"
    assert "timestamp" in data


def test_startup_event_initializes_service(client):
    """Test that startup event initializes the classification service."""
    from benz_sent_filter.api.app import app
    from benz_sent_filter.services.classifier import ClassificationService

    assert hasattr(app.state, "classifier")
    assert isinstance(app.state.classifier, ClassificationService)


def test_classify_endpoint_valid_opinion_headline(client):
    """Test POST /classify with opinion headline."""
    response = client.post("/classify", json={"headline": "Why the Fed Is Wrong About Inflation"})

    assert response.status_code == 200
    data = response.json()

    assert "is_opinion" in data
    assert "is_straight_news" in data
    assert "temporal_category" in data
    assert "scores" in data
    assert "headline" in data
    assert data["headline"] == "Why the Fed Is Wrong About Inflation"


def test_classify_endpoint_valid_news_headline(client):
    """Test POST /classify with news headline."""
    response = client.post("/classify", json={"headline": "Fed Raises Interest Rates by 25 Basis Points"})

    assert response.status_code == 200
    data = response.json()

    assert isinstance(data["is_opinion"], bool)
    assert isinstance(data["is_straight_news"], bool)


def test_classify_endpoint_empty_headline_validation_error(client):
    """Test POST /classify with empty headline returns 422."""
    response = client.post("/classify", json={"headline": ""})

    assert response.status_code == 422


def test_classify_endpoint_missing_headline_field(client):
    """Test POST /classify with missing headline field returns 422."""
    response = client.post("/classify", json={})

    assert response.status_code == 422


def test_classify_batch_endpoint_multiple_headlines(client):
    """Test POST /classify/batch with multiple headlines."""
    response = client.post(
        "/classify/batch",
        json={"headlines": ["headline1", "headline2"]}
    )

    assert response.status_code == 200
    data = response.json()

    assert "results" in data
    assert len(data["results"]) == 2


def test_classify_batch_endpoint_empty_list_validation_error(client):
    """Test POST /classify/batch with empty list returns 422."""
    response = client.post("/classify/batch", json={"headlines": []})

    assert response.status_code == 422


def test_classify_batch_endpoint_response_structure(client):
    """Test POST /classify/batch response has correct structure."""
    response = client.post(
        "/classify/batch",
        json={"headlines": ["test1", "test2"]}
    )

    assert response.status_code == 200
    data = response.json()

    assert "results" in data
    assert isinstance(data["results"], list)
    for result in data["results"]:
        assert "is_opinion" in result
        assert "is_straight_news" in result
        assert "temporal_category" in result
        assert "scores" in result
        assert "headline" in result


def test_classify_endpoint_response_includes_all_scores(client):
    """Test that /classify response includes all 5 scores."""
    response = client.post("/classify", json={"headline": "Test headline"})

    assert response.status_code == 200
    data = response.json()

    scores = data["scores"]
    assert "opinion_score" in scores
    assert "news_score" in scores
    assert "past_score" in scores
    assert "future_score" in scores
    assert "general_score" in scores


def test_classify_endpoint_response_includes_temporal_category(client):
    """Test that /classify response includes temporal category."""
    response = client.post("/classify", json={"headline": "Test headline"})

    assert response.status_code == 200
    data = response.json()

    assert "temporal_category" in data
    assert data["temporal_category"] in ["past_event", "future_event", "general_topic"]

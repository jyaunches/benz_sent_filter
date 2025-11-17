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


# Phase 3: Company Relevance API Endpoint Tests


@pytest.fixture
def client_with_company(mock_transformers_pipeline):
    """Create a test client with company relevance mocking."""
    import sys

    # Clear module cache before importing app
    if "benz_sent_filter.api.app" in sys.modules:
        del sys.modules["benz_sent_filter.api.app"]
    if "benz_sent_filter.services.classifier" in sys.modules:
        del sys.modules["benz_sent_filter.services.classifier"]

    # Set up mock with company relevance scores
    mock_transformers_pipeline({
        "This is an opinion piece or editorial": 0.2,
        "This is a factual news report": 0.75,
        "This is about a past event that already happened": 0.7,
        "This is about a future event or forecast": 0.1,
        "This is a general topic or analysis": 0.2,
        "This article is about Dell": 0.85,
        "This article is about Tesla": 0.15,
    })

    from benz_sent_filter.api.app import app

    # Use context manager to trigger startup/shutdown events
    with TestClient(app) as client:
        yield client


def test_classify_endpoint_with_company_returns_relevance_fields(client_with_company):
    """Test POST /classify with company parameter returns relevance fields."""
    response = client_with_company.post(
        "/classify",
        json={"headline": "Dell launches product", "company": "Dell"}
    )

    assert response.status_code == 200
    data = response.json()

    # Verify company relevance fields present
    assert "is_about_company" in data
    assert "company_score" in data
    assert "company" in data

    assert data["is_about_company"] is True
    assert data["company_score"] == 0.85
    assert data["company"] == "Dell"

    # Verify existing fields still present
    assert "is_opinion" in data
    assert "is_straight_news" in data


def test_classify_endpoint_without_company_omits_relevance_fields(client):
    """Test POST /classify without company omits relevance fields."""
    response = client.post(
        "/classify",
        json={"headline": "Dell launches product"}
    )

    assert response.status_code == 200
    data = response.json()

    # Company fields should not be present (exclude_none=True)
    assert "is_about_company" not in data
    assert "company_score" not in data
    assert "company" not in data

    # Existing fields still present
    assert "is_opinion" in data
    assert "headline" in data


def test_classify_endpoint_with_none_company_explicit(client):
    """Test POST /classify with explicit null company parameter."""
    response = client.post(
        "/classify",
        json={"headline": "Test", "company": None}
    )

    assert response.status_code == 200
    data = response.json()

    # Company fields should not be present
    assert "is_about_company" not in data
    assert "company_score" not in data
    assert "company" not in data


def test_classify_endpoint_with_company_response_schema_complete(client_with_company):
    """Test POST /classify with company has complete response schema."""
    response = client_with_company.post(
        "/classify",
        json={"headline": "Dell Unveils AI Platform", "company": "Dell"}
    )

    assert response.status_code == 200
    data = response.json()

    # Verify all existing fields
    assert "is_opinion" in data
    assert "is_straight_news" in data
    assert "temporal_category" in data
    assert "scores" in data
    assert "headline" in data

    # Verify company fields
    assert "is_about_company" in data
    assert isinstance(data["is_about_company"], bool)
    assert "company_score" in data
    assert isinstance(data["company_score"], float)
    assert "company" in data
    assert isinstance(data["company"], str)


def test_classify_endpoint_with_company_and_empty_headline_validation_error(client_with_company):
    """Test POST /classify with company and empty headline returns 422."""
    response = client_with_company.post(
        "/classify",
        json={"headline": "", "company": "Dell"}
    )

    assert response.status_code == 422


def test_classify_endpoint_company_field_type_validation(client):
    """Test POST /classify with invalid company type returns 422."""
    response = client.post(
        "/classify",
        json={"headline": "Test", "company": 123}
    )

    assert response.status_code == 422


def test_classify_batch_endpoint_with_company_all_results_include_relevance(client_with_company):
    """Test POST /classify/batch with company includes relevance in all results."""
    response = client_with_company.post(
        "/classify/batch",
        json={"headlines": ["h1", "h2"], "company": "Dell"}
    )

    assert response.status_code == 200
    data = response.json()

    assert "results" in data
    assert len(data["results"]) == 2

    # Verify all results have company relevance fields
    for result in data["results"]:
        assert "is_about_company" in result
        assert "company_score" in result
        assert "company" in result
        assert result["company"] == "Dell"


def test_classify_batch_endpoint_without_company_backward_compatible(client):
    """Test POST /classify/batch without company is backward compatible."""
    response = client.post(
        "/classify/batch",
        json={"headlines": ["h1", "h2"]}
    )

    assert response.status_code == 200
    data = response.json()

    assert "results" in data
    assert len(data["results"]) == 2

    # Verify company fields not present
    for result in data["results"]:
        assert "is_about_company" not in result
        assert "company_score" not in result
        assert "company" not in result


def test_classify_batch_endpoint_with_company_response_structure(client_with_company):
    """Test POST /classify/batch with company has correct response structure."""
    response = client_with_company.post(
        "/classify/batch",
        json={"headlines": ["Dell product", "Dell news"], "company": "Dell"}
    )

    assert response.status_code == 200
    data = response.json()

    assert "results" in data
    assert isinstance(data["results"], list)
    assert len(data["results"]) == 2

    # Verify each result has complete structure
    for result in data["results"]:
        assert "is_opinion" in result
        assert "is_straight_news" in result
        assert "temporal_category" in result
        assert "scores" in result
        assert "headline" in result
        assert "is_about_company" in result
        assert "company_score" in result
        assert "company" in result


def test_health_endpoint_unaffected_by_company_feature(client_with_company):
    """Test GET /health is unaffected by company feature."""
    response = client_with_company.get("/health")

    assert response.status_code == 200
    data = response.json()

    assert data["status"] == "healthy"
    assert data["service"] == "benz_sent_filter"

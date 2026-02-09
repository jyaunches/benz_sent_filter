"""Tests for the API endpoints."""

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client(mock_transformers_pipeline):
    """Create a test client for the FastAPI app."""
    import sys

    # Clear module cache before importing app
    modules_to_clear = [
        "benz_sent_filter.api.app",
        "benz_sent_filter.services.classifier",
        "benz_sent_filter.services.routine_detector_mnls",
        "benz_sent_filter.services.quantitative_catalyst_detector_mnls",
        "benz_sent_filter.services.routine_detector",
    ]
    for module in modules_to_clear:
        if module in sys.modules:
            del sys.modules[module]

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


def test_routine_operations_endpoint_accepts_ticker_symbols_array(client):
    """Test POST /routine-operations with ticker_symbols array (multi-ticker format)."""
    response = client.post(
        "/routine-operations",
        json={
            "headline": "Bank announces quarterly dividend payment",
            "ticker_symbols": ["BAC", "JPM"]
        }
    )

    assert response.status_code == 200
    data = response.json()

    assert "headline" in data
    assert "core_classification" in data
    assert "routine_operations_by_ticker" in data
    assert "BAC" in data["routine_operations_by_ticker"]
    assert "JPM" in data["routine_operations_by_ticker"]


def test_routine_operations_endpoint_accepts_company_symbol_string(client):
    """Test POST /routine-operations with company_symbol string (single-ticker format).

    This tests backward compatibility - clients should be able to send a single
    ticker symbol as a string (company_symbol) and have it automatically converted
    to an array format internally.
    """
    response = client.post(
        "/routine-operations",
        json={
            "headline": "Bank announces quarterly dividend payment",
            "company_symbol": "BAC"
        }
    )

    assert response.status_code == 200
    data = response.json()

    assert "headline" in data
    assert "core_classification" in data
    assert "routine_operations_by_ticker" in data
    assert "BAC" in data["routine_operations_by_ticker"]
    assert len(data["routine_operations_by_ticker"]) == 1


def test_routine_operations_endpoint_response_structure(client):
    """Test POST /routine-operations response has correct structure."""
    response = client.post(
        "/routine-operations",
        json={
            "headline": "Test headline",
            "ticker_symbols": ["AAPL"]
        }
    )

    assert response.status_code == 200
    data = response.json()

    # Check top-level fields
    assert "headline" in data
    assert "core_classification" in data
    assert "routine_operations_by_ticker" in data

    # Check core_classification structure
    core = data["core_classification"]
    assert "is_opinion" in core
    assert "is_straight_news" in core
    assert "temporal_category" in core
    assert "scores" in core

    # Check routine_operations_by_ticker structure
    ticker_data = data["routine_operations_by_ticker"]["AAPL"]
    assert "routine_operation" in ticker_data
    assert "routine_confidence" in ticker_data
    assert "routine_metadata" in ticker_data


# ============================================================================
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
    modules_to_clear = [
        "benz_sent_filter.api.app",
        "benz_sent_filter.services.classifier",
        "benz_sent_filter.services.routine_detector_mnls",
        "benz_sent_filter.services.quantitative_catalyst_detector_mnls",
        "benz_sent_filter.services.routine_detector",
    ]
    for module in modules_to_clear:
        if module in sys.modules:
            del sys.modules[module]

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


# ============================================================================
# Far-Future Forecast Detection Tests (Phase 4: API Endpoint Updates)
# ============================================================================


def test_classify_endpoint_with_far_future_pattern(mock_transformers_pipeline):
    """Test POST /classify returns far-future fields for multi-year forecasts."""
    import sys

    # Clear module cache
    if "benz_sent_filter.api.app" in sys.modules:
        del sys.modules["benz_sent_filter.api.app"]
    if "benz_sent_filter.services.classifier" in sys.modules:
        del sys.modules["benz_sent_filter.services.classifier"]

    # Mock with FUTURE_EVENT scores
    mock_transformers_pipeline({
        "This is an opinion piece or editorial": 0.2,
        "This is a factual news report": 0.75,
        "This is about a past event that already happened": 0.1,
        "This is about a future event or forecast": 0.7,
        "This is a general topic or analysis": 0.2,
    })

    from benz_sent_filter.api.app import app
    from fastapi.testclient import TestClient

    with TestClient(app) as client:
        response = client.post(
            "/classify",
            json={"headline": "Projects $500M Revenue By 2028"}
        )

    assert response.status_code == 200
    data = response.json()

    # Verify far-future fields present
    assert "far_future_forecast" in data
    assert data["far_future_forecast"] is True
    assert "forecast_timeframe" in data
    assert data["forecast_timeframe"] is not None
    assert "2028" in data["forecast_timeframe"]

    # Verify temporal category is FUTURE_EVENT
    assert data["temporal_category"] == "future_event"


def test_classify_endpoint_without_far_future_pattern(mock_transformers_pipeline):
    """Test POST /classify excludes far-future fields for near-term guidance."""
    import sys

    # Clear module cache
    if "benz_sent_filter.api.app" in sys.modules:
        del sys.modules["benz_sent_filter.api.app"]
    if "benz_sent_filter.services.classifier" in sys.modules:
        del sys.modules["benz_sent_filter.services.classifier"]

    # Mock with FUTURE_EVENT scores (headline is future but near-term)
    mock_transformers_pipeline({
        "This is an opinion piece or editorial": 0.2,
        "This is a factual news report": 0.75,
        "This is about a past event that already happened": 0.1,
        "This is about a future event or forecast": 0.7,
        "This is a general topic or analysis": 0.2,
    })

    from benz_sent_filter.api.app import app
    from fastapi.testclient import TestClient

    with TestClient(app) as client:
        response = client.post(
            "/classify",
            json={"headline": "Q4 Guidance Raised to $100M"}
        )

    assert response.status_code == 200
    data = response.json()

    # Verify far-future fields NOT present (excluded by exclude_none=True)
    assert "far_future_forecast" not in data
    assert "forecast_timeframe" not in data


def test_classify_endpoint_past_event_no_far_future(mock_transformers_pipeline):
    """Test POST /classify excludes far-future fields for PAST_EVENT."""
    import sys

    # Clear module cache
    if "benz_sent_filter.api.app" in sys.modules:
        del sys.modules["benz_sent_filter.api.app"]
    if "benz_sent_filter.services.classifier" in sys.modules:
        del sys.modules["benz_sent_filter.services.classifier"]

    # Mock with PAST_EVENT scores
    mock_transformers_pipeline({
        "This is an opinion piece or editorial": 0.2,
        "This is a factual news report": 0.75,
        "This is about a past event that already happened": 0.7,
        "This is about a future event or forecast": 0.1,
        "This is a general topic or analysis": 0.2,
    })

    from benz_sent_filter.api.app import app
    from fastapi.testclient import TestClient

    with TestClient(app) as client:
        response = client.post(
            "/classify",
            json={"headline": "Reports Q2 Revenue of $1B"}
        )

    assert response.status_code == 200
    data = response.json()

    # Verify far-future fields NOT present
    assert "far_future_forecast" not in data
    assert "forecast_timeframe" not in data

    # Verify temporal category is PAST_EVENT
    assert data["temporal_category"] == "past_event"


def test_classify_endpoint_far_future_with_company(mock_transformers_pipeline):
    """Test POST /classify returns both far-future and company fields."""
    import sys

    # Clear module cache
    if "benz_sent_filter.api.app" in sys.modules:
        del sys.modules["benz_sent_filter.api.app"]
    if "benz_sent_filter.services.classifier" in sys.modules:
        del sys.modules["benz_sent_filter.services.classifier"]

    # Mock with FUTURE_EVENT scores and company relevance
    mock_transformers_pipeline({
        "This is an opinion piece or editorial": 0.2,
        "This is a factual news report": 0.75,
        "This is about a past event that already happened": 0.1,
        "This is about a future event or forecast": 0.7,
        "This is a general topic or analysis": 0.2,
        "This article is about Dell": 0.85,
    })

    from benz_sent_filter.api.app import app
    from fastapi.testclient import TestClient

    with TestClient(app) as client:
        response = client.post(
            "/classify",
            json={"headline": "Dell Projects $10B Revenue By 2027", "company": "Dell"}
        )

    assert response.status_code == 200
    data = response.json()

    # Verify far-future fields
    assert "far_future_forecast" in data
    assert data["far_future_forecast"] is True
    assert "forecast_timeframe" in data
    assert "2027" in data["forecast_timeframe"]

    # Verify company fields
    assert "is_about_company" in data
    assert data["is_about_company"] is True
    assert "company_score" in data
    assert "company" in data
    assert data["company"] == "Dell"


def test_classify_batch_endpoint_with_far_future_patterns(mock_transformers_pipeline):
    """Test POST /classify/batch returns far-future fields for applicable headlines."""
    import sys

    # Clear module cache
    if "benz_sent_filter.api.app" in sys.modules:
        del sys.modules["benz_sent_filter.api.app"]
    if "benz_sent_filter.services.classifier" in sys.modules:
        del sys.modules["benz_sent_filter.services.classifier"]

    # Mock with mixed temporal scores (future, future, past)
    mock_transformers_pipeline({
        "This is an opinion piece or editorial": 0.2,
        "This is a factual news report": 0.75,
        "This is about a past event that already happened": 0.4,
        "This is about a future event or forecast": 0.7,
        "This is a general topic or analysis": 0.2,
    })

    from benz_sent_filter.api.app import app
    from fastapi.testclient import TestClient

    with TestClient(app) as client:
        response = client.post(
            "/classify/batch",
            json={
                "headlines": [
                    "Projects $500M Revenue By 2028",  # far-future
                    "Q4 Guidance Raised to $100M",      # near-term
                    "Reports Q2 Revenue of $1B"         # past
                ]
            }
        )

    assert response.status_code == 200
    data = response.json()

    assert "results" in data
    assert len(data["results"]) == 3

    # First result should have far-future fields
    assert data["results"][0]["far_future_forecast"] is True
    assert "2028" in data["results"][0]["forecast_timeframe"]

    # Second result should NOT have far-future fields (near-term)
    assert "far_future_forecast" not in data["results"][1]
    assert "forecast_timeframe" not in data["results"][1]

    # Third result should NOT have far-future fields (past event)
    # Note: With current mock scores (past=0.4, future=0.7), third will be FUTURE_EVENT
    # But it won't match far-future pattern due to "Q2" quarterly language
    assert "far_future_forecast" not in data["results"][2]
    assert "forecast_timeframe" not in data["results"][2]


# ============================================================================
# Company Relevance Dedicated Endpoint Tests (Phase 3 Refactor)
# ============================================================================


def test_company_relevance_endpoint_single_headline(client_with_company):
    """Test POST /company-relevance returns relevance for single headline."""
    response = client_with_company.post(
        "/company-relevance",
        json={"headline": "Dell launches product", "company": "Dell"}
    )

    assert response.status_code == 200
    data = response.json()

    # Verify response structure
    assert "headline" in data
    assert "company" in data
    assert "is_about_company" in data
    assert "company_score" in data

    # Verify values
    assert data["headline"] == "Dell launches product"
    assert data["company"] == "Dell"
    assert data["is_about_company"] is True
    assert data["company_score"] == 0.85


def test_company_relevance_endpoint_not_relevant(client_with_company):
    """Test POST /company-relevance returns false for non-relevant headline."""
    response = client_with_company.post(
        "/company-relevance",
        json={"headline": "Dell launches product", "company": "Tesla"}
    )

    assert response.status_code == 200
    data = response.json()

    # Verify values
    assert data["is_about_company"] is False
    assert data["company_score"] == 0.15
    assert data["company"] == "Tesla"


def test_company_relevance_endpoint_missing_company_field(client_with_company):
    """Test POST /company-relevance without company field returns 422."""
    response = client_with_company.post(
        "/company-relevance",
        json={"headline": "Dell launches product"}
    )

    assert response.status_code == 422


def test_company_relevance_endpoint_missing_headline_field(client_with_company):
    """Test POST /company-relevance without headline field returns 422."""
    response = client_with_company.post(
        "/company-relevance",
        json={"company": "Dell"}
    )

    assert response.status_code == 422


def test_company_relevance_endpoint_empty_headline(client_with_company):
    """Test POST /company-relevance with empty headline returns 422."""
    response = client_with_company.post(
        "/company-relevance",
        json={"headline": "", "company": "Dell"}
    )

    assert response.status_code == 422


def test_company_relevance_endpoint_empty_company(client_with_company):
    """Test POST /company-relevance with empty company returns 422."""
    response = client_with_company.post(
        "/company-relevance",
        json={"headline": "Dell launches product", "company": ""}
    )

    assert response.status_code == 422


def test_company_relevance_batch_endpoint_multiple_headlines(client_with_company):
    """Test POST /company-relevance/batch returns relevance for multiple headlines."""
    response = client_with_company.post(
        "/company-relevance/batch",
        json={
            "headlines": ["Dell launches product", "Tesla updates software"],
            "company": "Dell"
        }
    )

    assert response.status_code == 200
    data = response.json()

    # Verify response structure
    assert "company" in data
    assert "results" in data
    assert len(data["results"]) == 2

    # Verify each result structure
    for result in data["results"]:
        assert "headline" in result
        assert "is_about_company" in result
        assert "company_score" in result


def test_company_relevance_batch_endpoint_empty_headlines(client_with_company):
    """Test POST /company-relevance/batch with empty list returns 422."""
    response = client_with_company.post(
        "/company-relevance/batch",
        json={"headlines": [], "company": "Dell"}
    )

    assert response.status_code == 422


def test_company_relevance_batch_endpoint_missing_company(client_with_company):
    """Test POST /company-relevance/batch without company returns 422."""
    response = client_with_company.post(
        "/company-relevance/batch",
        json={"headlines": ["test"]}
    )

    assert response.status_code == 422


# ============================================================================
# Quantitative Catalyst Detection API Endpoint Tests (Phase 4)
# ============================================================================


def test_detect_quantitative_catalyst_endpoint_with_dividend(mock_transformers_pipeline):
    """Test POST /detect-quantitative-catalyst detects dividend announcements."""
    import sys

    # Clear module cache
    if "benz_sent_filter.api.app" in sys.modules:
        del sys.modules["benz_sent_filter.api.app"]
    if "benz_sent_filter.services.classifier" in sys.modules:
        del sys.modules["benz_sent_filter.services.classifier"]

    # Mock MNLI scores for catalyst detection
    mock_transformers_pipeline({
        "This announces a corporate financial event with specific dollar amounts such as dividends, acquisitions, buybacks, earnings results, or revenue guidance": 0.9,
        "This describes general commentary, stock price changes, analyst opinions, or vague business updates without specific financial transactions": 0.1,
        "This announces that the company is paying out a dividend to shareholders": 0.85,
        "This does not announce a dividend payment to shareholders": 0.15,
        "This announces that the company is purchasing or acquiring another company or assets": 0.2,
        "This is not about the company purchasing or acquiring another company": 0.8,
        "This announces that the company is repurchasing its own shares from the market": 0.3,
        "This is not about the company repurchasing its own shares": 0.7,
        "This announces historical earnings results, net income, or profit from a completed reporting period": 0.2,
        "This is not about historical earnings results or net income from a completed reporting period": 0.8,
        "This provides forward-looking financial projections or guidance for future periods": 0.3,
        "This is not about forward-looking financial projections or guidance": 0.7,
    })

    from benz_sent_filter.api.app import app
    from fastapi.testclient import TestClient

    with TestClient(app) as client:
        response = client.post(
            "/detect-quantitative-catalyst",
            json={"headline": "Universal Security Instruments Increases Quarterly Dividend to $1 Per Share"}
        )

    assert response.status_code == 200
    data = response.json()

    # Verify response structure
    assert "headline" in data
    assert "has_quantitative_catalyst" in data
    assert "catalyst_type" in data
    assert "catalyst_values" in data
    assert "confidence" in data

    # Verify detection
    assert data["has_quantitative_catalyst"] is True
    assert data["catalyst_type"] == "dividend"
    assert "$1" in data["catalyst_values"]
    assert data["confidence"] > 0.5


def test_detect_quantitative_catalyst_endpoint_with_acquisition(mock_transformers_pipeline):
    """Test POST /detect-quantitative-catalyst detects acquisitions."""
    import sys

    # Clear module cache
    if "benz_sent_filter.api.app" in sys.modules:
        del sys.modules["benz_sent_filter.api.app"]
    if "benz_sent_filter.services.classifier" in sys.modules:
        del sys.modules["benz_sent_filter.services.classifier"]

    # Mock MNLI scores for acquisition
    mock_transformers_pipeline({
        "This announces a corporate financial event with specific dollar amounts such as dividends, acquisitions, buybacks, earnings results, or revenue guidance": 0.92,
        "This describes general commentary, stock price changes, analyst opinions, or vague business updates without specific financial transactions": 0.08,
        "This announces that the company is paying out a dividend to shareholders": 0.1,
        "This does not announce a dividend payment to shareholders": 0.9,
        "This announces that the company is purchasing or acquiring another company or assets": 0.88,
        "This is not about the company purchasing or acquiring another company": 0.12,
        "This announces that the company is repurchasing its own shares from the market": 0.2,
        "This is not about the company repurchasing its own shares": 0.8,
        "This announces historical earnings results, net income, or profit from a completed reporting period": 0.15,
        "This is not about historical earnings results or net income from a completed reporting period": 0.85,
        "This provides forward-looking financial projections or guidance for future periods": 0.25,
        "This is not about forward-looking financial projections or guidance": 0.75,
    })

    from benz_sent_filter.api.app import app
    from fastapi.testclient import TestClient

    with TestClient(app) as client:
        response = client.post(
            "/detect-quantitative-catalyst",
            json={"headline": "Alpha Metallurgical Resources to Acquire Ramaco Resources for $3.5B"}
        )

    assert response.status_code == 200
    data = response.json()

    assert data["has_quantitative_catalyst"] is True
    assert data["catalyst_type"] == "acquisition"
    assert "$3.5B" in data["catalyst_values"]
    assert data["confidence"] > 0.5


def test_detect_quantitative_catalyst_endpoint_no_catalyst(mock_transformers_pipeline):
    """Test POST /detect-quantitative-catalyst returns false for non-catalyst headlines."""
    import sys

    # Clear module cache
    if "benz_sent_filter.api.app" in sys.modules:
        del sys.modules["benz_sent_filter.api.app"]
    if "benz_sent_filter.services.classifier" in sys.modules:
        del sys.modules["benz_sent_filter.services.classifier"]

    # Mock MNLI scores for non-catalyst (price movement)
    mock_transformers_pipeline({
        "This announces a corporate financial event with specific dollar amounts such as dividends, acquisitions, buybacks, earnings results, or revenue guidance": 0.2,
        "This describes general commentary, stock price changes, analyst opinions, or vague business updates without specific financial transactions": 0.8,
        "This announces that the company is paying out a dividend to shareholders": 0.1,
        "This does not announce a dividend payment to shareholders": 0.9,
        "This announces that the company is purchasing or acquiring another company or assets": 0.15,
        "This is not about the company purchasing or acquiring another company": 0.85,
        "This announces that the company is repurchasing its own shares from the market": 0.1,
        "This is not about the company repurchasing its own shares": 0.9,
        "This announces historical earnings results, net income, or profit from a completed reporting period": 0.2,
        "This is not about historical earnings results or net income from a completed reporting period": 0.8,
        "This provides forward-looking financial projections or guidance for future periods": 0.15,
        "This is not about forward-looking financial projections or guidance": 0.85,
    })

    from benz_sent_filter.api.app import app
    from fastapi.testclient import TestClient

    with TestClient(app) as client:
        response = client.post(
            "/detect-quantitative-catalyst",
            json={"headline": "Stock reaches $100 milestone"}
        )

    assert response.status_code == 200
    data = response.json()

    assert data["has_quantitative_catalyst"] is False
    # catalyst_type is excluded when None (exclude_none=True)
    assert "catalyst_type" not in data
    assert data["catalyst_values"] == []
    assert data["confidence"] == 0.0


def test_detect_quantitative_catalyst_endpoint_empty_headline(client):
    """Test POST /detect-quantitative-catalyst with empty headline returns 422."""
    response = client.post(
        "/detect-quantitative-catalyst",
        json={"headline": ""}
    )

    assert response.status_code == 422


def test_detect_quantitative_catalyst_endpoint_missing_headline(client):
    """Test POST /detect-quantitative-catalyst without headline field returns 422."""
    response = client.post(
        "/detect-quantitative-catalyst",
        json={}
    )

    assert response.status_code == 422


def test_detect_quantitative_catalyst_endpoint_response_structure(mock_transformers_pipeline):
    """Test POST /detect-quantitative-catalyst has complete response structure."""
    import sys

    # Clear module cache
    if "benz_sent_filter.api.app" in sys.modules:
        del sys.modules["benz_sent_filter.api.app"]
    if "benz_sent_filter.services.classifier" in sys.modules:
        del sys.modules["benz_sent_filter.services.classifier"]

    # Mock MNLI scores
    mock_transformers_pipeline({
        "This announces a corporate financial event with specific dollar amounts such as dividends, acquisitions, buybacks, earnings results, or revenue guidance": 0.85,
        "This describes general commentary, stock price changes, analyst opinions, or vague business updates without specific financial transactions": 0.15,
        "This announces that the company is paying out a dividend to shareholders": 0.75,
        "This does not announce a dividend payment to shareholders": 0.25,
        "This announces that the company is purchasing or acquiring another company or assets": 0.2,
        "This is not about the company purchasing or acquiring another company": 0.8,
        "This announces that the company is repurchasing its own shares from the market": 0.3,
        "This is not about the company repurchasing its own shares": 0.7,
        "This announces historical earnings results, net income, or profit from a completed reporting period": 0.2,
        "This is not about historical earnings results or net income from a completed reporting period": 0.8,
        "This provides forward-looking financial projections or guidance for future periods": 0.3,
        "This is not about forward-looking financial projections or guidance": 0.7,
    })

    from benz_sent_filter.api.app import app
    from fastapi.testclient import TestClient

    with TestClient(app) as client:
        response = client.post(
            "/detect-quantitative-catalyst",
            json={"headline": "Test dividend $1/share"}
        )

    assert response.status_code == 200
    data = response.json()

    # Verify all required fields present
    assert "headline" in data
    assert isinstance(data["headline"], str)

    assert "has_quantitative_catalyst" in data
    assert isinstance(data["has_quantitative_catalyst"], bool)

    assert "catalyst_type" in data
    assert data["catalyst_type"] in ["dividend", "acquisition", "buyback", "earnings", "guidance", "mixed", None]

    assert "catalyst_values" in data
    assert isinstance(data["catalyst_values"], list)

    assert "confidence" in data
    assert isinstance(data["confidence"], float)
    assert 0.0 <= data["confidence"] <= 1.0


# ============================================================================
# Conditional Language Detection API Integration Tests (Phase 4)
# ============================================================================


def test_classify_endpoint_conditional_language_detected_future_event(mock_transformers_pipeline):
    """Test POST /classify returns conditional language fields for FUTURE_EVENT with conditional patterns."""
    import sys

    # Clear module cache
    if "benz_sent_filter.api.app" in sys.modules:
        del sys.modules["benz_sent_filter.api.app"]
    if "benz_sent_filter.services.classifier" in sys.modules:
        del sys.modules["benz_sent_filter.services.classifier"]

    mock_transformers_pipeline({
        "This is an opinion piece or editorial": 0.2,
        "This is a factual news report": 0.75,
        "This is about a past event that already happened": 0.1,
        "This is about a future event or forecast": 0.7,
        "This is a general topic or analysis": 0.2,
        "This article describes a routine business operation like quarterly dividends, regular loan portfolio sales, scheduled buybacks, or normal refinancing": 0.3,
    })

    from benz_sent_filter.api.app import app
    from fastapi.testclient import TestClient

    with TestClient(app) as client:
        response = client.post(
            "/classify",
            json={"headline": "Apple plans to explore AI opportunities in 2025"}
        )

    assert response.status_code == 200
    data = response.json()

    # Verify temporal category
    assert data["temporal_category"] == "future_event"

    # Verify conditional language fields present
    assert data["conditional_language"] is True
    assert "conditional_patterns" in data
    assert "plans to" in data["conditional_patterns"]
    assert "explore" in data["conditional_patterns"]


def test_classify_endpoint_no_conditional_language_concrete_future(mock_transformers_pipeline):
    """Test POST /classify excludes conditional fields for concrete FUTURE_EVENT statements."""
    import sys

    # Clear module cache
    if "benz_sent_filter.api.app" in sys.modules:
        del sys.modules["benz_sent_filter.api.app"]
    if "benz_sent_filter.services.classifier" in sys.modules:
        del sys.modules["benz_sent_filter.services.classifier"]

    mock_transformers_pipeline({
        "This is an opinion piece or editorial": 0.2,
        "This is a factual news report": 0.75,
        "This is about a past event that already happened": 0.1,
        "This is about a future event or forecast": 0.7,
        "This is a general topic or analysis": 0.2,
        "This article describes a routine business operation like quarterly dividends, regular loan portfolio sales, scheduled buybacks, or normal refinancing": 0.3,
    })

    from benz_sent_filter.api.app import app
    from fastapi.testclient import TestClient

    with TestClient(app) as client:
        response = client.post(
            "/classify",
            json={"headline": "Apple will launch iPhone 16 in September"}
        )

    assert response.status_code == 200
    data = response.json()

    # Verify temporal category
    assert data["temporal_category"] == "future_event"

    # Verify conditional language fields NOT in response (exclude_none)
    assert "conditional_language" not in data
    assert "conditional_patterns" not in data


def test_classify_endpoint_conditional_language_not_detected_past_event(mock_transformers_pipeline):
    """Test POST /classify excludes conditional fields for PAST_EVENT (even with conditional words)."""
    import sys

    # Clear module cache
    if "benz_sent_filter.api.app" in sys.modules:
        del sys.modules["benz_sent_filter.api.app"]
    if "benz_sent_filter.services.classifier" in sys.modules:
        del sys.modules["benz_sent_filter.services.classifier"]

    mock_transformers_pipeline({
        "This is an opinion piece or editorial": 0.2,
        "This is a factual news report": 0.75,
        "This is about a past event that already happened": 0.7,
        "This is about a future event or forecast": 0.1,
        "This is a general topic or analysis": 0.2,
        "This article describes a routine business operation like quarterly dividends, regular loan portfolio sales, scheduled buybacks, or normal refinancing": 0.3,
    })

    from benz_sent_filter.api.app import app
    from fastapi.testclient import TestClient

    with TestClient(app) as client:
        response = client.post(
            "/classify",
            json={"headline": "Apple planned to expand but changed direction"}
        )

    assert response.status_code == 200
    data = response.json()

    # Verify temporal category
    assert data["temporal_category"] == "past_event"

    # Verify conditional language fields NOT in response (only analyzed for FUTURE_EVENT)
    assert "conditional_language" not in data
    assert "conditional_patterns" not in data


def test_classify_endpoint_conditional_with_far_future_combination(mock_transformers_pipeline):
    """Test POST /classify with both conditional language and far-future patterns."""
    import sys

    # Clear module cache
    if "benz_sent_filter.api.app" in sys.modules:
        del sys.modules["benz_sent_filter.api.app"]
    if "benz_sent_filter.services.classifier" in sys.modules:
        del sys.modules["benz_sent_filter.services.classifier"]

    mock_transformers_pipeline({
        "This is an opinion piece or editorial": 0.2,
        "This is a factual news report": 0.75,
        "This is about a past event that already happened": 0.1,
        "This is about a future event or forecast": 0.7,
        "This is a general topic or analysis": 0.2,
        "This article describes a routine business operation like quarterly dividends, regular loan portfolio sales, scheduled buybacks, or normal refinancing": 0.3,
    })

    from benz_sent_filter.api.app import app
    from fastapi.testclient import TestClient

    with TestClient(app) as client:
        response = client.post(
            "/classify",
            json={"headline": "Dell may target $10B revenue by 2028"}
        )

    assert response.status_code == 200
    data = response.json()

    # Verify temporal category
    assert data["temporal_category"] == "future_event"

    # Verify conditional language fields present
    assert data["conditional_language"] is True
    assert "conditional_patterns" in data
    assert "may" in data["conditional_patterns"]

    # Verify far-future fields also present
    assert data["far_future_forecast"] is True
    assert data["forecast_timeframe"] is not None
    assert "2028" in data["forecast_timeframe"]


# ============================================================================
# Strategic Catalyst Detection API Endpoint Tests (Phase 2)
# ============================================================================


def test_detect_strategic_catalyst_endpoint_executive_change(mock_transformers_pipeline):
    """Test POST /detect-strategic-catalyst detects executive changes."""
    import sys

    # Clear module cache
    if "benz_sent_filter.api.app" in sys.modules:
        del sys.modules["benz_sent_filter.api.app"]
    if "benz_sent_filter.services.classifier" in sys.modules:
        del sys.modules["benz_sent_filter.services.classifier"]

    # Mock MNLI scores for strategic catalyst detection (tuned labels)
    mock_transformers_pipeline({
        "This announces a specific strategic corporate event like an executive change, merger, partnership, product launch, or rebranding": 0.9,
        "This describes financial results, stock price movements, routine operations, or general market commentary": 0.1,
        "This announces that a C-suite executive (CEO, CFO, President, or COO) is joining, leaving, stepping down from, or being appointed to their leadership position": 0.85,
        "This does not announce executive appointments, departures, or C-suite leadership transitions": 0.15,
        "This announces that two or more separate companies are signing an agreement to collaborate, partner, or work together on a joint project while remaining independent companies": 0.2,
        "This does not announce a partnership, collaboration agreement, or companies working together while staying separate": 0.8,
        "This announces that a single company is launching, releasing, or making available a new finished product, service, or platform that is ready for customers to use now": 0.15,
        "This does not announce a product launch, release, or new offering becoming available to customers": 0.85,
        "This announces a merger where companies combine into one entity or an acquisition where one company purchases and takes control of another company": 0.1,
        "This does not announce a merger, acquisition, or companies combining into a single entity": 0.9,
        "This announces a company is changing its corporate name, rebranding its identity, changing its ticker symbol, or restructuring its corporate structure": 0.1,
        "This does not announce a name change, rebranding, ticker change, or corporate restructuring": 0.9,
        "This announces positive or negative results, outcomes, or data from a completed Phase 1, Phase 2, or Phase 3 clinical trial or medical study": 0.05,
        "This does not announce clinical trial results, medical study outcomes, or research findings from completed trials": 0.95,
    })

    from benz_sent_filter.api.app import app
    from fastapi.testclient import TestClient

    with TestClient(app) as client:
        response = client.post(
            "/detect-strategic-catalyst",
            json={"headline": "X4 Pharmaceuticals' President And CEO Paula Ragan And CFO Adam Mostafa Have Stepped Down..."}
        )

    assert response.status_code == 200
    data = response.json()

    # Verify response structure
    assert "headline" in data
    assert "has_strategic_catalyst" in data
    assert "catalyst_subtype" in data
    assert "confidence" in data

    # Verify detection
    assert data["has_strategic_catalyst"] is True
    assert data["catalyst_subtype"] == "executive_changes"
    assert data["confidence"] >= 0.6


def test_detect_strategic_catalyst_endpoint_merger(mock_transformers_pipeline):
    """Test POST /detect-strategic-catalyst detects merger agreements."""
    import sys

    # Clear module cache
    if "benz_sent_filter.api.app" in sys.modules:
        del sys.modules["benz_sent_filter.api.app"]
    if "benz_sent_filter.services.classifier" in sys.modules:
        del sys.modules["benz_sent_filter.services.classifier"]

    # Mock MNLI scores for merger detection (tuned labels)
    mock_transformers_pipeline({
        "This announces a specific strategic corporate event like an executive change, merger, partnership, product launch, or rebranding": 0.92,
        "This describes financial results, stock price movements, routine operations, or general market commentary": 0.08,
        "This announces that a C-suite executive (CEO, CFO, President, or COO) is joining, leaving, stepping down from, or being appointed to their leadership position": 0.1,
        "This does not announce executive appointments, departures, or C-suite leadership transitions": 0.9,
        "This announces that two or more separate companies are signing an agreement to collaborate, partner, or work together on a joint project while remaining independent companies": 0.2,
        "This does not announce a partnership, collaboration agreement, or companies working together while staying separate": 0.8,
        "This announces that a single company is launching, releasing, or making available a new finished product, service, or platform that is ready for customers to use now": 0.15,
        "This does not announce a product launch, release, or new offering becoming available to customers": 0.85,
        "This announces a merger where companies combine into one entity or an acquisition where one company purchases and takes control of another company": 0.88,
        "This does not announce a merger, acquisition, or companies combining into a single entity": 0.12,
        "This announces a company is changing its corporate name, rebranding its identity, changing its ticker symbol, or restructuring its corporate structure": 0.1,
        "This does not announce a name change, rebranding, ticker change, or corporate restructuring": 0.9,
        "This announces positive or negative results, outcomes, or data from a completed Phase 1, Phase 2, or Phase 3 clinical trial or medical study": 0.05,
        "This does not announce clinical trial results, medical study outcomes, or research findings from completed trials": 0.95,
    })

    from benz_sent_filter.api.app import app
    from fastapi.testclient import TestClient

    with TestClient(app) as client:
        response = client.post(
            "/detect-strategic-catalyst",
            json={"headline": "Workhorse Group And ATW Partners Announce Merger Agreement"}
        )

    assert response.status_code == 200
    data = response.json()

    assert data["has_strategic_catalyst"] is True
    assert data["catalyst_subtype"] == "m&a"
    assert data["confidence"] >= 0.6


def test_detect_strategic_catalyst_endpoint_no_catalyst(mock_transformers_pipeline):
    """Test POST /detect-strategic-catalyst returns false for non-catalyst headlines."""
    import sys

    # Clear module cache
    if "benz_sent_filter.api.app" in sys.modules:
        del sys.modules["benz_sent_filter.api.app"]
    if "benz_sent_filter.services.classifier" in sys.modules:
        del sys.modules["benz_sent_filter.services.classifier"]

    # Mock MNLI scores for non-catalyst (financial results)
    mock_transformers_pipeline({
        "This announces a specific strategic corporate event like an executive change, merger, partnership, product launch, or rebranding": 0.2,
        "This describes financial results, stock price movements, routine operations, or general market commentary": 0.8,
        "This announces a C-suite executive appointment, departure, or transition including CEO, CFO, President, or other senior leadership": 0.1,
        "This does not announce an executive leadership change": 0.9,
        "This announces a strategic partnership, collaboration agreement, memorandum of understanding, or joint venture": 0.15,
        "This does not announce a strategic partnership": 0.85,
        "This announces a new product launch, technology platform deployment, or service introduction": 0.1,
        "This does not announce a product launch": 0.9,
        "This announces a merger agreement, acquisition announcement, or strategic combination": 0.1,
        "This does not announce a merger or acquisition": 0.9,
        "This announces a company name change, ticker symbol change, or corporate rebranding": 0.05,
        "This does not announce a rebranding": 0.95,
        "This announces clinical trial results, medical research findings, or drug efficacy data": 0.05,
        "This does not announce clinical trial results": 0.95,
    })

    from benz_sent_filter.api.app import app
    from fastapi.testclient import TestClient

    with TestClient(app) as client:
        response = client.post(
            "/detect-strategic-catalyst",
            json={"headline": "Company reports Q3 earnings of $1.2B revenue"}
        )

    assert response.status_code == 200
    data = response.json()

    assert data["has_strategic_catalyst"] is False
    # catalyst_subtype is excluded when None (exclude_none=True)
    assert "catalyst_subtype" not in data
    # Confidence reflects presence score even when no catalyst detected
    assert data["confidence"] < 0.5  # Below presence threshold


def test_detect_strategic_catalyst_endpoint_validation_empty_headline(client):
    """Test POST /detect-strategic-catalyst with empty headline returns 422."""
    response = client.post(
        "/detect-strategic-catalyst",
        json={"headline": ""}
    )

    assert response.status_code == 422


def test_detect_strategic_catalyst_endpoint_validation_missing_headline(client):
    """Test POST /detect-strategic-catalyst without headline field returns 422."""
    response = client.post(
        "/detect-strategic-catalyst",
        json={}
    )

    assert response.status_code == 422


def test_detect_strategic_catalyst_response_model_structure(mock_transformers_pipeline):
    """Test POST /detect-strategic-catalyst has correct response structure."""
    import sys

    # Clear module cache
    if "benz_sent_filter.api.app" in sys.modules:
        del sys.modules["benz_sent_filter.api.app"]
    if "benz_sent_filter.services.classifier" in sys.modules:
        del sys.modules["benz_sent_filter.services.classifier"]

    # Mock MNLI scores for clinical trial results
    mock_transformers_pipeline({
        "This announces a specific strategic corporate event like an executive change, merger, partnership, product launch, or rebranding": 0.9,
        "This describes financial results, stock price movements, routine operations, or general market commentary": 0.1,
        "This announces a C-suite executive appointment, departure, or transition including CEO, CFO, President, or other senior leadership": 0.1,
        "This does not announce an executive leadership change": 0.9,
        "This announces a strategic partnership, collaboration agreement, memorandum of understanding, or joint venture": 0.15,
        "This does not announce a strategic partnership": 0.85,
        "This announces a new product launch, technology platform deployment, or service introduction": 0.1,
        "This does not announce a product launch": 0.9,
        "This announces a merger agreement, acquisition announcement, or strategic combination": 0.1,
        "This does not announce a merger or acquisition": 0.9,
        "This announces a company name change, ticker symbol change, or corporate rebranding": 0.05,
        "This does not announce a rebranding": 0.95,
        "This announces clinical trial results, medical research findings, or drug efficacy data": 0.82,
        "This does not announce clinical trial results": 0.18,
    })

    from benz_sent_filter.api.app import app
    from fastapi.testclient import TestClient

    with TestClient(app) as client:
        response = client.post(
            "/detect-strategic-catalyst",
            json={"headline": "Positron Announces Positive Phase 1 Clinical Trial Results"}
        )

    assert response.status_code == 200
    data = response.json()

    # Verify all required fields present
    assert "headline" in data
    assert isinstance(data["headline"], str)

    assert "has_strategic_catalyst" in data
    assert isinstance(data["has_strategic_catalyst"], bool)

    assert "catalyst_subtype" in data
    assert data["catalyst_subtype"] in ["executive_changes", "m&a", "partnership", "product_launch", "corporate_restructuring", "clinical_trial", "mixed", None]

    assert "confidence" in data
    assert isinstance(data["confidence"], float)
    assert 0.0 <= data["confidence"] <= 1.0


def test_detect_strategic_catalyst_backward_compatibility(client):
    """Test that existing endpoints work unchanged after adding strategic catalyst endpoint."""
    # Test /health endpoint
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"

    # Test /classify endpoint
    response = client.post("/classify", json={"headline": "Test headline"})
    assert response.status_code == 200
    assert "is_opinion" in response.json()
    assert "is_straight_news" in response.json()
    assert "temporal_category" in response.json()

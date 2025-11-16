"""Tests for the API endpoints."""

import pytest
from fastapi.testclient import TestClient

from benz_sent_filter.api.app import app


@pytest.fixture
def client():
    """Create a test client for the FastAPI app."""
    return TestClient(app)


def test_health_check(client):
    """Test the health check endpoint."""
    response = client.get("/health")
    assert response.status_code == 200

    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "benz_sent_filter"
    assert "timestamp" in data

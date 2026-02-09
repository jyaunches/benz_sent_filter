"""Pytest configuration for integration tests."""

import pytest


@pytest.fixture(scope="module")
def real_classifier():
    """Create real classification service shared across all tests in this module.

    Module scope ensures the model loads only once per test file, significantly
    improving test execution speed while maintaining sufficient isolation.

    The ClassificationService is stateless, so sharing the instance across tests
    is safe and reflects realistic usage (service persists across requests).

    Returns:
        ClassificationService: Real service with loaded DeBERTa-MNLI model
    """
    from benz_sent_filter.services.classifier import ClassificationService

    return ClassificationService()


# Sample headline fixtures (needed by integration tests)
@pytest.fixture
def sample_headline_opinion():
    """Sample opinion/editorial headline for testing."""
    return "Why Tesla Is Doomed and Investors Should Sell Now"


@pytest.fixture
def sample_headline_news():
    """Sample straight news headline for testing."""
    return "Tesla Reports Q4 Earnings Beat Expectations"


@pytest.fixture
def sample_headline_past():
    """Sample past event headline for testing."""
    return "Fed Raised Interest Rates by 0.25% Yesterday"


@pytest.fixture
def sample_headline_future():
    """Sample future event headline for testing."""
    return "Fed to Announce Rate Decision Next Week"


@pytest.fixture
def sample_headline_general():
    """Sample general topic headline for testing."""
    return "How Tesla Changed the EV Market"

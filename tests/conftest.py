"""Pytest configuration and fixtures for benz_sent_filter tests."""

import pytest


@pytest.fixture
def sample_headline_opinion():
    """Sample opinion headline for testing."""
    return "Why the Fed Is Wrong About Inflation"


@pytest.fixture
def sample_headline_news():
    """Sample straight news headline for testing."""
    return "Fed Raises Interest Rates by 25 Basis Points"


@pytest.fixture
def sample_headline_past():
    """Sample past event headline for testing."""
    return "Tesla Shares Surge After Yesterday's Earnings Beat"


@pytest.fixture
def sample_headline_future():
    """Sample future event headline for testing."""
    return "Tesla to Report Q4 Earnings Next Week"


@pytest.fixture
def sample_headline_general():
    """Sample general topic headline for testing."""
    return "How Tesla Changed the EV Market"

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


@pytest.fixture
def mock_transformers_pipeline(monkeypatch):
    """Factory fixture for creating mocked pipeline with configurable scores.

    This fixture provides a reusable way to mock transformers.pipeline across all unit tests.
    Use this instead of creating inline mocks to ensure consistency and reduce duplication.

    Usage:
        def test_example(mock_transformers_pipeline):
            # Create mock with specific scores for each label
            mock_transformers_pipeline({
                "This is an opinion piece or editorial": 0.75,
                "This is a factual news report": 0.25,
                "This is about a past event that already happened": 0.1,
                "This is about a future event or forecast": 0.1,
                "This is a general topic or analysis": 0.2
            })
            # Now create ClassificationService - it will use the mocked pipeline
            service = ClassificationService()
            result = service.classify_headline("test headline")
    """
    # Store score dict in mutable container so nested function can update it
    score_dict_container = [{}]

    def _mock_pipeline(task, model):
        def pipeline_fn(text, candidate_labels):
            # Use the current score dict from the container
            scores = [
                score_dict_container[0].get(label, 0.2) for label in candidate_labels
            ]
            return {"labels": candidate_labels, "scores": scores}

        return pipeline_fn

    # Apply the mock once (before any imports)
    monkeypatch.setattr("transformers.pipeline", _mock_pipeline)

    def _create_mock(score_dict: dict[str, float]):
        # Update the score dict in the container
        score_dict_container[0] = score_dict

    return _create_mock

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
        ClassificationService: Real service with loaded DistilBERT-MNLI model
    """
    from benz_sent_filter.services.classifier import ClassificationService

    return ClassificationService()

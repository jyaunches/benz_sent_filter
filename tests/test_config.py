"""Tests for configuration module."""

import pytest


def test_model_name_constant_exists():
    """Test MODEL_NAME constant is accessible and has correct value."""
    from benz_sent_filter.config.settings import MODEL_NAME

    assert isinstance(MODEL_NAME, str)
    assert MODEL_NAME == "typeform/distilbert-base-uncased-mnli"


def test_classification_threshold_constant():
    """Test CLASSIFICATION_THRESHOLD constant is accessible and has correct value."""
    from benz_sent_filter.config.settings import CLASSIFICATION_THRESHOLD

    assert isinstance(CLASSIFICATION_THRESHOLD, float)
    assert CLASSIFICATION_THRESHOLD == 0.6


def test_constants_are_module_level():
    """Test constants are module-level (not class attributes)."""
    from benz_sent_filter.config import settings

    # Constants should be directly accessible as module attributes
    assert hasattr(settings, "MODEL_NAME")
    assert hasattr(settings, "CLASSIFICATION_THRESHOLD")

    # Should be importable directly (not through a class)
    from benz_sent_filter.config.settings import (
        CLASSIFICATION_THRESHOLD,
        MODEL_NAME,
    )

    assert isinstance(MODEL_NAME, str)
    assert isinstance(CLASSIFICATION_THRESHOLD, float)

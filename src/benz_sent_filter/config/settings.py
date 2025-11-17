"""Configuration settings for benz_sent_filter.

This module provides simple module-level constants for ML model configuration.
No class-based settings or environment variables - just constants.
"""

# Model configuration
MODEL_NAME: str = "typeform/distilbert-base-uncased-mnli"

# Classification threshold for boolean conversion
CLASSIFICATION_THRESHOLD: float = 0.6

"""Configuration settings for benz_sent_filter.

This module provides pydantic-settings based configuration for the service.
Module-level constants are exported for backward compatibility.
"""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings with type validation."""

    # Model Configuration
    model_name: str = Field(
        default="MoritzLaurer/deberta-v3-large-zeroshot-v2.0",
        description="HuggingFace model for sentiment classification"
    )

    # Classification Thresholds
    classification_threshold: float = Field(
        default=0.6,
        ge=0.0,
        le=1.0,
        description="Classification threshold for boolean conversion"
    )
    company_relevance_threshold: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="Company relevance threshold (lower than opinion/news threshold)"
    )

    # API Configuration
    api_host: str = Field(default="0.0.0.0", description="API host to bind to")
    api_port: int = Field(default=8002, ge=1, le=65535, description="API port to bind to")
    uvicorn_workers: int = Field(
        default=1,
        ge=1,
        le=16,
        description="Number of uvicorn workers for concurrent request handling"
    )

    # Logging
    log_level: str = Field(default="INFO", description="Logging level")

    # Model configuration
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )


# Global settings instance
settings = Settings()

# Backward compatibility: Export module-level constants
MODEL_NAME: str = settings.model_name
CLASSIFICATION_THRESHOLD: float = settings.classification_threshold
COMPANY_RELEVANCE_THRESHOLD: float = settings.company_relevance_threshold

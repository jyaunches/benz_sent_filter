"""Loguru logging configuration for benz_sent_filter."""

import os
from pathlib import Path

from loguru import logger


def setup_logging():
    """Setup Loguru logging configuration.

    Configures two handlers:
    1. JSON file handler with daily rotation for Loki ingestion
    2. Colored console handler for development

    Log level controlled by LOG_LEVEL environment variable (default: INFO).
    """
    logger.remove()  # Remove default handler

    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)

    log_level = os.getenv("LOG_LEVEL", "INFO")

    # JSON file handler with daily rotation
    logger.add(
        log_dir / "benz_sent_filter_{time:YYYY-MM-DD}.log",
        rotation="1 day",
        serialize=True,  # JSON output for Loki
        level=log_level,
    )

    # Colored console for development
    logger.add(
        lambda msg: print(msg, end=""),
        colorize=True,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>",
        level=log_level,
    )

    logger.info("Logging initialized", service="benz_sent_filter", log_level=log_level)

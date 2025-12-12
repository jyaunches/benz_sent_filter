"""Entry point for running the benz_sent_filter service."""

import sys

import uvicorn
from loguru import logger

from benz_sent_filter.config.settings import Settings
from benz_sent_filter.logging_config import setup_logging


def main():
    """Run the benz_sent_filter service."""
    # Setup Loguru logging first
    setup_logging()

    # Load settings
    try:
        settings = Settings()
        logger.info(
            "Settings loaded successfully",
            api_host=settings.api_host,
            api_port=settings.api_port,
            log_level=settings.log_level,
            uvicorn_workers=settings.uvicorn_workers,
        )
    except Exception as e:
        logger.error("Failed to load settings", error=str(e))
        sys.exit(1)

    # Run the server
    logger.info(
        "Starting uvicorn server",
        host=settings.api_host,
        port=settings.api_port,
        workers=settings.uvicorn_workers,
    )
    uvicorn.run(
        "benz_sent_filter.api.app:app",
        host=settings.api_host,
        port=settings.api_port,
        log_level=settings.log_level.lower(),
        workers=settings.uvicorn_workers,
    )


if __name__ == "__main__":
    main()

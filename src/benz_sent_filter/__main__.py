"""Entry point for running the benz_sent_filter service."""

import logging
import sys

import uvicorn

from benz_sent_filter.config.settings import Settings


def main():
    """Run the benz_sent_filter service."""
    # Load settings first to get log level
    try:
        settings = Settings()
    except Exception as e:
        logging.error(f"Failed to load settings: {e}")
        sys.exit(1)

    # Configure logging with settings
    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper()),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    # Configure uvicorn logging
    log_config = uvicorn.config.LOGGING_CONFIG
    log_config["formatters"]["default"]["fmt"] = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    log_config["formatters"]["access"]["fmt"] = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

    # Run the server
    uvicorn.run(
        "benz_sent_filter.api.app:app",
        host=settings.api_host,
        port=settings.api_port,
        log_level=settings.log_level.lower(),
        log_config=log_config,
        workers=settings.uvicorn_workers,
    )


if __name__ == "__main__":
    main()

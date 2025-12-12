"""RunPod serverless handler for benz_sent_filter.

This module provides a thin wrapper around ClassificationService for RunPod GPU deployment.
The service is loaded once at module level (worker startup) and reused across requests.
"""

import runpod
from loguru import logger

from benz_sent_filter.services.classifier import ClassificationService

# Load service at module level (once per worker)
logger.info("Initializing ClassificationService for RunPod worker")
service = ClassificationService()
logger.info("ClassificationService ready for requests")


def handler(job: dict) -> dict:
    """Process RunPod job and return classification results.

    Args:
        job: RunPod job dict with 'input' key containing:
            - operation: str - One of: classify, classify_batch, routine_operations,
                             company_relevance, company_relevance_batch,
                             detect_quantitative_catalyst, detect_strategic_catalyst
            - Additional fields depend on operation

    Returns:
        Dict with operation-specific results (Pydantic models converted to dicts)

    Raises:
        ValueError: For invalid operations or missing required fields
    """
    try:
        job_input = job.get("input", {})
        operation = job_input.get("operation")

        if not operation:
            raise ValueError("Missing required field 'operation'")

        # Route to appropriate ClassificationService method
        if operation == "classify":
            headline = job_input.get("headline")
            if not headline:
                raise ValueError("Missing required field 'headline' for classify operation")

            company = job_input.get("company")

            result = service.classify_headline(
                headline=headline,
                company=company,
            )
            # Convert Pydantic model to dict for JSON serialization
            return result.model_dump(exclude_none=True)

        elif operation == "classify_batch":
            headlines = job_input.get("headlines")
            if not headlines:
                raise ValueError("Missing required field 'headlines' for classify_batch operation")

            company = job_input.get("company")

            results = service.classify_batch(
                headlines=headlines,
                company=company,
            )
            # Convert list of Pydantic models to list of dicts
            return [r.model_dump(exclude_none=True) for r in results]

        elif operation == "routine_operations":
            headline = job_input.get("headline")
            ticker_symbols = job_input.get("ticker_symbols")

            if not headline:
                raise ValueError("Missing required field 'headline' for routine_operations operation")
            if not ticker_symbols:
                raise ValueError("Missing required field 'ticker_symbols' for routine_operations operation")

            result = service.classify_headline_multi_ticker(
                headline=headline,
                ticker_symbols=ticker_symbols,
            )
            # Result is already a dict with nested dicts
            return result

        elif operation == "company_relevance":
            headline = job_input.get("headline")
            company = job_input.get("company")

            if not headline:
                raise ValueError("Missing required field 'headline' for company_relevance operation")
            if not company:
                raise ValueError("Missing required field 'company' for company_relevance operation")

            result = service.check_company_relevance(headline=headline, company=company)
            return result

        elif operation == "company_relevance_batch":
            headlines = job_input.get("headlines")
            company = job_input.get("company")

            if not headlines:
                raise ValueError("Missing required field 'headlines' for company_relevance_batch operation")
            if not company:
                raise ValueError("Missing required field 'company' for company_relevance_batch operation")

            results = service.check_company_relevance_batch(headlines=headlines, company=company)
            return results

        elif operation == "detect_quantitative_catalyst":
            headline = job_input.get("headline")

            if not headline:
                raise ValueError("Missing required field 'headline' for detect_quantitative_catalyst operation")

            result = service.detect_quantitative_catalyst(headline=headline)
            # Convert Pydantic model to dict
            return result.model_dump(exclude_none=True)

        elif operation == "detect_strategic_catalyst":
            headline = job_input.get("headline")

            if not headline:
                raise ValueError("Missing required field 'headline' for detect_strategic_catalyst operation")

            result = service.detect_strategic_catalyst(headline=headline)
            # Convert Pydantic model to dict
            return result.model_dump(exclude_none=True)

        else:
            raise ValueError(f"Invalid operation: {operation}")

    except Exception as e:
        logger.error(f"Handler error: {e}", operation=operation if 'operation' in locals() else None)
        raise


if __name__ == "__main__":
    # Start RunPod serverless handler
    logger.info("Starting RunPod serverless handler")
    runpod.serverless.start({"handler": handler})

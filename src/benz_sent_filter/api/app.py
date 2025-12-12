"""FastAPI application for benz_sent_filter."""

import time
from datetime import datetime

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from loguru import logger
from pydantic import BaseModel

from benz_sent_filter.models.classification import (
    BatchClassificationResult,
    BatchClassifyRequest,
    ClassificationResult,
    ClassifyRequest,
    CompanyRelevanceBatchRequest,
    CompanyRelevanceBatchResponse,
    CompanyRelevanceRequest,
    CompanyRelevanceResult,
    MultiTickerRoutineRequest,
    MultiTickerRoutineResponse,
    QuantitativeCatalystRequest,
    QuantitativeCatalystResult,
    StrategicCatalystRequest,
    StrategicCatalystResult,
)
from benz_sent_filter.services.classifier import ClassificationService
from benz_sent_filter.logging_config import setup_logging


# Initialize logging when module is imported (covers both direct uvicorn and __main__ entry)
# setup_logging() is idempotent - safe to call multiple times
setup_logging()


app = FastAPI(
    title="Benz Sent Filter",
    description="MNLS-based sentiment classification service for article title analysis",
    version="0.1.0",
)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all HTTP requests and responses with timing."""
    start_time = time.time()

    # Log incoming request
    logger.info(
        "HTTP request received",
        method=request.method,
        path=request.url.path,
        client_host=request.client.host if request.client else None,
    )

    # Process request
    response = await call_next(request)

    # Calculate duration
    duration = time.time() - start_time

    # Log response
    logger.info(
        "HTTP request completed",
        method=request.method,
        path=request.url.path,
        status_code=response.status_code,
        duration_ms=round(duration * 1000, 2),
    )

    return response


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Log validation errors for debugging and return 422 response."""
    logger.error(
        "Validation error",
        method=request.method,
        path=request.url.path,
        errors=exc.errors(),
    )
    # Return standard 422 response
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": exc.errors()},
    )


class HealthResponse(BaseModel):
    """Health check response model."""

    status: str
    service: str
    timestamp: datetime


@app.on_event("startup")
async def startup_event():
    """Initialize classification service on startup (eager loading)."""
    logger.info("FastAPI startup event - initializing classification service")
    start_time = time.time()
    app.state.classifier = ClassificationService()
    duration = time.time() - start_time
    logger.info(
        "Classification service initialized successfully",
        duration_seconds=round(duration, 2),
    )


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown."""
    logger.info("FastAPI shutdown event - cleaning up resources")


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    logger.debug("Health check requested")
    return HealthResponse(
        status="healthy",
        service="benz_sent_filter",
        timestamp=datetime.utcnow(),
    )


@app.post("/classify", response_model=ClassificationResult, response_model_exclude_none=True)
async def classify_headline(request: ClassifyRequest):
    """Classify a single headline.

    Returns boolean flags, temporal category, and all raw scores.
    Optionally includes company relevance when company parameter provided.
    """
    logger.info(
        "POST /classify",
        headline_length=len(request.headline),
        has_company=request.company is not None,
    )
    start_time = time.time()

    result = app.state.classifier.classify_headline(
        request.headline, company=request.company
    )

    duration = time.time() - start_time
    logger.info(
        "POST /classify completed",
        status="success",
        duration_ms=round(duration * 1000, 2),
    )
    return result


@app.post("/classify/batch", response_model=BatchClassificationResult, response_model_exclude_none=True)
async def classify_batch(request: BatchClassifyRequest):
    """Classify multiple headlines.

    Returns array of classification results in same order as input.
    Optionally includes company relevance when company parameter provided.
    """
    logger.info(
        "POST /classify/batch",
        batch_size=len(request.headlines),
        has_company=request.company is not None,
    )
    start_time = time.time()

    results = app.state.classifier.classify_batch(
        request.headlines, company=request.company
    )

    duration = time.time() - start_time
    logger.info(
        "POST /classify/batch completed",
        status="success",
        batch_size=len(results),
        duration_ms=round(duration * 1000, 2),
    )
    return BatchClassificationResult(results=results)


@app.post("/routine-operations", response_model=MultiTickerRoutineResponse, response_model_exclude_none=True)
async def classify_routine_operations_multi_ticker(request: MultiTickerRoutineRequest):
    """Classify routine operations for multiple ticker symbols.

    Optimized endpoint that runs core classification once, then analyzes
    routine operations separately for each ticker symbol. Provides 40-50%
    performance improvement over multiple /classify calls.

    Args:
        request: Request containing headline and list of ticker symbols

    Returns:
        Core classification results plus routine operations analysis per ticker

    Example:
        Request:
        {
            "headline": "Bank announces quarterly dividend payment",
            "ticker_symbols": ["BAC", "JPM", "C"]
        }

        Response:
        {
            "headline": "Bank announces quarterly dividend payment",
            "core_classification": {
                "is_opinion": false,
                "is_straight_news": true,
                "temporal_category": "past_event",
                "scores": {...}
            },
            "routine_operations_by_ticker": {
                "BAC": {"routine_operation": true, "routine_confidence": 0.87, ...},
                "JPM": {"routine_operation": true, "routine_confidence": 0.65, ...},
                "C": {"routine_operation": true, "routine_confidence": 0.71, ...}
            }
        }
    """
    logger.info(
        "POST /routine-operations",
        headline_length=len(request.headline),
        ticker_count=len(request.ticker_symbols),
    )
    start_time = time.time()

    result = app.state.classifier.classify_headline_multi_ticker(
        request.headline, request.ticker_symbols
    )

    duration = time.time() - start_time
    logger.info(
        "POST /routine-operations completed",
        status="success",
        ticker_count=len(request.ticker_symbols),
        duration_ms=round(duration * 1000, 2),
    )
    return MultiTickerRoutineResponse(
        headline=request.headline,
        core_classification=result["core_classification"],
        routine_operations_by_ticker=result["routine_operations_by_ticker"],
    )


@app.post("/company-relevance", response_model=CompanyRelevanceResult)
async def check_company_relevance(request: CompanyRelevanceRequest):
    """Check if a headline is relevant to a specific company.

    Performs zero-shot NLI classification to determine if the headline
    is about the specified company.

    Args:
        request: Request containing headline and company name

    Returns:
        Relevance result with boolean flag and confidence score

    Example:
        Request:
        {
            "headline": "Dell launches new AI server platform",
            "company": "Dell"
        }

        Response:
        {
            "headline": "Dell launches new AI server platform",
            "company": "Dell",
            "is_about_company": true,
            "company_score": 0.92
        }
    """
    logger.info(
        "POST /company-relevance",
        headline_length=len(request.headline),
        company=request.company,
    )
    start_time = time.time()

    result = app.state.classifier.check_company_relevance(
        request.headline, request.company
    )

    duration = time.time() - start_time
    logger.info(
        "POST /company-relevance completed",
        status="success",
        is_about_company=result["is_about_company"],
        duration_ms=round(duration * 1000, 2),
    )
    return CompanyRelevanceResult(**result)


@app.post("/company-relevance/batch", response_model=CompanyRelevanceBatchResponse)
async def check_company_relevance_batch(request: CompanyRelevanceBatchRequest):
    """Check company relevance for multiple headlines.

    Analyzes multiple headlines against the same company name.

    Args:
        request: Request containing headlines list and company name

    Returns:
        Batch response with relevance results for all headlines

    Example:
        Request:
        {
            "headlines": [
                "Dell launches new AI server platform",
                "Tesla updates Autopilot software"
            ],
            "company": "Dell"
        }

        Response:
        {
            "company": "Dell",
            "results": [
                {
                    "headline": "Dell launches new AI server platform",
                    "is_about_company": true,
                    "company_score": 0.92
                },
                {
                    "headline": "Tesla updates Autopilot software",
                    "is_about_company": false,
                    "company_score": 0.15
                }
            ]
        }
    """
    logger.info(
        "POST /company-relevance/batch",
        batch_size=len(request.headlines),
        company=request.company,
    )
    start_time = time.time()

    results = app.state.classifier.check_company_relevance_batch(
        request.headlines, request.company
    )

    duration = time.time() - start_time
    logger.info(
        "POST /company-relevance/batch completed",
        status="success",
        batch_size=len(results),
        duration_ms=round(duration * 1000, 2),
    )
    return CompanyRelevanceBatchResponse(
        company=request.company,
        results=[CompanyRelevanceResult(**r) for r in results],
    )


@app.post("/detect-quantitative-catalyst", response_model=QuantitativeCatalystResult, response_model_exclude_none=True)
async def detect_quantitative_catalyst(request: QuantitativeCatalystRequest):
    """Detect quantitative financial catalysts in headline.

    Uses MNLI-based semantic understanding combined with regex value extraction
    to identify specific, quantitative financial catalysts such as dividends,
    acquisitions, buybacks, earnings, and guidance announcements.

    Args:
        request: Request containing headline text to analyze

    Returns:
        Detection result with catalyst presence, type, values, and confidence

    Example:
        Request:
        {
            "headline": "Universal Security Instruments Increases Quarterly Dividend to $1 Per Share"
        }

        Response:
        {
            "headline": "Universal Security Instruments Increases Quarterly Dividend to $1 Per Share",
            "has_quantitative_catalyst": true,
            "catalyst_type": "dividend",
            "catalyst_values": ["$1/Share"],
            "confidence": 0.87
        }
    """
    logger.info(
        "POST /detect-quantitative-catalyst", headline_length=len(request.headline)
    )
    start_time = time.time()

    result = app.state.classifier.detect_quantitative_catalyst(request.headline)

    duration = time.time() - start_time
    logger.info(
        "POST /detect-quantitative-catalyst completed",
        status="success",
        has_catalyst=result.has_quantitative_catalyst,
        catalyst_type=result.catalyst_type,
        duration_ms=round(duration * 1000, 2),
    )
    return result


@app.post("/detect-strategic-catalyst", response_model=StrategicCatalystResult, response_model_exclude_none=True)
async def detect_strategic_catalyst(request: StrategicCatalystRequest):
    """Detect strategic corporate catalysts in headline.

    Uses MNLI-based semantic understanding to identify strategic corporate
    catalysts such as executive changes, mergers, partnerships, product launches,
    rebranding, and clinical trial results.

    Args:
        request: Request containing headline text to analyze

    Returns:
        Detection result with catalyst presence, type, and confidence

    Example:
        Request:
        {
            "headline": "X4 Pharmaceuticals' President And CEO Paula Ragan And CFO Adam Mostafa Have Stepped Down..."
        }

        Response:
        {
            "headline": "X4 Pharmaceuticals' President And CEO Paula Ragan And CFO Adam Mostafa Have Stepped Down...",
            "has_strategic_catalyst": true,
            "catalyst_type": "executive_change",
            "confidence": 0.94
        }
    """
    logger.info(
        "POST /detect-strategic-catalyst", headline_length=len(request.headline)
    )
    start_time = time.time()

    result = app.state.classifier.detect_strategic_catalyst(request.headline)

    duration = time.time() - start_time
    logger.info(
        "POST /detect-strategic-catalyst completed",
        status="success",
        has_catalyst=result.has_strategic_catalyst,
        catalyst_subtype=result.catalyst_subtype,
        duration_ms=round(duration * 1000, 2),
    )
    return result

"""FastAPI application for benz_sent_filter."""

import logging
from datetime import datetime

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
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
)
from benz_sent_filter.services.classifier import ClassificationService

# Set up logging
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Benz Sent Filter",
    description="MNLS-based sentiment classification service for article title analysis",
    version="0.1.0",
)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Log validation errors with request payload for debugging."""
    body = await request.body()
    logger.error(
        f"Validation error on {request.method} {request.url.path}\n"
        f"Request body: {body.decode('utf-8')}\n"
        f"Errors: {exc.errors()}"
    )
    # Re-raise to return standard 422 response
    raise exc


class HealthResponse(BaseModel):
    """Health check response model."""

    status: str
    service: str
    timestamp: datetime


@app.on_event("startup")
async def startup_event():
    """Initialize classification service on startup (eager loading)."""
    app.state.classifier = ClassificationService()


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
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
    Optionally includes routine operation detection when company_symbol parameter provided.
    """
    result = app.state.classifier.classify_headline(
        request.headline, company=request.company, company_symbol=request.company_symbol
    )
    return result


@app.post("/classify/batch", response_model=BatchClassificationResult, response_model_exclude_none=True)
async def classify_batch(request: BatchClassifyRequest):
    """Classify multiple headlines.

    Returns array of classification results in same order as input.
    Optionally includes company relevance when company parameter provided.
    Optionally includes routine operation detection when company_symbol parameter provided.
    """
    results = app.state.classifier.classify_batch(
        request.headlines, company=request.company, company_symbol=request.company_symbol
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
    result = app.state.classifier.classify_headline_multi_ticker(
        request.headline, request.ticker_symbols
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
    result = app.state.classifier.check_company_relevance(
        request.headline, request.company
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
    results = app.state.classifier.check_company_relevance_batch(
        request.headlines, request.company
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
    result = app.state.classifier.detect_quantitative_catalyst(request.headline)
    return result

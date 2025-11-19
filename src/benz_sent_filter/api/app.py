"""FastAPI application for benz_sent_filter."""

from datetime import datetime

from fastapi import FastAPI
from pydantic import BaseModel

from benz_sent_filter.models.classification import (
    BatchClassificationResult,
    BatchClassifyRequest,
    ClassificationResult,
    ClassifyRequest,
    MultiTickerRoutineRequest,
    MultiTickerRoutineResponse,
)
from benz_sent_filter.services.classifier import ClassificationService

app = FastAPI(
    title="Benz Sent Filter",
    description="MNLS-based sentiment classification service for article title analysis",
    version="0.1.0",
)


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

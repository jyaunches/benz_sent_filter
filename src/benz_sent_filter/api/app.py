"""FastAPI application for benz_sent_filter."""

from datetime import datetime

from fastapi import FastAPI
from pydantic import BaseModel

from benz_sent_filter.models.classification import (
    BatchClassificationResult,
    BatchClassifyRequest,
    ClassificationResult,
    ClassifyRequest,
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
    """
    result = app.state.classifier.classify_headline(
        request.headline, company=request.company
    )
    return result


@app.post("/classify/batch", response_model=BatchClassificationResult, response_model_exclude_none=True)
async def classify_batch(request: BatchClassifyRequest):
    """Classify multiple headlines.

    Returns array of classification results in same order as input.
    Optionally includes company relevance when company parameter provided.
    """
    results = app.state.classifier.classify_batch(
        request.headlines, company=request.company
    )
    return BatchClassificationResult(results=results)

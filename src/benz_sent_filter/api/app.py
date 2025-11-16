"""FastAPI application for benz_sent_filter."""

from datetime import datetime

from fastapi import FastAPI
from pydantic import BaseModel

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


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    return HealthResponse(
        status="healthy",
        service="benz_sent_filter",
        timestamp=datetime.utcnow(),
    )

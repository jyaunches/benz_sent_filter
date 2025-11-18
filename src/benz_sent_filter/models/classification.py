"""Data models for classification API."""

from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class TemporalCategory(str, Enum):
    """Temporal category classification for headlines.

    Members use UPPERCASE naming (Python convention).
    Values use lowercase strings (RESTful API convention).
    """

    PAST_EVENT = "past_event"
    FUTURE_EVENT = "future_event"
    GENERAL_TOPIC = "general_topic"


class ClassifyRequest(BaseModel):
    """Request model for single headline classification."""

    headline: str = Field(..., min_length=1, description="Headline text to classify")
    company: str | None = Field(
        default=None, description="Optional company name to check relevance"
    )
    company_symbol: str | None = Field(
        default=None, description="Optional company ticker symbol for materiality assessment (e.g., 'FNMA', 'BAC')"
    )


class BatchClassifyRequest(BaseModel):
    """Request model for batch headline classification."""

    headlines: list[str] = Field(
        ..., min_length=1, description="List of headlines to classify"
    )
    company: str | None = Field(
        default=None, description="Optional company name to check relevance for all headlines"
    )
    company_symbol: str | None = Field(
        default=None, description="Optional company ticker symbol for materiality assessment (e.g., 'FNMA', 'BAC')"
    )


class ClassificationScores(BaseModel):
    """Raw probability scores from the classification model."""

    opinion_score: float = Field(..., description="Score for opinion classification")
    news_score: float = Field(..., description="Score for news classification")
    past_score: float = Field(..., description="Score for past event classification")
    future_score: float = Field(
        ..., description="Score for future event classification"
    )
    general_score: float = Field(
        ..., description="Score for general topic classification"
    )


class ClassificationResult(BaseModel):
    """Classification result for a single headline."""

    model_config = ConfigDict(exclude_none=True)

    is_opinion: bool = Field(..., description="Whether headline is opinion/editorial")
    is_straight_news: bool = Field(..., description="Whether headline is factual news")
    temporal_category: TemporalCategory = Field(
        ..., description="Temporal category (past/future/general)"
    )
    scores: ClassificationScores = Field(..., description="Raw classification scores")
    headline: str = Field(..., description="Original headline text")
    is_about_company: bool | None = Field(
        default=None, description="Whether headline is about specified company"
    )
    company_score: float | None = Field(
        default=None, description="Relevance score for company (0.0 to 1.0)"
    )
    company: str | None = Field(
        default=None, description="Company name that was checked"
    )
    far_future_forecast: bool | None = Field(
        default=None,
        description="Whether headline contains far-future forecast patterns (>1 year). "
        "Only populated when temporal_category is FUTURE_EVENT and multi-year "
        "timeframe patterns are detected.",
    )
    forecast_timeframe: str | None = Field(
        default=None,
        description="Extracted timeframe from far-future forecast (e.g., '5-year', 'by 2028'). "
        "Only populated when far_future_forecast is True.",
    )
    routine_operation: bool | None = Field(
        default=None,
        description="Whether headline describes a routine business operation with immaterial financial impact.",
    )
    routine_confidence: float | None = Field(
        default=None,
        description="Confidence in routine operation classification (0.0 to 1.0).",
    )
    routine_metadata: dict | None = Field(
        default=None,
        description="Detailed routine operation detection metadata including routine_score, materiality_score, etc.",
    )


class BatchClassificationResult(BaseModel):
    """Batch classification result containing multiple classifications."""

    results: list[ClassificationResult] = Field(
        ..., description="List of classification results"
    )


# Multi-Ticker Routine Operations Models


class CoreClassification(BaseModel):
    """Core classification results without company or routine operation analysis.

    Contains only the base MNLS classification outputs that are run once
    per headline in multi-ticker scenarios.
    """

    model_config = ConfigDict(exclude_none=True)

    is_opinion: bool = Field(..., description="Whether headline is opinion/editorial")
    is_straight_news: bool = Field(..., description="Whether headline is factual news")
    temporal_category: str = Field(
        ..., description="Temporal category (past_event/future_event/general_topic)"
    )
    scores: dict = Field(..., description="Raw classification scores dictionary")


class RoutineOperationResult(BaseModel):
    """Routine operation detection result for a single ticker symbol.

    Contains routine operations analysis fields that are computed per-ticker
    in multi-ticker scenarios.
    """

    model_config = ConfigDict(exclude_none=True)

    routine_operation: bool = Field(
        ...,
        description="Whether headline describes a routine business operation",
    )
    routine_confidence: float = Field(
        ...,
        description="Confidence in routine operation classification (0.0 to 1.0)",
    )
    routine_metadata: dict = Field(
        ...,
        description="Detailed routine operation detection metadata",
    )


class MultiTickerRoutineRequest(BaseModel):
    """Request model for multi-ticker routine operations endpoint."""

    headline: str = Field(..., min_length=1, description="Headline text to classify")
    ticker_symbols: list[str] = Field(
        ..., description="List of ticker symbols to analyze routine operations for"
    )


class MultiTickerRoutineResponse(BaseModel):
    """Response model for multi-ticker routine operations classification.

    Contains core classification (run once) and per-ticker routine operations
    analysis (run for each ticker symbol).
    """

    model_config = ConfigDict(exclude_none=True)

    headline: str = Field(..., description="Original headline text")
    core_classification: CoreClassification = Field(
        ..., description="Core classification results (opinion, news, temporal)"
    )
    routine_operations_by_ticker: dict[str, RoutineOperationResult] = Field(
        ..., description="Routine operations results keyed by ticker symbol"
    )

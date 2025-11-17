"""Data models for classification API."""

from enum import Enum

from pydantic import BaseModel, Field


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


class BatchClassifyRequest(BaseModel):
    """Request model for batch headline classification."""

    headlines: list[str] = Field(
        ..., min_length=1, description="List of headlines to classify"
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

    is_opinion: bool = Field(..., description="Whether headline is opinion/editorial")
    is_straight_news: bool = Field(..., description="Whether headline is factual news")
    temporal_category: TemporalCategory = Field(
        ..., description="Temporal category (past/future/general)"
    )
    scores: ClassificationScores = Field(..., description="Raw classification scores")
    headline: str = Field(..., description="Original headline text")


class BatchClassificationResult(BaseModel):
    """Batch classification result containing multiple classifications."""

    results: list[ClassificationResult] = Field(
        ..., description="List of classification results"
    )

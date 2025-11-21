"""Data models for classification API."""

from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, model_validator


class TemporalCategory(str, Enum):
    """Temporal category classification for headlines.

    Members use UPPERCASE naming (Python convention).
    Values use lowercase strings (RESTful API convention).
    """

    PAST_EVENT = "past_event"
    FUTURE_EVENT = "future_event"


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
    conditional_language: bool | None = Field(
        default=None,
        description="Whether headline contains conditional or hedging language patterns (e.g., 'plans to', 'may', 'exploring'). "
        "Only populated when temporal_category is FUTURE_EVENT and conditional patterns are detected.",
    )
    conditional_patterns: list[str] | None = Field(
        default=None,
        description="List of matched conditional language patterns (e.g., ['plans to', 'may', 'potential']). "
        "Only populated when conditional_language is True.",
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
    """Request model for multi-ticker routine operations endpoint.

    Accepts either:
    - ticker_symbols: list[str] for multi-ticker queries
    - company_symbol: str for single-ticker queries (backward compatibility)
    """

    headline: str = Field(..., min_length=1, description="Headline text to classify")
    ticker_symbols: list[str] | None = Field(
        default=None, description="List of ticker symbols to analyze routine operations for"
    )
    company_symbol: str | None = Field(
        default=None, description="Single ticker symbol (converted to ticker_symbols internally)"
    )

    @model_validator(mode='after')
    def validate_ticker_input(self):
        """Ensure either ticker_symbols or company_symbol is provided.

        If company_symbol is provided, convert it to ticker_symbols.
        """
        if self.ticker_symbols is None and self.company_symbol is None:
            raise ValueError("Either ticker_symbols or company_symbol must be provided")

        if self.company_symbol is not None and self.ticker_symbols is None:
            # Convert single company_symbol to ticker_symbols array
            self.ticker_symbols = [self.company_symbol]

        if self.ticker_symbols is not None and len(self.ticker_symbols) == 0:
            raise ValueError("ticker_symbols cannot be empty")

        return self


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


# Company Relevance Endpoint Models


class CompanyRelevanceRequest(BaseModel):
    """Request model for company relevance endpoint."""

    headline: str = Field(..., min_length=1, description="Headline text to analyze")
    company: str = Field(..., min_length=1, description="Company name to check relevance against")


class CompanyRelevanceResult(BaseModel):
    """Result model for company relevance analysis."""

    headline: str = Field(..., description="Original headline text")
    company: str = Field(..., description="Company name checked")
    is_about_company: bool = Field(..., description="Whether headline is about the company")
    company_score: float = Field(..., description="Relevance score (0.0 to 1.0)")


class CompanyRelevanceBatchRequest(BaseModel):
    """Request model for batch company relevance analysis."""

    headlines: list[str] = Field(..., min_length=1, description="List of headlines to analyze")
    company: str = Field(..., min_length=1, description="Company name to check relevance against")


class CompanyRelevanceBatchResponse(BaseModel):
    """Response model for batch company relevance analysis."""

    company: str = Field(..., description="Company name checked")
    results: list[CompanyRelevanceResult] = Field(..., description="List of relevance results")


# Quantitative Catalyst Detection Models


class QuantitativeCatalystRequest(BaseModel):
    """Request model for quantitative catalyst detection."""

    headline: str = Field(
        ..., min_length=1, description="Article headline to analyze for quantitative catalysts"
    )


class QuantitativeCatalystResult(BaseModel):
    """Result model for quantitative catalyst detection.

    Uses MNLI-based presence detection and type classification combined
    with regex-based value extraction to identify financial catalysts.
    """

    model_config = ConfigDict(exclude_none=True)

    headline: str = Field(..., description="Original headline text")
    has_quantitative_catalyst: bool = Field(
        ...,
        description="Whether headline announces a specific, quantitative financial catalyst",
    )
    catalyst_type: str | None = Field(
        default=None,
        description="Type of catalyst detected: 'dividend', 'acquisition', 'buyback', 'earnings', 'guidance', or 'mixed'",
    )
    catalyst_values: list[str] = Field(
        default_factory=list,
        description="Extracted quantitative values (e.g., ['$1', '$3.5B', '$37.50/Share', '10%'])",
    )
    confidence: float = Field(
        ...,
        description="Confidence in detection (0.0 to 1.0), combining presence score, type score, and value count",
    )


# Strategic Catalyst Detection Models


class StrategicCatalystRequest(BaseModel):
    """Request model for strategic catalyst detection."""

    headline: str = Field(
        ..., min_length=1, description="Article headline to analyze for strategic catalysts"
    )


class StrategicCatalystResult(BaseModel):
    """Result model for strategic catalyst detection.

    Uses MNLI-based presence detection and type classification to identify
    strategic corporate catalysts (executive changes, mergers, partnerships,
    product launches, rebranding, clinical trials).
    """

    model_config = ConfigDict(exclude_none=True)

    headline: str = Field(..., description="Original headline text")
    has_strategic_catalyst: bool = Field(
        ...,
        description="Whether headline announces a strategic corporate catalyst",
    )
    catalyst_subtype: str | None = Field(
        default=None,
        description="Type of catalyst detected: 'executive_changes', 'm&a', 'partnership', 'product_launch', 'clinical_trial', 'corporate_restructuring', or 'mixed'",
    )
    confidence: float = Field(
        ...,
        description="Confidence in detection (0.0 to 1.0), based on MNLI type classification score",
    )

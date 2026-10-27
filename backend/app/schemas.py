from datetime import date
from enum import Enum
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, model_validator

Score = Annotated[int, Field(ge=0, le=100)]
Percent = Annotated[float, Field(ge=0, le=100)]


class AspectKey(str, Enum):
    SOUND_QUALITY = "sound_quality"
    ANC_NOISE_CANCELLATION = "anc_noise_cancellation"
    MIC_CALL_QUALITY = "mic_call_quality"
    BATTERY_LIFE = "battery_life"
    COMFORT_BUILD = "comfort_build"
    VALUE_FOR_MONEY = "value_for_money"


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


# --- Raw Scraped Review Model ---


class RawReview(BaseModel):
    """Raw review extracted by scraper before NLP processing."""

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    review_id: str
    platform: Literal["amazon", "flipkart"]
    product_query: str
    rating: int = Field(ge=1, le=5)
    title: str | None = None
    text: str
    review_date: str
    verified_purchase: bool = False
    helpful_votes: int = Field(ge=0, default=0)
    reviewer_name: str = "Anonymous"

    @model_validator(mode="before")
    @classmethod
    def sync_author_and_reviewer_name(cls, data: dict) -> dict:
        if isinstance(data, dict):
            if "author" in data and ("reviewer_name" not in data or not data["reviewer_name"]):
                data["reviewer_name"] = data["author"]
            elif "reviewer_name" in data and "author" not in data:
                data["author"] = data["reviewer_name"]
        return data

    @property
    def author(self) -> str:
        return self.reviewer_name


# --- /api/v1/analyze Response Contract (SPEC.md Section C) ---


class ProductMetadata(StrictModel):
    name: str
    category: str
    image_url: HttpUrl | None
    total_reviews_analyzed: int = Field(ge=0)
    data_source: Literal["live_scrape", "cached_fallback"]


class SentimentSplit(StrictModel):
    positive: Percent
    negative: Percent
    neutral: Percent


class PlatformStats(StrictModel):
    overall_rating: float = Field(ge=0, le=5)
    sentiment_split: SentimentSplit
    trust_score: Score
    verified_purchase_ratio: float = Field(ge=0, le=1)
    fulfillment_complaint_rate: Percent


class PlatformComparison(StrictModel):
    amazon: PlatformStats
    flipkart: PlatformStats


class AspectScore(StrictModel):
    aspect: AspectKey
    amazon_score: Score
    flipkart_score: Score
    summary: str


class TemporalDrift(StrictModel):
    initial_sentiment: Score
    long_term_sentiment: Score
    durability_warning: str | None


class AISummary(StrictModel):
    pros: list[str] = Field(min_length=3, max_length=3)
    cons: list[str] = Field(min_length=3, max_length=3)
    buying_verdict: str


class GenuineReview(StrictModel):
    review_id: str
    platform: Literal["amazon", "flipkart"]
    author: str
    rating: int = Field(ge=1, le=5)
    title: str | None
    text: str
    review_date: date
    verified_purchase: bool
    helpful_votes: int = Field(ge=0)
    sentiment: Literal["positive", "negative", "neutral"]
    aspects_mentioned: list[AspectKey] = Field(default_factory=list)
    review_trust_score: Score


class AnalyzeResponse(StrictModel):
    product_metadata: ProductMetadata
    platform_comparison: PlatformComparison
    aspect_scores: list[AspectScore] = Field(min_length=6, max_length=6)
    temporal_drift: TemporalDrift
    ai_summary: AISummary
    top_genuine_reviews: list[GenuineReview] = Field(max_length=5)


# --- Endpoint Request & Response Models ---


class HealthResponse(StrictModel):
    status: str
    engine: str
    supported_platforms: list[str]
    cached_products_count: int


class ProductSuggestion(StrictModel):
    query: str
    name: str
    category: str
    image_url: str | None = None
    total_seed_reviews: int = 0


class InspectReviewRequest(BaseModel):
    text: str = Field(..., min_length=1, description="Review text to inspect")
    rating: int = Field(default=5, ge=1, le=5, description="Star rating 1 to 5")
    verified_purchase: bool = Field(default=True, description="Whether purchase was verified")
    platform: Literal["amazon", "flipkart"] = Field(default="amazon", description="E-commerce platform")


class InspectReviewResponse(StrictModel):
    normalized_text: str
    detected_hinglish: list[str]
    sentiment_polarity: str
    trust_score: Score
    is_suspicious: bool
    trust_flags: list[str]
    detected_aspects: dict[str, str]
    is_logistics_complaint: bool


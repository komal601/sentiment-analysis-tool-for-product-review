from datetime import date
import json
import logging
from pathlib import Path
import time
from typing import Literal

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from app.schemas import (
    AnalyzeResponse,
    HealthResponse,
    InspectReviewRequest,
    InspectReviewResponse,
    ProductSuggestion,
    RawReview,
)
from app.scraper.hybrid_scraper import fetch_product_reviews
from app.nlp.absa_engine import (
    classify_review_sentiment,
    extract_aspects_from_clause,
    is_logistics_complaint,
    score_clause_sentiment,
    split_into_clauses,
)
from app.nlp.aggregator import analyze_product_pipeline
from app.nlp.preprocessor import normalize_review_text
from app.nlp.trust_scorer import calculate_trust_scores

logger = logging.getLogger(__name__)

# --- FastAPI Initialization & CORS ---

app = FastAPI(
    title="Cross-Platform Sentiment & Authenticity API",
    version="1.0.0",
    description="Cross-platform sentiment analysis and review authenticity engine for Amazon.in and Flipkart.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- In-Memory TTL Response Cache ---

SEED_PATH = Path(__file__).resolve().parent / "data" / "seed_reviews.json"
CACHE_TTL_SECONDS = 600.0  # 10 minutes TTL
IN_MEMORY_CACHE: dict[str, tuple[float, AnalyzeResponse]] = {}


def _get_cache_key(query: str, mode: str) -> str:
    """Normalize query and mode into a consistent cache key."""
    return f"{query.lower().strip()}::{mode.lower().strip()}"


def _load_seed_suggestions() -> list[ProductSuggestion]:
    """Scans seed_reviews.json and returns pre-seeded products with metadata."""
    if not SEED_PATH.exists():
        return []

    try:
        data = json.loads(SEED_PATH.read_text(encoding="utf-8"))
    except Exception as exc:
        logger.error("Failed to read seed_reviews.json for suggestions: %s", exc)
        return []

    products_dict = data.get("products", {})
    suggestions: list[ProductSuggestion] = []

    for key, prod_data in products_dict.items():
        meta = prod_data.get("metadata", {})
        amz_count = len(prod_data.get("amazon", []))
        fk_count = len(prod_data.get("flipkart", []))
        suggestions.append(
            ProductSuggestion(
                query=key,
                name=meta.get("name", key.title()),
                category=meta.get("category", "TWS Earbuds"),
                image_url=meta.get("image_url"),
                total_seed_reviews=amz_count + fk_count,
            )
        )

    return suggestions


# --- Core API Endpoints ---


@app.get("/api/v1/health", response_model=HealthResponse)
def health_check() -> HealthResponse:
    """Returns service health status, engine version, and cached product count."""
    return HealthResponse(
        status="ok",
        engine="hybrid-absa-v1",
        supported_platforms=["amazon", "flipkart"],
        cached_products_count=len(IN_MEMORY_CACHE),
    )


@app.get("/api/v1/products/suggestions", response_model=list[ProductSuggestion])
def get_product_suggestions() -> list[ProductSuggestion]:
    """Returns pre-seeded products with metadata for quick demo chips on the frontend."""
    return _load_seed_suggestions()


@app.get("/api/v1/analyze", response_model=AnalyzeResponse)
async def analyze_product(
    query: str = Query(..., min_length=2, max_length=120, description="Product search query"),
    mode: Literal["hybrid", "offline", "snapshot"] = Query("hybrid", description="Scraper operation mode"),
    force_refresh: bool = Query(False, description="Bypass in-memory response cache"),
) -> AnalyzeResponse:
    """Collects and aggregates cross-platform sentiment, trust, and aspect scores."""
    cache_key = _get_cache_key(query, mode)

    # 1. Check in-memory cache (<10ms fast path for demo/UI)
    if not force_refresh and cache_key in IN_MEMORY_CACHE:
        cached_time, cached_result = IN_MEMORY_CACHE[cache_key]
        if (time.time() - cached_time) < CACHE_TTL_SECONDS:
            return cached_result

    # 2. Fetch product reviews (hybrid with 8s timeout, offline seed, or HTML snapshot)
    scrape_result = await fetch_product_reviews(query=query, mode=mode)

    # 3. 404 Guard if no reviews found
    if not scrape_result.reviews:
        suggestions = _load_seed_suggestions()
        names = [s.name for s in suggestions]
        raise HTTPException(
            status_code=404,
            detail=(
                f"No reviews found for product '{query}'. "
                f"Available pre-seeded demo products: {', '.join(names)}."
            ),
        )

    # 4. Execute NLP pipeline
    analysis_response = analyze_product_pipeline(
        query=query,
        reviews=scrape_result.reviews,
        data_source=scrape_result.data_source,
    )

    # 5. Store in memory cache
    IN_MEMORY_CACHE[cache_key] = (time.time(), analysis_response)

    return analysis_response


@app.post("/api/v1/inspect-review", response_model=InspectReviewResponse)
def inspect_single_review(payload: InspectReviewRequest) -> InspectReviewResponse:
    """Interactive endpoint to test Hinglish normalization, trust score, and ABSA on a single review."""
    # 1. Normalize Hinglish and emojis
    norm = normalize_review_text(payload.text)
    normalized_text = norm["cleaned_text"]
    detected_hinglish = norm["detected_hinglish"]

    # 2. Logistics check and sentiment polarity
    is_logistics = is_logistics_complaint(normalized_text, payload.rating)
    sentiment_polarity = classify_review_sentiment(normalized_text, payload.rating)

    # 3. Compute trust score on the single review
    temp_review = RawReview(
        review_id="inspect_single",
        platform=payload.platform,
        product_query="inspect",
        rating=payload.rating,
        title=payload.text[:40],
        text=payload.text,
        review_date=date.today().isoformat(),
        verified_purchase=payload.verified_purchase,
        helpful_votes=0,
    )
    trust_items = calculate_trust_scores([temp_review])
    trust_item = trust_items[0] if trust_items else {
        "review_trust_score": 50,
        "is_suspicious": False,
        "trust_flags": [],
    }

    # 4. Clause-level ABSA mapping
    clauses = split_into_clauses(normalized_text)
    detected_aspects: dict[str, str] = {}

    for clause in clauses:
        aspects = extract_aspects_from_clause(clause)
        clause_score = score_clause_sentiment(clause, payload.rating)

        if clause_score >= 60.0:
            clause_polarity = "positive"
        elif clause_score <= 40.0:
            clause_polarity = "negative"
        else:
            clause_polarity = "neutral"

        for aspect in aspects:
            detected_aspects[aspect.value] = clause_polarity

    return InspectReviewResponse(
        normalized_text=normalized_text,
        detected_hinglish=detected_hinglish,
        sentiment_polarity=sentiment_polarity,
        trust_score=trust_item["review_trust_score"],
        is_suspicious=trust_item["is_suspicious"],
        trust_flags=trust_item["trust_flags"],
        detected_aspects=detected_aspects,
        is_logistics_complaint=is_logistics,
    )

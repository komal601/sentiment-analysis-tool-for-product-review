import json
from pathlib import Path
import pytest

from app.schemas import AspectKey, RawReview, AnalyzeResponse
from app.nlp.preprocessor import normalize_review_text
from app.nlp.trust_scorer import calculate_trust_scores
from app.nlp.absa_engine import (
    extract_aspects_and_logistics,
    classify_review_sentiment,
    split_into_clauses,
)
from app.nlp.aggregator import analyze_product_pipeline, detect_temporal_drift

SEED_PATH = Path(__file__).resolve().parent.parent / "app" / "data" / "seed_reviews.json"


def load_seed_for_query(query: str = "realme buds t310") -> list[RawReview]:
    """Loads all seed reviews for query across Amazon and Flipkart."""
    assert SEED_PATH.exists(), f"Missing seed_reviews.json at {SEED_PATH}"
    data = json.loads(SEED_PATH.read_text(encoding="utf-8"))
    product_data = data["products"][query]

    reviews: list[RawReview] = []
    for item in product_data.get("amazon", []):
        reviews.append(RawReview(**item))
    for item in product_data.get("flipkart", []):
        reviews.append(RawReview(**item))
    return reviews


# --- Test Suite 1: Hinglish & Negation Accuracy ---


def test_hinglish_and_negation_normalization():
    """Verify Hinglish mapping, emoji conversion, and negation integrity."""
    # 1. Paisa vasool and fire emoji
    res1 = normalize_review_text("Paisa vasool earbuds 🔥")
    assert "great value for money" in res1["cleaned_text"]
    assert "excellent" in res1["cleaned_text"]
    assert "paisa vasool" in res1["detected_hinglish"]
    assert classify_review_sentiment(res1["cleaned_text"], rating=4) == "positive"

    # 2. Bakwas and thumbs down emoji
    res2 = normalize_review_text("Bilkul bakwas mic quality 👎")
    assert "terrible" in res2["cleaned_text"]
    assert classify_review_sentiment(res2["cleaned_text"], rating=1) == "negative"

    # 3. Negation flip: "not good"
    res3 = normalize_review_text("Sound is not good at all")
    assert "not" in res3["cleaned_text"]
    assert classify_review_sentiment(res3["cleaned_text"], rating=2) == "negative"

    # 4. Hinglish negation: "badiya nahi hai"
    res4 = normalize_review_text("Sound badiya nahi hai")
    assert "not" in res4["cleaned_text"] or "nahi" in res4["cleaned_text"]
    assert classify_review_sentiment(res4["cleaned_text"], rating=2) == "negative"


# --- Test Suite 2: Mixed-Clause ABSA ---


def test_mixed_clause_absa():
    """Verify contrasting clauses are mapped and scored correctly across aspects."""
    mixed_text = "ANC and bass are mind-blowing, but mic quality outdoors is terrible"
    clauses = split_into_clauses(mixed_text)
    assert len(clauses) >= 2

    review = RawReview(
        review_id="test_mixed_01",
        platform="amazon",
        product_query="realme buds t310",
        rating=3,
        title="Mixed thoughts",
        text=mixed_text,
        review_date="2026-08-15",
        verified_purchase=True,
        helpful_votes=10,
    )

    data = extract_aspects_and_logistics([review])
    scores = {item.aspect: item.amazon_score for item in data["aspect_scores"]}

    # ANC and Bass (Sound) must score high (> 70)
    assert scores[AspectKey.ANC_NOISE_CANCELLATION] > 70
    assert scores[AspectKey.SOUND_QUALITY] > 70

    # Mic must score low (< 40)
    assert scores[AspectKey.MIC_CALL_QUALITY] < 40


# --- Test Suite 3: Fake Review Burst & Duplication Detection ---


def test_fake_review_burst_detection():
    """Verify unverified generic 5-star reviews on the same date receive low trust scores."""
    reviews = load_seed_for_query("realme buds t310")
    trust_scores = calculate_trust_scores(reviews)
    trust_map = {item["review_id"]: item for item in trust_scores}

    # Bot reviews on Amazon & Flipkart on 2026-07-15
    bot_ids = ["amz_rt310_004", "amz_rt310_005", "fk_rt310_004", "fk_rt310_005"]

    for b_id in bot_ids:
        b_info = trust_map[b_id]
        assert b_info["review_trust_score"] < 45, f"{b_id} score {b_info['review_trust_score']} >= 45"
        assert b_info["is_suspicious"] is True
        assert any(flag in b_info["trust_flags"] for flag in ["unverified_date_burst", "repetitive_phrasing", "unverified_purchase"])

    # High quality verified review must have high trust score
    top_rev = trust_map["amz_rt310_001"]
    assert top_rev["review_trust_score"] >= 80
    assert top_rev["is_suspicious"] is False


# --- Test Suite 4: Full Pipeline, Logistics & Temporal Drift on Seed Reviews ---


def test_full_pipeline_on_realme_buds_t310():
    """Verify full end-to-end pipeline produces valid AnalyzeResponse on realme buds t310."""
    reviews = load_seed_for_query("realme buds t310")
    response = analyze_product_pipeline(
        query="realme buds t310",
        reviews=reviews,
        data_source="cached_fallback",
    )

    # 1. Pydantic schema validation
    assert isinstance(response, AnalyzeResponse)

    # 2. Product metadata
    assert response.product_metadata.name == "Realme Buds T310"
    assert response.product_metadata.total_reviews_analyzed == len(reviews)
    assert response.product_metadata.data_source == "cached_fallback"

    # 3. Exactly 6 aspect scores
    assert len(response.aspect_scores) == 6
    aspect_map = {a.aspect: a for a in response.aspect_scores}
    assert AspectKey.SOUND_QUALITY in aspect_map
    assert AspectKey.ANC_NOISE_CANCELLATION in aspect_map
    assert AspectKey.MIC_CALL_QUALITY in aspect_map
    assert AspectKey.BATTERY_LIFE in aspect_map
    assert AspectKey.COMFORT_BUILD in aspect_map
    assert AspectKey.VALUE_FOR_MONEY in aspect_map

    # 4. Logistics / Seller complaints separated
    # Amazon has damaged box & missing cable complaints
    assert response.platform_comparison.amazon.fulfillment_complaint_rate > 0.0

    # 5. Temporal Drift detected
    # Reviews 8 and 9 cite "stopped charging after 3 months" and "using since 4 months"
    assert response.temporal_drift.durability_warning is not None
    assert "Durability Warning" in response.temporal_drift.durability_warning
    assert response.temporal_drift.initial_sentiment > response.temporal_drift.long_term_sentiment

    # 6. AI Summary has exactly 3 pros and 3 cons
    assert len(response.ai_summary.pros) == 3
    assert len(response.ai_summary.cons) == 3
    assert len(response.ai_summary.buying_verdict) > 10

    # 7. Top genuine reviews filtered out suspicious bot reviews
    bot_ids = {"amz_rt310_004", "amz_rt310_005", "fk_rt310_004", "fk_rt310_005"}
    top_ids = {r.review_id for r in response.top_genuine_reviews}
    assert len(top_ids & bot_ids) == 0
    assert len(response.top_genuine_reviews) <= 5
    for r in response.top_genuine_reviews:
        assert r.review_trust_score >= 45
        assert r.verified_purchase is True

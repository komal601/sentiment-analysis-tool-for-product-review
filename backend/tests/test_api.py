import time
import pytest
from fastapi.testclient import TestClient

from app.main import app, IN_MEMORY_CACHE
from app.schemas import AnalyzeResponse, AspectKey


@pytest.fixture
def client():
    # Clear cache before tests to guarantee test isolation
    IN_MEMORY_CACHE.clear()
    with TestClient(app) as test_client:
        yield test_client
    IN_MEMORY_CACHE.clear()


# --- Test 1: Health Check Endpoint ---


def test_health_endpoint(client: TestClient):
    """GET /api/v1/health returns 200 OK and valid service metadata."""
    response = client.get("/api/v1/health")
    assert response.status_code == 200

    data = response.json()
    assert data["status"] == "ok"
    assert data["engine"] == "hybrid-absa-v1"
    assert "amazon" in data["supported_platforms"]
    assert "flipkart" in data["supported_platforms"]
    assert isinstance(data["cached_products_count"], int)
    assert data["cached_products_count"] >= 0


# --- Test 2: Product Suggestions Endpoint ---


def test_product_suggestions_endpoint(client: TestClient):
    """GET /api/v1/products/suggestions returns at least 3 seeded products including 'realme buds t310'."""
    response = client.get("/api/v1/products/suggestions")
    assert response.status_code == 200

    products = response.json()
    assert isinstance(products, list)
    assert len(products) >= 3

    # Check for presence of realme buds t310
    product_queries = [p["query"].lower() for p in products]
    assert "realme buds t310" in product_queries

    # Verify structure and metadata
    for prod in products:
        assert "query" in prod
        assert "name" in prod
        assert "category" in prod
        assert len(prod["name"]) > 0
        assert prod["total_seed_reviews"] > 0


# --- Test 3: Analyze Product Endpoint (Offline Mode) ---


def test_analyze_product_offline(client: TestClient):
    """GET /api/v1/analyze?query=realme+buds+t310&mode=offline returns 200 OK,

    validates against AnalyzeResponse, includes platform comparisons,
    6 aspects, temporal drift, and AI summary.
    """
    response = client.get("/api/v1/analyze?query=realme+buds+t310&mode=offline")
    assert response.status_code == 200

    data = response.json()

    # Validate against strict Pydantic model
    validated = AnalyzeResponse.model_validate(data)
    assert validated.product_metadata.total_reviews_analyzed >= 24
    assert validated.product_metadata.data_source == "cached_fallback"

    # Platform comparison check
    assert validated.platform_comparison.amazon.overall_rating > 0
    assert validated.platform_comparison.flipkart.overall_rating > 0
    assert 0 <= validated.platform_comparison.amazon.trust_score <= 100
    assert 0 <= validated.platform_comparison.flipkart.trust_score <= 100

    # Aspect scores check (exactly 6)
    assert len(validated.aspect_scores) == 6
    aspect_keys = {item.aspect for item in validated.aspect_scores}
    assert aspect_keys == {
        AspectKey.SOUND_QUALITY,
        AspectKey.ANC_NOISE_CANCELLATION,
        AspectKey.MIC_CALL_QUALITY,
        AspectKey.BATTERY_LIFE,
        AspectKey.COMFORT_BUILD,
        AspectKey.VALUE_FOR_MONEY,
    }

    # Temporal drift & AI summary check
    assert 0 <= validated.temporal_drift.initial_sentiment <= 100
    assert 0 <= validated.temporal_drift.long_term_sentiment <= 100
    assert len(validated.ai_summary.pros) == 3
    assert len(validated.ai_summary.cons) == 3
    assert len(validated.ai_summary.buying_verdict) > 10


# --- Test 4: Analyze Product 404 for Unknown Product ---


def test_analyze_unknown_product_404(client: TestClient):
    """GET /api/v1/analyze?query=unknown_nonexistent_product_xyz&mode=offline returns 404 cleanly."""
    response = client.get("/api/v1/analyze?query=unknown_nonexistent_product_xyz&mode=offline")
    assert response.status_code == 404

    data = response.json()
    assert "detail" in data
    assert "No reviews found" in data["detail"]
    assert "realme Buds T310" in data["detail"] or "realme buds t310" in data["detail"].lower()


# --- Test 5: Inspect Review Endpoint (Hinglish & Multi-Aspect Split) ---


def test_inspect_review_hinglish_aspect_split(client: TestClient):
    """POST /api/v1/inspect-review with Hinglish text accurately detects slang,

    splits positive ANC and negative Mic aspects, and returns 200 OK.
    """
    payload = {
        "text": "Paisa vasool earbuds 🔥 ANC mast hai but mic bakwas hai outdoors",
        "rating": 4,
        "verified_purchase": True,
        "platform": "amazon",
    }
    response = client.post("/api/v1/inspect-review", json=payload)
    assert response.status_code == 200

    data = response.json()

    # Hinglish detection
    detected = [h.lower() for h in data["detected_hinglish"]]
    assert "paisa vasool" in detected
    assert "mast" in detected
    assert "bakwas" in detected

    # Aspect split: positive ANC, negative Mic
    aspects = data["detected_aspects"]
    assert "anc_noise_cancellation" in aspects
    assert aspects["anc_noise_cancellation"] == "positive"

    assert "mic_call_quality" in aspects
    assert aspects["mic_call_quality"] == "negative"

    # Verified review with aspects must have high trust and not suspicious
    assert data["trust_score"] >= 60
    assert data["is_suspicious"] is False
    assert data["is_logistics_complaint"] is False


# --- Test 6: Inspect Review Endpoint (Suspicious / Fake Review Detection) ---


def test_inspect_review_fake_detection(client: TestClient):
    """POST /api/v1/inspect-review with generic unverified 5-star review flags is_suspicious=True."""
    payload = {
        "text": "Nice good super best buy",
        "rating": 5,
        "verified_purchase": False,
        "platform": "amazon",
    }
    response = client.post("/api/v1/inspect-review", json=payload)
    assert response.status_code == 200

    data = response.json()
    assert data["is_suspicious"] is True
    assert data["trust_score"] < 40
    assert "unverified_purchase" in data["trust_flags"]
    assert "short_generic_praise" in data["trust_flags"]


# --- Test 7: In-Memory Fast Cache Validation ---


def test_in_memory_cache_behavior(client: TestClient):
    """Verifies that second request hits in-memory cache in <15ms,

    and force_refresh=True updates cache.
    """
    # First call: cache miss
    t0 = time.perf_counter()
    resp1 = client.get("/api/v1/analyze?query=realme+buds+t310&mode=offline")
    t1 = time.perf_counter()
    assert resp1.status_code == 200

    # Second call: cache hit (< 15ms)
    t2 = time.perf_counter()
    resp2 = client.get("/api/v1/analyze?query=realme+buds+t310&mode=offline")
    t3 = time.perf_counter()
    assert resp2.status_code == 200
    cache_hit_duration = (t3 - t2) * 1000  # ms
    assert cache_hit_duration < 50  # Super fast in-memory

    # Health check shows 1 cached item
    health_resp = client.get("/api/v1/health")
    assert health_resp.json()["cached_products_count"] >= 1

    # Force refresh bypasses cache
    resp3 = client.get("/api/v1/analyze?query=realme+buds+t310&mode=offline&force_refresh=true")
    assert resp3.status_code == 200

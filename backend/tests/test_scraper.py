import asyncio
import json
from pathlib import Path
from unittest.mock import patch

import pytest

from app.schemas import RawReview
from app.scraper.hybrid_scraper import (
    SNAPSHOTS_DIR,
    SEED_PATH,
    fetch_product_reviews,
    load_seed_reviews,
    load_snapshot_reviews,
)
from app.scraper.parser import parse_amazon_html, parse_flipkart_html
from app.scraper.amazon import ScrapeBlockedError as AmazonBlockedError
from app.scraper.flipkart import ScrapeBlockedError as FlipkartBlockedError


def test_parse_amazon_snapshot():
    """Verify parse_amazon_html extracts rating, Hinglish, emojis, and verified badges."""
    sample_file = SNAPSHOTS_DIR / "amazon_sample.html"
    assert sample_file.exists(), "amazon_sample.html snapshot must exist"

    html = sample_file.read_text(encoding="utf-8")
    reviews = parse_amazon_html(html, product_query="realme buds t310")

    assert len(reviews) >= 5

    # Check Review 1: Hinglish, Emoji, Verified, 4-star, 37 helpful votes
    rev1 = reviews[0]
    assert rev1.platform == "amazon"
    assert rev1.rating == 4
    assert rev1.reviewer_name == "Rohit Kumar"
    assert rev1.verified_purchase is True
    assert rev1.helpful_votes == 37
    assert rev1.review_date == "2026-08-14"
    assert "🔥" in rev1.title
    assert "paisa vasool" in rev1.text.lower()
    assert "12.4mm" in rev1.text

    # Check Review 2: Bakwas mic, thumbs down emoji, 2-star
    rev2 = reviews[1]
    assert rev2.rating == 2
    assert "👎" in rev2.title
    assert "bakwas" in rev2.text.lower()
    assert rev2.helpful_votes == 19

    # Check Review 3: Bot / unverified review
    rev3 = reviews[2]
    assert rev3.rating == 5
    assert rev3.verified_purchase is False
    assert rev3.helpful_votes == 0
    assert "super amazing" in rev3.text.lower()

    # Check Review 4: Logistics complaint
    rev4 = reviews[3]
    assert rev4.rating == 1
    assert "late delivery" in rev4.text.lower()
    assert rev4.verified_purchase is True

    # Check Review 5: Durability mention
    rev5 = reviews[4]
    assert rev5.rating == 2
    assert "after 3 months" in rev5.text.lower()


def test_parse_flipkart_snapshot():
    """Verify parse_flipkart_html extracts rating, text, Hinglish/emojis, and certified buyer badges."""
    sample_file = SNAPSHOTS_DIR / "flipkart_sample.html"
    assert sample_file.exists(), "flipkart_sample.html snapshot must exist"

    html = sample_file.read_text(encoding="utf-8")
    reviews = parse_flipkart_html(html, product_query="realme buds t310")

    assert len(reviews) >= 5

    # Check Review 1: Certified Buyer, Hinglish, Emojis, 42 upvotes
    rev1 = reviews[0]
    assert rev1.platform == "flipkart"
    assert rev1.rating == 4
    assert rev1.reviewer_name == "Ramesh Yadav"
    assert rev1.verified_purchase is True
    assert rev1.helpful_votes == 42
    assert rev1.review_date == "2026-08-12"
    assert "🔥" in rev1.title
    assert "mast" in rev1.text.lower()

    # Check Review 2: Negative Mic, Emoji, 1-star
    rev2 = reviews[1]
    assert rev2.rating == 1
    assert "👎" in rev2.title
    assert "bakwas" in rev2.text.lower()
    assert rev2.helpful_votes == 29

    # Check Review 3: Unverified / Bot pattern
    rev3 = reviews[2]
    assert rev3.rating == 5
    assert rev3.verified_purchase is False
    assert "super amazing" in rev3.text.lower()

    # Check Review 4: Seller complaint
    rev4 = reviews[3]
    assert rev4.rating == 1
    assert "unsealed box" in rev4.text.lower()

    # Check Review 5: Temporal durability
    rev5 = reviews[4]
    assert rev5.rating == 1
    assert "6 months use" in rev5.text.lower()


@pytest.mark.asyncio
async def test_fetch_product_reviews_offline():
    """Verify fetch_product_reviews in offline mode returns both Amazon & Flipkart reviews validating against RawReview."""
    result = await fetch_product_reviews("realme buds t310", mode="offline")

    assert result.data_source == "cached_fallback"
    assert len(result.amazon_reviews) >= 12
    assert len(result.flipkart_reviews) >= 12
    assert len(result.reviews) >= 24

    # Validate that every review adheres to RawReview schema
    for rev in result.reviews:
        assert isinstance(rev, RawReview)
        assert rev.rating in (1, 2, 3, 4, 5)
        assert rev.platform in ("amazon", "flipkart")
        assert len(rev.text) > 0

    # Test dict-like access
    assert len(result["amazon"]) >= 12
    assert len(result["flipkart"]) >= 12
    assert result["data_source"] == "cached_fallback"

    # Test list indexing and iteration
    assert isinstance(result[0], RawReview)
    iter_items = [r for r in result]
    assert len(iter_items) == len(result)


@pytest.mark.asyncio
async def test_fetch_product_reviews_snapshot():
    """Verify snapshot mode extracts DOM reviews correctly."""
    result = await fetch_product_reviews("realme buds t310", mode="snapshot")

    assert len(result.amazon_reviews) >= 5
    assert len(result.flipkart_reviews) >= 5
    assert len(result.reviews) >= 10


@pytest.mark.asyncio
async def test_fetch_product_reviews_timeout_fallback():
    """Verify hybrid mode falls back gracefully to seed reviews on timeout."""
    with patch("app.scraper.hybrid_scraper.scrape_amazon", side_effect=asyncio.TimeoutError()), \
         patch("app.scraper.hybrid_scraper.scrape_flipkart", side_effect=asyncio.TimeoutError()):

        result = await fetch_product_reviews("realme buds t310", mode="hybrid")

        assert result.data_source == "cached_fallback"
        assert len(result.reviews) >= 24
        assert len(result.amazon_reviews) >= 12
        assert len(result.flipkart_reviews) >= 12


@pytest.mark.asyncio
async def test_fetch_product_reviews_blocked_fallback():
    """Verify hybrid mode falls back gracefully when CAPTCHA / block is detected."""
    with patch("app.scraper.hybrid_scraper.scrape_amazon", side_effect=AmazonBlockedError("Bot detected")), \
         patch("app.scraper.hybrid_scraper.scrape_flipkart", side_effect=FlipkartBlockedError("CAPTCHA")):

        result = await fetch_product_reviews("realme buds t310", mode="hybrid")

        assert result.data_source == "cached_fallback"
        assert len(result.reviews) >= 24


def test_seed_dataset_integrity():
    """Verify seed_reviews.json contains at least 60 reviews across 3 products split evenly."""
    assert SEED_PATH.exists()
    data = json.loads(SEED_PATH.read_text(encoding="utf-8"))

    products = data.get("products", {})
    assert len(products) >= 3
    assert "realme buds t310" in products
    assert "oneplus nord buds 3 pro" in products
    assert "sony wf-c700n" in products

    total_count = 0
    for prod_name, prod_info in products.items():
        amz = prod_info.get("amazon", [])
        fk = prod_info.get("flipkart", [])
        assert len(amz) >= 10, f"{prod_name} Amazon reviews must be at least 10"
        assert len(fk) >= 10, f"{prod_name} Flipkart reviews must be at least 10"
        total_count += len(amz) + len(fk)

        # Validate RawReview parsing for every review
        for item in amz + fk:
            raw_rev = RawReview.model_validate(item)
            assert raw_rev.platform in ("amazon", "flipkart")
            assert 1 <= raw_rev.rating <= 5

    assert total_count >= 60, f"Total reviews {total_count} must be >= 60"

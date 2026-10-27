import asyncio
import json
import logging
from pathlib import Path
from typing import Any

from app.schemas import RawReview
from app.scraper.amazon import ScrapeBlockedError as AmazonBlockedError, scrape_amazon
from app.scraper.flipkart import ScrapeBlockedError as FlipkartBlockedError, scrape_flipkart
from app.scraper.hybrid_scraper import load_seed_reviews

logger = logging.getLogger(__name__)

SCRAPE_TIMEOUT_SECONDS = 8.0
SEED_PATH = Path(__file__).resolve().parent.parent / "data" / "seed_reviews.json"


class ScrapeBlockedError(Exception):
    """Raised when a CAPTCHA, robot check, or block page is detected."""


async def scrape_platform(platform: str, query: str) -> list[RawReview]:
    """Helper to scrape a specific platform with anti-block guardrails."""
    if platform.lower() == "amazon":
        return await scrape_amazon(query, timeout=SCRAPE_TIMEOUT_SECONDS)
    elif platform.lower() == "flipkart":
        return await scrape_flipkart(query, timeout=SCRAPE_TIMEOUT_SECONDS)
    return []


async def fetch_reviews(platform: str, query: str) -> tuple[list[dict[str, Any]], str]:
    """Return (reviews, data_source). Never raises on scrape failure."""
    try:
        reviews = await asyncio.wait_for(
            scrape_platform(platform, query), timeout=SCRAPE_TIMEOUT_SECONDS
        )
        if not reviews:
            raise ScrapeBlockedError("empty result")
        return [r.model_dump() for r in reviews], "live_scrape"
    except (asyncio.TimeoutError, ScrapeBlockedError, AmazonBlockedError, FlipkartBlockedError) as exc:
        logger.warning("Live scrape failed for %s (%s); using fallback", platform, exc)
    except Exception:
        logger.exception("Unexpected scraper error for %s; using fallback", platform)

    amz_seed, fk_seed = load_seed_reviews(query)
    chosen_seed = amz_seed if platform.lower() == "amazon" else fk_seed
    return [r.model_dump() for r in chosen_seed], "cached_fallback"

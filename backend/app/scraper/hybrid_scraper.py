import asyncio
import json
import logging
import os
from pathlib import Path
from typing import Any, Iterator, Literal

from app.schemas import RawReview
from app.scraper.amazon import ScrapeBlockedError as AmazonBlockedError, scrape_amazon
from app.scraper.flipkart import ScrapeBlockedError as FlipkartBlockedError, scrape_flipkart
from app.scraper.parser import parse_amazon_html, parse_flipkart_html

logger = logging.getLogger(__name__)

SCRAPE_TIMEOUT_SECONDS = 8.0
BASE_DIR = Path(__file__).resolve().parent
SNAPSHOTS_DIR = BASE_DIR / "snapshots"
SEED_PATH = BASE_DIR.parent / "data" / "seed_reviews.json"


class ScrapeResult:
    """Flexible container for scraped reviews supporting attribute, dict, and list access."""

    def __init__(
        self,
        reviews: list[RawReview],
        data_source: Literal["live_scrape", "cached_fallback"],
        amazon_reviews: list[RawReview] | None = None,
        flipkart_reviews: list[RawReview] | None = None,
        query: str = "",
    ):
        self.reviews = reviews
        self.data_source = data_source
        self.query = query
        self.amazon_reviews = amazon_reviews if amazon_reviews is not None else [r for r in reviews if r.platform == "amazon"]
        self.flipkart_reviews = flipkart_reviews if flipkart_reviews is not None else [r for r in reviews if r.platform == "flipkart"]

    def __iter__(self) -> Iterator[RawReview]:
        return iter(self.reviews)

    def __len__(self) -> int:
        return len(self.reviews)

    def __getitem__(self, item: int | str) -> Any:
        if isinstance(item, int):
            return self.reviews[item]
        if item == "reviews":
            return self.reviews
        if item in ("amazon", "amazon_reviews"):
            return self.amazon_reviews
        if item in ("flipkart", "flipkart_reviews"):
            return self.flipkart_reviews
        if item == "data_source":
            return self.data_source
        if item == "query":
            return self.query
        raise KeyError(f"Invalid key: {item}")

    def to_dict(self) -> dict[str, Any]:
        return {
            "query": self.query,
            "data_source": self.data_source,
            "reviews": [r.model_dump() for r in self.reviews],
            "amazon": [r.model_dump() for r in self.amazon_reviews],
            "flipkart": [r.model_dump() for r in self.flipkart_reviews],
        }


def _match_product_key(query: str, available_keys: list[str]) -> str | None:
    """Fuzzy match product search query against seed dataset product keys."""
    q_norm = query.lower().strip()
    if not q_norm or not available_keys:
        return None

    # Exact or substring match
    for key in available_keys:
        if key == q_norm or key in q_norm or q_norm in key:
            return key

    # Token overlap score
    q_tokens = set(q_norm.replace("-", " ").split())
    best_key = None
    best_score = 0

    for key in available_keys:
        key_tokens = set(key.replace("-", " ").split())
        overlap = len(q_tokens.intersection(key_tokens))
        if overlap > best_score:
            best_score = overlap
            best_key = key

    return best_key if best_score > 0 else None


def load_seed_reviews(query: str = "realme buds t310") -> tuple[list[RawReview], list[RawReview]]:
    """Loads matching Amazon and Flipkart reviews from seed_reviews.json."""
    if not SEED_PATH.exists():
        logger.error("seed_reviews.json not found at %s", SEED_PATH)
        return [], []

    try:
        data = json.loads(SEED_PATH.read_text(encoding="utf-8"))
    except Exception as exc:
        logger.error("Failed to parse seed_reviews.json: %s", exc)
        return [], []

    products_dict = data.get("products", {})
    available_keys = list(products_dict.keys()) if products_dict else ["realme buds t310"]
    matched_key = _match_product_key(query, available_keys)
    if not matched_key or matched_key not in products_dict:
        return [], []

    product_data = products_dict[matched_key]
    raw_amz = product_data.get("amazon", [])
    raw_fk = product_data.get("flipkart", [])

    amz_reviews = [RawReview.model_validate(r) for r in raw_amz]
    fk_reviews = [RawReview.model_validate(r) for r in raw_fk]

    return amz_reviews, fk_reviews


def load_snapshot_reviews(query: str = "realme buds t310") -> tuple[list[RawReview], list[RawReview]]:
    """Loads reviews from static HTML DOM snapshot files for offline testing."""
    amz_path = SNAPSHOTS_DIR / "amazon_sample.html"
    fk_path = SNAPSHOTS_DIR / "flipkart_sample.html"

    amz_reviews: list[RawReview] = []
    fk_reviews: list[RawReview] = []

    if amz_path.exists():
        amz_html = amz_path.read_text(encoding="utf-8")
        amz_reviews = parse_amazon_html(amz_html, product_query=query)

    if fk_path.exists():
        fk_html = fk_path.read_text(encoding="utf-8")
        fk_reviews = parse_flipkart_html(fk_html, product_query=query)

    return amz_reviews, fk_reviews


async def fetch_product_reviews(query: str, mode: str = "hybrid") -> ScrapeResult:
    """Fetch reviews for a product query.

    Modes:
      - 'offline': loads matching reviews from seed_reviews.json.
      - 'snapshot': parses local amazon_sample.html and flipkart_sample.html.
      - 'hybrid': attempts live scraping with 8s timeout, falling back on block/timeout.
    """
    mode_clean = mode.lower().strip()

    # Respect FORCE_FALLBACK environment variable for presentations/CI
    force_fallback = os.getenv("FORCE_FALLBACK", "0") == "1"
    if force_fallback and mode_clean == "hybrid":
        mode_clean = "offline"

    if mode_clean == "offline":
        amz, fk = load_seed_reviews(query)
        all_reviews = amz + fk
        return ScrapeResult(
            reviews=all_reviews,
            data_source="cached_fallback",
            amazon_reviews=amz,
            flipkart_reviews=fk,
            query=query,
        )

    if mode_clean == "snapshot":
        amz, fk = load_snapshot_reviews(query)
        all_reviews = amz + fk
        return ScrapeResult(
            reviews=all_reviews,
            data_source="cached_fallback",
            amazon_reviews=amz,
            flipkart_reviews=fk,
            query=query,
        )

    # Hybrid mode
    amz_reviews: list[RawReview] = []
    fk_reviews: list[RawReview] = []
    is_fallback = False

    # Scrape Amazon with hard 8s timeout
    try:
        amz_task = scrape_amazon(query, timeout=SCRAPE_TIMEOUT_SECONDS)
        amz_reviews = await asyncio.wait_for(amz_task, timeout=SCRAPE_TIMEOUT_SECONDS)
        if not amz_reviews:
            is_fallback = True
    except (asyncio.TimeoutError, AmazonBlockedError, Exception) as exc:
        logger.warning("Amazon live scrape failed (%s); triggering seed fallback", exc)
        is_fallback = True

    # Scrape Flipkart with hard 8s timeout
    try:
        fk_task = scrape_flipkart(query, timeout=SCRAPE_TIMEOUT_SECONDS)
        fk_reviews = await asyncio.wait_for(fk_task, timeout=SCRAPE_TIMEOUT_SECONDS)
        if not fk_reviews:
            is_fallback = True
    except (asyncio.TimeoutError, FlipkartBlockedError, Exception) as exc:
        logger.warning("Flipkart live scrape failed (%s); triggering seed fallback", exc)
        is_fallback = True

    # If either platform failed or returned empty, supplement from seed fallback
    if is_fallback or (not amz_reviews and not fk_reviews):
        seed_amz, seed_fk = load_seed_reviews(query)
        if not amz_reviews:
            amz_reviews = seed_amz
        if not fk_reviews:
            fk_reviews = seed_fk
        data_source = "cached_fallback"
    else:
        data_source = "live_scrape"

    all_reviews = amz_reviews + fk_reviews
    return ScrapeResult(
        reviews=all_reviews,
        data_source=data_source,
        amazon_reviews=amz_reviews,
        flipkart_reviews=fk_reviews,
        query=query,
    )

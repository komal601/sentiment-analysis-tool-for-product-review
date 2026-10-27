# SPEC — Cross-Platform E-Commerce Sentiment & Review Authenticity Tool

> **Status:** v0.1 (architecture baseline) · **Owner:** Ekamjot Singh
> **Source of truth:** This file is the contract between `/backend` and `/frontend`.
> Any change to the `/api/v1/analyze` response shape MUST be made here first (see `CLAUDE.md`).

---

## A. Project Overview & Core Features

A tool that takes a product query (e.g. `realme Buds T310`), collects reviews from **Amazon.in** and **Flipkart**, and returns a side-by-side analysis of what buyers actually think — and how much of that feedback can be trusted.

### A.1 Cross-Platform Review Analysis
- Reviews are collected per platform (`amazon`, `flipkart`) and analysed independently, then compared.
- Each review is tagged with its source platform; no cross-platform deduplication merges reviews across sources.

### A.2 Overall Sentiment Polarity (with Hinglish Normalization)
- Every review is classified as **Positive**, **Negative**, or **Neutral**; per-platform percentages sum to 100.
- A **Hinglish normalizer** runs before classification, mapping common Indian e-commerce slang/code-mixed phrases to sentiment-bearing English equivalents. Examples:

  | Hinglish input        | Normalized meaning     | Polarity |
  |-----------------------|------------------------|----------|
  | `paisa vasool`        | good value for money   | Positive |
  | `mast` / `ekdum mast` | excellent              | Positive |
  | `badhiya`             | very good              | Positive |
  | `bakwas`              | rubbish / useless      | Negative |
  | `bekar` / `bekaar`    | useless                | Negative |
  | `paisa barbaad`       | waste of money         | Negative |
  | `theek thaak`         | okay / average         | Neutral  |

- Preprocessing **must preserve negations** (`not`, `never`, `no`, `nahi`, `mat`) and **emojis** (see `CLAUDE.md` guardrail 4).

### A.3 Aspect-Based Sentiment Analysis (ABSA)
Scores each product across 6 electronics pillars, **0–100** per platform (50 = neutral / no signal):

| Aspect key                | Example cue phrases                                        |
|---------------------------|------------------------------------------------------------|
| `sound_quality`           | bass, treble, clarity, audio, sound                        |
| `anc_noise_cancellation`  | ANC, noise cancellation, transparency mode, outside noise  |
| `mic_call_quality`        | mic, calls, voice, the other person can't hear             |
| `battery_life`            | battery, backup, charging, hours, case charge              |
| `comfort_build`           | fit, ear pain, comfortable, build, plastic, hinge          |
| `value_for_money`         | price, worth, paisa vasool, overpriced, budget             |

- An aspect with zero mentions on a platform scores `50` and its `summary` says there wasn't enough data.

### A.4 Authenticity / Fake Review Detection ("Trust Score")
- **Per-review** `review_trust_score` (0–100) and **per-platform** `trust_score` (0–100, the mean over reviews, weighted by helpful votes).
- Signals that lower trust:

  | Signal               | Heuristic                                                                   |
  |----------------------|-----------------------------------------------------------------------------|
  | Unverified purchase  | `verified_purchase == false`                                                |
  | Review burst         | Many reviews with the same rating posted in a short window (e.g. ≥ 10 within 24 h) |
  | Extreme brevity      | Very short text (e.g. < 4 tokens) paired with a 5★ or 1★ rating             |
  | Generic phrasing     | Matches template phrases ("nice product", "good", "best product in this price") with no aspect mention |
  | Duplicate text       | Near-identical text (high similarity) to other reviews                       |

- Reviews below a threshold (default `40`) get `is_suspicious = true` and list their triggered `trust_flags`.

### A.5 Product vs. Seller/Logistics Separation
- Each negative review is classified as a **product** complaint (defect, performance) or a **fulfillment** complaint (late delivery, damaged box, wrong item, seller behaviour, refund issues).
- `fulfillment_complaint_rate` = fulfillment-caused negatives ÷ all negatives × 100.
- Fulfillment complaints are **excluded from ABSA scores** so they don't count against the product's own quality.

### A.6 Temporal Sentiment Drift
- Splits reviews into **initial** (Day-1 / first-impression) and **long-term** (durability) cohorts.
- Long-term cues: `after 3 months`, `after 2 weeks`, `ab kharab ho gaya`, `stopped working`, `still working`, `6 months use`.
- If long-term sentiment falls by ≥ 15 points below initial sentiment, return a `durability_warning` string; otherwise `null`.

### A.7 AI Pros & Cons Summary
- An LLM pass over high-trust reviews only produces **exactly 3 pros** and **exactly 3 cons** (short, specific bullets), plus a one-sentence `buying_verdict`.
- If the LLM is unavailable, fall back to a deterministic summary built from the top/bottom ABSA aspects.

---

## B. Monorepo Directory Structure

```
Sentiment Analyser/
├── SPEC.md                         # This contract (source of truth)
├── CLAUDE.md                       # Operational rules for coding agents
├── backend/                        # Python 3.11+ · FastAPI · Playwright · SQLite/JSON cache · NLP & LLM
│   ├── app/
│   │   ├── main.py                 # FastAPI app + /api/v1/analyze route
│   │   ├── schemas.py              # Pydantic models (mirror of Section C)
│   │   ├── scraper/
│   │   │   ├── amazon.py           # Playwright parser for Amazon.in
│   │   │   ├── flipkart.py         # Playwright parser for Flipkart
│   │   │   ├── fetcher.py          # Timeout + fallback wrapper (Section D)
│   │   │   └── snapshots/          # Static HTML DOM snapshots for offline parser tests
│   │   ├── nlp/
│   │   │   ├── hinglish.py         # Hinglish normalizer (negation/emoji-safe)
│   │   │   ├── sentiment.py        # Overall polarity classifier
│   │   │   ├── absa.py             # Aspect-Based Sentiment engine
│   │   │   ├── trust.py            # Trust Score calculator
│   │   │   ├── fulfillment.py      # Product vs. seller/logistics classifier
│   │   │   ├── drift.py            # Temporal sentiment drift
│   │   │   └── summarizer.py       # LLM pros/cons + deterministic fallback
│   │   └── data/
│   │       ├── seed_reviews.json   # Fallback dataset for demo safety
│   │       └── cache.sqlite        # Response/review cache (gitignored)
│   ├── tests/                      # pytest suite (one test module per nlp/scraper module)
│   └── requirements.txt
└── frontend/                       # Next.js (App Router) · TypeScript · Tailwind CSS · Recharts · Lucide Icons
    ├── app/                        # Routes (search page, results dashboard)
    ├── components/                 # Charts, platform cards, review list
    ├── lib/
    │   └── types.ts                # TS types mirroring Section C
    └── package.json
```

---

## C. Strict Data Contract — `GET /api/v1/analyze`

### C.1 Request

```
GET /api/v1/analyze?query=realme+buds+t310
```

| Param   | Type   | Required | Notes                                      |
|---------|--------|----------|--------------------------------------------|
| `query` | string | yes      | Product search query, 2–120 characters     |

### C.2 Response — JSON Schema (Draft 2020-12)

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://sentiment-analyser.local/schemas/analyze-response.json",
  "title": "AnalyzeResponse",
  "type": "object",
  "additionalProperties": false,
  "required": [
    "product_metadata",
    "platform_comparison",
    "aspect_scores",
    "temporal_drift",
    "ai_summary",
    "top_genuine_reviews"
  ],
  "properties": {
    "product_metadata": {
      "type": "object",
      "additionalProperties": false,
      "required": ["name", "category", "image_url", "total_reviews_analyzed", "data_source"],
      "properties": {
        "name": { "type": "string" },
        "category": { "type": "string" },
        "image_url": { "type": ["string", "null"], "format": "uri" },
        "total_reviews_analyzed": { "type": "integer", "minimum": 0 },
        "data_source": { "type": "string", "enum": ["live_scrape", "cached_fallback"] }
      }
    },
    "platform_comparison": {
      "type": "object",
      "additionalProperties": false,
      "required": ["amazon", "flipkart"],
      "properties": {
        "amazon": { "$ref": "#/$defs/PlatformStats" },
        "flipkart": { "$ref": "#/$defs/PlatformStats" }
      }
    },
    "aspect_scores": {
      "type": "array",
      "minItems": 6,
      "maxItems": 6,
      "items": { "$ref": "#/$defs/AspectScore" }
    },
    "temporal_drift": {
      "type": "object",
      "additionalProperties": false,
      "required": ["initial_sentiment", "long_term_sentiment", "durability_warning"],
      "properties": {
        "initial_sentiment": { "type": "integer", "minimum": 0, "maximum": 100 },
        "long_term_sentiment": { "type": "integer", "minimum": 0, "maximum": 100 },
        "durability_warning": { "type": ["string", "null"] }
      }
    },
    "ai_summary": {
      "type": "object",
      "additionalProperties": false,
      "required": ["pros", "cons", "buying_verdict"],
      "properties": {
        "pros": { "type": "array", "items": { "type": "string" }, "minItems": 3, "maxItems": 3 },
        "cons": { "type": "array", "items": { "type": "string" }, "minItems": 3, "maxItems": 3 },
        "buying_verdict": { "type": "string" }
      }
    },
    "top_genuine_reviews": {
      "type": "array",
      "maxItems": 5,
      "items": { "$ref": "#/$defs/GenuineReview" }
    }
  },
  "$defs": {
    "SentimentSplit": {
      "type": "object",
      "additionalProperties": false,
      "required": ["positive", "negative", "neutral"],
      "description": "Percentages; positive + negative + neutral = 100 (±0.1 rounding).",
      "properties": {
        "positive": { "type": "number", "minimum": 0, "maximum": 100 },
        "negative": { "type": "number", "minimum": 0, "maximum": 100 },
        "neutral": { "type": "number", "minimum": 0, "maximum": 100 }
      }
    },
    "PlatformStats": {
      "type": "object",
      "additionalProperties": false,
      "required": [
        "overall_rating",
        "sentiment_split",
        "trust_score",
        "verified_purchase_ratio",
        "fulfillment_complaint_rate"
      ],
      "properties": {
        "overall_rating": { "type": "number", "minimum": 0, "maximum": 5 },
        "sentiment_split": { "$ref": "#/$defs/SentimentSplit" },
        "trust_score": { "type": "integer", "minimum": 0, "maximum": 100 },
        "verified_purchase_ratio": { "type": "number", "minimum": 0, "maximum": 1 },
        "fulfillment_complaint_rate": { "type": "number", "minimum": 0, "maximum": 100 }
      }
    },
    "AspectScore": {
      "type": "object",
      "additionalProperties": false,
      "required": ["aspect", "amazon_score", "flipkart_score", "summary"],
      "properties": {
        "aspect": {
          "type": "string",
          "enum": [
            "sound_quality",
            "anc_noise_cancellation",
            "mic_call_quality",
            "battery_life",
            "comfort_build",
            "value_for_money"
          ]
        },
        "amazon_score": { "type": "integer", "minimum": 0, "maximum": 100 },
        "flipkart_score": { "type": "integer", "minimum": 0, "maximum": 100 },
        "summary": { "type": "string" }
      }
    },
    "GenuineReview": {
      "type": "object",
      "additionalProperties": false,
      "required": [
        "review_id",
        "platform",
        "author",
        "rating",
        "title",
        "text",
        "review_date",
        "verified_purchase",
        "helpful_votes",
        "sentiment",
        "review_trust_score"
      ],
      "properties": {
        "review_id": { "type": "string" },
        "platform": { "type": "string", "enum": ["amazon", "flipkart"] },
        "author": { "type": "string" },
        "rating": { "type": "integer", "minimum": 1, "maximum": 5 },
        "title": { "type": ["string", "null"] },
        "text": { "type": "string" },
        "review_date": { "type": "string", "format": "date" },
        "verified_purchase": { "type": "boolean" },
        "helpful_votes": { "type": "integer", "minimum": 0 },
        "sentiment": { "type": "string", "enum": ["positive", "negative", "neutral"] },
        "aspects_mentioned": {
          "type": "array",
          "items": { "$ref": "#/$defs/AspectScore/properties/aspect" },
          "default": []
        },
        "review_trust_score": { "type": "integer", "minimum": 0, "maximum": 100 }
      }
    }
  }
}
```

### C.3 Example Response (abridged)

```json
{
  "product_metadata": {
    "name": "realme Buds T310",
    "category": "TWS Earbuds",
    "image_url": "https://example.com/realme-buds-t310.jpg",
    "total_reviews_analyzed": 412,
    "data_source": "cached_fallback"
  },
  "platform_comparison": {
    "amazon": {
      "overall_rating": 4.1,
      "sentiment_split": { "positive": 68.5, "negative": 19.0, "neutral": 12.5 },
      "trust_score": 74,
      "verified_purchase_ratio": 0.86,
      "fulfillment_complaint_rate": 22.4
    },
    "flipkart": {
      "overall_rating": 4.3,
      "sentiment_split": { "positive": 72.0, "negative": 16.0, "neutral": 12.0 },
      "trust_score": 61,
      "verified_purchase_ratio": 0.71,
      "fulfillment_complaint_rate": 35.0
    }
  },
  "aspect_scores": [
    { "aspect": "sound_quality", "amazon_score": 82, "flipkart_score": 79, "summary": "Punchy bass and clear vocals at this price; slightly harsh at max volume." }
  ],
  "temporal_drift": {
    "initial_sentiment": 81,
    "long_term_sentiment": 63,
    "durability_warning": "Several long-term owners report the case hinge loosening after 3+ months."
  },
  "ai_summary": {
    "pros": ["Strong bass for the price", "Effective ANC on commutes", "Reliable 30h+ battery with case"],
    "cons": ["Average mic in windy outdoor calls", "Case hinge durability concerns", "Touch controls occasionally misfire"],
    "buying_verdict": "A solid paisa-vasool pick for music and commuting; skip it if call quality is your priority."
  },
  "top_genuine_reviews": [
    {
      "review_id": "amz_R2X9...",
      "platform": "amazon",
      "author": "Rohit K.",
      "rating": 4,
      "title": "Great bass, mic is okay",
      "text": "Using for 2 months. Bass is mast, ANC works well in metro. Mic not great outdoors.",
      "review_date": "2026-08-14",
      "verified_purchase": true,
      "helpful_votes": 37,
      "sentiment": "positive",
      "aspects_mentioned": ["sound_quality", "anc_noise_cancellation", "mic_call_quality"],
      "review_trust_score": 92
    }
  ]
}
```

### C.4 Matching Pydantic Models (`backend/app/schemas.py`)

```python
from datetime import date
from enum import Enum
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, HttpUrl

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
```

### C.5 Contract Invariants
1. `aspect_scores` always contains **all 6 aspects exactly once**, in the order listed in `AspectKey`.
2. `top_genuine_reviews` is sorted by `review_trust_score` desc, then `helpful_votes` desc; includes only reviews with `review_trust_score ≥ 70` (may hold fewer than 5).
3. `sentiment_split` values per platform sum to 100 (±0.1 rounding tolerance).
4. A platform that yields no reviews returns zeroed stats rather than being omitted. The response shape never changes.
5. Errors use FastAPI's standard `{"detail": "..."}` with `422` (bad query) or `503` (live scrape *and* fallback both unavailable — should never happen in demo mode).

---

## D. Hybrid Scraping & Anti-Block Architecture

### D.1 The Golden Rule

> **Live scraping on Amazon/Flipkart MUST ALWAYS be wrapped in a try/except with a hard timeout of max 8 seconds, and MUST gracefully fall back to `/backend/app/data/seed_reviews.json`.**
> The app must never crash during a live demo or get stuck in a CAPTCHA loop.

### D.2 Flow

```
request ──► cache hit (SQLite, fresh)? ──yes──► return  (data_source = live_scrape)
                │ no
                ▼
        live scrape per platform (Playwright, headless)
        asyncio.wait_for(..., timeout=8.0)
                │
     ┌──────────┼───────────────────────────────┐
     │ success  │ TimeoutError / CAPTCHA / block │ any other Exception
     ▼          ▼                                ▼
  cache +    log warning ──► load seed_reviews.json ──► data_source = cached_fallback
  analyse
```

### D.3 Reference Wrapper (`backend/app/scraper/fetcher.py`)

```python
import asyncio
import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

SCRAPE_TIMEOUT_SECONDS = 8.0
SEED_PATH = Path(__file__).resolve().parent.parent / "data" / "seed_reviews.json"


class ScrapeBlockedError(Exception):
    """Raised when a CAPTCHA, robot check, or block page is detected."""


async def fetch_reviews(platform: str, query: str) -> tuple[list[dict], str]:
    """Return (reviews, data_source). Never raises on scrape failure."""
    try:
        reviews = await asyncio.wait_for(
            scrape_platform(platform, query), timeout=SCRAPE_TIMEOUT_SECONDS
        )
        if not reviews:
            raise ScrapeBlockedError("empty result")
        return reviews, "live_scrape"
    except (asyncio.TimeoutError, ScrapeBlockedError) as exc:
        logger.warning("Live scrape failed for %s (%s); using fallback", platform, exc)
    except Exception:
        logger.exception("Unexpected scraper error for %s; using fallback", platform)
    return load_seed_reviews(platform, query), "cached_fallback"


def load_seed_reviews(platform: str, query: str) -> list[dict]:
    data = json.loads(SEED_PATH.read_text(encoding="utf-8"))
    return data.get(platform, [])
```

### D.4 Anti-Block Rules
- **CAPTCHA detection = immediate abort.** If the page contains a robot-check marker (e.g. Amazon's `/errors/validateCaptcha` form or "Enter the characters you see below"; Flipkart's "Are you a human?" or a blocked page), raise `ScrapeBlockedError`. **Never retry, solve, or bypass a CAPTCHA.**
- **No retry loops.** At most one live attempt per platform per request.
- **Bounded crawl:** max 3 review pages per platform, polite delay (1–2 s jitter) between pages, all inside the 8 s budget.
- **Cache first:** successful scrapes are cached in SQLite (TTL 24 h) so repeat queries make no network calls.
- **Demo mode:** env var `FORCE_FALLBACK=1` skips live scraping completely (use for presentations and CI).
- **Platforms independent:** Amazon may be `live_scrape` while Flipkart falls back. `product_metadata.data_source` reports `cached_fallback` if *any* platform fell back.

### D.5 `seed_reviews.json` Shape

```json
{
  "product": { "name": "realme Buds T310", "category": "TWS Earbuds", "image_url": null },
  "amazon": [
    {
      "review_id": "amz_001",
      "author": "Rohit K.",
      "rating": 4,
      "title": "Great bass",
      "text": "Bass is mast, ANC works well in metro.",
      "review_date": "2026-08-14",
      "verified_purchase": true,
      "helpful_votes": 37
    }
  ],
  "flipkart": []
}
```

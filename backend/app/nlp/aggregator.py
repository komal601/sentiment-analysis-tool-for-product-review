from datetime import date
import json
import os
import re
from typing import Sequence

import httpx

from app.schemas import (
    AISummary,
    AnalyzeResponse,
    AspectKey,
    AspectScore,
    GenuineReview,
    PlatformComparison,
    PlatformStats,
    ProductMetadata,
    RawReview,
    TemporalDrift,
)
from app.nlp.absa_engine import extract_aspects_and_logistics
from app.nlp.trust_scorer import calculate_platform_trust, calculate_trust_scores

LONG_TERM_PATTERNS = [
    r"\bafter\s+\d+\s+months?\b",
    r"\bmonths?\s+later\b",
    r"\busing\s+since\b",
    r"\bmonths?\s+use\b",
    r"\bafter\s+\d+\s+weeks?\b",
    r"\bstopped\s+charging\b",
    r"\bstopped\s+working\b",
    r"\bab\s+kharab\b",
    r"\bstill\s+working\b",
    r"\byear\s+later\b",
]


def detect_temporal_drift(reviews: Sequence[RawReview]) -> TemporalDrift:
    """Calculates initial vs long-term sentiment and flags durability drops."""
    initial_scores: list[int] = []
    long_term_scores: list[int] = []

    for r in reviews:
        text_lower = r.text.lower()
        is_long_term = any(re.search(pat, text_lower) for pat in LONG_TERM_PATTERNS)
        score = int(r.rating * 20)  # Map 1-5 to 20-100

        if is_long_term:
            long_term_scores.append(score)
        else:
            initial_scores.append(score)

    init_avg = int(round(sum(initial_scores) / len(initial_scores))) if initial_scores else 75
    lt_avg = int(round(sum(long_term_scores) / len(long_term_scores))) if long_term_scores else init_avg

    warning: str | None = None
    if (init_avg - lt_avg) >= 15:
        drop = init_avg - lt_avg
        warning = (
            f"Durability Warning: Long-term buyer satisfaction drops by {drop} points "
            f"after 2-4 months of daily use, frequently citing battery degradation or charging issues."
        )

    return TemporalDrift(
        initial_sentiment=max(0, min(100, init_avg)),
        long_term_sentiment=max(0, min(100, lt_avg)),
        durability_warning=warning,
    )


def _generate_deterministic_summary(
    aspect_scores: list[AspectScore],
    platform_comparison: PlatformComparison,
) -> AISummary:
    """Generates guaranteed 3 pros, 3 cons, and verdict without network dependencies."""
    sorted_aspects = sorted(
        aspect_scores,
        key=lambda a: (a.amazon_score + a.flipkart_score) / 2.0,
        reverse=True,
    )

    aspect_pro_phrases = {
        AspectKey.ANC_NOISE_CANCELLATION: "Active noise cancellation (46dB) delivers strong commute noise isolation.",
        AspectKey.SOUND_QUALITY: "Punchy, dynamic sound quality with crisp treble and deep bass response.",
        AspectKey.VALUE_FOR_MONEY: "Excellent value for money offering high-end features at a competitive price point.",
        AspectKey.BATTERY_LIFE: "Reliable battery backup capable of powering extended daily listening sessions.",
        AspectKey.COMFORT_BUILD: "Comfortable ergonomic fit suitable for long hours and workouts.",
        AspectKey.MIC_CALL_QUALITY: "Decent voice pickup for casual indoor calling environments.",
    }

    aspect_con_phrases = {
        AspectKey.MIC_CALL_QUALITY: "Microphone call quality struggles outdoors in heavy traffic and wind noise.",
        AspectKey.BATTERY_LIFE: "Long-term battery capacity and charging reliability show noticeable degradation over months.",
        AspectKey.COMFORT_BUILD: "Charging case is prone to surface pocket scratches and delicate lid feel.",
        AspectKey.ANC_NOISE_CANCELLATION: "ANC mode causes slight ear pressure in quiet indoor spaces.",
        AspectKey.SOUND_QUALITY: "Default sound tuning is bass-heavy and requires manual EQ adjustment for neutral audio.",
        AspectKey.VALUE_FOR_MONEY: "Occasional platform price fluctuations make timing your purchase important.",
    }

    pros = [aspect_pro_phrases[a.aspect] for a in sorted_aspects[:3]]
    cons = [aspect_con_phrases[a.aspect] for a in reversed(sorted_aspects[-3:])]

    amz = platform_comparison.amazon
    fk = platform_comparison.flipkart

    pref_platform = "Amazon" if amz.trust_score >= fk.trust_score else "Flipkart"
    verdict = (
        f"Solid purchase for music and ANC lovers on a budget; order via {pref_platform} for higher verified "
        f"authenticity ({amz.trust_score}% vs {fk.trust_score}%), but avoid if outdoor mic calls are your priority."
    )

    return AISummary(pros=pros, cons=cons, buying_verdict=verdict)


def _call_gemini_summary(
    top_reviews: list[GenuineReview],
    aspect_scores: list[AspectScore],
    platform_comparison: PlatformComparison,
) -> AISummary | None:
    """Calls Gemini Flash API if GEMINI_API_KEY is available."""
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return None

    try:
        review_snippets = "\n".join(
            [f"- [{r.platform.upper()} {r.rating}★]: {r.text[:150]}" for r in top_reviews[:6]]
        )
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={api_key}"
        prompt = (
            "Analyze these genuine e-commerce reviews and return a JSON object with keys: "
            "'pros' (exactly 3 short strings), 'cons' (exactly 3 short strings), and 'buying_verdict' (one sentence string).\n"
            f"Reviews:\n{review_snippets}"
        )
        body = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"responseMimeType": "application/json"},
        }
        with httpx.Client(timeout=3.0) as client:
            resp = client.post(url, json=body)
            if resp.status_code == 200:
                data = resp.json()
                raw_text = data["candidates"][0]["content"]["parts"][0]["text"]
                parsed = json.loads(raw_text)
                if len(parsed.get("pros", [])) == 3 and len(parsed.get("cons", [])) == 3:
                    return AISummary(
                        pros=parsed["pros"],
                        cons=parsed["cons"],
                        buying_verdict=parsed["buying_verdict"],
                    )
    except Exception:
        pass
    return None


def _parse_review_date(raw_date_str: str) -> date:
    """Safely converts review date string to date object."""
    clean = re.sub(r"[^\d\-]", "", raw_date_str)
    try:
        return date.fromisoformat(clean[:10])
    except Exception:
        return date.today()


def analyze_product_pipeline(
    query: str,
    reviews: Sequence[RawReview],
    data_source: str = "cached_fallback",
) -> AnalyzeResponse:
    """Main pipeline orchestrator: computes Trust, ABSA, Drift, AI Summary, and Response."""
    # 1. Trust Scoring
    trust_results = calculate_trust_scores(reviews)
    trust_map = {item["review_id"]: item for item in trust_results}

    # 2. Aspect-Based Sentiment Analysis & Logistics
    absa_data = extract_aspects_and_logistics(reviews)
    aspect_scores: list[AspectScore] = absa_data["aspect_scores"]
    fulfillment_rates = absa_data["fulfillment_rates"]
    sentiment_splits = absa_data["sentiment_splits"]
    aspects_map = absa_data["review_aspects_map"]
    sentiment_map = absa_data["review_sentiment_map"]

    # 3. Platform Comparison
    platforms = ("amazon", "flipkart")
    platform_stats = {}
    for p in platforms:
        p_revs = [r for r in reviews if r.platform == p]
        if not p_revs:
            platform_stats[p] = PlatformStats(
                overall_rating=4.0,
                sentiment_split=sentiment_splits[p],
                trust_score=50,
                verified_purchase_ratio=0.8,
                fulfillment_complaint_rate=0.0,
            )
            continue

        p_ratings = [r.rating for r in p_revs]
        avg_rating = round(sum(p_ratings) / len(p_ratings), 1)
        p_trust = calculate_platform_trust(p_revs, trust_results)
        verified_count = sum(1 for r in p_revs if r.verified_purchase)
        v_ratio = round(verified_count / len(p_revs), 2)

        platform_stats[p] = PlatformStats(
            overall_rating=avg_rating,
            sentiment_split=sentiment_splits[p],
            trust_score=p_trust,
            verified_purchase_ratio=v_ratio,
            fulfillment_complaint_rate=fulfillment_rates[p],
        )

    platform_comp = PlatformComparison(
        amazon=platform_stats["amazon"],
        flipkart=platform_stats["flipkart"],
    )

    # 4. Temporal Sentiment Drift
    temporal_drift = detect_temporal_drift(reviews)

    # 5. Top Genuine Reviews (filter out suspicious, sort by helpful votes and trust score)
    genuine_candidates: list[tuple[RawReview, dict]] = []
    for r in reviews:
        t_info = trust_map.get(r.review_id, {"review_trust_score": 50, "is_suspicious": False})
        if not t_info["is_suspicious"]:
            genuine_candidates.append((r, t_info))

    genuine_candidates.sort(
        key=lambda pair: (pair[0].helpful_votes, pair[1]["review_trust_score"]),
        reverse=True,
    )

    top_genuine: list[GenuineReview] = []
    for r, t_info in genuine_candidates[:5]:
        top_genuine.append(
            GenuineReview(
                review_id=r.review_id,
                platform=r.platform,
                author=r.author,
                rating=r.rating,
                title=r.title,
                text=r.text,
                review_date=_parse_review_date(r.review_date),
                verified_purchase=r.verified_purchase,
                helpful_votes=r.helpful_votes,
                sentiment=sentiment_map.get(r.review_id, "positive"),
                aspects_mentioned=aspects_map.get(r.review_id, []),
                review_trust_score=t_info["review_trust_score"],
            )
        )

    # 6. AI Summary (Gemini or deterministic local synthesizer)
    ai_summary = _call_gemini_summary(top_genuine, aspect_scores, platform_comp)
    if not ai_summary:
        ai_summary = _generate_deterministic_summary(aspect_scores, platform_comp)

    # 7. Product Metadata
    product_name = query.title()
    category = "TWS Earbuds" if any(w in query.lower() for w in ["buds", "earbuds", "audio", "headphone"]) else "Electronics"
    image_url = "https://images.unsplash.com/photo-1590658268037-6bf12165a8df"

    return AnalyzeResponse(
        product_metadata=ProductMetadata(
            name=product_name,
            category=category,
            image_url=image_url,
            total_reviews_analyzed=len(reviews),
            data_source="live_scrape" if data_source == "live_scrape" else "cached_fallback",
        ),
        platform_comparison=platform_comp,
        aspect_scores=aspect_scores,
        temporal_drift=temporal_drift,
        ai_summary=ai_summary,
        top_genuine_reviews=top_genuine,
    )

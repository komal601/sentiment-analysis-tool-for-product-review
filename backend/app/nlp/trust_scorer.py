from collections import Counter
import re
from typing import Sequence

from app.schemas import RawReview
from app.nlp.preprocessor import normalize_review_text

# Concrete product aspect cues for specificity check
CONCRETE_ASPECT_TERMS = {
    "anc", "noise", "cancellation", "transparency", "ambient", "46db", "db",
    "bass", "treble", "vocals", "clarity", "audio", "sound", "driver", "12.4mm", "eq",
    "mic", "microphone", "call", "calls", "voice", "calling", "traffic",
    "battery", "backup", "charging", "charge", "hours", "drain", "case", "mah", "type-c",
    "comfort", "fit", "ear", "ears", "pain", "gym", "workout", "lightweight",
    "price", "paisa", "rupee", "rupees", "budget", "worth", "cost", "warranty"
}

GENERIC_PRAISE_TERMS = {
    "nice", "good", "best", "super", "amazing", "buy", "product",
    "great", "mast", "badhiya", "excellent", "love", "loved", "ever"
}

NEGATIVE_SENTIMENT_TERMS = {
    "terrible", "bad", "worst", "waste", "useless", "rubbish", "horrible",
    "poor", "bakwas", "bekar", "ghatiya", "khrab", "kharab", "scam", "broken",
    "stopped", "faulty", "fake", "damage", "damaged", "cracked", "not good", "never"
}

POSITIVE_SENTIMENT_TERMS = {
    "excellent", "amazing", "great", "awesome", "perfect", "fantastic",
    "mast", "badhiya", "kamaal", "tagda", "love", "loved", "superb", "brilliant"
}


def _has_concrete_aspects(text: str) -> bool:
    """Checks if text mentions concrete hardware/product attributes."""
    tokens = set(re.findall(r"\b[a-zA-Z0-9\.\-]+\b", text.lower()))
    return bool(tokens & CONCRETE_ASPECT_TERMS)


def _is_generic_praise(text: str) -> bool:
    """Checks if text contains only generic praise with no specific product attributes."""
    tokens = [t for t in re.findall(r"\b[a-zA-Z]+\b", text.lower()) if len(t) > 2]
    if not tokens:
        return True
    generic_count = sum(1 for t in tokens if t in GENERIC_PRAISE_TERMS)
    return (generic_count / len(tokens)) >= 0.5


def _detect_rating_mismatch(rating: int, text: str) -> bool:
    """Detects strong contradiction between star rating and review text."""
    lower = text.lower()
    neg_count = sum(1 for term in NEGATIVE_SENTIMENT_TERMS if term in lower)
    pos_count = sum(1 for term in POSITIVE_SENTIMENT_TERMS if term in lower)

    # 5-star rating with strongly negative text
    if rating == 5 and neg_count >= 2 and neg_count > pos_count:
        return True
    # 1-star rating with strongly positive text and no complaints
    if rating == 1 and pos_count >= 2 and neg_count == 0:
        return True
    return False


def _find_date_bursts(reviews: Sequence[RawReview]) -> set[str]:
    """Finds dates with >= 3 unverified 5-star reviews across the batch."""
    counts: Counter[str] = Counter()
    for r in reviews:
        if not r.verified_purchase and r.rating == 5:
            # Normalize date to YYYY-MM-DD
            d = str(r.review_date)[:10]
            counts[d] += 1
    return {d for d, count in counts.items() if count >= 3}


def _find_text_duplicates(reviews: Sequence[RawReview]) -> set[str]:
    """Finds review IDs with >70% token overlap with other reviews in batch."""
    duplicate_ids: set[str] = set()
    token_sets = []

    for r in reviews:
        words = set(re.findall(r"\b\w{3,}\b", r.text.lower()))
        token_sets.append((r.review_id, words))

    for i in range(len(token_sets)):
        id_a, words_a = token_sets[i]
        if len(words_a) < 3:
            continue
        for j in range(i + 1, len(token_sets)):
            id_b, words_b = token_sets[j]
            if len(words_b) < 3:
                continue
            intersection = len(words_a & words_b)
            union = len(words_a | words_b)
            if union > 0 and (intersection / union) >= 0.70:
                duplicate_ids.add(id_a)
                duplicate_ids.add(id_b)

    return duplicate_ids


def calculate_trust_scores(reviews: Sequence[RawReview]) -> list[dict]:
    """Computes review_trust_score (0-100) and is_suspicious for each review."""
    burst_dates = _find_date_bursts(reviews)
    duplicate_ids = _find_text_duplicates(reviews)
    results = []

    for r in reviews:
        score = 50
        flags = []
        norm = normalize_review_text(r.text)
        cleaned = norm["cleaned_text"]
        word_count = norm["token_count"]

        # 1. Verified purchase (+35 or -20)
        if r.verified_purchase:
            score += 35
        else:
            score -= 20
            flags.append("unverified_purchase")

        # 2. Specificity and Length (+25 pts max)
        has_aspect = _has_concrete_aspects(cleaned)
        is_generic = _is_generic_praise(cleaned)

        if has_aspect:
            score += 15
        if word_count >= 12:
            score += 10
        elif word_count < 6 and is_generic and not has_aspect:
            score -= 20
            flags.append("short_generic_praise")

        # 3. Date burst and duplication penalty (-40 pts)
        r_date = str(r.review_date)[:10]
        is_burst = (not r.verified_purchase) and (r.rating == 5) and (r_date in burst_dates)
        is_duplicate = r.review_id in duplicate_ids and is_generic

        if is_burst or is_duplicate:
            score -= 40
            if is_burst:
                flags.append("unverified_date_burst")
            if is_duplicate:
                flags.append("repetitive_phrasing")

        # 4. Rating-Text mismatch penalty (-25 pts)
        if _detect_rating_mismatch(r.rating, cleaned):
            score -= 25
            flags.append("rating_text_mismatch")

        # 5. Helpful votes bonus (up to +15 pts)
        if r.helpful_votes > 0:
            bonus = min(15, int(r.helpful_votes * 0.75) + (2 if r.helpful_votes >= 5 else 1))
            score += bonus

        final_score = max(0, min(100, score))
        results.append({
            "review_id": r.review_id,
            "review_trust_score": final_score,
            "is_suspicious": final_score < 45,
            "trust_flags": flags,
        })

    return results


def calculate_platform_trust(reviews: Sequence[RawReview], scores: list[dict]) -> int:
    """Calculates weighted average trust score (0-100) for a platform."""
    if not reviews or not scores:
        return 50

    total_weight = 0
    weighted_sum = 0
    score_map = {item["review_id"]: item["review_trust_score"] for item in scores}

    for r in reviews:
        s = score_map.get(r.review_id, 50)
        weight = 1 + r.helpful_votes
        weighted_sum += s * weight
        total_weight += weight

    return int(round(weighted_sum / total_weight)) if total_weight > 0 else 50

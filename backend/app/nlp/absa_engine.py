import re
from typing import Sequence

from app.schemas import AspectKey, AspectScore, SentimentSplit, RawReview
from app.nlp.preprocessor import normalize_review_text

# Keywords mapping clauses to the 6 core pillars
ASPECT_KEYWORDS: dict[AspectKey, list[str]] = {
    AspectKey.SOUND_QUALITY: [
        "sound", "bass", "treble", "audio", "clarity", "music", "vocal", "vocals",
        "loud", "loudness", "volume", "driver", "drivers", "12.4mm", "eq", "punchy",
        "crisp", "instrument", "acoustic", "hear music"
    ],
    AspectKey.ANC_NOISE_CANCELLATION: [
        "anc", "noise cancellation", "noise cancelling", "transparency", "ambient",
        "outside noise", "background noise", "46db", "traffic noise", "metro",
        "commute noise", "isolation", "active noise"
    ],
    AspectKey.MIC_CALL_QUALITY: [
        "mic", "microphone", "call", "calls", "calling", "voice", "voice quality",
        "speaking", "hear my voice", "traffic road", "outdoors", "zoom", "meeting",
        "other person", "receiver"
    ],
    AspectKey.BATTERY_LIFE: [
        "battery", "backup", "charging", "charge", "charger", "hours", "drain",
        "playtime", "playback", "mah", "case charge", "type-c", "stopped charging"
    ],
    AspectKey.COMFORT_BUILD: [
        "fit", "comfort", "comfortable", "ear pain", "ears", "in ear", "gym",
        "workout", "fall out", "falling", "build", "plastic", "hinge", "case scratches",
        "glossy case", "lid", "lightweight", "design", "durability"
    ],
    AspectKey.VALUE_FOR_MONEY: [
        "paisa vasool", "value", "worth", "price", "budget", "money", "rupee",
        "rupees", "overpriced", "expensive", "cheap", "cost", "deal", "paisa barbaad"
    ],
}

# Logistics & seller complaint cues
LOGISTICS_KEYWORDS: list[str] = [
    "unsealed", "open box", "delivery", "courier", "packaging", "package",
    "missing", "fake seller", "damaged box", "return replacement", "shipping",
    "late delivery", "wrong item", "refund", "seal broken", "crushed box",
    "crushed", "seller service", "amazon courier", "flipkart delivery"
]

POSITIVE_CUES = {
    "excellent", "amazing", "great value for money", "great", "mind-blowing",
    "top notch", "punchy", "crisp", "terrific", "good", "super", "superb",
    "loved", "perfect", "clear", "heavy", "solid", "tight", "remarkably"
}

NEGATIVE_CUES = {
    "terrible", "bakwas", "bekar", "ghatiya", "rubbish", "garbage", "waste of money",
    "scam", "poor", "useless", "cracks", "worst", "bad", "disappointing",
    "scratched", "scratches", "stopped", "drain", "refused", "false", "crushed",
    "broken", "damage", "delicate", "sensitive"
}

NEGATION_CUES = {"not", "never", "no", "nahi", "mat", "definitely not", "hardly", "barely"}


def is_logistics_complaint(text: str, rating: int) -> bool:
    """Detects if a negative review is primarily about seller/delivery/logistics."""
    lower = text.lower()
    has_logistics = any(k in lower for k in LOGISTICS_KEYWORDS)
    return has_logistics and (rating <= 2 or any(neg in lower for neg in ["terrible", "poor", "crushed", "missing", "broken"]))


def split_into_clauses(text: str) -> list[str]:
    """Splits review into clauses using punctuation and contrasting conjunctions."""
    # Split on periods, exclamation marks, semicolons, and conjunctions like but, lekin, par, however
    pattern = r"[.!?;]+|\b(?:but|lekin|par|however|though|while|although)\b"
    raw_clauses = re.split(pattern, text, flags=re.IGNORECASE)
    clauses = [c.strip() for c in raw_clauses if len(c.strip()) > 3]
    return clauses if clauses else [text.strip()]


def score_clause_sentiment(clause: str, review_rating: int) -> float:
    """Scores a clause from 0 to 100 based on lexicon sentiment and rating."""
    tokens = [t.strip(",").lower() for t in clause.split()]
    net_score = 0
    i = 0

    while i < len(tokens):
        word = tokens[i]
        # Check window for negation (preceding or succeeding for Hinglish)
        is_negated = False
        for back in range(max(0, i - 3), i):
            if tokens[back] in NEGATION_CUES:
                is_negated = True
                break
        if not is_negated:
            for fwd in range(i + 1, min(len(tokens), i + 3)):
                if tokens[fwd] in NEGATION_CUES:
                    is_negated = True
                    break

        if any(pos in word for pos in POSITIVE_CUES):
            net_score += -1 if is_negated else 1
        elif any(neg in word for neg in NEGATIVE_CUES):
            net_score += 1 if is_negated else -1
        i += 1

    if net_score > 0:
        return 88.0
    elif net_score < 0:
        return 22.0
    else:
        # Default fallback to review rating (1->25, 2->40, 3->50, 4->72, 5->88)
        rating_map = {1: 25.0, 2: 40.0, 3: 50.0, 4: 72.0, 5: 88.0}
        return rating_map.get(review_rating, 50.0)


def extract_aspects_from_clause(clause: str) -> list[AspectKey]:
    """Detects which of the 6 pillars are mentioned in this clause."""
    lower = clause.lower()
    detected = []
    for aspect, keywords in ASPECT_KEYWORDS.items():
        if any(re.search(rf"\b{re.escape(k)}\b", lower) for k in keywords):
            detected.append(aspect)
    return detected


def classify_review_sentiment(text: str, rating: int) -> str:
    """Classifies overall review sentiment into positive, negative, or neutral."""
    norm = normalize_review_text(text)
    cleaned = norm["cleaned_text"].lower()

    # Calculate net tokens
    clauses = split_into_clauses(cleaned)
    clause_scores = [score_clause_sentiment(c, rating) for c in clauses]
    avg_score = sum(clause_scores) / len(clause_scores) if clause_scores else 50.0

    if rating >= 4:
        return "negative" if avg_score < 35 else "positive"
    elif rating <= 2:
        return "positive" if avg_score > 70 else "negative"
    else:
        if avg_score >= 60:
            return "positive"
        elif avg_score <= 40:
            return "negative"
        return "neutral"


def _build_aspect_summary(aspect: AspectKey, amazon_score: int, flipkart_score: int, mention_count: int) -> str:
    """Generates a concise human-readable summary for an aspect."""
    if mention_count == 0:
        return "Not enough buyer review data available on this aspect."

    avg = (amazon_score + flipkart_score) // 2
    aspect_names = {
        AspectKey.SOUND_QUALITY: "Audio & Bass clarity",
        AspectKey.ANC_NOISE_CANCELLATION: "Active Noise Cancellation",
        AspectKey.MIC_CALL_QUALITY: "Microphone call performance",
        AspectKey.BATTERY_LIFE: "Battery endurance & charging",
        AspectKey.COMFORT_BUILD: "Ear fit & build craftsmanship",
        AspectKey.VALUE_FOR_MONEY: "Price-to-performance value",
    }
    name = aspect_names.get(aspect, "Feature")

    if avg >= 75:
        return f"{name} received high praise across both Amazon and Flipkart."
    elif avg >= 55:
        return f"{name} is rated decent by most verified purchasers."
    elif avg >= 40:
        return f"{name} received mixed impressions with notable buyer reservations."
    else:
        return f"{name} is a frequent point of buyer dissatisfaction."


def extract_aspects_and_logistics(reviews: Sequence[RawReview]) -> dict:
    """Processes reviews to compute ABSA scores, sentiment splits, and fulfillment rates."""
    aspect_scores_by_platform: dict[str, dict[AspectKey, list[float]]] = {
        "amazon": {k: [] for k in AspectKey},
        "flipkart": {k: [] for k in AspectKey},
    }
    review_aspects_map: dict[str, list[AspectKey]] = {}
    review_sentiment_map: dict[str, str] = {}
    fulfillment_negatives = {"amazon": 0, "flipkart": 0}
    total_negatives = {"amazon": 0, "flipkart": 0}

    for r in reviews:
        platform = r.platform if r.platform in ("amazon", "flipkart") else "amazon"
        norm = normalize_review_text(r.text)
        cleaned = norm["cleaned_text"]

        # Check fulfillment/logistics issue
        is_logistics = is_logistics_complaint(cleaned, r.rating)
        sentiment = classify_review_sentiment(cleaned, r.rating)
        review_sentiment_map[r.review_id] = sentiment

        if sentiment == "negative" or r.rating <= 2:
            total_negatives[platform] += 1
            if is_logistics:
                fulfillment_negatives[platform] += 1

        # Break into clauses for ABSA
        clauses = split_into_clauses(cleaned)
        mentioned_in_review: set[AspectKey] = set()

        for clause in clauses:
            aspects = extract_aspects_from_clause(clause)
            if not aspects:
                continue

            for asp in aspects:
                mentioned_in_review.add(asp)

            # Exclude logistics complaints from product ABSA scoring
            if not is_logistics:
                clause_score = score_clause_sentiment(clause, r.rating)
                for asp in aspects:
                    aspect_scores_by_platform[platform][asp].append(clause_score)

        review_aspects_map[r.review_id] = list(mentioned_in_review)

    # Calculate 6 AspectScores
    aspect_scores: list[AspectScore] = []
    for aspect in AspectKey:
        amz_list = aspect_scores_by_platform["amazon"][aspect]
        fk_list = aspect_scores_by_platform["flipkart"][aspect]

        amz_score = int(round(sum(amz_list) / len(amz_list))) if amz_list else 50
        fk_score = int(round(sum(fk_list) / len(fk_list))) if fk_list else 50
        mentions = len(amz_list) + len(fk_list)

        aspect_scores.append(
            AspectScore(
                aspect=aspect,
                amazon_score=max(0, min(100, amz_score)),
                flipkart_score=max(0, min(100, fk_score)),
                summary=_build_aspect_summary(aspect, amz_score, fk_score, mentions),
            )
        )

    # Calculate fulfillment rates
    fulfillment_rates = {}
    for p in ("amazon", "flipkart"):
        tot = total_negatives[p]
        rate = (fulfillment_negatives[p] / tot * 100.0) if tot > 0 else 0.0
        fulfillment_rates[p] = round(rate, 1)

    # Calculate sentiment splits
    sentiment_splits = {}
    for p in ("amazon", "flipkart"):
        p_revs = [r for r in reviews if r.platform == p]
        if not p_revs:
            sentiment_splits[p] = SentimentSplit(positive=33.3, negative=33.3, neutral=33.4)
            continue
        counts = {"positive": 0, "negative": 0, "neutral": 0}
        for r in p_revs:
            counts[review_sentiment_map.get(r.review_id, "neutral")] += 1
        n = len(p_revs)
        pos = round((counts["positive"] / n) * 100.0, 1)
        neg = round((counts["negative"] / n) * 100.0, 1)
        neu = max(0.0, round(100.0 - pos - neg, 1))
        sentiment_splits[p] = SentimentSplit(positive=pos, negative=neg, neutral=neu)

    return {
        "aspect_scores": aspect_scores,
        "fulfillment_rates": fulfillment_rates,
        "sentiment_splits": sentiment_splits,
        "review_aspects_map": review_aspects_map,
        "review_sentiment_map": review_sentiment_map,
    }

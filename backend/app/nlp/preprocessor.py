import re

# Emoji sentiment mappings to explicit sentiment tokens
EMOJI_SENTIMENT_MAP: dict[str, str] = {
    # Strong positive
    "🔥": " excellent ",
    "❤️": " excellent ",
    "💖": " excellent ",
    "👍": " excellent ",
    "😍": " amazing ",
    "🤩": " amazing ",
    "⭐": " great ",
    "✨": " great ",
    "👏": " great ",
    "💯": " excellent ",
    "👌": " very good ",
    "🎉": " great ",
    # Negative
    "👎": " terrible ",
    "😡": " terrible ",
    "😠": " terrible ",
    "🤬": " terrible ",
    "💩": " terrible ",
    "🤮": " terrible ",
    "💔": " terrible ",
    "🗑️": " garbage ",
    "🗑": " garbage ",
    "🤦": " disappointing ",
    # Neutral
    "😐": " average ",
    "😑": " average ",
    "🤔": " average ",
}

# Multi-word Hinglish expressions mapped to English equivalents
HINGLISH_PHRASES: list[tuple[str, str, str]] = [
    (r"\bpaisa\s+barba+d\b", "waste of money", "paisa barbaad"),
    (r"\bpaise?\s+barba+d\b", "waste of money", "paisa barbaad"),
    (r"\bpaisa\s+vasoo?l\b", "great value for money", "paisa vasool"),
    (r"\bpaise?\s+vasoo?l\b", "great value for money", "paisa vasool"),
    (r"\bbilkul\s+nahi\b", "definitely not", "bilkul nahi"),
    (r"\bbilkul\s+bhi\s+nahi\b", "definitely not", "bilkul nahi"),
    (r"\bekdam\s+mast\b", "excellent", "ekdam mast"),
    (r"\bekdum\s+mast\b", "excellent", "ekdum mast"),
    (r"\bekdam\s+bakwa+s\b", "terrible", "ekdam bakwas"),
    (r"\bekdum\s+bakwa+s\b", "terrible", "ekdum bakwas"),
    (r"\btheek\s+tha+k\b", "okay average", "theek thaak"),
    (r"\bthik\s+tha+k\b", "okay average", "theek thaak"),
    (r"\btheek\s+hai\b", "okay average", "theek hai"),
    (r"\bthik\s+hai\b", "okay average", "thik hai"),
    (r"\bthird\s+class\b", "terrible", "third class"),
    (r"\bchuna\s+laga\s*(?:diya)?\b", "scam", "chuna laga diya"),
    (r"\b(?:badiya|badhiya|mast|tagda|kamaal)\s+(?:bhi\s+)?(?:nahi|nahin)\b", "not good", "badiya nahi"),
    (r"\bachha\s+(?:bhi\s+)?(?:nahi|nahin)\b", "not good", "achha nahi"),
]

# Single-word Hinglish slang to English sentiment tokens
HINGLISH_WORDS: dict[str, tuple[str, str]] = {
    "mast": ("excellent", "mast"),
    "jhakas": ("excellent", "jhakas"),
    "jhakaas": ("excellent", "jhakaas"),
    "badiya": ("excellent", "badiya"),
    "badhiya": ("excellent", "badhiya"),
    "tagda": ("excellent", "tagda"),
    "tagdi": ("excellent", "tagda"),
    "kamaal": ("amazing", "kamaal"),
    "kamal": ("amazing", "kamal"),
    "zabardast": ("terrific", "zabardast"),
    "shandar": ("terrific", "shandar"),
    "gazab": ("terrific", "gazab"),
    "gajab": ("terrific", "gazab"),
    "bakwas": ("terrible", "bakwas"),
    "bakwaas": ("terrible", "bakwas"),
    "bekar": ("terrible", "bekar"),
    "bekaar": ("terrible", "bekar"),
    "ghatiya": ("terrible", "ghatiya"),
    "khrab": ("terrible", "khrab"),
    "kharab": ("terrible", "kharab"),
    "chuna": ("scam", "chuna"),
    "choona": ("scam", "chuna"),
    "dhoka": ("scam", "dhoka"),
    "dhokha": ("scam", "dhoka"),
    "kachra": ("garbage", "kachra"),
    "nahi": ("not", "nahi"),
    "nahin": ("not", "nahin"),
    "mat": ("do not", "mat"),
    "na": ("not", "na"),
}


def replace_emojis(text: str) -> str:
    """Converts sentiment-bearing emojis into explicit words."""
    result = []
    for char in text:
        if char in EMOJI_SENTIMENT_MAP:
            result.append(EMOJI_SENTIMENT_MAP[char])
        else:
            result.append(char)
    return "".join(result)


def replace_hinglish(text: str) -> tuple[str, list[str]]:
    """Normalizes Hinglish slang expressions and returns detected terms."""
    detected: list[str] = []
    normalized = text

    # Process multi-word phrases first
    for pattern, replacement, label in HINGLISH_PHRASES:
        if re.search(pattern, normalized, flags=re.IGNORECASE):
            detected.append(label)
            normalized = re.sub(pattern, f" {replacement} ", normalized, flags=re.IGNORECASE)

    # Process single-word mappings
    for word, (replacement, label) in HINGLISH_WORDS.items():
        pattern = rf"\b{re.escape(word)}\b"
        if re.search(pattern, normalized, flags=re.IGNORECASE):
            if label not in detected:
                detected.append(label)
            normalized = re.sub(pattern, f" {replacement} ", normalized, flags=re.IGNORECASE)

    return normalized, detected


def normalize_review_text(text: str) -> dict:
    """Normalizes review text converting emojis, Hinglish, and preserving negations."""
    if not text:
        return {"cleaned_text": "", "token_count": 0, "detected_hinglish": []}

    # 1. Map emojis
    with_emojis = replace_emojis(text)

    # 2. Map Hinglish expressions
    with_hinglish, detected = replace_hinglish(with_emojis)

    # 3. Clean up excess whitespace while preserving punctuation for clause splitting
    cleaned = re.sub(r"[ \t]+", " ", with_hinglish).strip()
    tokens = [t for t in re.split(r"\s+", cleaned) if t]

    return {
        "cleaned_text": cleaned,
        "token_count": len(tokens),
        "detected_hinglish": detected,
    }

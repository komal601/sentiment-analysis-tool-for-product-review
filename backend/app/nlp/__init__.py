"""Core NLP modules for sentiment, trust scoring, ABSA, and aggregation."""

from app.nlp.preprocessor import normalize_review_text
from app.nlp.trust_scorer import calculate_trust_scores, calculate_platform_trust
from app.nlp.absa_engine import extract_aspects_and_logistics
from app.nlp.aggregator import analyze_product_pipeline, detect_temporal_drift

__all__ = [
    "normalize_review_text",
    "calculate_trust_scores",
    "calculate_platform_trust",
    "extract_aspects_and_logistics",
    "analyze_product_pipeline",
    "detect_temporal_drift",
]

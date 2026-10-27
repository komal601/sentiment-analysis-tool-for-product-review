export type AspectKey =
  | "sound_quality"
  | "anc_noise_cancellation"
  | "mic_call_quality"
  | "battery_life"
  | "comfort_build"
  | "value_for_money";

export interface ProductMetadata {
  name: string;
  category: string;
  image_url: string | null;
  total_reviews_analyzed: number;
  data_source: "live_scrape" | "cached_fallback";
}

export interface SentimentSplit {
  positive: number;
  negative: number;
  neutral: number;
}

export interface PlatformStats {
  overall_rating: number;
  sentiment_split: SentimentSplit;
  trust_score: number;
  verified_purchase_ratio: number;
  fulfillment_complaint_rate: number;
}

/** Alias for compatibility with task requirements */
export type PlatformMetrics = PlatformStats;

export interface PlatformComparison {
  amazon: PlatformStats;
  flipkart: PlatformStats;
}

export interface AspectScore {
  aspect: AspectKey;
  amazon_score: number;
  flipkart_score: number;
  summary: string;
}

export interface TemporalDrift {
  initial_sentiment: number;
  long_term_sentiment: number;
  durability_warning: string | null;
}

export interface AISummary {
  pros: string[];
  cons: string[];
  buying_verdict: string;
}

export interface GenuineReview {
  review_id: string;
  platform: "amazon" | "flipkart";
  author: string;
  rating: number;
  title: string | null;
  text: string;
  review_date: string;
  verified_purchase: boolean;
  helpful_votes: number;
  sentiment: "positive" | "negative" | "neutral";
  aspects_mentioned: AspectKey[];
  review_trust_score: number;
}

export interface AnalyzeResponse {
  product_metadata: ProductMetadata;
  platform_comparison: PlatformComparison;
  aspect_scores: AspectScore[];
  temporal_drift: TemporalDrift;
  ai_summary: AISummary;
  top_genuine_reviews: GenuineReview[];
}

export interface ProductSuggestion {
  query: string;
  name: string;
  category: string;
  image_url?: string | null;
  total_seed_reviews: number;
}

export interface InspectReviewRequest {
  text: string;
  rating: number;
  verified_purchase: boolean;
  platform: "amazon" | "flipkart";
}

export interface InspectReviewResponse {
  normalized_text: string;
  detected_hinglish: string[];
  sentiment_polarity: string;
  trust_score: number;
  is_suspicious: boolean;
  trust_flags: string[];
  detected_aspects: Record<string, string>;
  is_logistics_complaint: boolean;
}

export interface HealthResponse {
  status: string;
  engine: string;
  supported_platforms: string[];
  cached_products_count: number;
}

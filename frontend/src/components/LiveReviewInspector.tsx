"use client";

import React, { useState } from "react";
import {
  FlaskConical,
  Send,
  Loader2,
  Languages,
  ShieldAlert,
  ShieldCheck,
  Truck,
  Sparkles,
  ChevronDown,
  ChevronUp,
} from "lucide-react";
import { InspectReviewRequest, InspectReviewResponse } from "@/types/analysis";
import { inspectSingleReview } from "@/lib/api";

export function LiveReviewInspector() {
  const [isOpen, setIsOpen] = useState(true);
  const [text, setText] = useState(
    "Bass is ekdum mast and sound quality badiya hai, but mic bekar hai outdoors. Overall paisa vasool!"
  );
  const [rating, setRating] = useState<number>(4);
  const [verified, setVerified] = useState<boolean>(true);
  const [platform, setPlatform] = useState<"amazon" | "flipkart">("amazon");
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [result, setResult] = useState<InspectReviewResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  const presets = [
    {
      label: "Hinglish Mixed Review",
      text: "Bass is ekdum mast and sound quality badiya hai, but mic bekar hai outdoors. Overall paisa vasool!",
      rating: 4,
      verified: true,
      platform: "amazon" as const,
    },
    {
      label: "Fake Bot Review",
      text: "nice product good",
      rating: 5,
      verified: false,
      platform: "flipkart" as const,
    },
    {
      label: "Delivery / Open Box Complaint",
      text: "Received unsealed box with missing ear tips. Amazon delivery was delayed by 4 days, terrible seller service!",
      rating: 1,
      verified: true,
      platform: "amazon" as const,
    },
  ];

  const handleInspect = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    if (!text.trim() || isLoading) return;

    setIsLoading(true);
    setError(null);

    try {
      const payload: InspectReviewRequest = {
        text: text.trim(),
        rating,
        verified_purchase: verified,
        platform,
      };
      const res = await inspectSingleReview(payload);
      setResult(res);
    } catch (err: unknown) {
      setError(
        err instanceof Error ? err.message : "Failed to inspect review."
      );
    } finally {
      setIsLoading(false);
    }
  };

  const applyPreset = (preset: (typeof presets)[0]) => {
    setText(preset.text);
    setRating(preset.rating);
    setVerified(preset.verified);
    setPlatform(preset.platform);
  };

  return (
    <div className="w-full max-w-5xl mx-auto px-4 mb-10">
      <div className="rounded-2xl bg-slate-900/80 border border-slate-800 p-5 md:p-6 backdrop-blur-md shadow-2xl">
        {/* Toggle Header */}
        <div className="flex items-center justify-between pb-4 border-b border-slate-800">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-xl bg-purple-500/10 border border-purple-500/30 text-purple-400">
              <FlaskConical className="w-5 h-5" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h3 className="text-base font-bold text-white">
                  Live Review Inspector & Sandbox
                </h3>
                <span className="text-[10px] uppercase font-bold tracking-wider px-2 py-0.5 rounded-full bg-purple-500/20 text-purple-300 border border-purple-500/30">
                  Interactive Viva Sandbox
                </span>
              </div>
              <p className="text-xs text-slate-400 mt-0.5">
                Type or paste any custom Hinglish text or bot template to test normalization, trust scoring, and clause-level ABSA in real time.
              </p>
            </div>
          </div>

          <button
            type="button"
            onClick={() => setIsOpen(!isOpen)}
            className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition"
          >
            {isOpen ? <ChevronUp className="w-5 h-5" /> : <ChevronDown className="w-5 h-5" />}
          </button>
        </div>

        {isOpen && (
          <div className="mt-4 space-y-4">
            {/* Quick Presets */}
            <div className="flex flex-wrap items-center gap-2 text-xs">
              <span className="text-slate-400 font-medium">Quick Presets:</span>
              {presets.map((p, idx) => (
                <button
                  key={idx}
                  type="button"
                  onClick={() => applyPreset(p)}
                  className="px-2.5 py-1 rounded-lg bg-slate-950 border border-slate-800 text-slate-300 hover:text-white hover:border-slate-700 transition text-[11px]"
                >
                  {p.label}
                </button>
              ))}
            </div>

            {/* Input Form */}
            <form onSubmit={handleInspect} className="space-y-3">
              <textarea
                value={text}
                onChange={(e) => setText(e.target.value)}
                rows={3}
                placeholder="Enter review text (e.g., Hinglish slang, suspicious short text, or complaints)..."
                className="w-full rounded-xl bg-slate-950 border border-slate-800 p-3 text-xs md:text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:border-purple-500/60 focus:ring-1 focus:ring-purple-500/30 transition resize-none"
              />

              {/* Controls bar */}
              <div className="flex flex-wrap items-center justify-between gap-3 bg-slate-950/60 p-3 rounded-xl border border-slate-800/80">
                <div className="flex flex-wrap items-center gap-4 text-xs">
                  {/* Rating Selector */}
                  <div className="flex items-center gap-1.5">
                    <span className="text-slate-400 font-medium">Rating:</span>
                    <select
                      value={rating}
                      onChange={(e) => setRating(Number(e.target.value))}
                      className="bg-slate-900 border border-slate-700 text-white rounded-lg px-2 py-1 text-xs focus:outline-none"
                    >
                      <option value={5}>5 Stars ★★★★★</option>
                      <option value={4}>4 Stars ★★★★☆</option>
                      <option value={3}>3 Stars ★★★☆☆</option>
                      <option value={2}>2 Stars ★★☆☆☆</option>
                      <option value={1}>1 Star ★☆☆☆☆</option>
                    </select>
                  </div>

                  {/* Platform Selector */}
                  <div className="flex items-center gap-1.5">
                    <span className="text-slate-400 font-medium">Platform:</span>
                    <select
                      value={platform}
                      onChange={(e) => setPlatform(e.target.value as "amazon" | "flipkart")}
                      className="bg-slate-900 border border-slate-700 text-white rounded-lg px-2 py-1 text-xs focus:outline-none"
                    >
                      <option value="amazon">Amazon.in</option>
                      <option value="flipkart">Flipkart</option>
                    </select>
                  </div>

                  {/* Verified Checkbox */}
                  <label className="flex items-center gap-1.5 cursor-pointer text-slate-300">
                    <input
                      type="checkbox"
                      checked={verified}
                      onChange={(e) => setVerified(e.target.checked)}
                      className="rounded border-slate-700 text-emerald-500 focus:ring-emerald-500/20 bg-slate-900"
                    />
                    <span>Verified Purchase</span>
                  </label>
                </div>

                {/* Inspect Button */}
                <button
                  type="submit"
                  disabled={isLoading || !text.trim()}
                  className="flex items-center gap-2 px-4 py-2 rounded-xl bg-purple-600 hover:bg-purple-500 text-white font-bold text-xs transition disabled:opacity-50 disabled:cursor-not-allowed shadow-md shadow-purple-600/20 active:scale-95"
                >
                  {isLoading ? (
                    <>
                      <Loader2 className="w-3.5 h-3.5 animate-spin" />
                      <span>Inspecting...</span>
                    </>
                  ) : (
                    <>
                      <Send className="w-3.5 h-3.5" />
                      <span>Inspect Review</span>
                    </>
                  )}
                </button>
              </div>
            </form>

            {/* Error Message */}
            {error && (
              <div className="p-3 rounded-xl bg-rose-500/10 border border-rose-500/30 text-rose-300 text-xs">
                {error}
              </div>
            )}

            {/* Inspection Results Panel */}
            {result && (
              <div className="mt-4 p-4 rounded-xl bg-slate-950 border border-purple-500/30 space-y-3.5">
                <div className="flex flex-wrap items-center justify-between gap-2 pb-2.5 border-b border-slate-800">
                  <span className="text-xs font-bold text-purple-300 flex items-center gap-1.5">
                    <Sparkles className="w-3.5 h-3.5" />
                    Real-Time Pipeline Breakdown
                  </span>
                  <div className="flex items-center gap-2">
                    <span
                      className={`text-[11px] font-bold px-2 py-0.5 rounded-full border ${
                        result.trust_score >= 70
                          ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/30"
                          : result.trust_score >= 40
                          ? "bg-amber-500/10 text-amber-400 border-amber-500/30"
                          : "bg-rose-500/10 text-rose-400 border-rose-500/30"
                      }`}
                    >
                      Trust Score: {result.trust_score}/100
                    </span>

                    <span
                      className={`text-[11px] font-bold px-2 py-0.5 rounded-full uppercase ${
                        result.sentiment_polarity === "positive"
                          ? "bg-emerald-500/20 text-emerald-400"
                          : result.sentiment_polarity === "negative"
                          ? "bg-rose-500/20 text-rose-400"
                          : "bg-slate-700 text-slate-300"
                      }`}
                    >
                      {result.sentiment_polarity}
                    </span>
                  </div>
                </div>

                {/* Normalized English & Hinglish slang */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                  <div className="p-3 rounded-lg bg-slate-900/60 border border-slate-800">
                    <div className="text-[11px] text-slate-400 font-semibold mb-1 flex items-center gap-1.5">
                      <Languages className="w-3.5 h-3.5 text-cyan-400" />
                      <span>Normalized English Representation:</span>
                    </div>
                    <p className="text-xs text-slate-200 leading-relaxed font-mono">
                      {result.normalized_text}
                    </p>
                  </div>

                  <div className="p-3 rounded-lg bg-slate-900/60 border border-slate-800">
                    <div className="text-[11px] text-slate-400 font-semibold mb-1">
                      Detected Hinglish Slang Terms:
                    </div>
                    {result.detected_hinglish.length > 0 ? (
                      <div className="flex flex-wrap gap-1.5 mt-1">
                        {result.detected_hinglish.map((term, i) => (
                          <span
                            key={i}
                            className="text-[10px] font-mono font-semibold px-2 py-0.5 rounded-md bg-purple-500/20 text-purple-300 border border-purple-500/30"
                          >
                            {term}
                          </span>
                        ))}
                      </div>
                    ) : (
                      <span className="text-xs text-slate-500">None detected (Standard English)</span>
                    )}
                  </div>
                </div>

                {/* Trust Flags & Logistics Status */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                  {/* Trust Flags */}
                  <div className="p-3 rounded-lg bg-slate-900/60 border border-slate-800">
                    <div className="text-[11px] text-slate-400 font-semibold mb-1 flex items-center gap-1.5">
                      {result.is_suspicious ? (
                        <ShieldAlert className="w-3.5 h-3.5 text-rose-400" />
                      ) : (
                        <ShieldCheck className="w-3.5 h-3.5 text-emerald-400" />
                      )}
                      <span>Anti-Bot Flags:</span>
                    </div>
                    {result.trust_flags.length > 0 ? (
                      <div className="flex flex-wrap gap-1.5 mt-1">
                        {result.trust_flags.map((flag, i) => (
                          <span
                            key={i}
                            className="text-[10px] font-semibold px-2 py-0.5 rounded-md bg-rose-500/20 text-rose-300 border border-rose-500/30"
                          >
                            {flag}
                          </span>
                        ))}
                      </div>
                    ) : (
                      <span className="text-xs text-emerald-400">Zero suspicious flags detected</span>
                    )}
                  </div>

                  {/* Logistics / Fulfillment Separator */}
                  <div className="p-3 rounded-lg bg-slate-900/60 border border-slate-800">
                    <div className="text-[11px] text-slate-400 font-semibold mb-1 flex items-center gap-1.5">
                      <Truck className="w-3.5 h-3.5 text-amber-400" />
                      <span>Logistics Complaint Detection:</span>
                    </div>
                    {result.is_logistics_complaint ? (
                      <div className="text-xs text-amber-300 mt-1">
                        <span className="font-bold">Flagged as Fulfillment / Delivery issue</span>
                        <p className="text-[10px] text-slate-400 mt-0.5">
                          Excluded from product hardware aspect scoring.
                        </p>
                      </div>
                    ) : (
                      <div className="text-xs text-slate-400 mt-1">
                        Product hardware review (Included in ABSA).
                      </div>
                    )}
                  </div>
                </div>

                {/* Extracted Aspect Scores */}
                <div>
                  <div className="text-[11px] text-slate-400 font-semibold mb-1.5">
                    Extracted Aspect Sentiments:
                  </div>
                  {Object.keys(result.detected_aspects).length > 0 ? (
                    <div className="flex flex-wrap gap-2">
                      {Object.entries(result.detected_aspects).map(([aspect, polarity]) => (
                        <div
                          key={aspect}
                          className="flex items-center gap-1.5 text-xs px-2.5 py-1 rounded-lg bg-slate-900 border border-slate-800"
                        >
                          <span className="text-slate-300 font-medium capitalize">
                            {aspect.replace(/_/g, " ")}:
                          </span>
                          <span
                            className={`font-bold capitalize ${
                              polarity === "positive"
                                ? "text-emerald-400"
                                : polarity === "negative"
                                ? "text-rose-400"
                                : "text-slate-400"
                            }`}
                          >
                            {polarity}
                          </span>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <span className="text-xs text-slate-500">
                      No specific hardware aspects mentioned in this review.
                    </span>
                  )}
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

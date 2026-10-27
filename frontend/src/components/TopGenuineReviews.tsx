"use client";

import React from "react";
import { Star, ShieldCheck, ThumbsUp, CheckCircle, MessageSquareQuote } from "lucide-react";
import { GenuineReview } from "@/types/analysis";

interface TopGenuineReviewsProps {
  reviews: GenuineReview[];
}

export function TopGenuineReviews({ reviews }: TopGenuineReviewsProps) {
  if (!reviews || reviews.length === 0) {
    return (
      <div className="w-full max-w-5xl mx-auto px-4 mb-6">
        <div className="rounded-2xl bg-slate-900/60 border border-slate-800 p-6 text-center text-slate-400 text-sm">
          No high-trust reviews found matching the verification threshold.
        </div>
      </div>
    );
  }

  return (
    <div className="w-full max-w-5xl mx-auto px-4 mb-6">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h2 className="text-base md:text-lg font-bold text-white flex items-center gap-2">
            <MessageSquareQuote className="w-5 h-5 text-emerald-400" />
            <span>Top Genuine Verified Buyer Reviews</span>
          </h2>
          <p className="text-xs text-slate-400 mt-0.5">
            Filtered by Trust Score (≥ 70), verified purchase status, and organic language patterns.
          </p>
        </div>
        <span className="text-xs text-slate-400 font-mono">
          Showing top {reviews.length} authenticated
        </span>
      </div>

      <div className="space-y-3">
        {reviews.map((rev) => {
          const isAmazon = rev.platform === "amazon";

          return (
            <div
              key={rev.review_id}
              className="rounded-2xl bg-slate-900/70 border border-slate-800/80 p-4 md:p-5 backdrop-blur-sm hover:border-slate-700 transition-all shadow-md"
            >
              {/* Review Card Header */}
              <div className="flex flex-wrap items-center justify-between gap-2 mb-2.5">
                <div className="flex items-center gap-2.5">
                  {/* Platform Badge */}
                  <span
                    className={`text-[11px] font-bold px-2 py-0.5 rounded-md uppercase tracking-wider ${
                      isAmazon
                        ? "bg-amber-500/15 text-amber-300 border border-amber-500/30"
                        : "bg-cyan-500/15 text-cyan-300 border border-cyan-500/30"
                    }`}
                  >
                    {isAmazon ? "Amazon.in" : "Flipkart"}
                  </span>

                  {/* Author Name */}
                  <span className="text-xs font-semibold text-slate-200">
                    {rev.author || "Anonymous Buyer"}
                  </span>

                  {/* Verified Badge */}
                  {rev.verified_purchase && (
                    <span className="inline-flex items-center gap-1 text-[10px] text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded-full border border-emerald-500/20">
                      <CheckCircle className="w-3 h-3" />
                      Verified Purchase
                    </span>
                  )}
                </div>

                <div className="flex items-center gap-2.5">
                  {/* Trust Score Pill */}
                  <div className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 text-xs font-bold">
                    <ShieldCheck className="w-3.5 h-3.5" />
                    <span>Trust: {rev.review_trust_score}/100</span>
                  </div>

                  {/* Star Rating */}
                  <div className="flex items-center gap-0.5">
                    {Array.from({ length: 5 }).map((_, i) => (
                      <Star
                        key={i}
                        className={`w-3.5 h-3.5 ${
                          i < rev.rating
                            ? "text-amber-400 fill-amber-400"
                            : "text-slate-700"
                        }`}
                      />
                    ))}
                  </div>
                </div>
              </div>

              {/* Title & Body */}
              {rev.title && (
                <h4 className="text-sm font-bold text-slate-100 mb-1">
                  {rev.title}
                </h4>
              )}
              <p className="text-xs md:text-sm text-slate-300 leading-relaxed">
                {rev.text}
              </p>

              {/* Footer: Aspects mentioned & Helpful Votes */}
              <div className="mt-3 pt-2.5 border-t border-slate-800/80 flex flex-wrap items-center justify-between gap-2 text-xs">
                <div className="flex flex-wrap items-center gap-1.5">
                  <span className="text-[11px] text-slate-500">Aspects:</span>
                  {rev.aspects_mentioned && rev.aspects_mentioned.length > 0 ? (
                    rev.aspects_mentioned.map((aspect) => (
                      <span
                        key={aspect}
                        className="text-[10px] px-2 py-0.5 rounded-md bg-slate-800/90 text-slate-300 border border-slate-700 font-medium"
                      >
                        {aspect.replace(/_/g, " ")}
                      </span>
                    ))
                  ) : (
                    <span className="text-[10px] text-slate-600">General feedback</span>
                  )}
                </div>

                <div className="flex items-center gap-3 text-[11px] text-slate-400">
                  <span>{rev.review_date}</span>
                  {rev.helpful_votes > 0 && (
                    <span className="flex items-center gap-1 text-slate-300">
                      <ThumbsUp className="w-3 h-3 text-slate-400" />
                      {rev.helpful_votes} found helpful
                    </span>
                  )}
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

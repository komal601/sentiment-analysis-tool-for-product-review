"use client";

import React from "react";
import { Star, ShieldCheck, ShieldAlert, Truck, CheckCircle2, AlertTriangle } from "lucide-react";
import { PlatformComparison } from "@/types/analysis";

interface PlatformComparisonCardsProps {
  comparison: PlatformComparison;
}

export function PlatformComparisonCards({ comparison }: PlatformComparisonCardsProps) {
  const { amazon, flipkart } = comparison;

  const getTrustBadge = (score: number) => {
    if (score >= 70) {
      return {
        label: "High Trust",
        bg: "bg-emerald-500/10 text-emerald-400 border-emerald-500/30",
        icon: <ShieldCheck className="w-4 h-4 text-emerald-400" />,
      };
    } else if (score >= 50) {
      return {
        label: "Moderate Trust",
        bg: "bg-amber-500/10 text-amber-400 border-amber-500/30",
        icon: <ShieldAlert className="w-4 h-4 text-amber-400" />,
      };
    } else {
      return {
        label: "Low Authenticity",
        bg: "bg-rose-500/10 text-rose-400 border-rose-500/30",
        icon: <AlertTriangle className="w-4 h-4 text-rose-400" />,
      };
    }
  };

  const renderCard = (
    platformName: "Amazon India" | "Flipkart",
    stats: typeof amazon,
    theme: {
      border: string;
      headerBg: string;
      badgeText: string;
      logoText: string;
      accentColor: string;
    }
  ) => {
    const trustBadge = getTrustBadge(stats.trust_score);
    const verifiedPercent = Math.round(stats.verified_purchase_ratio * 100);
    const isHighLogistics = stats.fulfillment_complaint_rate >= 25;

    return (
      <div
        className={`flex-1 rounded-2xl bg-slate-900/70 border ${theme.border} p-5 backdrop-blur-sm shadow-xl flex flex-col justify-between transition-all hover:border-slate-700`}
      >
        <div>
          {/* Platform Header */}
          <div className="flex items-center justify-between pb-4 border-b border-slate-800">
            <div className="flex items-center gap-2.5">
              <span className={`text-xl font-black tracking-tight ${theme.logoText}`}>
                {platformName}
              </span>
              <span className={`text-[11px] font-semibold px-2 py-0.5 rounded-full border ${theme.headerBg} ${theme.badgeText}`}>
                Verified Source
              </span>
            </div>
            {/* Overall Star Rating */}
            <div className="flex items-center gap-1.5 bg-slate-950/80 px-2.5 py-1 rounded-xl border border-slate-800">
              <Star className="w-4 h-4 text-amber-400 fill-amber-400" />
              <span className="font-bold text-white text-base">
                {stats.overall_rating.toFixed(1)}
              </span>
              <span className="text-xs text-slate-500 font-medium">/ 5.0</span>
            </div>
          </div>

          {/* Trust Score Gauge & Badges */}
          <div className="grid grid-cols-2 gap-3 my-4">
            <div className="p-3 rounded-xl bg-slate-950/60 border border-slate-800/80">
              <div className="text-[11px] text-slate-400 font-medium mb-1 flex items-center justify-between">
                <span>Trust Score</span>
                <span className="text-[10px] text-slate-500">Anti-Bot</span>
              </div>
              <div className="flex items-baseline gap-2">
                <span className="text-2xl font-black text-white">{stats.trust_score}</span>
                <span className="text-xs text-slate-500">/ 100</span>
              </div>
              <div className={`mt-1.5 inline-flex items-center gap-1 px-2 py-0.5 rounded-md border text-[11px] font-semibold ${trustBadge.bg}`}>
                {trustBadge.icon}
                <span>{trustBadge.label}</span>
              </div>
            </div>

            <div className="p-3 rounded-xl bg-slate-950/60 border border-slate-800/80">
              <div className="text-[11px] text-slate-400 font-medium mb-1 flex items-center justify-between">
                <span>Verified Purchases</span>
                <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
              </div>
              <div className="flex items-baseline gap-2">
                <span className="text-2xl font-black text-white">{verifiedPercent}%</span>
                <span className="text-xs text-slate-500">of buyers</span>
              </div>
              <div className="mt-1.5 text-[11px] text-slate-400 font-medium">
                {verifiedPercent >= 75 ? (
                  <span className="text-emerald-400">High direct buyer ratio</span>
                ) : (
                  <span className="text-amber-400">Moderate unverified ratio</span>
                )}
              </div>
            </div>
          </div>

          {/* Sentiment Split Stacked Progress Bar */}
          <div className="mb-4">
            <div className="flex items-center justify-between text-xs font-semibold mb-1.5 text-slate-300">
              <span>Sentiment Split</span>
              <div className="flex items-center gap-3 text-[11px]">
                <span className="text-emerald-400 font-bold">{stats.sentiment_split.positive.toFixed(0)}% Pos</span>
                <span className="text-slate-400">{stats.sentiment_split.neutral.toFixed(0)}% Neu</span>
                <span className="text-rose-400 font-bold">{stats.sentiment_split.negative.toFixed(0)}% Neg</span>
              </div>
            </div>

            {/* Stacked Bar */}
            <div className="h-3 w-full bg-slate-950 rounded-full overflow-hidden flex p-0.5 border border-slate-800">
              <div
                style={{ width: `${stats.sentiment_split.positive}%` }}
                className="h-full bg-emerald-500 rounded-l-full transition-all duration-500"
                title={`Positive: ${stats.sentiment_split.positive}%`}
              />
              <div
                style={{ width: `${stats.sentiment_split.neutral}%` }}
                className="h-full bg-slate-500 transition-all duration-500"
                title={`Neutral: ${stats.sentiment_split.neutral}%`}
              />
              <div
                style={{ width: `${stats.sentiment_split.negative}%` }}
                className="h-full bg-rose-500 rounded-r-full transition-all duration-500"
                title={`Negative: ${stats.sentiment_split.negative}%`}
              />
            </div>
          </div>
        </div>

        {/* Fulfillment / Logistics Separation Warning */}
        <div className="mt-2 pt-3 border-t border-slate-800/80">
          <div className="flex items-start gap-2.5">
            <Truck className={`w-4 h-4 shrink-0 mt-0.5 ${isHighLogistics ? "text-amber-400" : "text-slate-400"}`} />
            <div className="text-xs">
              <div className="flex items-center gap-2">
                <span className="font-semibold text-slate-200">
                  Seller / Delivery Complaints:
                </span>
                <span
                  className={`font-mono font-bold px-1.5 py-0.5 rounded text-[11px] ${
                    isHighLogistics
                      ? "bg-amber-500/20 text-amber-300 border border-amber-500/30"
                      : "bg-slate-800 text-slate-300"
                  }`}
                >
                  {stats.fulfillment_complaint_rate.toFixed(1)}% of negatives
                </span>
              </div>
              <p className="text-slate-400 text-[11px] mt-0.5 leading-relaxed">
                {isHighLogistics ? (
                  <span className="text-amber-300/90">
                    Warning: Elevated complaints regarding unsealed boxes, late delivery, or wrong item. (Isolated from product ABSA).
                  </span>
                ) : (
                  "Low seller issues; negative feedback relates purely to actual product hardware."
                )}
              </p>
            </div>
          </div>
        </div>
      </div>
    );
  };

  return (
    <div className="w-full max-w-5xl mx-auto px-4 mb-6">
      <div className="flex items-center justify-between mb-3">
        <h2 className="text-base md:text-lg font-bold text-white flex items-center gap-2">
          <span>Platform Head-to-Head Comparison</span>
        </h2>
        <span className="text-xs text-slate-400 font-medium">
          Both platforms independently processed & cross-verified
        </span>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {renderCard("Amazon India", amazon, {
          border: "border-amber-500/30",
          headerBg: "bg-amber-500/10",
          badgeText: "text-amber-400",
          logoText: "text-amber-400",
          accentColor: "#f59e0b",
        })}

        {renderCard("Flipkart", flipkart, {
          border: "border-blue-500/30",
          headerBg: "bg-blue-500/10",
          badgeText: "text-cyan-400",
          logoText: "text-cyan-400",
          accentColor: "#06b6d4",
        })}
      </div>
    </div>
  );
}

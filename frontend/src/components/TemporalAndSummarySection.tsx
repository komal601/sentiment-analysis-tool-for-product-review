"use client";

import React from "react";
import {
  CheckCircle2,
  XCircle,
  Clock,
  AlertTriangle,
  Lightbulb,
  TrendingDown,
  TrendingUp,
  Sparkles,
} from "lucide-react";
import { AISummary, TemporalDrift } from "@/types/analysis";

interface TemporalAndSummarySectionProps {
  aiSummary: AISummary;
  temporalDrift: TemporalDrift;
}

export function TemporalAndSummarySection({
  aiSummary,
  temporalDrift,
}: TemporalAndSummarySectionProps) {
  const { pros, cons, buying_verdict } = aiSummary;
  const { initial_sentiment, long_term_sentiment, durability_warning } = temporalDrift;

  const driftDiff = long_term_sentiment - initial_sentiment;
  const isDeclining = driftDiff <= -15;

  return (
    <div className="w-full max-w-5xl mx-auto px-4 mb-6 space-y-4">
      {/* AI Buying Verdict Banner */}
      <div className="relative overflow-hidden rounded-2xl bg-gradient-to-r from-emerald-950/60 via-slate-900/90 to-teal-950/60 border border-emerald-500/30 p-5 md:p-6 backdrop-blur shadow-2xl">
        <div className="flex items-start gap-3">
          <div className="p-2.5 rounded-xl bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 shrink-0 mt-0.5">
            <Sparkles className="w-5 h-5" />
          </div>
          <div>
            <div className="flex items-center gap-2 mb-1">
              <span className="text-xs font-bold uppercase tracking-wider text-emerald-400">
                AI Cross-Platform Buying Verdict
              </span>
              <span className="text-[10px] px-2 py-0.5 rounded-full bg-slate-800 text-slate-400 border border-slate-700">
                LLM Synthesized
              </span>
            </div>
            <p className="text-sm md:text-base font-medium text-slate-100 leading-relaxed">
              {buying_verdict}
            </p>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-12 gap-4">
        {/* Pros & Cons Columns (7 cols) */}
        <div className="md:col-span-7 rounded-2xl bg-slate-900/70 border border-slate-800 p-5 backdrop-blur-sm shadow-xl flex flex-col justify-between">
          <div>
            <h3 className="text-sm font-bold text-white mb-4 flex items-center gap-2">
              <Lightbulb className="w-4 h-4 text-amber-400" />
              <span>Key Pros & Cons (Verified Review Insights)</span>
            </h3>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              {/* Pros */}
              <div className="space-y-2.5">
                <div className="text-xs font-bold text-emerald-400 uppercase tracking-wide flex items-center gap-1.5">
                  <CheckCircle2 className="w-3.5 h-3.5" />
                  <span>The Good</span>
                </div>
                <ul className="space-y-2">
                  {pros.map((pro, idx) => (
                    <li
                      key={idx}
                      className="text-xs text-slate-300 flex items-start gap-2 bg-emerald-950/20 border border-emerald-900/30 p-2.5 rounded-xl leading-snug"
                    >
                      <span className="text-emerald-400 font-bold shrink-0 mt-0.5">•</span>
                      <span>{pro}</span>
                    </li>
                  ))}
                </ul>
              </div>

              {/* Cons */}
              <div className="space-y-2.5">
                <div className="text-xs font-bold text-rose-400 uppercase tracking-wide flex items-center gap-1.5">
                  <XCircle className="w-3.5 h-3.5" />
                  <span>The Bad</span>
                </div>
                <ul className="space-y-2">
                  {cons.map((con, idx) => (
                    <li
                      key={idx}
                      className="text-xs text-slate-300 flex items-start gap-2 bg-rose-950/20 border border-rose-900/30 p-2.5 rounded-xl leading-snug"
                    >
                      <span className="text-rose-400 font-bold shrink-0 mt-0.5">•</span>
                      <span>{con}</span>
                    </li>
                  ))}
                </ul>
              </div>
            </div>
          </div>
        </div>

        {/* Temporal Sentiment Drift Card (5 cols) */}
        <div className="md:col-span-5 rounded-2xl bg-slate-900/70 border border-slate-800 p-5 backdrop-blur-sm shadow-xl flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-3">
              <h3 className="text-sm font-bold text-white flex items-center gap-2">
                <Clock className="w-4 h-4 text-cyan-400" />
                <span>Temporal Sentiment Drift</span>
              </h3>
              <span className="text-[10px] text-slate-400 font-medium">
                Day 1 vs. 3+ Months
              </span>
            </div>

            <p className="text-xs text-slate-400 mb-4 leading-relaxed">
              Detects if enthusiasm fades over long-term usage due to battery degradation, hinge issues, or build failure.
            </p>

            {/* Score Comparison Display */}
            <div className="grid grid-cols-2 gap-3 mb-4">
              <div className="p-3 rounded-xl bg-slate-950/60 border border-slate-800 text-center">
                <div className="text-[11px] text-slate-400 mb-1">Initial / Day 1</div>
                <div className="text-2xl font-black text-emerald-400">{initial_sentiment}%</div>
                <div className="text-[10px] text-slate-500 mt-0.5">Unboxing score</div>
              </div>

              <div className="p-3 rounded-xl bg-slate-950/60 border border-slate-800 text-center">
                <div className="text-[11px] text-slate-400 mb-1">Long-Term (3+ mo)</div>
                <div
                  className={`text-2xl font-black ${
                    long_term_sentiment < 65 ? "text-amber-400" : "text-emerald-400"
                  }`}
                >
                  {long_term_sentiment}%
                </div>
                <div className="text-[10px] text-slate-500 mt-0.5 flex items-center justify-center gap-1">
                  {driftDiff < 0 ? (
                    <span className="text-rose-400 font-bold flex items-center">
                      <TrendingDown className="w-3 h-3 inline mr-0.5" />
                      {driftDiff}%
                    </span>
                  ) : (
                    <span className="text-emerald-400 font-bold flex items-center">
                      <TrendingUp className="w-3 h-3 inline mr-0.5" />
                      +{driftDiff}%
                    </span>
                  )}
                </div>
              </div>
            </div>
          </div>

          {/* Durability Warning Callout */}
          {durability_warning || isDeclining ? (
            <div className="p-3 rounded-xl bg-amber-500/10 border border-amber-500/30 text-amber-300 text-xs">
              <div className="flex items-start gap-2">
                <AlertTriangle className="w-4 h-4 text-amber-400 shrink-0 mt-0.5" />
                <div>
                  <span className="font-bold block text-amber-200 mb-0.5">
                    Durability Warning Alert
                  </span>
                  <span className="text-[11px] leading-relaxed text-amber-300/90">
                    {durability_warning || "Significant drop detected in long-term sentiment."}
                  </span>
                </div>
              </div>
            </div>
          ) : (
            <div className="p-2.5 rounded-xl bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 text-xs flex items-center gap-2">
              <CheckCircle2 className="w-4 h-4 shrink-0" />
              <span className="text-[11px]">
                No significant durability drop detected. Sentiment holds steady over time.
              </span>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

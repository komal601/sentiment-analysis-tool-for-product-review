"use client";

import React, { useState, useEffect } from "react";
import { SearchHero } from "@/components/SearchHero";
import { PlatformComparisonCards } from "@/components/PlatformComparisonCards";
import { AspectRadarChart } from "@/components/AspectRadarChart";
import { TemporalAndSummarySection } from "@/components/TemporalAndSummarySection";
import { TopGenuineReviews } from "@/components/TopGenuineReviews";
import { LiveReviewInspector } from "@/components/LiveReviewInspector";
import { AnalyzeResponse } from "@/types/analysis";
import { analyzeProduct } from "@/lib/api";
import {
  AlertTriangle,
  RefreshCw,
  Layers,
  Server,
  Package,
} from "lucide-react";

export default function DashboardPage() {
  const [data, setData] = useState<AnalyzeResponse | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [currentQuery, setCurrentQuery] = useState<string>("realme buds t310");
  const [currentMode, setCurrentMode] = useState<"hybrid" | "offline">("offline");

  // User-triggered search
  const handleSearch = async (query: string, mode: "hybrid" | "offline" = "offline") => {
    setIsLoading(true);
    setError(null);
    setCurrentQuery(query);
    setCurrentMode(mode);

    try {
      const result = await analyzeProduct(query, mode);
      setData(result);
    } catch (err: unknown) {
      setError(
        err instanceof Error
          ? err.message
          : "Failed to load analysis. Please ensure the backend server is running on http://localhost:8000."
      );
    } finally {
      setIsLoading(false);
    }
  };

  // Initial load on mount for immediate rich presentation without synchronous setState warning
  useEffect(() => {
    let ignore = false;
    async function fetchInitial() {
      try {
        const result = await analyzeProduct("realme buds t310", "offline");
        if (!ignore) {
          setData(result);
          setIsLoading(false);
        }
      } catch (err: unknown) {
        if (!ignore) {
          setError(
            err instanceof Error
              ? err.message
              : "Failed to load initial analysis from backend."
          );
          setIsLoading(false);
        }
      }
    }

    fetchInitial();
    return () => {
      ignore = true;
    };
  }, []);

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col justify-between selection:bg-emerald-500/30 selection:text-emerald-200">
      {/* Top Navbar */}
      <header className="border-b border-slate-800/80 bg-slate-950/80 backdrop-blur sticky top-0 z-50">
        <div className="max-w-6xl mx-auto px-4 h-14 flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <div className="h-8 w-8 rounded-xl bg-gradient-to-tr from-emerald-500 to-cyan-500 flex items-center justify-center shadow-lg shadow-emerald-500/20">
              <Layers className="w-4 h-4 text-slate-950 font-bold" />
            </div>
            <div>
              <span className="font-black text-white text-base tracking-tight">
                Review<span className="text-emerald-400">Lens</span> AI
              </span>
              <span className="hidden sm:inline-block ml-2 text-[10px] uppercase font-bold text-slate-400 bg-slate-900 px-2 py-0.5 rounded-full border border-slate-800">
                v1.0 Production
              </span>
            </div>
          </div>

          <div className="flex items-center gap-3 text-xs">
            <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-slate-900 border border-slate-800 text-slate-400">
              <Server className="w-3.5 h-3.5 text-emerald-400" />
              <span className="hidden sm:inline">Backend API:</span>
              <span className="font-mono text-emerald-400 font-semibold">:8000</span>
            </div>

            <a
              href="http://localhost:8000/docs"
              target="_blank"
              rel="noreferrer"
              className="text-slate-400 hover:text-slate-200 transition text-xs font-medium"
            >
              API Docs
            </a>
          </div>
        </div>
      </header>

      {/* Main Content Area */}
      <main className="flex-1 pb-16">
        {/* Search Hero */}
        <SearchHero
          onSearch={handleSearch}
          isLoading={isLoading}
          currentQuery={currentQuery}
        />

        {/* Error Notification Banner */}
        {error && (
          <div className="w-full max-w-5xl mx-auto px-4 mb-6">
            <div className="rounded-2xl bg-rose-500/10 border border-rose-500/30 p-4 md:p-5 flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-rose-200">
              <div className="flex items-start gap-3">
                <AlertTriangle className="w-5 h-5 text-rose-400 shrink-0 mt-0.5" />
                <div>
                  <h4 className="text-sm font-bold text-rose-100">
                    Connection or Analysis Warning
                  </h4>
                  <p className="text-xs text-rose-300/90 mt-0.5 leading-relaxed">
                    {error}
                  </p>
                </div>
              </div>
              <button
                type="button"
                onClick={() => handleSearch(currentQuery, currentMode)}
                className="inline-flex items-center justify-center gap-1.5 px-3 py-1.5 rounded-xl bg-rose-500/20 hover:bg-rose-500/30 border border-rose-500/40 text-rose-200 text-xs font-bold transition shrink-0"
              >
                <RefreshCw className="w-3.5 h-3.5" />
                <span>Retry</span>
              </button>
            </div>
          </div>
        )}

        {/* Loading Skeleton */}
        {isLoading && (
          <div className="w-full max-w-5xl mx-auto px-4 space-y-6 animate-pulse">
            {/* Meta Bar skeleton */}
            <div className="h-14 rounded-2xl bg-slate-900/60 border border-slate-800" />
            {/* Platform cards skeleton */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="h-56 rounded-2xl bg-slate-900/60 border border-slate-800" />
              <div className="h-56 rounded-2xl bg-slate-900/60 border border-slate-800" />
            </div>
            {/* Radar chart skeleton */}
            <div className="h-80 rounded-2xl bg-slate-900/60 border border-slate-800" />
            {/* Temporal & AI Summary skeleton */}
            <div className="h-64 rounded-2xl bg-slate-900/60 border border-slate-800" />
          </div>
        )}

        {/* Analysis Dashboard Output */}
        {!isLoading && data && (
          <div className="space-y-6">
            {/* Product Meta Header Bar */}
            <div className="w-full max-w-5xl mx-auto px-4">
              <div className="flex flex-wrap items-center justify-between gap-3 p-4 rounded-2xl bg-slate-900/80 border border-slate-800 backdrop-blur shadow-md">
                <div className="flex items-center gap-3">
                  <div className="p-2.5 rounded-xl bg-slate-950 border border-slate-800 text-emerald-400">
                    <Package className="w-5 h-5" />
                  </div>
                  <div>
                    <h2 className="text-base md:text-lg font-black text-white">
                      {data.product_metadata.name}
                    </h2>
                    <div className="flex items-center gap-2 text-xs text-slate-400 mt-0.5">
                      <span className="font-medium text-slate-300">
                        {data.product_metadata.category}
                      </span>
                      <span>•</span>
                      <span>
                        {data.product_metadata.total_reviews_analyzed.toLocaleString()} reviews processed
                      </span>
                    </div>
                  </div>
                </div>

                <div className="flex items-center gap-2">
                  <span
                    className={`inline-flex items-center gap-1.5 text-xs font-semibold px-3 py-1 rounded-full border ${
                      data.product_metadata.data_source === "live_scrape"
                        ? "bg-amber-500/10 text-amber-300 border-amber-500/30"
                        : "bg-emerald-500/10 text-emerald-300 border-emerald-500/30"
                    }`}
                  >
                    <span
                      className={`w-2 h-2 rounded-full ${
                        data.product_metadata.data_source === "live_scrape"
                          ? "bg-amber-400 animate-pulse"
                          : "bg-emerald-400"
                      }`}
                    />
                    <span>
                      {data.product_metadata.data_source === "live_scrape"
                        ? "Live Scraped Data"
                        : "High-Confidence Seed Cache"}
                    </span>
                  </span>
                </div>
              </div>
            </div>

            {/* 1. Platform Head-to-Head Cards */}
            <PlatformComparisonCards comparison={data.platform_comparison} />

            {/* 2. Aspect-Based Sentiment Analysis (ABSA Radar & Bars) */}
            <AspectRadarChart aspectScores={data.aspect_scores} />

            {/* 3. AI Verdict, Pros/Cons & Temporal Drift */}
            <TemporalAndSummarySection
              aiSummary={data.ai_summary}
              temporalDrift={data.temporal_drift}
            />

            {/* 4. Top Genuine Verified Reviews */}
            <TopGenuineReviews reviews={data.top_genuine_reviews} />

            {/* 5. Interactive Sandbox & Live Single Review Inspector */}
            <LiveReviewInspector />
          </div>
        )}
      </main>

      {/* Footer */}
      <footer className="border-t border-slate-800/80 bg-slate-950 py-6 text-center text-xs text-slate-500">
        <div className="max-w-5xl mx-auto px-4 flex flex-col sm:flex-row items-center justify-between gap-3">
          <div className="flex items-center gap-2">
            <span className="font-semibold text-slate-400">ReviewLens AI</span>
            <span>—</span>
            <span>Cross-Platform E-Commerce Sentiment & Authenticity Radar</span>
          </div>
          <div>
            <span>FastAPI • Next.js App Router • Recharts • ABSA Pipeline</span>
          </div>
        </div>
      </footer>
    </div>
  );
}

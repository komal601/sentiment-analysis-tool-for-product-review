"use client";

import React, { useState, useEffect } from "react";
import { Search, Sparkles, Database, Wifi, Loader2, ArrowRight } from "lucide-react";
import { ProductSuggestion } from "@/types/analysis";
import { fetchSuggestions } from "@/lib/api";

interface SearchHeroProps {
  onSearch: (query: string, mode: "hybrid" | "offline") => void;
  isLoading: boolean;
  currentQuery: string;
}

export function SearchHero({ onSearch, isLoading, currentQuery }: SearchHeroProps) {
  const [query, setQuery] = useState(currentQuery || "realme Buds T310");
  const [mode, setMode] = useState<"hybrid" | "offline">("offline");
  const [suggestions, setSuggestions] = useState<ProductSuggestion[]>([]);
  const [isFetchingSuggestions, setIsFetchingSuggestions] = useState(false);

  useEffect(() => {
    let mounted = true;
    async function load() {
      setIsFetchingSuggestions(true);
      try {
        const data = await fetchSuggestions();
        if (mounted && data.length > 0) {
          setSuggestions(data);
        }
      } catch (err) {
        console.warn("Could not fetch suggestions dynamically, using fallback chips:", err);
      } finally {
        if (mounted) setIsFetchingSuggestions(false);
      }
    }
    load();
    return () => {
      mounted = false;
    };
  }, []);

  const fallbackChips: ProductSuggestion[] = [
    { query: "realme buds t310", name: "realme Buds T310", category: "TWS Earbuds", total_seed_reviews: 412 },
    { query: "oneplus nord buds 3 pro", name: "OnePlus Nord Buds 3 Pro", category: "TWS Earbuds", total_seed_reviews: 48 },
    { query: "sony wf-c700n", name: "Sony WF-C700N", category: "Noise Cancelling Earbuds", total_seed_reviews: 32 },
  ];

  const chips = suggestions.length > 0 ? suggestions : fallbackChips;

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (query.trim() && !isLoading) {
      onSearch(query.trim(), mode);
    }
  };

  const handleChipClick = (itemQuery: string) => {
    setQuery(itemQuery);
    onSearch(itemQuery, mode);
  };

  return (
    <div className="relative w-full max-w-5xl mx-auto pt-6 pb-4 px-4 text-center">
      {/* Decorative gradient glow */}
      <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-3/4 h-32 bg-emerald-500/10 blur-[100px] pointer-events-none rounded-full" />

      {/* Brand & Badge */}
      <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-slate-900/90 border border-slate-800 text-xs text-slate-300 mb-4 backdrop-blur shadow-inner">
        <Sparkles className="w-3.5 h-3.5 text-emerald-400" />
        <span className="font-semibold text-slate-200">Cross-Platform Authenticity Radar</span>
        <span className="text-slate-500">|</span>
        <span className="text-amber-400 font-medium">Amazon.in</span>
        <span className="text-slate-500">vs</span>
        <span className="text-cyan-400 font-medium">Flipkart</span>
      </div>

      <h1 className="text-3xl md:text-5xl font-black tracking-tight text-white mb-3">
        Uncover What Indian Buyers <span className="text-transparent bg-clip-text bg-gradient-to-r from-emerald-400 via-teal-300 to-cyan-400">Actually Think</span>
      </h1>
      <p className="text-sm md:text-base text-slate-400 max-w-2xl mx-auto mb-6">
        Aspect-based sentiment analysis with Hinglish normalization, anti-bot review trust scoring, and seller fulfillment complaint separation.
      </p>

      {/* Main Search Bar & Mode Toggle */}
      <form onSubmit={handleSubmit} className="max-w-3xl mx-auto space-y-3">
        <div className="flex flex-col sm:flex-row items-center gap-2 p-1.5 rounded-2xl bg-slate-900/80 border border-slate-800 focus-within:border-emerald-500/60 focus-within:ring-2 focus-within:ring-emerald-500/20 transition-all shadow-2xl backdrop-blur-md">
          <div className="flex items-center w-full px-3 gap-2">
            <Search className="w-5 h-5 text-slate-400 shrink-0" />
            <input
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Search product (e.g., realme Buds T310, OnePlus Nord...)"
              className="w-full bg-transparent text-slate-100 placeholder-slate-500 text-sm md:text-base focus:outline-none py-2"
              disabled={isLoading}
            />
          </div>

          <div className="flex items-center gap-2 w-full sm:w-auto justify-end px-2 sm:px-0">
            {/* Mode Selector Toggle */}
            <div className="inline-flex rounded-xl bg-slate-950 p-1 border border-slate-800/80 text-xs shrink-0">
              <button
                type="button"
                onClick={() => setMode("offline")}
                className={`flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg transition-all font-medium ${
                  mode === "offline"
                    ? "bg-emerald-500/20 text-emerald-300 border border-emerald-500/30 shadow-sm"
                    : "text-slate-400 hover:text-slate-200"
                }`}
                title="Use pre-seeded offline demo reviews with 0s latency & 100% reliability"
              >
                <Database className="w-3.5 h-3.5 text-emerald-400" />
                <span>Offline Demo</span>
              </button>
              <button
                type="button"
                onClick={() => setMode("hybrid")}
                className={`flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg transition-all font-medium ${
                  mode === "hybrid"
                    ? "bg-amber-500/20 text-amber-300 border border-amber-500/30 shadow-sm"
                    : "text-slate-400 hover:text-slate-200"
                }`}
                title="Attempts live scrape (8s timeout) with automatic fallback to seed cache"
              >
                <Wifi className="w-3.5 h-3.5 text-amber-400" />
                <span>Hybrid Live</span>
              </button>
            </div>

            {/* Submit Button */}
            <button
              type="submit"
              disabled={isLoading || !query.trim()}
              className="flex items-center justify-center gap-2 px-5 py-2.5 rounded-xl bg-gradient-to-r from-emerald-500 to-teal-500 hover:from-emerald-400 hover:to-teal-400 text-slate-950 font-bold text-sm transition-all disabled:opacity-50 disabled:cursor-not-allowed shadow-lg shadow-emerald-500/20 active:scale-95 shrink-0"
            >
              {isLoading ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  <span>Analyzing...</span>
                </>
              ) : (
                <>
                  <span>Analyze</span>
                  <ArrowRight className="w-4 h-4" />
                </>
              )}
            </button>
          </div>
        </div>
      </form>

      {/* Quick Demo Chips */}
      <div className="mt-4 flex flex-wrap items-center justify-center gap-2 text-xs">
        <span className="text-slate-500 font-medium">Quick Evaluator Demos:</span>
        {isFetchingSuggestions && (
          <span className="text-slate-500 text-[10px] animate-pulse">loading seed items...</span>
        )}
        {chips.map((item) => (
          <button
            key={item.query}
            type="button"
            onClick={() => handleChipClick(item.query)}
            disabled={isLoading}
            className={`px-3 py-1 rounded-full border transition-all text-xs flex items-center gap-1.5 ${
              query.toLowerCase() === item.query.toLowerCase()
                ? "bg-slate-800 border-emerald-500/50 text-emerald-300 font-semibold shadow-sm"
                : "bg-slate-900/60 border-slate-800 text-slate-400 hover:text-slate-200 hover:border-slate-700"
            }`}
          >
            <span>{item.name}</span>
            {item.total_seed_reviews > 0 && (
              <span className="text-[10px] px-1.5 py-0.2 bg-slate-800 text-slate-400 rounded-full font-mono">
                {item.total_seed_reviews} revs
              </span>
            )}
          </button>
        ))}
      </div>
    </div>
  );
}

"use client";

import { useState, useEffect } from "react";
import { Phone, Clock, AlertTriangle, SmilePlus } from "lucide-react";
import { apiClient } from "@/lib/api";
import type { CallStatsResponse } from "@/types/voice";

function formatDuration(seconds: number): string {
  if (seconds === 0) return "0s";
  const m = Math.floor(seconds / 60);
  const s = Math.round(seconds % 60);
  if (m === 0) return `${s}s`;
  return `${m}m ${s}s`;
}

export function CallStatsCards() {
  const [stats, setStats] = useState<CallStatsResponse | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function fetchStats() {
      try {
        const data = await apiClient<CallStatsResponse>(
          "/api/v1/voice/calls/stats"
        );
        setStats(data);
      } catch (err) {
        console.error("Failed to fetch call stats:", err);
      } finally {
        setLoading(false);
      }
    }
    fetchStats();
  }, []);

  if (loading) {
    return (
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {[1, 2, 3, 4].map((i) => (
          <div
            key={i}
            className="bg-white border border-gray-200 rounded-lg p-4 animate-pulse"
          >
            <div className="h-4 bg-gray-200 rounded w-20 mb-2" />
            <div className="h-6 bg-gray-200 rounded w-12" />
          </div>
        ))}
      </div>
    );
  }

  if (!stats) return null;

  const { positive, neutral, negative } = stats.sentiment_distribution;
  const sentimentTotal = positive + neutral + negative;
  const sentimentLabel =
    sentimentTotal === 0
      ? "--"
      : positive >= neutral && positive >= negative
        ? "Positive"
        : negative >= neutral
          ? "Negative"
          : "Neutral";

  return (
    <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
      <div className="bg-white border border-gray-200 rounded-lg p-4">
        <div className="flex items-center gap-2 mb-1">
          <Phone className="w-4 h-4 text-blue-500" />
          <p className="text-xs text-gray-500 font-medium">Total Calls</p>
        </div>
        <p className="text-2xl font-bold text-gray-900">{stats.total_calls}</p>
      </div>

      <div className="bg-white border border-gray-200 rounded-lg p-4">
        <div className="flex items-center gap-2 mb-1">
          <Clock className="w-4 h-4 text-green-500" />
          <p className="text-xs text-gray-500 font-medium">Avg Duration</p>
        </div>
        <p className="text-2xl font-bold text-gray-900">
          {formatDuration(stats.avg_duration_sec)}
        </p>
      </div>

      <div className="bg-white border border-gray-200 rounded-lg p-4">
        <div className="flex items-center gap-2 mb-1">
          <AlertTriangle className="w-4 h-4 text-amber-500" />
          <p className="text-xs text-gray-500 font-medium">Escalation Rate</p>
        </div>
        <p className="text-2xl font-bold text-gray-900">
          {((stats.escalation_rate ?? 0) * 100).toFixed(0)}%
        </p>
      </div>

      <div className="bg-white border border-gray-200 rounded-lg p-4">
        <div className="flex items-center gap-2 mb-1">
          <SmilePlus className="w-4 h-4 text-purple-500" />
          <p className="text-xs text-gray-500 font-medium">Sentiment</p>
        </div>
        <p className="text-2xl font-bold text-gray-900">{sentimentLabel}</p>
        {sentimentTotal > 0 && (
          <p className="text-xs text-gray-400 mt-0.5">
            +{positive} / ~{neutral} / -{negative}
          </p>
        )}
      </div>
    </div>
  );
}

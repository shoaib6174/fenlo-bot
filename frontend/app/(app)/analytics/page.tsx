"use client";

import { useState, useMemo, useEffect } from "react";
import { FileDown, Calendar } from "lucide-react";
import { useAuth } from "@/providers/auth";
import { useSkin } from "@/providers/skin";
import {
  useAnalyticsOverview,
  useAnalyticsVolume,
  useAnalyticsSentiment,
  useAnalyticsTopQuestions,
  useAnalyticsChannels,
  useAnalyticsLeadScores,
  useWeeklyInsight,
} from "@/hooks/useAnalytics";
import { exportApi } from "@/lib/api";
import {
  publicApi,
  type PublicAnalyticsOverview,
  type PublicVolumePoint,
  type PublicSentimentPoint,
  type PublicTopQuestion,
} from "@/lib/public-api";
import { useDashboardWebSocket } from "@/hooks/useDashboardWebSocket";
import OverviewCards from "@/components/analytics/OverviewCards";
import LiveIndicators from "@/components/analytics/LiveIndicators";
import MessageFeed from "@/components/analytics/MessageFeed";
import VolumeChart from "@/components/analytics/VolumeChart";
import SentimentChart from "@/components/analytics/SentimentChart";
import TopQuestionsTable from "@/components/analytics/TopQuestionsTable";
import ChannelBreakdown from "@/components/analytics/ChannelBreakdown";
import LeadScoreDistribution from "@/components/analytics/LeadScoreDistribution";
import AIInsightsCard from "@/components/analytics/AIInsightsCard";

type RangePreset = "7d" | "30d" | "90d";

function daysAgo(n: number): string {
  const d = new Date();
  d.setDate(d.getDate() - n);
  return d.toISOString().slice(0, 10);
}

function today(): string {
  return new Date().toISOString().slice(0, 10);
}

/** Hook that returns { data, isLoading } from public API for guest mode */
function useGuestAnalytics(preset: RangePreset) {
  const demoToken = process.env.NEXT_PUBLIC_DEMO_SHARE_TOKEN || "";
  const range = useMemo(() => {
    const days = preset === "7d" ? 7 : preset === "90d" ? 90 : 30;
    return { start_date: daysAgo(days), end_date: today() };
  }, [preset]);
  const period = preset === "7d" ? "day" : preset === "30d" ? "day" : "week";

  const [overview, setOverview] = useState<{ data: PublicAnalyticsOverview | undefined; isLoading: boolean }>({ data: undefined, isLoading: true });
  const [volume, setVolume] = useState<{ data: PublicVolumePoint[] | undefined; isLoading: boolean }>({ data: undefined, isLoading: true });
  const [sentiment, setSentiment] = useState<{ data: PublicSentimentPoint[] | undefined; isLoading: boolean }>({ data: undefined, isLoading: true });
  const [topQuestions, setTopQuestions] = useState<{ data: PublicTopQuestion[] | undefined; isLoading: boolean }>({ data: undefined, isLoading: true });

  useEffect(() => {
    if (!demoToken) return;
    setOverview((s) => ({ ...s, isLoading: true }));
    setVolume((s) => ({ ...s, isLoading: true }));
    setSentiment((s) => ({ ...s, isLoading: true }));
    setTopQuestions((s) => ({ ...s, isLoading: true }));

    publicApi.analyticsOverview(demoToken, range).then((d) => setOverview({ data: d, isLoading: false })).catch(() => setOverview({ data: undefined, isLoading: false }));
    publicApi.analyticsVolume(demoToken, { ...range, period }).then((d) => setVolume({ data: d, isLoading: false })).catch(() => setVolume({ data: undefined, isLoading: false }));
    publicApi.analyticsSentiment(demoToken, { ...range, period }).then((d) => setSentiment({ data: d, isLoading: false })).catch(() => setSentiment({ data: undefined, isLoading: false }));
    publicApi.analyticsTopQuestions(demoToken, 10).then((d) => setTopQuestions({ data: d, isLoading: false })).catch(() => setTopQuestions({ data: undefined, isLoading: false }));
  }, [demoToken, range, period]);

  return { overview, volume, sentiment, topQuestions };
}

export default function AnalyticsPage() {
  const { user, isLoading: authLoading } = useAuth();
  const { isRagchat } = useSkin();
  const [preset, setPreset] = useState<RangePreset>("30d");

  // RAGChat standalone: always show guest/demo view
  const effectiveUser = isRagchat ? null : user;
  const isGuest = isRagchat || (!authLoading && !user);

  // Authenticated hooks (only call when user is present)
  const range = useMemo(() => {
    const days = preset === "7d" ? 7 : preset === "90d" ? 90 : 30;
    return { start_date: daysAgo(days), end_date: today() };
  }, [preset]);
  const period = preset === "7d" ? "day" : preset === "30d" ? "day" : "week";

  const authOverview = useAnalyticsOverview(range, !!effectiveUser);
  const authVolume = useAnalyticsVolume({ ...range, period }, !!effectiveUser);
  const authSentiment = useAnalyticsSentiment({ ...range, period }, !!effectiveUser);
  const authTopQuestions = useAnalyticsTopQuestions(10, !!effectiveUser);
  const channels = useAnalyticsChannels(!!effectiveUser);
  const leadScores = useAnalyticsLeadScores(!!effectiveUser);
  const insights = useWeeklyInsight(undefined, !!effectiveUser);
  const { connectionState, metrics: liveMetrics, feed } = useDashboardWebSocket();

  // Guest hooks
  const guest = useGuestAnalytics(isGuest ? preset : "30d");

  // Pick data source
  const overview = effectiveUser ? authOverview : guest.overview;
  const volume = effectiveUser ? authVolume : guest.volume;
  const sentiment = effectiveUser ? authSentiment : guest.sentiment;
  const topQuestions = effectiveUser ? authTopQuestions : guest.topQuestions;

  const handleExportCSV = () => {
    if (!effectiveUser) return;
    const url = exportApi.csvUrl();
    window.open(url, "_blank");
  };

  if (authLoading) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-sky-500"></div>
      </div>
    );
  }

  return (
    <div className="container mx-auto px-6 py-8 max-w-7xl">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Analytics</h1>
          <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
            Track conversations, quality, and AI performance
          </p>
        </div>
        <div className="flex items-center gap-3">
          {/* Date range presets */}
          <div className="flex items-center gap-1 bg-gray-100 dark:bg-gray-800 rounded-lg p-1">
            <Calendar className="w-4 h-4 text-gray-400 ml-2" />
            {(["7d", "30d", "90d"] as RangePreset[]).map((p) => (
              <button
                key={p}
                onClick={() => setPreset(p)}
                className={`px-3 py-1.5 text-xs font-medium rounded-md transition ${
                  preset === p
                    ? "bg-white dark:bg-gray-700 text-gray-900 dark:text-white shadow-sm"
                    : "text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200"
                }`}
              >
                {p === "7d" ? "7 Days" : p === "30d" ? "30 Days" : "90 Days"}
              </button>
            ))}
          </div>

          {/* Export — only for authenticated users */}
          {effectiveUser && (
            <button
              onClick={handleExportCSV}
              className="inline-flex items-center gap-2 px-3 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 transition"
            >
              <FileDown className="w-4 h-4" />
              Export CSV
            </button>
          )}
        </div>
      </div>

      {/* Overview Cards */}
      <div className="mb-6">
        <OverviewCards data={overview.data} isLoading={overview.isLoading} />
      </div>

      {/* Charts Row 1: Volume + Sentiment */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
        <VolumeChart data={volume.data} isLoading={volume.isLoading} />
        <SentimentChart data={sentiment.data} isLoading={sentiment.isLoading} />
      </div>

      {/* Charts Row 2: Questions + Channels (+ Lead Scores for non-ragchat) */}
      <div className={`grid grid-cols-1 ${isRagchat ? "lg:grid-cols-2" : "lg:grid-cols-3"} gap-6 mb-6`}>
        <TopQuestionsTable
          data={topQuestions.data}
          isLoading={topQuestions.isLoading}
        />
        <ChannelBreakdown
          data={channels.data}
          isLoading={channels.isLoading}
        />
        {!isRagchat && (
          <LeadScoreDistribution
            data={leadScores.data}
            isLoading={leadScores.isLoading}
          />
        )}
      </div>

      {/* Row 3: Live Indicators + Message Feed + AI Insights — only for authenticated users */}
      {effectiveUser && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-6">
          <LiveIndicators
            metrics={liveMetrics}
            connectionState={connectionState}
          />
          <MessageFeed messages={feed} />
          <AIInsightsCard
            data={insights.data}
            isLoading={insights.isLoading}
            isError={insights.isError}
          />
        </div>
      )}
    </div>
  );
}

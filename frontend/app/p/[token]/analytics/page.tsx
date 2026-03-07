"use client";

import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import {
  MessageSquare,
  MessagesSquare,
  Clock,
  TrendingUp,
  AlertTriangle,
  HelpCircle,
} from "lucide-react";
import {
  AreaChart,
  Area,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from "recharts";
import {
  publicApi,
  type PublicAnalyticsOverview,
  type PublicVolumePoint,
  type PublicSentimentPoint,
  type PublicTopQuestion,
} from "@/lib/public-api";

function formatDate(dateStr: string) {
  const d = new Date(dateStr);
  return d.toLocaleDateString("en-US", { month: "short", day: "numeric" });
}

function StatCard({
  label,
  value,
  icon: Icon,
  color,
  bgColor,
}: {
  label: string;
  value: string;
  icon: React.ComponentType<{ className?: string }>;
  color: string;
  bgColor: string;
}) {
  return (
    <div className="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-xl p-5">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-sm text-gray-500 dark:text-gray-400 mb-1">{label}</p>
          <p className="text-2xl font-bold text-gray-900 dark:text-white">{value}</p>
        </div>
        <div className={`p-2.5 rounded-xl ${bgColor}`}>
          <Icon className={`w-5 h-5 ${color}`} />
        </div>
      </div>
    </div>
  );
}

function ChartSkeleton({ title }: { title: string }) {
  return (
    <div className="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-xl p-6">
      <div className="h-4 w-40 bg-gray-200 dark:bg-gray-700 rounded mb-4 animate-pulse" />
      <div className="h-64 bg-gray-50 dark:bg-gray-800 rounded animate-pulse" />
    </div>
  );
}

export default function PublicAnalyticsPage() {
  const { token } = useParams<{ token: string }>();
  const [overview, setOverview] = useState<PublicAnalyticsOverview | null>(null);
  const [volume, setVolume] = useState<PublicVolumePoint[] | null>(null);
  const [sentiment, setSentiment] = useState<PublicSentimentPoint[] | null>(null);
  const [topQuestions, setTopQuestions] = useState<PublicTopQuestion[] | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([
      publicApi.analyticsOverview(token),
      publicApi.analyticsVolume(token),
      publicApi.analyticsSentiment(token),
      publicApi.analyticsTopQuestions(token),
    ])
      .then(([ov, vol, sent, tq]) => {
        setOverview(ov);
        setVolume(vol);
        setSentiment(sent);
        setTopQuestions(tq);
      })
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, [token]);

  if (error) {
    return (
      <div className="flex items-center justify-center h-[50vh]">
        <div className="text-center">
          <AlertTriangle className="w-12 h-12 text-gray-300 dark:text-gray-600 mx-auto mb-4" />
          <p className="text-gray-500 dark:text-gray-400">{error}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Analytics</h1>
        <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
          Last 30 days performance metrics
        </p>
      </div>

      {/* Overview Cards */}
      {loading ? (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {[1, 2, 3, 4].map((i) => (
            <div
              key={i}
              className="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-xl p-5 animate-pulse"
            >
              <div className="flex items-center justify-between">
                <div className="space-y-2">
                  <div className="h-4 w-24 bg-gray-200 dark:bg-gray-700 rounded" />
                  <div className="h-8 w-16 bg-gray-200 dark:bg-gray-700 rounded" />
                </div>
                <div className="h-10 w-10 bg-gray-100 dark:bg-gray-800 rounded-xl" />
              </div>
            </div>
          ))}
        </div>
      ) : overview ? (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <StatCard
            label="Conversations"
            value={overview.total_conversations.toLocaleString()}
            icon={MessageSquare}
            color="text-blue-600 dark:text-blue-400"
            bgColor="bg-blue-50 dark:bg-blue-900/30"
          />
          <StatCard
            label="Messages"
            value={overview.total_messages.toLocaleString()}
            icon={MessagesSquare}
            color="text-indigo-600 dark:text-indigo-400"
            bgColor="bg-indigo-50 dark:bg-indigo-900/30"
          />
          <StatCard
            label="Avg Response"
            value={
              overview.avg_response_time_ms < 1000
                ? `${Math.round(overview.avg_response_time_ms)}ms`
                : `${(overview.avg_response_time_ms / 1000).toFixed(1)}s`
            }
            icon={Clock}
            color="text-amber-600 dark:text-amber-400"
            bgColor="bg-amber-50 dark:bg-amber-900/30"
          />
          <StatCard
            label="Quality Score"
            value={`${Math.round(overview.avg_quality_score * 100)}%`}
            icon={TrendingUp}
            color="text-green-600 dark:text-green-400"
            bgColor="bg-green-50 dark:bg-green-900/30"
          />
        </div>
      ) : null}

      {/* Charts Row */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Volume Chart */}
        {loading ? (
          <ChartSkeleton title="Volume" />
        ) : volume && volume.length > 0 ? (
          <div className="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-xl p-6">
            <h3 className="text-sm font-semibold text-gray-900 dark:text-white mb-4">
              Message Volume
            </h3>
            <ResponsiveContainer width="100%" height={280}>
              <AreaChart data={volume.map((d) => ({ ...d, label: formatDate(d.date) }))}>
                <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                <XAxis dataKey="label" tick={{ fontSize: 12 }} />
                <YAxis tick={{ fontSize: 12 }} />
                <Tooltip />
                <Legend />
                <Area
                  type="monotone"
                  dataKey="message_count"
                  name="Messages"
                  stroke="#0ea5e9"
                  fill="#e0f2fe"
                  strokeWidth={2}
                />
                <Area
                  type="monotone"
                  dataKey="conversation_count"
                  name="Conversations"
                  stroke="#6366f1"
                  fill="#eef2ff"
                  strokeWidth={2}
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        ) : (
          <div className="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-xl p-6">
            <h3 className="text-sm font-semibold text-gray-900 dark:text-white mb-4">
              Message Volume
            </h3>
            <div className="h-64 flex items-center justify-center text-gray-400 text-sm">
              No volume data yet
            </div>
          </div>
        )}

        {/* Sentiment Chart */}
        {loading ? (
          <ChartSkeleton title="Sentiment" />
        ) : sentiment && sentiment.length > 0 ? (
          <div className="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-xl p-6">
            <h3 className="text-sm font-semibold text-gray-900 dark:text-white mb-4">
              Sentiment Trend
            </h3>
            <ResponsiveContainer width="100%" height={280}>
              <BarChart data={sentiment.map((d) => ({ ...d, label: formatDate(d.date) }))}>
                <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                <XAxis dataKey="label" tick={{ fontSize: 12 }} />
                <YAxis tick={{ fontSize: 12 }} />
                <Tooltip />
                <Legend />
                <Bar dataKey="positive" name="Positive" fill="#22c55e" stackId="s" />
                <Bar dataKey="neutral" name="Neutral" fill="#94a3b8" stackId="s" />
                <Bar dataKey="negative" name="Negative" fill="#ef4444" stackId="s" />
              </BarChart>
            </ResponsiveContainer>
          </div>
        ) : (
          <div className="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-xl p-6">
            <h3 className="text-sm font-semibold text-gray-900 dark:text-white mb-4">
              Sentiment Trend
            </h3>
            <div className="h-64 flex items-center justify-center text-gray-400 text-sm">
              No sentiment data yet
            </div>
          </div>
        )}
      </div>

      {/* Sentiment Summary + Top Questions */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Sentiment Donut Summary */}
        {overview && (
          <div className="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-xl p-6">
            <h3 className="text-sm font-semibold text-gray-900 dark:text-white mb-4">
              Overall Sentiment
            </h3>
            <div className="flex items-center justify-around py-4">
              {[
                {
                  label: "Positive",
                  value: overview.sentiment_distribution.positive,
                  color: "text-green-600 dark:text-green-400",
                  bg: "bg-green-100 dark:bg-green-900/30",
                },
                {
                  label: "Neutral",
                  value: overview.sentiment_distribution.neutral,
                  color: "text-gray-600 dark:text-gray-400",
                  bg: "bg-gray-100 dark:bg-gray-800",
                },
                {
                  label: "Negative",
                  value: overview.sentiment_distribution.negative,
                  color: "text-red-600 dark:text-red-400",
                  bg: "bg-red-100 dark:bg-red-900/30",
                },
              ].map((item) => (
                <div key={item.label} className="text-center">
                  <div
                    className={`w-16 h-16 rounded-full ${item.bg} flex items-center justify-center mx-auto mb-2`}
                  >
                    <span className={`text-lg font-bold ${item.color}`}>
                      {item.value}
                    </span>
                  </div>
                  <p className="text-xs text-gray-500 dark:text-gray-400">
                    {item.label}
                  </p>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Top Questions */}
        {loading ? (
          <ChartSkeleton title="Top Questions" />
        ) : topQuestions && topQuestions.length > 0 ? (
          <div className="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-xl p-6">
            <div className="flex items-center gap-2 mb-4">
              <HelpCircle className="w-4 h-4 text-gray-400" />
              <h3 className="text-sm font-semibold text-gray-900 dark:text-white">
                Top Questions
              </h3>
            </div>
            <div className="space-y-3">
              {topQuestions.map((q, i) => {
                const maxCount = Math.max(...topQuestions.map((tq) => tq.count));
                return (
                  <div key={i}>
                    <div className="flex items-center justify-between mb-1">
                      <p className="text-sm text-gray-700 dark:text-gray-300 truncate pr-4 max-w-[85%]">
                        {q.question}
                      </p>
                      <span className="text-xs font-medium text-gray-500 dark:text-gray-400 shrink-0">
                        {q.count}x
                      </span>
                    </div>
                    <div className="w-full bg-gray-100 dark:bg-gray-800 rounded-full h-1.5">
                      <div
                        className="bg-sky-500 rounded-full h-1.5 transition-all"
                        style={{ width: `${(q.count / maxCount) * 100}%` }}
                      />
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        ) : (
          <div className="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-xl p-6">
            <div className="flex items-center gap-2 mb-4">
              <HelpCircle className="w-4 h-4 text-gray-400" />
              <h3 className="text-sm font-semibold text-gray-900 dark:text-white">
                Top Questions
              </h3>
            </div>
            <div className="h-40 flex items-center justify-center text-gray-400 text-sm">
              No questions recorded yet
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

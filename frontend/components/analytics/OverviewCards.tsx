"use client";

import { MessageSquare, MessagesSquare, Clock, TrendingUp } from "lucide-react";
import type { AnalyticsOverview } from "@/lib/api";

interface Props {
  data: AnalyticsOverview | undefined;
  isLoading: boolean;
}

const cards = [
  {
    key: "total_conversations" as const,
    label: "Conversations",
    icon: MessageSquare,
    color: "text-blue-600",
    bgColor: "bg-blue-50",
    format: (v: number) => v.toLocaleString(),
  },
  {
    key: "total_messages" as const,
    label: "Messages",
    icon: MessagesSquare,
    color: "text-indigo-600",
    bgColor: "bg-indigo-50",
    format: (v: number) => v.toLocaleString(),
  },
  {
    key: "avg_response_time_ms" as const,
    label: "Avg Response",
    icon: Clock,
    color: "text-amber-600",
    bgColor: "bg-amber-50",
    format: (v: number) => (v < 1000 ? `${Math.round(v)}ms` : `${(v / 1000).toFixed(1)}s`),
  },
  {
    key: "avg_quality_score" as const,
    label: "Quality Score",
    icon: TrendingUp,
    color: "text-green-600",
    bgColor: "bg-green-50",
    format: (v: number) => `${Math.round(v * 100)}%`,
  },
];

function SkeletonCard() {
  return (
    <div className="bg-white border border-gray-200 rounded-lg p-5 animate-pulse">
      <div className="flex items-center justify-between">
        <div className="space-y-2">
          <div className="h-4 w-24 bg-gray-200 rounded" />
          <div className="h-8 w-16 bg-gray-200 rounded" />
        </div>
        <div className="h-10 w-10 bg-gray-100 rounded-lg" />
      </div>
    </div>
  );
}

export default function OverviewCards({ data, isLoading }: Props) {
  if (isLoading) {
    return (
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {cards.map((c) => (
          <SkeletonCard key={c.key} />
        ))}
      </div>
    );
  }

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
      {cards.map((c) => {
        const Icon = c.icon;
        const value = data?.[c.key] ?? 0;
        return (
          <div
            key={c.key}
            className="bg-white border border-gray-200 rounded-lg p-5"
          >
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-600 mb-1">{c.label}</p>
                <p className="text-2xl font-bold text-gray-900">
                  {c.format(value)}
                </p>
              </div>
              <div className={`p-2.5 rounded-lg ${c.bgColor}`}>
                <Icon className={`w-5 h-5 ${c.color}`} />
              </div>
            </div>
          </div>
        );
      })}
    </div>
  );
}

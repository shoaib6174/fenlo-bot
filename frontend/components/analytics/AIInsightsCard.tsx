"use client";

import { Sparkles, AlertCircle } from "lucide-react";
import type { WeeklyInsightData } from "@/lib/api";

interface Props {
  data: WeeklyInsightData | undefined;
  isLoading: boolean;
  isError: boolean;
}

export default function AIInsightsCard({ data, isLoading, isError }: Props) {
  if (isLoading) {
    return (
      <div className="bg-white border border-gray-200 rounded-lg p-6">
        <div className="h-4 w-40 bg-gray-200 rounded mb-4 animate-pulse" />
        <div className="space-y-2">
          <div className="h-3 w-full bg-gray-100 rounded animate-pulse" />
          <div className="h-3 w-3/4 bg-gray-100 rounded animate-pulse" />
          <div className="h-3 w-5/6 bg-gray-100 rounded animate-pulse" />
        </div>
      </div>
    );
  }

  if (isError || !data) {
    return (
      <div className="bg-white border border-gray-200 rounded-lg p-6">
        <div className="flex items-center gap-2 mb-3">
          <Sparkles className="w-4 h-4 text-amber-500" />
          <h3 className="text-sm font-semibold text-gray-900">AI Insights</h3>
        </div>
        <div className="flex items-start gap-2 text-sm text-gray-500">
          <AlertCircle className="w-4 h-4 shrink-0 mt-0.5" />
          <p>No insights generated yet. Insights are auto-generated weekly or can be triggered by an admin.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-gradient-to-br from-indigo-50 to-white border border-indigo-100 rounded-lg p-6">
      <div className="flex items-center gap-2 mb-3">
        <Sparkles className="w-4 h-4 text-indigo-600" />
        <h3 className="text-sm font-semibold text-gray-900">AI Weekly Insights</h3>
        <span className="text-xs text-gray-400 ml-auto">{data.period}</span>
      </div>

      <p className="text-sm text-gray-700 mb-4 leading-relaxed">{data.summary}</p>

      {data.recommendations && data.recommendations.length > 0 && (
        <div>
          <p className="text-xs font-medium text-gray-500 uppercase mb-2">
            Recommendations
          </p>
          <ul className="space-y-1.5">
            {data.recommendations.map((rec, i) => (
              <li
                key={i}
                className="text-sm text-gray-600 flex items-start gap-2"
              >
                <span className="text-indigo-400 mt-0.5 shrink-0">&#8226;</span>
                {rec}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}

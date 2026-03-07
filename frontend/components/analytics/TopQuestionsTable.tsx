"use client";

import { HelpCircle } from "lucide-react";
import type { TopQuestion } from "@/lib/api";

interface Props {
  data: TopQuestion[] | undefined;
  isLoading: boolean;
}

export default function TopQuestionsTable({ data, isLoading }: Props) {
  if (isLoading) {
    return (
      <div className="bg-white border border-gray-200 rounded-lg p-6">
        <div className="h-4 w-40 bg-gray-200 rounded mb-4 animate-pulse" />
        {[1, 2, 3, 4, 5].map((i) => (
          <div key={i} className="flex items-center gap-3 py-3">
            <div className="h-4 w-8 bg-gray-200 rounded animate-pulse" />
            <div className="h-4 flex-1 bg-gray-100 rounded animate-pulse" />
          </div>
        ))}
      </div>
    );
  }

  if (!data || data.length === 0) {
    return (
      <div className="bg-white border border-gray-200 rounded-lg p-6">
        <h3 className="text-sm font-semibold text-gray-900 mb-4">Top Questions</h3>
        <div className="h-40 flex items-center justify-center text-gray-400 text-sm">
          No questions recorded yet
        </div>
      </div>
    );
  }

  const maxCount = Math.max(...data.map((d) => d.count));

  return (
    <div className="bg-white border border-gray-200 rounded-lg p-6">
      <div className="flex items-center gap-2 mb-4">
        <HelpCircle className="w-4 h-4 text-gray-400" />
        <h3 className="text-sm font-semibold text-gray-900">Top Questions</h3>
      </div>
      <div className="space-y-3">
        {data.map((q, i) => (
          <div key={i} className="relative">
            <div className="flex items-center justify-between mb-1">
              <p className="text-sm text-gray-700 truncate pr-4 max-w-[85%]">
                {q.question}
              </p>
              <span className="text-xs font-medium text-gray-500 shrink-0">
                {q.count}x
              </span>
            </div>
            <div className="w-full bg-gray-100 rounded-full h-1.5">
              <div
                className="bg-blue-500 rounded-full h-1.5 transition-all"
                style={{ width: `${(q.count / maxCount) * 100}%` }}
              />
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

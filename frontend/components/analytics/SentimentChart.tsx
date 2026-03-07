"use client";

import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from "recharts";
import type { SentimentDataPoint } from "@/lib/api";

interface Props {
  data: SentimentDataPoint[] | undefined;
  isLoading: boolean;
}

function formatDate(dateStr: string) {
  const d = new Date(dateStr);
  return d.toLocaleDateString("en-US", { month: "short", day: "numeric" });
}

export default function SentimentChart({ data, isLoading }: Props) {
  if (isLoading) {
    return (
      <div className="bg-white border border-gray-200 rounded-lg p-6">
        <div className="h-4 w-40 bg-gray-200 rounded mb-4 animate-pulse" />
        <div className="h-64 bg-gray-50 rounded animate-pulse" />
      </div>
    );
  }

  if (!data || data.length === 0) {
    return (
      <div className="bg-white border border-gray-200 rounded-lg p-6">
        <h3 className="text-sm font-semibold text-gray-900 mb-4">Sentiment Trend</h3>
        <div className="h-64 flex items-center justify-center text-gray-400 text-sm">
          No sentiment data for this period
        </div>
      </div>
    );
  }

  const chartData = data.map((d) => ({
    ...d,
    label: formatDate(d.date),
  }));

  return (
    <div className="bg-white border border-gray-200 rounded-lg p-6">
      <h3 className="text-sm font-semibold text-gray-900 mb-4">Sentiment Trend</h3>
      <ResponsiveContainer width="100%" height={280}>
        <BarChart data={chartData}>
          <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
          <XAxis dataKey="label" tick={{ fontSize: 12 }} />
          <YAxis tick={{ fontSize: 12 }} />
          <Tooltip />
          <Legend />
          <Bar dataKey="positive" name="Positive" fill="#22c55e" stackId="sentiment" />
          <Bar dataKey="neutral" name="Neutral" fill="#94a3b8" stackId="sentiment" />
          <Bar dataKey="negative" name="Negative" fill="#ef4444" stackId="sentiment" />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

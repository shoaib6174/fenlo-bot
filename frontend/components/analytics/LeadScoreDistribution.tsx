"use client";

import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Cell,
} from "recharts";
import type { LeadScoreData } from "@/lib/api";

interface Props {
  data: LeadScoreData | undefined;
  isLoading: boolean;
}

const COLORS = ["#94a3b8", "#f59e0b", "#22c55e"];
const LABELS = [
  { key: "0-3", label: "Low (0-3)" },
  { key: "4-6", label: "Medium (4-6)" },
  { key: "7-10", label: "High (7-10)" },
];

export default function LeadScoreDistribution({ data, isLoading }: Props) {
  if (isLoading) {
    return (
      <div className="bg-white border border-gray-200 rounded-lg p-6">
        <div className="h-4 w-48 bg-gray-200 rounded mb-4 animate-pulse" />
        <div className="h-48 bg-gray-50 rounded animate-pulse" />
      </div>
    );
  }

  if (!data) {
    return (
      <div className="bg-white border border-gray-200 rounded-lg p-6">
        <h3 className="text-sm font-semibold text-gray-900 mb-4">Lead Scores</h3>
        <div className="h-48 flex items-center justify-center text-gray-400 text-sm">
          No lead score data yet
        </div>
      </div>
    );
  }

  const chartData = LABELS.map((l) => ({
    name: l.label,
    count: data.buckets[l.key as keyof typeof data.buckets] || 0,
  }));

  return (
    <div className="bg-white border border-gray-200 rounded-lg p-6">
      <h3 className="text-sm font-semibold text-gray-900 mb-4">Lead Score Distribution</h3>
      <ResponsiveContainer width="100%" height={200}>
        <BarChart data={chartData}>
          <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
          <XAxis dataKey="name" tick={{ fontSize: 12 }} />
          <YAxis tick={{ fontSize: 12 }} />
          <Tooltip />
          <Bar dataKey="count" name="Conversations" radius={[4, 4, 0, 0]}>
            {chartData.map((_entry, index) => (
              <Cell key={index} fill={COLORS[index]} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

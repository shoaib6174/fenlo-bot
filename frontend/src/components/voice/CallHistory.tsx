"use client";

import { useState, useEffect, useCallback } from "react";
import {
  PhoneIncoming,
  PhoneOutgoing,
  Globe,
  Clock,
  ChevronLeft,
  ChevronRight,
  AlertTriangle,
} from "lucide-react";
import { apiClient } from "@/lib/api";
import type { CallListResponse, CallLogResponse } from "@/types/voice";

interface CallHistoryProps {
  onSelectCall: (call: CallLogResponse) => void;
}

function formatDuration(seconds: number | null): string {
  if (seconds === null || seconds === 0) return "--";
  const m = Math.floor(seconds / 60);
  const s = seconds % 60;
  return `${m}:${s.toString().padStart(2, "0")}`;
}

function formatDate(dateStr: string): string {
  return new Date(dateStr).toLocaleString(undefined, {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function DirectionIcon({ direction }: { direction: string }) {
  switch (direction) {
    case "inbound":
      return <PhoneIncoming className="w-4 h-4 text-blue-500" />;
    case "outbound":
      return <PhoneOutgoing className="w-4 h-4 text-green-500" />;
    case "web":
      return <Globe className="w-4 h-4 text-purple-500" />;
    default:
      return <Clock className="w-4 h-4 text-gray-400" />;
  }
}

function SentimentBadge({ sentiment }: { sentiment: string | null }) {
  if (!sentiment) return null;
  const colors: Record<string, string> = {
    positive: "bg-green-100 text-green-700",
    neutral: "bg-gray-100 text-gray-600",
    negative: "bg-red-100 text-red-700",
  };
  return (
    <span
      className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${
        colors[sentiment] || colors.neutral
      }`}
    >
      {sentiment}
    </span>
  );
}

function EscalationBadge({
  actions,
}: {
  actions: Record<string, unknown>[] | null;
}) {
  if (!actions || actions.length === 0) return null;
  const hasEscalation = actions.some((a) => a.action === "escalate");
  if (!hasEscalation) return null;
  return (
    <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-amber-100 text-amber-700">
      <AlertTriangle className="w-3 h-3" />
      Escalated
    </span>
  );
}

export function CallHistory({ onSelectCall }: CallHistoryProps) {
  const [calls, setCalls] = useState<CallLogResponse[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const pageSize = 20;

  const fetchCalls = useCallback(async () => {
    setLoading(true);
    try {
      const data = await apiClient<CallListResponse>(
        `/api/v1/voice/calls?page=${page}&page_size=${pageSize}`
      );
      setCalls(data.calls);
      setTotal(data.total);
    } catch (err) {
      console.error("Failed to fetch calls:", err);
    } finally {
      setLoading(false);
    }
  }, [page]);

  useEffect(() => {
    fetchCalls();
  }, [fetchCalls]);

  const totalPages = Math.ceil(total / pageSize);

  if (loading && calls.length === 0) {
    return (
      <div className="py-8 text-center text-sm text-gray-500">
        Loading calls...
      </div>
    );
  }

  if (calls.length === 0) {
    return (
      <div className="py-12 text-center">
        <Clock className="w-12 h-12 text-gray-300 mx-auto mb-3" />
        <p className="text-sm text-gray-500">No calls yet</p>
        <p className="text-xs text-gray-400 mt-1">
          Make a test call or receive inbound calls to see history here
        </p>
      </div>
    );
  }

  return (
    <div>
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-gray-200">
              <th className="text-left py-3 px-3 text-xs font-medium text-gray-500 uppercase tracking-wider">
                Direction
              </th>
              <th className="text-left py-3 px-3 text-xs font-medium text-gray-500 uppercase tracking-wider">
                Date
              </th>
              <th className="text-left py-3 px-3 text-xs font-medium text-gray-500 uppercase tracking-wider">
                Duration
              </th>
              <th className="text-left py-3 px-3 text-xs font-medium text-gray-500 uppercase tracking-wider">
                Sentiment
              </th>
              <th className="text-left py-3 px-3 text-xs font-medium text-gray-500 uppercase tracking-wider">
                Status
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {calls.map((call) => (
              <tr
                key={call.id}
                onClick={() => onSelectCall(call)}
                className="hover:bg-gray-50 cursor-pointer transition-colors"
              >
                <td className="py-3 px-3">
                  <div className="flex items-center gap-2">
                    <DirectionIcon direction={call.direction} />
                    <span className="capitalize text-gray-700">
                      {call.direction}
                    </span>
                  </div>
                </td>
                <td className="py-3 px-3 text-gray-600">
                  {formatDate(call.created_at)}
                </td>
                <td className="py-3 px-3 text-gray-600">
                  {formatDuration(call.duration_sec)}
                </td>
                <td className="py-3 px-3">
                  <SentimentBadge sentiment={call.sentiment} />
                </td>
                <td className="py-3 px-3">
                  <EscalationBadge actions={call.actions_taken} />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex items-center justify-between px-3 py-3 border-t border-gray-200">
          <p className="text-xs text-gray-500">
            {total} call{total !== 1 ? "s" : ""}
          </p>
          <div className="flex items-center gap-2">
            <button
              onClick={() => setPage((p) => Math.max(1, p - 1))}
              disabled={page === 1}
              className="p-1 rounded hover:bg-gray-100 disabled:opacity-30 disabled:cursor-not-allowed"
            >
              <ChevronLeft className="w-4 h-4" />
            </button>
            <span className="text-xs text-gray-600">
              {page} / {totalPages}
            </span>
            <button
              onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
              disabled={page === totalPages}
              className="p-1 rounded hover:bg-gray-100 disabled:opacity-30 disabled:cursor-not-allowed"
            >
              <ChevronRight className="w-4 h-4" />
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

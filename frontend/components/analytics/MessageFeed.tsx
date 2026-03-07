"use client";

import { MessageCircle } from "lucide-react";
import type { FeedMessage } from "@/hooks/useDashboardWebSocket";

interface Props {
  messages: FeedMessage[];
}

const sentimentDot: Record<string, string> = {
  positive: "bg-green-400",
  neutral: "bg-gray-400",
  negative: "bg-red-400",
};

function timeAgo(date: Date): string {
  const seconds = Math.floor((Date.now() - date.getTime()) / 1000);
  if (seconds < 10) return "just now";
  if (seconds < 60) return `${seconds}s ago`;
  const minutes = Math.floor(seconds / 60);
  return `${minutes}m ago`;
}

export default function MessageFeed({ messages }: Props) {
  if (messages.length === 0) {
    return (
      <div className="bg-white border border-gray-200 rounded-lg p-6">
        <div className="flex items-center gap-2 mb-3">
          <MessageCircle className="w-4 h-4 text-gray-400" />
          <h3 className="text-sm font-semibold text-gray-900">Live Feed</h3>
        </div>
        <div className="h-48 flex items-center justify-center text-gray-400 text-sm">
          Waiting for messages...
        </div>
      </div>
    );
  }

  return (
    <div className="bg-white border border-gray-200 rounded-lg p-6">
      <div className="flex items-center gap-2 mb-3">
        <MessageCircle className="w-4 h-4 text-blue-600" />
        <h3 className="text-sm font-semibold text-gray-900">Live Feed</h3>
        <span className="text-xs text-gray-400 ml-auto">
          {messages.length} recent
        </span>
      </div>
      <div className="space-y-2 max-h-80 overflow-y-auto">
        {messages.map((msg) => (
          <div
            key={msg.id}
            className="flex items-start gap-2 p-2 rounded-lg hover:bg-gray-50 transition"
          >
            {/* Sentiment dot */}
            <span
              className={`w-2 h-2 rounded-full mt-1.5 shrink-0 ${
                msg.sentiment ? sentimentDot[msg.sentiment] || "bg-gray-300" : "bg-gray-300"
              }`}
            />
            <div className="flex-1 min-w-0">
              <p className="text-sm text-gray-700 truncate">{msg.preview}</p>
              <p className="text-[11px] text-gray-400">{timeAgo(msg.timestamp)}</p>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

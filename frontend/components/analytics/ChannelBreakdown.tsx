"use client";

import { MessageSquare, Phone, Globe, Share2 } from "lucide-react";
import type { ChannelBreakdownData } from "@/lib/api";

interface Props {
  data: ChannelBreakdownData | undefined;
  isLoading: boolean;
}

const channelMeta: Record<string, { label: string; icon: typeof MessageSquare; color: string }> = {
  web: { label: "Web Chat", icon: Globe, color: "text-blue-600" },
  whatsapp: { label: "WhatsApp", icon: MessageSquare, color: "text-green-600" },
  voice: { label: "Voice", icon: Phone, color: "text-purple-600" },
  widget: { label: "Widget", icon: Globe, color: "text-indigo-600" },
  unknown: { label: "Unknown", icon: Share2, color: "text-gray-600" },
};

export default function ChannelBreakdown({ data, isLoading }: Props) {
  if (isLoading) {
    return (
      <div className="bg-white border border-gray-200 rounded-lg p-6">
        <div className="h-4 w-40 bg-gray-200 rounded mb-4 animate-pulse" />
        <div className="grid grid-cols-2 gap-3">
          {[1, 2, 3, 4].map((i) => (
            <div key={i} className="h-20 bg-gray-50 rounded animate-pulse" />
          ))}
        </div>
      </div>
    );
  }

  const entries = data ? Object.entries(data) : [];

  if (entries.length === 0) {
    return (
      <div className="bg-white border border-gray-200 rounded-lg p-6">
        <h3 className="text-sm font-semibold text-gray-900 mb-4">Channels</h3>
        <div className="h-40 flex items-center justify-center text-gray-400 text-sm">
          No channel data yet
        </div>
      </div>
    );
  }

  return (
    <div className="bg-white border border-gray-200 rounded-lg p-6">
      <h3 className="text-sm font-semibold text-gray-900 mb-4">Channels</h3>
      <div className="grid grid-cols-2 gap-3">
        {entries.map(([channel, info]) => {
          const meta = channelMeta[channel] || channelMeta.unknown;
          const Icon = meta.icon;
          return (
            <div
              key={channel}
              className="border border-gray-100 rounded-lg p-3"
            >
              <div className="flex items-center gap-2 mb-2">
                <Icon className={`w-4 h-4 ${meta.color}`} />
                <span className="text-sm font-medium text-gray-700">
                  {meta.label}
                </span>
              </div>
              <p className="text-lg font-bold text-gray-900">{info.count}</p>
              <p className="text-xs text-gray-500">
                Quality: {Math.round(info.avg_quality * 100)}%
              </p>
            </div>
          );
        })}
      </div>
    </div>
  );
}

"use client";

import { MessageSquare, AlertTriangle, Zap, Wifi, WifiOff } from "lucide-react";
import type { ConnectionState, LiveMetrics } from "@/hooks/useDashboardWebSocket";

interface Props {
  metrics: LiveMetrics;
  connectionState: ConnectionState;
}

const statusConfig: Record<ConnectionState, { label: string; color: string; dot: string }> = {
  connected: { label: "Live", color: "text-green-600", dot: "bg-green-500" },
  connecting: { label: "Connecting", color: "text-amber-600", dot: "bg-amber-400" },
  reconnecting: { label: "Reconnecting", color: "text-amber-600", dot: "bg-amber-400" },
  disconnected: { label: "Offline", color: "text-red-500", dot: "bg-red-400" },
};

export default function LiveIndicators({ metrics, connectionState }: Props) {
  const status = statusConfig[connectionState];
  const isConnected = connectionState === "connected";

  return (
    <div className="bg-white border border-gray-200 rounded-lg p-4">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          {isConnected ? (
            <Wifi className="w-4 h-4 text-green-600" />
          ) : (
            <WifiOff className="w-4 h-4 text-gray-400" />
          )}
          <h3 className="text-sm font-semibold text-gray-900">Real-Time</h3>
        </div>
        <div className="flex items-center gap-1.5">
          <span
            className={`w-2 h-2 rounded-full ${status.dot} ${
              isConnected ? "animate-pulse" : ""
            }`}
          />
          <span className={`text-xs font-medium ${status.color}`}>
            {status.label}
          </span>
        </div>
      </div>

      <div className="grid grid-cols-3 gap-3">
        {/* Active Conversations */}
        <div className="text-center p-2 rounded-lg bg-blue-50">
          <MessageSquare className="w-4 h-4 text-blue-600 mx-auto mb-1" />
          <p className="text-xl font-bold text-gray-900">
            {metrics.activeConversations}
          </p>
          <p className="text-[11px] text-gray-500">Active Chats</p>
        </div>

        {/* Messages/min */}
        <div className="text-center p-2 rounded-lg bg-indigo-50">
          <Zap className="w-4 h-4 text-indigo-600 mx-auto mb-1" />
          <p className="text-xl font-bold text-gray-900">
            {metrics.messagesPerMinute}
          </p>
          <p className="text-[11px] text-gray-500">Msgs/min</p>
        </div>

        {/* Pending Escalations */}
        <div
          className={`text-center p-2 rounded-lg ${
            metrics.pendingEscalations > 0 ? "bg-red-50" : "bg-gray-50"
          }`}
        >
          <AlertTriangle
            className={`w-4 h-4 mx-auto mb-1 ${
              metrics.pendingEscalations > 0 ? "text-red-600" : "text-gray-400"
            }`}
          />
          <p
            className={`text-xl font-bold ${
              metrics.pendingEscalations > 0 ? "text-red-600" : "text-gray-900"
            }`}
          >
            {metrics.pendingEscalations}
          </p>
          <p className="text-[11px] text-gray-500">Escalations</p>
        </div>
      </div>
    </div>
  );
}

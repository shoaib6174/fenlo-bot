/**
 * ConversationList Component
 *
 * Displays list of conversations with channel badges, lead scores, and status
 */

"use client";

import { Phone, PhoneIncoming, PhoneOutgoing } from "lucide-react";
import { ChannelBadge } from "./ChannelBadge";
import type { InboxConversation } from "@/lib/api";

interface ConversationListProps {
  conversations: InboxConversation[];
  selectedId: string | null;
  onSelect: (id: string) => void;
}

function getVoiceDisplayName(conversation: InboxConversation): string {
  const cl = conversation.call_log;
  if (!cl) return "Voice Call";

  // Use phone number if available
  if (cl.phone_from && cl.phone_from !== "") {
    return cl.phone_from;
  }

  // Build a friendly name from direction + duration
  const dir = cl.direction === "inbound" ? "Inbound" : cl.direction === "outbound" ? "Outbound" : "Web";
  const dur = cl.duration_sec !== null ? ` - ${formatDuration(cl.duration_sec)}` : "";
  return `${dir} Call${dur}`;
}

function getVoicePreview(conversation: InboxConversation): string | null {
  const cl = conversation.call_log;
  if (!cl) return null;
  return cl.summary || (cl.status === "connected" ? "Call in progress..." : null);
}

function formatDuration(seconds: number): string {
  if (seconds === 0) return "0s";
  const m = Math.floor(seconds / 60);
  const s = seconds % 60;
  if (m === 0) return `${s}s`;
  return `${m}m ${s}s`;
}

export function ConversationList({
  conversations,
  selectedId,
  onSelect,
}: ConversationListProps) {
  if (conversations.length === 0) {
    return (
      <div className="flex items-center justify-center h-full text-gray-500 p-6">
        <p>No conversations found</p>
      </div>
    );
  }

  return (
    <div className="divide-y divide-gray-200 overflow-y-auto">
      {conversations.map((conversation) => {
        const isVoice = conversation.channel === "voice";
        const displayName = isVoice
          ? getVoiceDisplayName(conversation)
          : conversation.contact_name || conversation.contact_identifier;
        const preview = isVoice
          ? getVoicePreview(conversation)
          : conversation.last_message_preview;

        return (
          <button
            key={conversation.id}
            onClick={() => onSelect(conversation.id)}
            className={`w-full text-left px-4 py-4 hover:bg-gray-50 transition-colors ${
              selectedId === conversation.id ? "bg-blue-50 border-l-4 border-blue-600" : ""
            }`}
          >
            <div className="flex items-start gap-3">
              {/* Channel Badge */}
              <ChannelBadge channel={conversation.channel} size="sm" />

              {/* Content */}
              <div className="flex-1 min-w-0">
                {/* Contact Name & Lead Score */}
                <div className="flex items-center justify-between gap-2 mb-1">
                  <h3 className="font-medium text-gray-900 truncate">
                    {displayName}
                  </h3>
                  <LeadScoreBadge score={conversation.lead_score} />
                </div>

                {/* Voice call metadata line */}
                {isVoice && conversation.call_log && (
                  <div className="flex items-center gap-2 mb-1">
                    <VoiceCallBadge
                      direction={conversation.call_log.direction}
                      status={conversation.call_log.status}
                      durationSec={conversation.call_log.duration_sec}
                    />
                  </div>
                )}

                {/* Last Message Preview / Call Summary */}
                {preview && (
                  <p className="text-sm text-gray-600 truncate mb-1">
                    {preview}
                  </p>
                )}

                {/* Status & Timestamp */}
                <div className="flex items-center justify-between gap-2 text-xs">
                  <StatusBadge status={conversation.status} />
                  <span className="text-gray-500">
                    {formatTimestamp(conversation.last_message_at)}
                  </span>
                </div>
              </div>
            </div>
          </button>
        );
      })}
    </div>
  );
}

function VoiceCallBadge({
  direction,
  status,
  durationSec,
}: {
  direction: string;
  status: string;
  durationSec: number | null;
}) {
  const Icon = direction === "inbound" ? PhoneIncoming : direction === "outbound" ? PhoneOutgoing : Phone;
  const statusLabel = status === "ended" ? "Ended" : status === "connected" ? "Live" : status;
  const statusColor = status === "connected" ? "text-green-600" : "text-gray-500";

  return (
    <span className="inline-flex items-center gap-1.5 text-xs text-gray-500">
      <Icon className="w-3 h-3" />
      <span className={statusColor}>{statusLabel}</span>
      {durationSec !== null && durationSec > 0 && (
        <span>- {formatDuration(durationSec)}</span>
      )}
    </span>
  );
}

function LeadScoreBadge({ score }: { score: number | null }) {
  const s = score ?? 0;
  const getColor = (score: number) => {
    if (score >= 7) return "bg-green-100 text-green-800";
    if (score >= 4) return "bg-yellow-100 text-yellow-800";
    return "bg-gray-100 text-gray-600";
  };

  return (
    <span
      className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${getColor(
        s
      )}`}
    >
      {s.toFixed(1)}
    </span>
  );
}

function StatusBadge({ status }: { status: string }) {
  const statusConfig: Record<string, { label: string; color: string; dot: string }> = {
    active: {
      label: "Active",
      color: "bg-green-100 text-green-800",
      dot: "bg-green-500",
    },
    escalated: {
      label: "Escalated",
      color: "bg-orange-100 text-orange-800",
      dot: "bg-orange-500",
    },
    closed: {
      label: "Closed",
      color: "bg-gray-100 text-gray-600",
      dot: "bg-gray-400",
    },
  };

  const config = statusConfig[status] || {
    label: status || "Unknown",
    color: "bg-gray-100 text-gray-600",
    dot: "bg-gray-400",
  };

  return (
    <span className={`inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-xs font-medium ${config.color}`}>
      <span className={`w-1.5 h-1.5 rounded-full ${config.dot}`} />
      {config.label}
    </span>
  );
}

function formatTimestamp(timestamp: string): string {
  const date = new Date(timestamp);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffMins = Math.floor(diffMs / 60000);
  const diffHours = Math.floor(diffMins / 60);
  const diffDays = Math.floor(diffHours / 24);

  if (diffMins < 1) return "Just now";
  if (diffMins < 60) return `${diffMins}m ago`;
  if (diffHours < 24) return `${diffHours}h ago`;
  if (diffDays < 7) return `${diffDays}d ago`;

  return date.toLocaleDateString();
}

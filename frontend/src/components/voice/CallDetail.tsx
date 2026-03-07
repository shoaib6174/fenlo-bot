"use client";

import {
  ArrowLeft,
  PhoneIncoming,
  PhoneOutgoing,
  Globe,
  Clock,
  AlertTriangle,
  Play,
} from "lucide-react";
import type { CallLogResponse } from "@/types/voice";

interface CallDetailProps {
  call: CallLogResponse;
  onBack: () => void;
}

function formatDuration(seconds: number | null): string {
  if (seconds === null || seconds === 0) return "--";
  const m = Math.floor(seconds / 60);
  const s = seconds % 60;
  return `${m}m ${s}s`;
}

function formatDate(dateStr: string): string {
  return new Date(dateStr).toLocaleString(undefined, {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });
}

function DirectionLabel({ direction }: { direction: string }) {
  const config: Record<string, { icon: React.ReactNode; label: string; color: string }> = {
    inbound: {
      icon: <PhoneIncoming className="w-4 h-4" />,
      label: "Inbound Call",
      color: "text-blue-600",
    },
    outbound: {
      icon: <PhoneOutgoing className="w-4 h-4" />,
      label: "Outbound Call",
      color: "text-green-600",
    },
    web: {
      icon: <Globe className="w-4 h-4" />,
      label: "Web Call",
      color: "text-purple-600",
    },
  };
  const c = config[direction] || config.inbound;
  return (
    <span className={`inline-flex items-center gap-1.5 text-sm font-medium ${c.color}`}>
      {c.icon}
      {c.label}
    </span>
  );
}

function parseTranscript(text: string): { role: string; text: string }[] {
  const lines = text.split("\n").filter(Boolean);
  return lines.map((line) => {
    const match = line.match(/^(Customer|Assistant|User|Agent|AI):\s*(.*)/i);
    if (match) {
      return { role: match[1].toLowerCase(), text: match[2] };
    }
    return { role: "unknown", text: line };
  });
}

export function CallDetail({ call, onBack }: CallDetailProps) {
  const transcriptEntries = call.transcript
    ? parseTranscript(call.transcript)
    : [];

  const escalationAction = call.actions_taken?.find(
    (a) => a.action === "escalate"
  );

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center gap-3">
        <button
          onClick={onBack}
          className="p-1.5 rounded-lg hover:bg-gray-100 transition-colors"
        >
          <ArrowLeft className="w-5 h-5 text-gray-500" />
        </button>
        <div>
          <h2 className="text-lg font-semibold text-gray-900">Call Detail</h2>
          <p className="text-sm text-gray-500">{formatDate(call.created_at)}</p>
        </div>
      </div>

      {/* Metadata */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        <div className="bg-white border border-gray-200 rounded-lg p-3">
          <p className="text-xs text-gray-500 mb-1">Direction</p>
          <DirectionLabel direction={call.direction} />
        </div>
        <div className="bg-white border border-gray-200 rounded-lg p-3">
          <p className="text-xs text-gray-500 mb-1">Duration</p>
          <p className="text-sm font-medium text-gray-900 flex items-center gap-1">
            <Clock className="w-4 h-4 text-gray-400" />
            {formatDuration(call.duration_sec)}
          </p>
        </div>
        <div className="bg-white border border-gray-200 rounded-lg p-3">
          <p className="text-xs text-gray-500 mb-1">From</p>
          <p className="text-sm font-medium text-gray-900">{call.phone_from || "--"}</p>
        </div>
        <div className="bg-white border border-gray-200 rounded-lg p-3">
          <p className="text-xs text-gray-500 mb-1">Sentiment</p>
          {call.sentiment ? (
            <span
              className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${
                call.sentiment === "positive"
                  ? "bg-green-100 text-green-700"
                  : call.sentiment === "negative"
                    ? "bg-red-100 text-red-700"
                    : "bg-gray-100 text-gray-600"
              }`}
            >
              {call.sentiment}
            </span>
          ) : (
            <p className="text-sm text-gray-400">--</p>
          )}
        </div>
      </div>

      {/* Escalation info */}
      {escalationAction && (
        <div className="bg-amber-50 border border-amber-200 rounded-lg p-4">
          <div className="flex items-center gap-2 mb-2">
            <AlertTriangle className="w-4 h-4 text-amber-600" />
            <h3 className="text-sm font-semibold text-amber-800">
              Escalation Triggered
            </h3>
          </div>
          <div className="text-sm text-amber-700 space-y-1">
            <p>
              <span className="font-medium">Rule type:</span>{" "}
              {String(escalationAction.rule_type)}
            </p>
            {escalationAction.matched != null && (
              <p>
                <span className="font-medium">Matched:</span>{" "}
                {String(escalationAction.matched)}
              </p>
            )}
          </div>
        </div>
      )}

      {/* Summary */}
      {call.summary && (
        <div className="bg-white border border-gray-200 rounded-lg p-4">
          <h3 className="text-sm font-semibold text-gray-900 mb-2">Summary</h3>
          <p className="text-sm text-gray-700 leading-relaxed">{call.summary}</p>
        </div>
      )}

      {/* Recording */}
      {call.recording_url && (
        <div className="bg-white border border-gray-200 rounded-lg p-4">
          <h3 className="text-sm font-semibold text-gray-900 mb-2">Recording</h3>
          <audio controls className="w-full" src={call.recording_url}>
            <track kind="captions" />
            Your browser does not support audio playback.
          </audio>
        </div>
      )}

      {/* Transcript */}
      <div className="bg-white border border-gray-200 rounded-lg p-4">
        <h3 className="text-sm font-semibold text-gray-900 mb-3">Transcript</h3>
        {transcriptEntries.length === 0 ? (
          <p className="text-sm text-gray-400">No transcript available</p>
        ) : (
          <div className="space-y-3">
            {transcriptEntries.map((entry, i) => (
              <div key={i} className="flex gap-3">
                <div
                  className={`w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 text-xs font-medium ${
                    entry.role === "customer" || entry.role === "user"
                      ? "bg-blue-100 text-blue-600"
                      : "bg-green-100 text-green-600"
                  }`}
                >
                  {entry.role === "customer" || entry.role === "user"
                    ? "U"
                    : "A"}
                </div>
                <div className="flex-1">
                  <p className="text-xs text-gray-500 capitalize mb-0.5">
                    {entry.role}
                  </p>
                  <p className="text-sm text-gray-800">{entry.text}</p>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

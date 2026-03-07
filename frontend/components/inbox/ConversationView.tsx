/**
 * ConversationView Component
 *
 * Displays message thread with sentiment/intent badges.
 * For voice conversations, shows call metadata card + parsed transcript.
 */

"use client";

import { useEffect, useRef, useState } from "react";
import {
  Send,
  Phone,
  PhoneIncoming,
  PhoneOutgoing,
  Clock,
  Mic,
  FileText,
  AlertTriangle,
} from "lucide-react";
import { toast } from "sonner";
import { useSendReply } from "@/hooks/useInbox";
import type { InboxMessage, CallLogDetail } from "@/lib/api";

interface ConversationViewProps {
  messages: InboxMessage[];
  conversationId: string;
  channel?: string;
  callLog?: CallLogDetail;
}

export function ConversationView({
  messages,
  conversationId,
  channel,
  callLog,
}: ConversationViewProps) {
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const [replyText, setReplyText] = useState("");
  const sendReply = useSendReply();

  // Auto-scroll to bottom on new messages
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, callLog]);

  const handleSend = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!replyText.trim()) return;

    try {
      await sendReply.mutateAsync({
        conversationId,
        data: { content: replyText },
      });
      setReplyText("");
      toast.success("Reply sent successfully");
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Failed to send reply");
    }
  };

  const isVoice = channel === "voice";
  const hasContent = messages.length > 0 || (isVoice && callLog);

  if (!hasContent) {
    return (
      <div className="flex items-center justify-center h-full text-gray-500">
        <p>No messages</p>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full">
      {/* Messages / Voice Content */}
      <div className="flex-1 overflow-y-auto p-6 space-y-4">
        {/* Voice Call Metadata Card */}
        {isVoice && callLog && <CallMetadataCard callLog={callLog} />}

        {/* Voice Transcript (parsed into chat-like turns) */}
        {isVoice && callLog?.transcript && (
          <VoiceTranscript transcript={callLog.transcript} />
        )}

        {/* Regular text messages */}
        {messages.map((message) => (
          <div
            key={message.id}
            className={`flex ${message.role === "user" ? "justify-start" : "justify-end"}`}
          >
            <div
              className={`max-w-[70%] rounded-lg px-4 py-3 ${
                message.role === "user"
                  ? "bg-gray-100 text-gray-900"
                  : "bg-blue-600 text-white"
              }`}
            >
              {/* Message Content */}
              <p className="text-sm whitespace-pre-wrap break-words">{message.content}</p>

              {/* Metadata Badges */}
              <div className="flex flex-wrap gap-2 mt-2">
                {message.sentiment && <SentimentBadge sentiment={message.sentiment} />}
                {message.intent && <IntentBadge intent={message.intent} />}
                {message.quality_score !== null && message.quality_score !== undefined && (
                  <QualityBadge score={message.quality_score} />
                )}
              </div>

              {/* Timestamp */}
              <p
                className={`text-xs mt-2 ${
                  message.role === "user" ? "text-gray-500" : "text-blue-100"
                }`}
              >
                {new Date(message.created_at).toLocaleTimeString()}
              </p>
            </div>
          </div>
        ))}
        <div ref={messagesEndRef} />
      </div>

      {/* Reply Input — hidden for voice (can't text-reply to a phone call) */}
      {isVoice ? (
        <div className="border-t border-gray-200 px-4 py-3 bg-gray-50 flex items-center gap-2 text-sm text-gray-500">
          <Phone className="w-4 h-4" />
          <span>Reply not available for voice calls</span>
        </div>
      ) : (
        <form
          onSubmit={handleSend}
          className="border-t border-gray-200 p-4 bg-white"
        >
          <div className="flex gap-2">
            <input
              type="text"
              value={replyText}
              onChange={(e) => setReplyText(e.target.value)}
              placeholder="Type your reply..."
              className="flex-1 px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              disabled={sendReply.isPending}
            />
            <button
              type="submit"
              disabled={!replyText.trim() || sendReply.isPending}
              className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
            >
              <Send className="w-4 h-4" />
              Send
            </button>
          </div>
        </form>
      )}
    </div>
  );
}

// ---- Voice-specific components ----

function CallMetadataCard({ callLog }: { callLog: CallLogDetail }) {
  const DirIcon =
    callLog.direction === "inbound"
      ? PhoneIncoming
      : callLog.direction === "outbound"
        ? PhoneOutgoing
        : Phone;

  const statusColors: Record<string, string> = {
    ended: "bg-gray-100 text-gray-700",
    connected: "bg-green-100 text-green-700",
    failed: "bg-red-100 text-red-700",
    canceled: "bg-yellow-100 text-yellow-700",
    initiated: "bg-blue-100 text-blue-700",
    ringing: "bg-blue-100 text-blue-700",
    no_answer: "bg-yellow-100 text-yellow-700",
  };

  const sentimentColors: Record<string, string> = {
    positive: "bg-green-100 text-green-700",
    neutral: "bg-gray-100 text-gray-600",
    negative: "bg-red-100 text-red-700",
  };

  return (
    <div className="bg-purple-50 border border-purple-200 rounded-lg p-4 space-y-3">
      {/* Header row */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <div className="p-1.5 bg-purple-100 rounded-lg">
            <DirIcon className="w-4 h-4 text-purple-600" />
          </div>
          <div>
            <span className="text-sm font-semibold text-gray-900">
              {callLog.direction === "inbound"
                ? "Inbound Call"
                : callLog.direction === "outbound"
                  ? "Outbound Call"
                  : "Web Call"}
            </span>
            {callLog.phone_from && (
              <span className="text-xs text-gray-500 ml-2">
                from {callLog.phone_from}
              </span>
            )}
          </div>
        </div>
        <span
          className={`text-xs font-medium px-2 py-0.5 rounded-full ${
            statusColors[callLog.status] || statusColors.ended
          }`}
        >
          {callLog.status}
        </span>
      </div>

      {/* Stats row */}
      <div className="flex flex-wrap gap-4 text-xs">
        {callLog.duration_sec !== null && (
          <div className="flex items-center gap-1 text-gray-600">
            <Clock className="w-3.5 h-3.5" />
            <span>{formatCallDuration(callLog.duration_sec)}</span>
          </div>
        )}
        {callLog.sentiment && (
          <span
            className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full font-medium ${
              sentimentColors[callLog.sentiment] || sentimentColors.neutral
            }`}
          >
            {callLog.sentiment}
          </span>
        )}
        {callLog.created_at && (
          <span className="text-gray-500">
            {new Date(callLog.created_at).toLocaleString()}
          </span>
        )}
      </div>

      {/* Summary */}
      {callLog.summary && (
        <div className="flex items-start gap-2 pt-1">
          <FileText className="w-3.5 h-3.5 text-gray-400 mt-0.5 flex-shrink-0" />
          <p className="text-sm text-gray-700">{callLog.summary}</p>
        </div>
      )}

      {/* Actions taken (escalation etc) */}
      {callLog.actions_taken && callLog.actions_taken.length > 0 && (
        <div className="flex items-start gap-2 pt-1">
          <AlertTriangle className="w-3.5 h-3.5 text-orange-500 mt-0.5 flex-shrink-0" />
          <div className="text-xs text-orange-700">
            {callLog.actions_taken.map((action, i) => (
              <span key={i}>
                {action.action_type}
                {action.details ? `: ${action.details}` : ""}
                {i < callLog.actions_taken!.length - 1 ? " | " : ""}
              </span>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

interface TranscriptTurn {
  speaker: "ai" | "user";
  text: string;
}

function parseTranscript(raw: string): TranscriptTurn[] {
  const turns: TranscriptTurn[] = [];

  // Try to parse structured transcript: "AI: ...", "User: ..."
  const lines = raw.split("\n").filter((l) => l.trim());
  let currentSpeaker: "ai" | "user" | null = null;
  let currentText = "";

  for (const line of lines) {
    const aiMatch = line.match(/^(AI|Bot|Assistant|Agent)\s*:\s*(.*)/i);
    const userMatch = line.match(/^(User|Customer|Caller|Human)\s*:\s*(.*)/i);

    if (aiMatch) {
      if (currentSpeaker && currentText) {
        turns.push({ speaker: currentSpeaker, text: currentText.trim() });
      }
      currentSpeaker = "ai";
      currentText = aiMatch[2];
    } else if (userMatch) {
      if (currentSpeaker && currentText) {
        turns.push({ speaker: currentSpeaker, text: currentText.trim() });
      }
      currentSpeaker = "user";
      currentText = userMatch[2];
    } else if (currentSpeaker) {
      currentText += " " + line.trim();
    }
  }

  // Push last turn
  if (currentSpeaker && currentText) {
    turns.push({ speaker: currentSpeaker, text: currentText.trim() });
  }

  // If parsing didn't produce turns, show as single block
  if (turns.length === 0 && raw.trim()) {
    turns.push({ speaker: "ai", text: raw.trim() });
  }

  return turns;
}

function VoiceTranscript({ transcript }: { transcript: string }) {
  const turns = parseTranscript(transcript);

  return (
    <div className="space-y-1">
      <div className="flex items-center gap-2 mb-3">
        <Mic className="w-4 h-4 text-gray-400" />
        <span className="text-xs font-medium text-gray-500 uppercase tracking-wide">
          Call Transcript
        </span>
      </div>
      <div className="space-y-3">
        {turns.map((turn, i) => (
          <div
            key={i}
            className={`flex ${turn.speaker === "user" ? "justify-start" : "justify-end"}`}
          >
            <div
              className={`max-w-[70%] rounded-lg px-4 py-3 ${
                turn.speaker === "user"
                  ? "bg-gray-100 text-gray-900"
                  : "bg-purple-600 text-white"
              }`}
            >
              <p className="text-xs font-medium mb-1 opacity-70">
                {turn.speaker === "user" ? "Customer" : "AI Agent"}
              </p>
              <p className="text-sm whitespace-pre-wrap break-words">{turn.text}</p>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function formatCallDuration(seconds: number): string {
  if (seconds === 0) return "0s";
  const m = Math.floor(seconds / 60);
  const s = seconds % 60;
  if (m === 0) return `${s}s`;
  return `${m}m ${s}s`;
}

function SentimentBadge({ sentiment }: { sentiment: string }) {
  const config = {
    positive: "bg-green-100 text-green-800",
    neutral: "bg-gray-100 text-gray-800",
    negative: "bg-red-100 text-red-800",
  };

  return (
    <span
      className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${
        config[sentiment as keyof typeof config] || config.neutral
      }`}
    >
      {sentiment}
    </span>
  );
}

function IntentBadge({ intent }: { intent: string }) {
  const config = {
    faq: "bg-blue-100 text-blue-800",
    booking: "bg-purple-100 text-purple-800",
    sales: "bg-green-100 text-green-800",
    support: "bg-yellow-100 text-yellow-800",
    escalation: "bg-red-100 text-red-800",
    other: "bg-gray-100 text-gray-800",
  };

  return (
    <span
      className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${
        config[intent as keyof typeof config] || config.other
      }`}
    >
      {intent}
    </span>
  );
}

function QualityBadge({ score }: { score: number }) {
  const getColor = (score: number) => {
    if (score >= 0.7) return "bg-green-100 text-green-800";
    if (score >= 0.4) return "bg-yellow-100 text-yellow-800";
    return "bg-red-100 text-red-800";
  };

  return (
    <span
      className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${getColor(
        score
      )}`}
    >
      Q: {score.toFixed(2)}
    </span>
  );
}

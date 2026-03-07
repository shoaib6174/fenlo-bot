"use client";

import { useParams, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { useAuth } from "@/providers/auth";
import { apiClient } from "@/lib/api";
import {
  ArrowLeft,
  FileText,
  BarChart3,
  MessageSquare,
  Target,
  Smile,
  Zap,
  Clock,
  Hash,
} from "lucide-react";

interface DebugMessage {
  id: string;
  role: "user" | "assistant" | "system";
  content: string;
  sentiment: string | null;
  intent: string | null;
  quality_score: number | null;
  tokens_used: number | null;
  latency_ms: number | null;
  citations: Array<{
    doc_name: string;
    page_number?: number;
    chunk_text: string;
    relevance_score: number;
    document_id?: string;
  }>;
  feedback: string | null;
  created_at: string;
}

interface ConversationMeta {
  status: string;
  channel: string;
  lead_score: number | null;
  started_at: string | null;
  message_count: number;
}

interface DebugData {
  conversation_id: string;
  conversation: ConversationMeta;
  messages: DebugMessage[];
  confidence_scores: number[];
  intents: string[];
}

const sentimentColors: Record<string, string> = {
  positive: "bg-green-100 text-green-800",
  neutral: "bg-gray-100 text-gray-700",
  negative: "bg-red-100 text-red-800",
};

const intentColors: Record<string, string> = {
  faq: "bg-blue-100 text-blue-800",
  sales: "bg-purple-100 text-purple-800",
  booking: "bg-amber-100 text-amber-800",
  support: "bg-teal-100 text-teal-800",
  escalation: "bg-red-100 text-red-800",
  other: "bg-gray-100 text-gray-700",
};

export default function DebugSandboxPage() {
  const { conversationId } = useParams<{ conversationId: string }>();
  const router = useRouter();
  const { isAuthenticated } = useAuth();
  const [debugData, setDebugData] = useState<DebugData | null>(null);
  const [selectedMsgId, setSelectedMsgId] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!isAuthenticated || !conversationId) return;

    async function fetchDebug() {
      setLoading(true);
      try {
        const data = await apiClient<DebugData>(
          `/api/v1/chat/conversations/${conversationId}/debug`
        );
        setDebugData(data);
        // Auto-select first assistant message
        const firstAssistant = data.messages.find((m) => m.role === "assistant");
        if (firstAssistant) setSelectedMsgId(firstAssistant.id);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to load debug data");
      } finally {
        setLoading(false);
      }
    }

    fetchDebug();
  }, [isAuthenticated, conversationId]);

  const selectedMsg = debugData?.messages.find((m) => m.id === selectedMsgId);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600" />
      </div>
    );
  }

  if (error || !debugData) {
    return (
      <div className="flex flex-col items-center justify-center h-full gap-4">
        <p className="text-red-600">{error || "No data available"}</p>
        <button
          onClick={() => router.push("/chat")}
          className="text-blue-600 hover:underline text-sm"
        >
          Back to Chat
        </button>
      </div>
    );
  }

  return (
    <div className="h-full flex flex-col">
      {/* Header */}
      <div className="px-6 py-4 border-b border-gray-200 bg-white flex items-center gap-4">
        <button
          onClick={() => router.back()}
          className="p-1 hover:bg-gray-100 rounded"
        >
          <ArrowLeft className="w-5 h-5 text-gray-600" />
        </button>
        <div>
          <h1 className="text-lg font-semibold text-gray-900">
            Debug Sandbox
          </h1>
          <p className="text-sm text-gray-500">
            {debugData.conversation.message_count} messages
            {debugData.conversation.channel && ` \u00b7 ${debugData.conversation.channel}`}
            {debugData.conversation.lead_score !== null &&
              ` \u00b7 Lead: ${debugData.conversation.lead_score}`}
          </p>
        </div>
      </div>

      {/* Split Pane */}
      <div className="flex-1 flex overflow-hidden">
        {/* Left: Messages */}
        <div className="w-1/2 border-r border-gray-200 overflow-y-auto bg-white">
          <div className="p-4 space-y-3">
            {debugData.messages.map((msg) => (
              <button
                key={msg.id}
                onClick={() => setSelectedMsgId(msg.id)}
                className={`w-full text-left p-3 rounded-lg border transition-colors ${
                  selectedMsgId === msg.id
                    ? "border-blue-500 bg-blue-50"
                    : "border-gray-200 hover:border-gray-300 bg-white"
                }`}
              >
                <div className="flex items-center gap-2 mb-1">
                  <span
                    className={`text-xs font-medium px-2 py-0.5 rounded ${
                      msg.role === "user"
                        ? "bg-gray-200 text-gray-700"
                        : "bg-blue-100 text-blue-700"
                    }`}
                  >
                    {msg.role}
                  </span>
                  <span className="text-xs text-gray-400">
                    {new Date(msg.created_at).toLocaleTimeString()}
                  </span>
                  {msg.sentiment && (
                    <span
                      className={`text-xs px-1.5 py-0.5 rounded ${
                        sentimentColors[msg.sentiment] || sentimentColors.neutral
                      }`}
                    >
                      {msg.sentiment}
                    </span>
                  )}
                  {msg.intent && (
                    <span
                      className={`text-xs px-1.5 py-0.5 rounded ${
                        intentColors[msg.intent] || intentColors.other
                      }`}
                    >
                      {msg.intent}
                    </span>
                  )}
                </div>
                <p className="text-sm text-gray-800 line-clamp-2">
                  {msg.content}
                </p>
              </button>
            ))}
          </div>
        </div>

        {/* Right: Debug Panel */}
        <div className="w-1/2 overflow-y-auto bg-gray-50">
          {selectedMsg ? (
            <div className="p-6 space-y-6">
              {/* Pipeline Replay Header */}
              <div>
                <h2 className="text-sm font-semibold text-gray-900 mb-1">
                  Pipeline Breakdown
                </h2>
                <p className="text-xs text-gray-500">
                  {selectedMsg.role === "user"
                    ? "User input that triggered the pipeline"
                    : "Assistant response with full analytics"}
                </p>
              </div>

              {/* Message Content */}
              <div className="bg-white rounded-lg border border-gray-200 p-4">
                <div className="flex items-center gap-2 mb-2">
                  <MessageSquare className="w-4 h-4 text-gray-500" />
                  <span className="text-xs font-medium text-gray-500 uppercase">
                    {selectedMsg.role} Message
                  </span>
                </div>
                <p className="text-sm text-gray-800 whitespace-pre-wrap">
                  {selectedMsg.content}
                </p>
              </div>

              {/* Analytics Badges */}
              {selectedMsg.role === "assistant" && (
                <div className="grid grid-cols-2 gap-3">
                  {selectedMsg.sentiment && (
                    <div className="bg-white rounded-lg border border-gray-200 p-3">
                      <div className="flex items-center gap-2 mb-1">
                        <Smile className="w-4 h-4 text-gray-400" />
                        <span className="text-xs font-medium text-gray-500">
                          Sentiment
                        </span>
                      </div>
                      <span
                        className={`text-sm font-medium px-2 py-0.5 rounded ${
                          sentimentColors[selectedMsg.sentiment] ||
                          sentimentColors.neutral
                        }`}
                      >
                        {selectedMsg.sentiment}
                      </span>
                    </div>
                  )}

                  {selectedMsg.intent && (
                    <div className="bg-white rounded-lg border border-gray-200 p-3">
                      <div className="flex items-center gap-2 mb-1">
                        <Target className="w-4 h-4 text-gray-400" />
                        <span className="text-xs font-medium text-gray-500">
                          Intent
                        </span>
                      </div>
                      <span
                        className={`text-sm font-medium px-2 py-0.5 rounded ${
                          intentColors[selectedMsg.intent] || intentColors.other
                        }`}
                      >
                        {selectedMsg.intent}
                      </span>
                    </div>
                  )}

                  {selectedMsg.quality_score !== null && (
                    <div className="bg-white rounded-lg border border-gray-200 p-3">
                      <div className="flex items-center gap-2 mb-1">
                        <BarChart3 className="w-4 h-4 text-gray-400" />
                        <span className="text-xs font-medium text-gray-500">
                          Quality
                        </span>
                      </div>
                      <span className="text-sm font-medium text-gray-900">
                        {Math.round(selectedMsg.quality_score * 100)}%
                      </span>
                    </div>
                  )}

                  {selectedMsg.tokens_used !== null && (
                    <div className="bg-white rounded-lg border border-gray-200 p-3">
                      <div className="flex items-center gap-2 mb-1">
                        <Hash className="w-4 h-4 text-gray-400" />
                        <span className="text-xs font-medium text-gray-500">
                          Tokens
                        </span>
                      </div>
                      <span className="text-sm font-medium text-gray-900">
                        {selectedMsg.tokens_used}
                      </span>
                    </div>
                  )}

                  {selectedMsg.latency_ms !== null && (
                    <div className="bg-white rounded-lg border border-gray-200 p-3">
                      <div className="flex items-center gap-2 mb-1">
                        <Clock className="w-4 h-4 text-gray-400" />
                        <span className="text-xs font-medium text-gray-500">
                          Latency
                        </span>
                      </div>
                      <span className="text-sm font-medium text-gray-900">
                        {selectedMsg.latency_ms}ms
                      </span>
                    </div>
                  )}

                  {selectedMsg.feedback && (
                    <div className="bg-white rounded-lg border border-gray-200 p-3">
                      <div className="flex items-center gap-2 mb-1">
                        <Zap className="w-4 h-4 text-gray-400" />
                        <span className="text-xs font-medium text-gray-500">
                          Feedback
                        </span>
                      </div>
                      <span
                        className={`text-sm font-medium ${
                          selectedMsg.feedback === "positive"
                            ? "text-green-600"
                            : "text-red-600"
                        }`}
                      >
                        {selectedMsg.feedback}
                      </span>
                    </div>
                  )}
                </div>
              )}

              {/* RAG Citations / Chunks */}
              {selectedMsg.citations.length > 0 && (
                <div>
                  <div className="flex items-center gap-2 mb-3">
                    <FileText className="w-4 h-4 text-gray-500" />
                    <h3 className="text-sm font-semibold text-gray-900">
                      Retrieved Chunks ({selectedMsg.citations.length})
                    </h3>
                  </div>
                  <div className="space-y-2">
                    {selectedMsg.citations.map((citation, idx) => (
                      <div
                        key={idx}
                        className="bg-white rounded-lg border border-gray-200 p-3"
                      >
                        <div className="flex items-center justify-between mb-2">
                          <span className="text-xs font-medium text-gray-700">
                            {citation.doc_name}
                            {citation.page_number !== null &&
                              ` \u00b7 p.${citation.page_number}`}
                          </span>
                          <span
                            className={`text-xs font-mono px-2 py-0.5 rounded ${
                              citation.relevance_score >= 0.8
                                ? "bg-green-100 text-green-700"
                                : citation.relevance_score >= 0.6
                                  ? "bg-amber-100 text-amber-700"
                                  : "bg-red-100 text-red-700"
                            }`}
                          >
                            {((citation.relevance_score ?? 0) * 100).toFixed(0)}%
                          </span>
                        </div>
                        <p className="text-xs text-gray-600 leading-relaxed">
                          {citation.chunk_text}
                        </p>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Pipeline Timeline (Conversation Replay) */}
              {selectedMsg.role === "assistant" && (
                <div>
                  <h3 className="text-sm font-semibold text-gray-900 mb-3">
                    Pipeline Timeline
                  </h3>
                  <div className="space-y-0">
                    {/* Find the preceding user message */}
                    {(() => {
                      const msgIndex = debugData.messages.findIndex(
                        (m) => m.id === selectedMsg.id
                      );
                      const userMsg =
                        msgIndex > 0
                          ? debugData.messages[msgIndex - 1]
                          : null;
                      return (
                        <>
                          <TimelineStep
                            step="1"
                            label="User Input"
                            value={
                              userMsg?.content.slice(0, 100) ||
                              "N/A"
                            }
                            done
                          />
                          <TimelineStep
                            step="2"
                            label="RAG Retrieval"
                            value={
                              selectedMsg.citations.length > 0
                                ? `${selectedMsg.citations.length} chunks (top: ${(selectedMsg.citations[0].relevance_score * 100).toFixed(0)}%)`
                                : "No chunks retrieved"
                            }
                            done
                          />
                          <TimelineStep
                            step="3"
                            label="LLM Response"
                            value={`${selectedMsg.content.length} chars${selectedMsg.tokens_used ? `, ${selectedMsg.tokens_used} tokens` : ""}`}
                            done
                          />
                          <TimelineStep
                            step="4"
                            label="Sentiment"
                            value={selectedMsg.sentiment || "N/A"}
                            done={!!selectedMsg.sentiment}
                          />
                          <TimelineStep
                            step="5"
                            label="Intent"
                            value={selectedMsg.intent || "N/A"}
                            done={!!selectedMsg.intent}
                          />
                          <TimelineStep
                            step="6"
                            label="Quality Score"
                            value={
                              selectedMsg.quality_score !== null
                                ? `${Math.round(selectedMsg.quality_score * 100)}%`
                                : "N/A"
                            }
                            done={selectedMsg.quality_score !== null}
                            last
                          />
                        </>
                      );
                    })()}
                  </div>
                </div>
              )}
            </div>
          ) : (
            <div className="flex items-center justify-center h-full text-gray-400 text-sm">
              Select a message to view pipeline details
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function TimelineStep({
  step,
  label,
  value,
  done,
  last,
}: {
  step: string;
  label: string;
  value: string;
  done: boolean;
  last?: boolean;
}) {
  return (
    <div className="flex gap-3">
      <div className="flex flex-col items-center">
        <div
          className={`w-6 h-6 rounded-full flex items-center justify-center text-xs font-medium ${
            done
              ? "bg-blue-600 text-white"
              : "bg-gray-200 text-gray-500"
          }`}
        >
          {step}
        </div>
        {!last && <div className="w-px h-8 bg-gray-200" />}
      </div>
      <div className="pb-6">
        <p className="text-xs font-medium text-gray-700">{label}</p>
        <p className="text-xs text-gray-500 mt-0.5">{value}</p>
      </div>
    </div>
  );
}

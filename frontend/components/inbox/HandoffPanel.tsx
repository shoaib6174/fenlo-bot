/**
 * HandoffPanel Component
 *
 * Displays enriched context for escalated conversations:
 * - RAG context
 * - Quality scores
 * - Intent history
 * - Sentiment timeline
 */

"use client";

import { useHandoffContext } from "@/hooks/useInbox";
import { FileText, TrendingUp, Target, Smile } from "lucide-react";

interface HandoffPanelProps {
  conversationId: string;
}

export function HandoffPanel({ conversationId }: HandoffPanelProps) {
  const { data: context, isLoading } = useHandoffContext(conversationId);

  if (isLoading) {
    return (
      <div className="bg-white border-t border-gray-200 p-6">
        <p className="text-sm text-gray-500">Loading handoff context...</p>
      </div>
    );
  }

  if (!context) {
    return (
      <div className="bg-white border-t border-gray-200 p-6">
        <p className="text-sm text-gray-500">No handoff context available</p>
      </div>
    );
  }

  return (
    <div className="bg-white border-t border-gray-200 p-6 space-y-6">
      <h3 className="text-lg font-semibold text-gray-900">Handoff Context</h3>

      {/* RAG Context */}
      {context.rag_contexts && context.rag_contexts.length > 0 && (
        <div>
          <div className="flex items-center gap-2 mb-3">
            <FileText className="w-4 h-4 text-blue-600" />
            <h4 className="font-medium text-gray-900">Knowledge Base Context</h4>
          </div>
          <div className="space-y-2">
            {context.rag_contexts.slice(0, 3).map((ctx, idx) => (
              <div key={idx} className="p-3 bg-gray-50 rounded-lg">
                <p className="text-sm text-gray-800 mb-1">{ctx.content}</p>
                <div className="flex items-center justify-between text-xs text-gray-500">
                  <span>Source: {ctx.source}</span>
                  <span>Relevance: {((ctx.score ?? 0) * 100).toFixed(0)}%</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Quality Scores */}
      {context.quality_scores && context.quality_scores.filter((qs: any) => qs?.score !== null).length > 0 && (
        <div>
          <div className="flex items-center gap-2 mb-3">
            <TrendingUp className="w-4 h-4 text-green-600" />
            <h4 className="font-medium text-gray-900">Quality Scores</h4>
          </div>
          <div className="space-y-1">
            {context.quality_scores.filter((qs: any) => qs?.score !== null).slice(-5).map((qs: any, idx: number) => (
              <div key={idx} className="flex items-center justify-between text-sm">
                <span className="text-gray-600">
                  {qs.timestamp ? new Date(qs.timestamp).toLocaleTimeString() : "—"}
                </span>
                <QualityBar score={qs.score} />
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Intent History */}
      {context.intent_history && context.intent_history.filter((ih: any) => ih?.intent !== null).length > 0 && (
        <div>
          <div className="flex items-center gap-2 mb-3">
            <Target className="w-4 h-4 text-purple-600" />
            <h4 className="font-medium text-gray-900">Intent Timeline</h4>
          </div>
          <div className="space-y-1">
            {context.intent_history.filter((ih: any) => ih?.intent !== null).slice(-5).map((ih: any, idx: number) => (
              <div key={idx} className="flex items-center justify-between text-sm">
                <span className="text-gray-600">
                  {ih.timestamp ? new Date(ih.timestamp).toLocaleTimeString() : "—"}
                </span>
                <IntentBadge intent={ih.intent} />
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Sentiment Timeline */}
      {context.sentiment_timeline && context.sentiment_timeline.filter((st: any) => st?.sentiment !== null).length > 0 && (
        <div>
          <div className="flex items-center gap-2 mb-3">
            <Smile className="w-4 h-4 text-yellow-600" />
            <h4 className="font-medium text-gray-900">Sentiment Timeline</h4>
          </div>
          <div className="space-y-1">
            {context.sentiment_timeline.filter((st: any) => st?.sentiment !== null).slice(-5).map((st: any, idx: number) => (
              <div key={idx} className="flex items-center justify-between text-sm">
                <span className="text-gray-600">
                  {st.timestamp ? new Date(st.timestamp).toLocaleTimeString() : "—"}
                </span>
                <SentimentBadge sentiment={st.sentiment} />
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function QualityBar({ score }: { score: number }) {
  const percentage = Math.round(score * 100);
  const getColor = (score: number) => {
    if (score >= 0.7) return "bg-green-500";
    if (score >= 0.4) return "bg-yellow-500";
    return "bg-red-500";
  };

  return (
    <div className="flex items-center gap-2">
      <div className="w-24 h-2 bg-gray-200 rounded-full overflow-hidden">
        <div
          className={`h-full ${getColor(score)}`}
          style={{ width: `${percentage}%` }}
        />
      </div>
      <span className="text-xs text-gray-500">{percentage}%</span>
    </div>
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

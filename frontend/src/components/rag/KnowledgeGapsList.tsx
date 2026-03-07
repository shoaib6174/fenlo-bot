'use client';

import { useState } from 'react';
import { AlertCircle, Plus, X, Loader2 } from 'lucide-react';
import type { KnowledgeGap } from '@/types/rag';

interface KnowledgeGapsListProps {
  gaps: KnowledgeGap[];
  onDismiss?: (gapId: string) => void;
  onAddress?: (gapId: string, queryText: string) => void;
  readOnly?: boolean;
}

export function KnowledgeGapsList({ gaps, onDismiss, onAddress, readOnly }: KnowledgeGapsListProps) {
  const [dismissingId, setDismissingId] = useState<string | null>(null);

  const handleDismiss = async (gapId: string) => {
    setDismissingId(gapId);
    try {
      const response = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL || ""}/api/v1/kb/gaps/${gapId}/dismiss`,
        {
          method: 'POST',
          credentials: 'include',
        }
      );

      if (!response.ok) {
        throw new Error('Failed to dismiss gap');
      }

      onDismiss?.(gapId);
    } catch (error) {
      alert(error instanceof Error ? error.message : 'Failed to dismiss gap');
    } finally {
      setDismissingId(null);
    }
  };

  const activeGaps = gaps.filter((gap) => gap.status === 'active');

  if (activeGaps.length === 0) {
    return (
      <div className="bg-green-50 border border-green-200 rounded-lg p-6 text-center">
        <AlertCircle className="w-12 h-12 text-green-600 mx-auto mb-4" />
        <h3 className="text-lg font-semibold text-green-900 mb-2">
          No Knowledge Gaps!
        </h3>
        <p className="text-green-700">
          Your chatbot can answer all common questions. Great job!
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      <div className="bg-amber-50 border border-amber-200 rounded-lg p-4">
        <div className="flex items-start gap-3">
          <AlertCircle className="w-5 h-5 text-amber-600 flex-shrink-0 mt-0.5" />
          <div>
            <h3 className="font-semibold text-amber-900 mb-1">
              Knowledge Gaps Detected
            </h3>
            <p className="text-sm text-amber-700">
              These questions were asked but couldn&apos;t be answered with your current
              knowledge base. Add documents covering these topics to improve your bot.
            </p>
          </div>
        </div>
      </div>

      {activeGaps
        .sort((a, b) => b.occurrence_count - a.occurrence_count)
        .map((gap) => (
          <div
            key={gap.id}
            className="bg-white border border-gray-200 rounded-lg p-4 hover:shadow-sm transition"
          >
            <div className="flex items-start justify-between gap-4">
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 mb-2">
                  <span className="flex-shrink-0 px-2 py-1 bg-red-100 text-red-800 text-xs font-semibold rounded-full">
                    {gap.occurrence_count}x
                  </span>
                  <p className="text-gray-900 font-medium">
                    &ldquo;{gap.query_text}&rdquo;
                  </p>
                </div>

                <div className="flex items-center gap-4 text-sm text-gray-500">
                  <span>
                    First asked:{' '}
                    {new Date(gap.first_asked_at).toLocaleDateString()}
                  </span>
                  <span>
                    Last asked:{' '}
                    {new Date(gap.last_asked_at).toLocaleDateString()}
                  </span>
                </div>
              </div>

              {/* Actions */}
              {!readOnly && (
                <div className="flex gap-2 flex-shrink-0">
                  <button
                    onClick={() => onAddress?.(gap.id, gap.query_text)}
                    className="flex items-center gap-1 px-3 py-1.5 text-sm bg-blue-600 text-white rounded hover:bg-blue-700 transition"
                    title="Add document to address this gap"
                  >
                    <Plus className="w-4 h-4" />
                    Add to KB
                  </button>

                  <button
                    onClick={() => handleDismiss(gap.id)}
                    disabled={dismissingId === gap.id}
                    className="flex items-center gap-1 px-3 py-1.5 text-sm bg-gray-200 text-gray-700 rounded hover:bg-gray-300 disabled:bg-gray-100 transition"
                    title="Dismiss this gap"
                  >
                    {dismissingId === gap.id ? (
                      <Loader2 className="w-4 h-4 animate-spin" />
                    ) : (
                      <X className="w-4 h-4" />
                    )}
                  </button>
                </div>
              )}
            </div>
          </div>
        ))}
    </div>
  );
}

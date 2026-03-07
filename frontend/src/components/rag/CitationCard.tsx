'use client';

import { FileText } from 'lucide-react';
import type { Citation } from '@/types/rag';

interface CitationCardProps {
  citation: Citation;
  index: number;
}

export function CitationCard({ citation, index }: CitationCardProps) {
  return (
    <div className="bg-blue-50 border border-blue-200 rounded-lg p-3 text-sm">
      <div className="flex items-start gap-2">
        <div className="flex-shrink-0">
          <div className="w-6 h-6 bg-blue-600 text-white rounded-full flex items-center justify-center text-xs font-semibold">
            {index + 1}
          </div>
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <FileText className="w-4 h-4 text-blue-600" />
            <span className="font-semibold text-blue-900 truncate">
              {citation.doc_name}
            </span>
            {citation.page_number && (
              <span className="text-blue-700 text-xs">
                (Page {citation.page_number})
              </span>
            )}
          </div>
          <p className="text-gray-700 line-clamp-3 mb-2">
            {citation.chunk_text}
          </p>
          <div className="flex items-center justify-between">
            <span className="text-xs text-gray-500">
              Relevance: {((citation.relevance_score ?? 0) * 100).toFixed(0)}%
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}

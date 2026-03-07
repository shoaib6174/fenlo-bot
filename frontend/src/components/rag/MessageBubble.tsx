'use client';

import { ThumbsUp, ThumbsDown, User, Bot } from 'lucide-react';
import { useState } from 'react';
import type { RAGMessage } from '@/types/rag';
import { CitationCard } from './CitationCard';

const SENTIMENT_STYLES: Record<string, string> = {
  positive: 'bg-green-100 text-green-700',
  neutral: 'bg-gray-100 text-gray-600',
  negative: 'bg-red-100 text-red-700',
};

interface MessageBubbleProps {
  message: RAGMessage;
  onFeedback?: (messageId: string, feedback: 'positive' | 'negative') => void;
}

export function MessageBubble({ message, onFeedback }: MessageBubbleProps) {
  const [localFeedback, setLocalFeedback] = useState<'positive' | 'negative' | null>(
    message.feedback || null
  );

  const handleFeedback = (feedback: 'positive' | 'negative') => {
    setLocalFeedback(feedback);
    onFeedback?.(message.id, feedback);
  };

  const isUser = message.role === 'user';

  return (
    <div className={`flex gap-3 ${isUser ? 'flex-row-reverse' : 'flex-row'}`}>
      {/* Avatar */}
      <div
        className={`flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center ${
          isUser ? 'bg-blue-600' : 'bg-gray-300'
        }`}
      >
        {isUser ? (
          <User className="w-5 h-5 text-white" />
        ) : (
          <Bot className="w-5 h-5 text-gray-700" />
        )}
      </div>

      {/* Message Content */}
      <div className={`flex-1 ${isUser ? 'text-right' : 'text-left'}`}>
        <div
          className={`inline-block max-w-2xl px-4 py-3 rounded-lg ${
            isUser
              ? 'bg-blue-600 text-white'
              : 'bg-gray-100 text-gray-900'
          }`}
        >
          <p className="whitespace-pre-wrap break-words">{message.content}</p>
        </div>

        {/* Analytics Badges */}
        {!isUser && (message.sentiment || message.intent || message.quality_score != null) && (
          <div className="flex flex-wrap gap-1.5 mt-1.5 px-1">
            {message.sentiment && (
              <span
                className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${
                  SENTIMENT_STYLES[message.sentiment] || SENTIMENT_STYLES.neutral
                }`}
              >
                {message.sentiment}
              </span>
            )}
            {message.intent && (
              <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-700">
                {message.intent}
              </span>
            )}
            {message.quality_score != null && (
              <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-amber-100 text-amber-700">
                Q: {(message.quality_score * 100).toFixed(0)}%
              </span>
            )}
          </div>
        )}

        <div className="text-xs text-gray-500 mt-1 px-1">
          {new Date(message.timestamp).toLocaleTimeString([], {
            hour: '2-digit',
            minute: '2-digit',
          })}
        </div>

        {/* Citations */}
        {!isUser && message.citations && message.citations.length > 0 && (
          <div className="mt-3 space-y-2">
            <p className="text-sm font-semibold text-gray-700 mb-2">
              Sources ({message.citations.length}):
            </p>
            {message.citations.map((citation, index) => (
              <CitationCard key={index} citation={citation} index={index} />
            ))}
          </div>
        )}

        {/* Feedback Buttons */}
        {!isUser && onFeedback && (
          <div className="flex gap-2 mt-2">
            <button
              onClick={() => handleFeedback('positive')}
              className={`p-2 rounded-lg transition ${
                localFeedback === 'positive'
                  ? 'bg-green-100 text-green-600'
                  : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
              }`}
              aria-label="Thumbs up"
            >
              <ThumbsUp className="w-4 h-4" />
            </button>
            <button
              onClick={() => handleFeedback('negative')}
              className={`p-2 rounded-lg transition ${
                localFeedback === 'negative'
                  ? 'bg-red-100 text-red-600'
                  : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
              }`}
              aria-label="Thumbs down"
            >
              <ThumbsDown className="w-4 h-4" />
            </button>
          </div>
        )}
      </div>
    </div>
  );
}

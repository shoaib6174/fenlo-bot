'use client'

import { Message } from '@/lib/chat'
import { cn } from '@/lib/utils'
import { format } from 'date-fns'
import ReactMarkdown from 'react-markdown'
import { ThumbsUp, ThumbsDown } from 'lucide-react'
import { BookingCard } from './BookingCard'

interface MessageBubbleProps {
  message: Message
  onFeedback?: (messageId: string, feedback: 'positive' | 'negative') => void
}

export function MessageBubble({ message, onFeedback }: MessageBubbleProps) {
  const isUser = message.role === 'user'
  const timestamp = format(new Date(message.created_at), 'HH:mm')

  return (
    <div
      className={cn(
        'flex w-full gap-3 px-4 py-3',
        isUser ? 'justify-end' : 'justify-start'
      )}
    >
      <div
        className={cn(
          'flex flex-col gap-2 max-w-[70%]',
          isUser && 'items-end'
        )}
      >
        <div
          className={cn(
            'rounded-2xl px-4 py-3',
            isUser
              ? 'bg-blue-600 text-white'
              : 'bg-gray-100 text-gray-900'
          )}
        >
          <div className="prose prose-sm max-w-none">
            {isUser ? (
              <p className="m-0 whitespace-pre-wrap">{message.content}</p>
            ) : (
              <ReactMarkdown
                components={{
                  p: ({ children }) => <p className="m-0 mb-2 last:mb-0">{children}</p>,
                  a: ({ href, children }) => (
                    <a
                      href={href}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-blue-600 hover:underline"
                    >
                      {children}
                    </a>
                  ),
                  code: ({ children, className }) => {
                    const isInline = !className
                    return isInline ? (
                      <code className="bg-gray-200 px-1 py-0.5 rounded text-sm">
                        {children}
                      </code>
                    ) : (
                      <code className="block bg-gray-200 p-2 rounded text-sm overflow-x-auto">
                        {children}
                      </code>
                    )
                  },
                }}
              >
                {message.content}
              </ReactMarkdown>
            )}
          </div>

          {/* Citations */}
          {message.metadata?.citations && message.metadata.citations.length > 0 && (
            <div className="mt-3 pt-3 border-t border-gray-300">
              <p className="text-xs font-semibold mb-1">Sources:</p>
              {message.metadata.citations.map((citation, idx) => (
                <div key={idx} className="text-xs text-gray-600 mb-1">
                  {citation.doc_name}
                  {citation.page_number && ` (p. ${citation.page_number})`}
                  {' '}•{' '}
                  <span className="italic">
                    {citation.chunk_text.substring(0, 80)}
                    {citation.chunk_text.length > 80 && '...'}
                  </span>
                </div>
              ))}
            </div>
          )}

          {/* Booking Card */}
          {message.metadata?.booking_config && (
            <BookingCard config={message.metadata.booking_config} />
          )}
        </div>

        {/* Timestamp and feedback */}
        <div className="flex items-center gap-2 px-2">
          <span className="text-xs text-gray-500">{timestamp}</span>

          {/* Feedback buttons for assistant messages */}
          {!isUser && onFeedback && (
            <div className="flex items-center gap-1">
              <button
                onClick={() => onFeedback(message.id, 'positive')}
                className={cn(
                  'p-1 rounded hover:bg-gray-200 transition-colors',
                  message.feedback === 'positive' && 'bg-green-100 text-green-600'
                )}
                aria-label="Thumbs up"
              >
                <ThumbsUp size={14} />
              </button>
              <button
                onClick={() => onFeedback(message.id, 'negative')}
                className={cn(
                  'p-1 rounded hover:bg-gray-200 transition-colors',
                  message.feedback === 'negative' && 'bg-red-100 text-red-600'
                )}
                aria-label="Thumbs down"
              >
                <ThumbsDown size={14} />
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

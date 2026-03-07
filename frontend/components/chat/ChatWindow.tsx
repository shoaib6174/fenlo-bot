'use client'

import { useEffect, useRef } from 'react'
import { useChat } from '@/hooks/useChat'
import { MessageBubble } from './MessageBubble'
import { ChatInput } from './ChatInput'
import { TypingIndicator } from './TypingIndicator'
import { ConversationSidebar } from './ConversationSidebar'
import { cn } from '@/lib/utils'
import { MessageSquare } from 'lucide-react'

interface ChatWindowProps {
  initialConversationId?: string
  showSidebar?: boolean
}

export function ChatWindow({ initialConversationId, showSidebar = true }: ChatWindowProps) {
  const {
    messages,
    conversations,
    isTyping,
    streamingContent,
    currentConversationId,
    setCurrentConversationId,
    sendMessage,
    submitFeedback,
  } = useChat({
    conversationId: initialConversationId,
    onError: (error) => {
      console.error('Chat error:', error)
      // TODO: Show error toast
    },
  })

  const messagesEndRef = useRef<HTMLDivElement>(null)

  // Auto-scroll to bottom on new messages
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, isTyping, streamingContent])

  const handleNewConversation = () => {
    setCurrentConversationId(undefined)
  }

  const handleSelectConversation = (conversationId: string) => {
    setCurrentConversationId(conversationId)
  }

  return (
    <div className="flex h-screen bg-gray-50">
      {/* Sidebar */}
      {showSidebar && (
        <div className="w-80 flex-shrink-0">
          <ConversationSidebar
            conversations={conversations}
            currentConversationId={currentConversationId}
            onSelectConversation={handleSelectConversation}
            onNewConversation={handleNewConversation}
          />
        </div>
      )}

      {/* Main chat area */}
      <div className="flex-1 flex flex-col">
        {/* Messages */}
        <div className="flex-1 overflow-y-auto">
          {messages.length === 0 && !isTyping ? (
            <div className="flex flex-col items-center justify-center h-full text-gray-500 p-8">
              <MessageSquare size={64} className="mb-4 opacity-30" />
              <h2 className="text-2xl font-semibold mb-2">Start a conversation</h2>
              <p className="text-center text-sm max-w-md">
                Ask me anything! I&apos;m here to help answer your questions.
              </p>
            </div>
          ) : (
            <div className="py-4">
              {messages.map((message) => (
                <MessageBubble
                  key={message.id}
                  message={message}
                  onFeedback={submitFeedback}
                />
              ))}

              {/* Streaming content */}
              {streamingContent && (
                <div className="flex w-full gap-3 px-4 py-3">
                  <div className="flex flex-col gap-2 max-w-[70%]">
                    <div className="rounded-2xl px-4 py-3 bg-gray-100 text-gray-900">
                      <div className="prose prose-sm max-w-none">
                        <p className="m-0 whitespace-pre-wrap">{streamingContent}</p>
                      </div>
                    </div>
                  </div>
                </div>
              )}

              {/* Typing indicator */}
              {isTyping && !streamingContent && <TypingIndicator />}

              <div ref={messagesEndRef} />
            </div>
          )}
        </div>

        {/* Input */}
        <ChatInput
          onSend={sendMessage}
          disabled={isTyping}
          placeholder={isTyping ? 'Waiting for response...' : 'Type a message...'}
        />
      </div>
    </div>
  )
}

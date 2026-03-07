'use client'

import { Conversation } from '@/lib/chat'
import { cn } from '@/lib/utils'
import { format } from 'date-fns'
import { MessageSquare, Plus, Search } from 'lucide-react'
import { useState } from 'react'

interface ConversationSidebarProps {
  conversations: Conversation[]
  currentConversationId?: string
  onSelectConversation: (conversationId: string) => void
  onNewConversation: () => void
}

export function ConversationSidebar({
  conversations,
  currentConversationId,
  onSelectConversation,
  onNewConversation,
}: ConversationSidebarProps) {
  const [searchQuery, setSearchQuery] = useState('')

  const filteredConversations = conversations.filter((conv) => {
    if (!searchQuery) return true
    return (
      conv.title?.toLowerCase().includes(searchQuery.toLowerCase()) ||
      conv.id.toLowerCase().includes(searchQuery.toLowerCase())
    )
  })

  const getLeadScoreBadge = (score?: number) => {
    if (!score) return null
    if (score >= 61) return { label: 'Hot', color: 'bg-red-500' }
    if (score >= 31) return { label: 'Warm', color: 'bg-yellow-500' }
    return { label: 'Cold', color: 'bg-blue-500' }
  }

  return (
    <div className="flex flex-col h-full bg-white border-r border-gray-200">
      {/* Header */}
      <div className="p-4 border-b border-gray-200">
        <button
          onClick={onNewConversation}
          className={cn(
            'w-full flex items-center justify-center gap-2',
            'px-4 py-2 bg-blue-600 text-white rounded-lg',
            'hover:bg-blue-700 transition-colors'
          )}
        >
          <Plus size={20} />
          <span>New Chat</span>
        </button>
      </div>

      {/* Search */}
      <div className="p-4 border-b border-gray-200">
        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" size={18} />
          <input
            type="text"
            placeholder="Search conversations..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className={cn(
              'w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg',
              'focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent'
            )}
          />
        </div>
      </div>

      {/* Conversations list */}
      <div className="flex-1 overflow-y-auto">
        {filteredConversations.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full text-gray-500 p-4">
            <MessageSquare size={48} className="mb-2 opacity-50" />
            <p className="text-sm text-center">
              {searchQuery ? 'No conversations found' : 'No conversations yet'}
            </p>
          </div>
        ) : (
          <div className="space-y-1 p-2">
            {filteredConversations.map((conv) => {
              const leadBadge = getLeadScoreBadge(conv.lead_score)
              const isActive = conv.id === currentConversationId

              return (
                <button
                  key={conv.id}
                  onClick={() => onSelectConversation(conv.id)}
                  className={cn(
                    'w-full text-left p-3 rounded-lg transition-colors',
                    'hover:bg-gray-100',
                    isActive && 'bg-blue-50 border border-blue-200'
                  )}
                >
                  <div className="flex items-start justify-between gap-2 mb-1">
                    <div className="flex items-center gap-2 flex-1 min-w-0">
                      <MessageSquare size={16} className="text-gray-400 flex-shrink-0" />
                      <span className="text-sm font-medium truncate">
                        {conv.title || 'New conversation'}
                      </span>
                    </div>
                    {leadBadge && (
                      <span
                        className={cn(
                          'px-2 py-0.5 rounded-full text-xs font-semibold text-white flex-shrink-0',
                          leadBadge.color
                        )}
                      >
                        {leadBadge.label}
                      </span>
                    )}
                  </div>
                  <div className="flex items-center justify-between text-xs text-gray-500">
                    <span>{format(new Date(conv.started_at), 'MMM d, HH:mm')}</span>
                    {conv.message_count && (
                      <span>{conv.message_count} message{conv.message_count !== 1 && 's'}</span>
                    )}
                  </div>
                </button>
              )
            })}
          </div>
        )}
      </div>
    </div>
  )
}

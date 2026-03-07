'use client';

import { useState, useEffect, useCallback } from 'react';
import { useAuth } from '@/providers/auth';
import { useSkin } from '@/providers/skin';
import { publicApi, type PublicConversation, type PublicConversationDetail } from '@/lib/public-api';
import {
  Loader2,
  AlertCircle,
  MessageSquare,
  ArrowLeft,
  ChevronRight,
  User,
  Bot,
  Hash,
} from 'lucide-react';

export default function ConversationsPage() {
  const { user, isLoading: authLoading } = useAuth();
  const { isRagchat } = useSkin();

  const isGuest = isRagchat || (!authLoading && !user);
  const effectiveUser = isRagchat ? null : user;
  const demoToken = process.env.NEXT_PUBLIC_DEMO_SHARE_TOKEN;

  const [conversations, setConversations] = useState<PublicConversation[]>([]);
  const [selectedConv, setSelectedConv] = useState<PublicConversationDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [detailLoading, setDetailLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchConversations = useCallback(async () => {
    try {
      setLoading(true);
      if (isGuest) {
        if (!demoToken) {
          setError('Demo not configured');
          return;
        }
        const data = await publicApi.conversations(demoToken);
        setConversations(data);
      } else {
        const apiUrl = process.env.NEXT_PUBLIC_API_URL || '';
        const response = await fetch(`${apiUrl}/api/v1/chat/conversations?limit=50`, {
          credentials: 'include',
        });
        if (!response.ok) throw new Error('Failed to fetch conversations');
        const data = await response.json();
        // Normalize authenticated response to match public format
        const items = (data.conversations || data || []).map(

          (c: any) => ({
            id: c.id,
            title: c.title || c.first_message || null,
            channel: c.channel || 'web',
            status: c.status || 'active',
            message_count: c.message_count || 0,
            started_at: c.started_at || c.created_at || null,
            lead_score: c.lead_score || null,
          })
        );
        setConversations(items);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load conversations');
    } finally {
      setLoading(false);
    }
  }, [isGuest, demoToken]);

  const fetchConversationDetail = useCallback(
    async (id: string) => {
      try {
        setDetailLoading(true);
        if (isGuest && demoToken) {
          const data = await publicApi.conversation(demoToken, id);
          setSelectedConv(data);
        } else {
          const apiUrl = process.env.NEXT_PUBLIC_API_URL || '';
          const response = await fetch(
            `${apiUrl}/api/v1/chat/conversations/${id}/messages`,
            { credentials: 'include' }
          );
          if (!response.ok) throw new Error('Failed to fetch conversation');
          const data = await response.json();
          const conv = conversations.find((c) => c.id === id);
          setSelectedConv({
            id,
            title: conv?.title || null,
            channel: conv?.channel || 'web',
            status: conv?.status || 'active',
            started_at: conv?.started_at || null,
            lead_score: conv?.lead_score || null,
            messages: (data.messages || data || []).map(

              (m: any) => ({
                id: m.id,
                role: m.role,
                content: m.content,
                citations: m.citations || null,
                sentiment: m.sentiment || null,
                quality_score: m.quality_score || null,
                created_at: m.created_at || m.timestamp || null,
              })
            ),
          });
        }
      } catch (err) {
        console.error('Failed to fetch conversation detail:', err);
      } finally {
        setDetailLoading(false);
      }
    },
    [isGuest, demoToken, conversations]
  );

  useEffect(() => {
    if (!authLoading) {
      fetchConversations();
    }
  }, [authLoading, fetchConversations]);

  if (loading || authLoading) {
    return (
      <div className="flex items-center justify-center h-full">
        <Loader2 className="w-8 h-8 text-sky-500 animate-spin" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="bg-red-50 dark:bg-red-950/30 border border-red-200 dark:border-red-800 rounded-lg p-6 flex items-center gap-3">
          <AlertCircle className="w-6 h-6 text-red-600 dark:text-red-400" />
          <span className="text-red-800 dark:text-red-300">{error}</span>
        </div>
      </div>
    );
  }

  // Detail view
  if (selectedConv) {
    return (
      <div className="h-full bg-gray-50 dark:bg-gray-950">
        <div className="container mx-auto px-6 py-8 max-w-4xl">
          {/* Back button */}
          <button
            onClick={() => setSelectedConv(null)}
            className="flex items-center gap-2 text-sm text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white mb-6 transition"
          >
            <ArrowLeft className="w-4 h-4" />
            Back to Conversations
          </button>

          {/* Header */}
          <div className="mb-6">
            <h1 className="text-xl font-bold text-gray-900 dark:text-white mb-2">
              {selectedConv.title || 'Untitled Conversation'}
            </h1>
            <div className="flex items-center gap-3 text-sm text-gray-500 dark:text-gray-400">
              <ChannelBadge channel={selectedConv.channel} />
              <StatusBadge status={selectedConv.status} />
              {selectedConv.started_at && (
                <span>
                  {new Date(selectedConv.started_at).toLocaleDateString('en-US', {
                    month: 'short',
                    day: 'numeric',
                    year: 'numeric',
                    hour: 'numeric',
                    minute: '2-digit',
                  })}
                </span>
              )}
              {selectedConv.lead_score != null && selectedConv.lead_score > 0 && (
                <span className="px-2 py-0.5 bg-amber-100 dark:bg-amber-900/30 text-amber-700 dark:text-amber-400 text-xs rounded-full font-medium">
                  Lead: {selectedConv.lead_score}
                </span>
              )}
            </div>
          </div>

          {/* Messages */}
          {detailLoading ? (
            <div className="flex items-center justify-center py-12">
              <Loader2 className="w-6 h-6 text-sky-500 animate-spin" />
            </div>
          ) : (
            <div className="space-y-4">
              {selectedConv.messages.map((msg) => (
                <div
                  key={msg.id}
                  className={`flex gap-3 ${msg.role === 'user' ? '' : ''}`}
                >
                  {/* Avatar */}
                  <div
                    className={`w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 ${
                      msg.role === 'user'
                        ? 'bg-gray-200 dark:bg-gray-700'
                        : 'bg-sky-100 dark:bg-sky-900/40'
                    }`}
                  >
                    {msg.role === 'user' ? (
                      <User className="w-4 h-4 text-gray-600 dark:text-gray-300" />
                    ) : (
                      <Bot className="w-4 h-4 text-sky-600 dark:text-sky-400" />
                    )}
                  </div>

                  {/* Content */}
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      <span className="text-sm font-medium text-gray-900 dark:text-white">
                        {msg.role === 'user' ? 'User' : 'Assistant'}
                      </span>
                      {msg.created_at && (
                        <span className="text-xs text-gray-400 dark:text-gray-500">
                          {new Date(msg.created_at).toLocaleTimeString('en-US', {
                            hour: 'numeric',
                            minute: '2-digit',
                          })}
                        </span>
                      )}
                      {msg.sentiment && (
                        <span
                          className={`text-xs px-1.5 py-0.5 rounded font-medium ${
                            msg.sentiment === 'positive'
                              ? 'bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-400'
                              : msg.sentiment === 'negative'
                              ? 'bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-400'
                              : 'bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-400'
                          }`}
                        >
                          {msg.sentiment}
                        </span>
                      )}
                      {msg.quality_score != null && (
                        <span className="text-xs text-gray-400 dark:text-gray-500">
                          Q: {Math.round(msg.quality_score * 100)}%
                        </span>
                      )}
                    </div>
                    <div className="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-700 rounded-lg p-3">
                      <p className="text-sm text-gray-800 dark:text-gray-200 whitespace-pre-wrap">
                        {msg.content}
                      </p>
                      {msg.citations && msg.citations.length > 0 && (
                        <div className="mt-2 pt-2 border-t border-gray-100 dark:border-gray-800">
                          <p className="text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">
                            Sources:
                          </p>
                          {msg.citations.map((cite, i) => (
                            <p
                              key={i}
                              className="text-xs text-gray-400 dark:text-gray-500 truncate"
                            >
                              [{i + 1}] {cite.doc_name}
                              {cite.page_number ? ` (p.${cite.page_number})` : ''}
                            </p>
                          ))}
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              ))}

              {selectedConv.messages.length === 0 && (
                <div className="text-center py-12">
                  <MessageSquare className="w-12 h-12 text-gray-300 dark:text-gray-600 mx-auto mb-3" />
                  <p className="text-gray-500 dark:text-gray-400">No messages in this conversation</p>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    );
  }

  // List view
  return (
    <div className="h-full bg-gray-50 dark:bg-gray-950">
      <div className="container mx-auto px-6 py-8 max-w-4xl">
        <div className="mb-6">
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white mb-1">
            Conversations
          </h1>
          <p className="text-sm text-gray-500 dark:text-gray-400">
            {isGuest
              ? 'Browse real conversations handled by this AI chatbot.'
              : 'View all conversations across channels.'}
          </p>
        </div>

        {conversations.length === 0 ? (
          <div className="text-center py-16">
            <MessageSquare className="w-16 h-16 text-gray-300 dark:text-gray-600 mx-auto mb-4" />
            <h2 className="text-lg font-semibold text-gray-700 dark:text-gray-300 mb-1">
              No Conversations Yet
            </h2>
            <p className="text-gray-500 dark:text-gray-400">
              Conversations will appear here once users start chatting.
            </p>
          </div>
        ) : (
          <div className="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-700 rounded-xl divide-y divide-gray-100 dark:divide-gray-800">
            {conversations.map((conv) => (
              <button
                key={conv.id}
                onClick={() => fetchConversationDetail(conv.id)}
                className="w-full flex items-center gap-4 px-5 py-4 text-left hover:bg-gray-50 dark:hover:bg-gray-800/50 transition group"
              >
                {/* Icon */}
                <div className="w-10 h-10 rounded-full bg-sky-50 dark:bg-sky-900/30 flex items-center justify-center flex-shrink-0">
                  <MessageSquare className="w-5 h-5 text-sky-500" />
                </div>

                {/* Info */}
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1">
                    <h3 className="text-sm font-medium text-gray-900 dark:text-white truncate">
                      {conv.title || 'Untitled Conversation'}
                    </h3>
                  </div>
                  <div className="flex items-center gap-3 text-xs text-gray-500 dark:text-gray-400">
                    <ChannelBadge channel={conv.channel} />
                    <StatusBadge status={conv.status} />
                    <span className="flex items-center gap-1">
                      <Hash className="w-3 h-3" />
                      {conv.message_count} msgs
                    </span>
                    {conv.started_at && (
                      <span>
                        {new Date(conv.started_at).toLocaleDateString('en-US', {
                          month: 'short',
                          day: 'numeric',
                          hour: 'numeric',
                          minute: '2-digit',
                        })}
                      </span>
                    )}
                    {conv.lead_score != null && conv.lead_score > 0 && (
                      <span className="px-1.5 py-0.5 bg-amber-100 dark:bg-amber-900/30 text-amber-700 dark:text-amber-400 rounded text-xs font-medium">
                        Lead: {conv.lead_score}
                      </span>
                    )}
                  </div>
                </div>

                {/* Arrow */}
                <ChevronRight className="w-4 h-4 text-gray-400 dark:text-gray-500 group-hover:text-gray-600 dark:group-hover:text-gray-300 flex-shrink-0 transition" />
              </button>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

function ChannelBadge({ channel }: { channel: string }) {
  const colors: Record<string, string> = {
    web: 'bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-400',
    widget: 'bg-purple-100 dark:bg-purple-900/30 text-purple-700 dark:text-purple-400',
    whatsapp: 'bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-400',
    telegram: 'bg-sky-100 dark:bg-sky-900/30 text-sky-700 dark:text-sky-400',
    voice: 'bg-orange-100 dark:bg-orange-900/30 text-orange-700 dark:text-orange-400',
  };
  return (
    <span className={`px-1.5 py-0.5 rounded text-xs font-medium ${colors[channel] || 'bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-400'}`}>
      {channel}
    </span>
  );
}

function StatusBadge({ status }: { status: string }) {
  const colors: Record<string, string> = {
    active: 'bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-400',
    escalated: 'bg-amber-100 dark:bg-amber-900/30 text-amber-700 dark:text-amber-400',
    closed: 'bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-400',
  };
  return (
    <span className={`px-1.5 py-0.5 rounded text-xs font-medium ${colors[status] || 'bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-400'}`}>
      {status}
    </span>
  );
}

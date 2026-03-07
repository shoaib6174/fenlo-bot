'use client'

import { useState, useEffect, useRef, useCallback } from 'react'
import { Message, Conversation, WSMessage } from '@/lib/chat'

const API_BASE = process.env.NEXT_PUBLIC_API_URL || ''
const WS_BASE = API_BASE.replace(/^http/, 'ws')

interface UseChatOptions {
  conversationId?: string
  onMessage?: (message: Message) => void
  onError?: (error: Error) => void
}

export function useChat({ conversationId, onMessage, onError }: UseChatOptions = {}) {
  const [messages, setMessages] = useState<Message[]>([])
  const [isConnected, setIsConnected] = useState(false)
  const [isTyping, setIsTyping] = useState(false)
  const [streamingContent, setStreamingContent] = useState('')
  const [conversations, setConversations] = useState<Conversation[]>([])
  const [currentConversationId, setCurrentConversationId] = useState(conversationId)

  const wsRef = useRef<WebSocket | null>(null)
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | undefined>(undefined)
  const reconnectAttemptsRef = useRef(0)
  const streamingContentRef = useRef('')
  const MAX_RECONNECT_ATTEMPTS = 5
  const RECONNECT_DELAY = 2000

  // Fetch WS token
  const fetchWSToken = async (): Promise<string> => {
    const response = await fetch(`${API_BASE}/api/v1/auth/ws-token`, {
      credentials: 'include',
    })
    if (!response.ok) {
      throw new Error('Failed to fetch WebSocket token')
    }
    const data = await response.json()
    return data.access_token || data.token
  }

  // Connect to WebSocket
  const connect = useCallback(async () => {
    if (!currentConversationId) return

    try {
      const token = await fetchWSToken()
      const ws = new WebSocket(`${WS_BASE}/api/v1/chat/stream?token=${token}&conversation_id=${currentConversationId}`)

      ws.onopen = () => {
        setIsConnected(true)
        reconnectAttemptsRef.current = 0
      }

      ws.onmessage = (event) => {
        try {
          const message: WSMessage = JSON.parse(event.data)

          switch (message.type) {
            case 'token': {
              const tokenText = typeof message.data === 'string' ? message.data : message.data?.token || ''
              streamingContentRef.current += tokenText
              setStreamingContent((prev) => prev + tokenText)
              break
            }

            case 'typing':
              setIsTyping(typeof message.data === 'boolean' ? message.data : message.data?.is_typing ?? false)
              break

            case 'done':
              setIsTyping(false)
              // Build assistant message from accumulated streaming content
              if (message.data) {
                const doneData = message.data
                const newMessage: Message = {
                  id: doneData.message_id || `resp-${Date.now()}`,
                  conversation_id: doneData.conversation_id || currentConversationId || '',
                  role: 'assistant',
                  content: streamingContentRef.current,
                  created_at: new Date().toISOString(),
                  metadata: {
                    sentiment: doneData.sentiment,
                    quality_score: doneData.quality_score,
                    intent: doneData.intent,
                    citations: doneData.citations,
                  },
                }
                setMessages((prev) => [...prev, newMessage])
                onMessage?.(newMessage)

                // Update conversation ID if this was a new conversation
                if (doneData.conversation_id && !currentConversationId) {
                  setCurrentConversationId(doneData.conversation_id)
                }
              }
              streamingContentRef.current = ''
              setStreamingContent('')
              break

            case 'error':
              setIsTyping(false)
              streamingContentRef.current = ''
              setStreamingContent('')
              onError?.(new Error(message.data?.message || 'An error occurred'))
              break
          }
        } catch (error) {
          console.error('Failed to parse WebSocket message:', error)
        }
      }

      ws.onerror = (error) => {
        console.error('WebSocket error:', error)
        onError?.(new Error('WebSocket connection error'))
      }

      ws.onclose = () => {
        setIsConnected(false)

        // Attempt reconnection
        if (reconnectAttemptsRef.current < MAX_RECONNECT_ATTEMPTS) {
          reconnectAttemptsRef.current += 1
          reconnectTimeoutRef.current = setTimeout(() => {
            connect()
          }, RECONNECT_DELAY * reconnectAttemptsRef.current)
        }
      }

      wsRef.current = ws
    } catch (error) {
      onError?.(error as Error)
    }
  }, [currentConversationId, onMessage, onError])

  // Disconnect WebSocket
  const disconnect = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current)
    }
    if (wsRef.current) {
      wsRef.current.close()
      wsRef.current = null
    }
    setIsConnected(false)
  }, [])

  // Send message
  const sendMessage = useCallback(async (content: string) => {
    if (!currentConversationId) {
      // Create new conversation via HTTP
      const response = await fetch(`${API_BASE}/api/v1/chat/send`, {
        method: 'POST',
        credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: content }),
      })

      if (!response.ok) {
        throw new Error('Failed to send message')
      }

      const data = await response.json()
      setCurrentConversationId(data.conversation_id)
      setMessages([
        {
          id: `user-${Date.now()}`,
          conversation_id: data.conversation_id,
          role: 'user',
          content,
          created_at: new Date().toISOString(),
        },
        {
          id: `resp-${Date.now()}`,
          conversation_id: data.conversation_id,
          role: 'assistant',
          content: data.assistant_message,
          created_at: new Date().toISOString(),
          metadata: data.metadata ? {
            sentiment: data.metadata.sentiment,
            quality_score: data.metadata.quality_score,
            intent: data.metadata.intent,
            citations: data.metadata.citations,
          } : undefined,
        },
      ])
      return
    }

    // Add user message optimistically
    const userMessage: Message = {
      id: `temp-${Date.now()}`,
      conversation_id: currentConversationId,
      role: 'user',
      content,
      created_at: new Date().toISOString(),
    }
    setMessages((prev) => [...prev, userMessage])

    // Send via WebSocket
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ message: content }))
    } else {
      // Fallback to HTTP
      const response = await fetch(`${API_BASE}/api/v1/chat/send`, {
        method: 'POST',
        credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: content, conversation_id: currentConversationId }),
      })

      if (!response.ok) {
        throw new Error('Failed to send message')
      }

      const data = await response.json()
      const assistantMsg: Message = {
        id: `resp-${Date.now()}`,
        conversation_id: data.conversation_id,
        role: 'assistant',
        content: data.assistant_message,
        created_at: new Date().toISOString(),
        metadata: data.metadata ? {
          sentiment: data.metadata.sentiment,
          quality_score: data.metadata.quality_score,
          intent: data.metadata.intent,
          citations: data.metadata.citations,
        } : undefined,
      }
      setMessages((prev) => [...prev, assistantMsg])
    }
  }, [currentConversationId])

  // Fetch conversations
  const fetchConversations = useCallback(async () => {
    try {
      const response = await fetch(`${API_BASE}/api/v1/chat/conversations`, {
        credentials: 'include',
      })
      if (response.ok) {
        const data = await response.json()
        setConversations(data.conversations || data)
      }
    } catch (error) {
      console.error('Failed to fetch conversations:', error)
    }
  }, [])

  // Fetch messages for a conversation
  const fetchMessages = useCallback(async (convId: string) => {
    try {
      const response = await fetch(`${API_BASE}/api/v1/chat/conversations/${convId}/messages`, {
        credentials: 'include',
      })
      if (response.ok) {
        const data = await response.json()
        const rawMessages = data.messages || data
        // Map backend message format to frontend Message type with citations
        const mapped: Message[] = rawMessages.map((msg: any) => ({
          id: msg.id,
          conversation_id: convId,
          role: msg.role,
          content: msg.content,
          created_at: msg.created_at,
          feedback: msg.feedback,
          metadata: {
            sentiment: msg.sentiment,
            quality_score: msg.quality_score,
            intent: msg.intent,
            citations: msg.citations,
          },
        }))
        setMessages(mapped)
      }
    } catch (error) {
      console.error('Failed to fetch messages:', error)
    }
  }, [])

  // Submit feedback
  const submitFeedback = useCallback(async (messageId: string, feedback: 'positive' | 'negative') => {
    try {
      const response = await fetch(`${API_BASE}/api/v1/chat/messages/${messageId}/feedback`, {
        method: 'POST',
        credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ feedback }),
      })

      if (response.ok) {
        // Update local message
        setMessages((prev) =>
          prev.map((msg) =>
            msg.id === messageId ? { ...msg, feedback } : msg
          )
        )
      }
    } catch (error) {
      console.error('Failed to submit feedback:', error)
    }
  }, [])

  // Connect/disconnect on conversation change
  useEffect(() => {
    if (currentConversationId) {
      reconnectAttemptsRef.current = 0
      connect()
      fetchMessages(currentConversationId)
    }

    return () => disconnect()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [currentConversationId])

  // Fetch conversations on mount
  useEffect(() => {
    fetchConversations()
  }, [fetchConversations])

  return {
    messages,
    conversations,
    isConnected,
    isTyping,
    streamingContent,
    currentConversationId,
    setCurrentConversationId,
    sendMessage,
    submitFeedback,
    fetchConversations,
  }
}

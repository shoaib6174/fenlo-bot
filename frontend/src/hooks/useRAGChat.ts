'use client';

import { useState, useEffect, useRef, useCallback } from 'react';
import type { RAGMessage } from '@/types/rag';

interface UseRAGChatOptions {
  conversationId?: string;
  kbId?: string;
}

interface WSMessage {
  type: 'token' | 'typing' | 'done' | 'error' | 'citation' | 'quality_score';
  content?: string;
  citations?: any[];
  error?: string;
  sentiment?: 'positive' | 'neutral' | 'negative';
  intent?: string;
  quality_score?: number;
}

export type ConnectionState = 'connecting' | 'connected' | 'disconnected' | 'reconnecting';

const MAX_RECONNECT_ATTEMPTS = 10;
const BASE_RECONNECT_DELAY = 1000; // 1 second
const MAX_RECONNECT_DELAY = 30000; // 30 seconds

/** Calculate exponential backoff delay with jitter */
function getBackoffDelay(attempt: number): number {
  const exponentialDelay = Math.min(
    BASE_RECONNECT_DELAY * Math.pow(2, attempt),
    MAX_RECONNECT_DELAY
  );
  // Add ±25% jitter to prevent thundering herd
  const jitter = exponentialDelay * 0.25 * (Math.random() * 2 - 1);
  return Math.max(0, exponentialDelay + jitter);
}

export function useRAGChat({ conversationId, kbId }: UseRAGChatOptions = {}) {
  const [messages, setMessages] = useState<RAGMessage[]>([]);
  const [connectionState, setConnectionState] = useState<ConnectionState>('disconnected');
  const [isTyping, setIsTyping] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const currentAssistantMessageRef = useRef<string>('');
  const currentCitationsRef = useRef<any[]>([]);
  const reconnectAttemptsRef = useRef(0);
  const reconnectTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const connect = useCallback(async () => {
    try {
      setConnectionState(
        reconnectAttemptsRef.current > 0 ? 'reconnecting' : 'connecting'
      );

      // Get WebSocket token from backend
      const response = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL || ""}/api/v1/auth/ws-token`,
        {
          credentials: 'include',
        }
      );

      if (!response.ok) {
        throw new Error('Failed to get WebSocket token');
      }

      const { ws_token } = await response.json();

      // Construct WebSocket URL with query parameters
      const wsUrl = new URL(
        `${process.env.NEXT_PUBLIC_WS_URL}/api/v1/chat/stream`,
        process.env.NEXT_PUBLIC_WS_URL
      );
      wsUrl.searchParams.set('token', ws_token);
      if (conversationId) {
        wsUrl.searchParams.set('conversation_id', conversationId);
      }
      if (kbId) {
        wsUrl.searchParams.set('kb_id', kbId);
      }

      const ws = new WebSocket(wsUrl.toString());

      ws.onopen = () => {
        setConnectionState('connected');
        setError(null);
        reconnectAttemptsRef.current = 0; // Reset on successful connection
      };

      ws.onmessage = (event) => {
        const data: WSMessage = JSON.parse(event.data);

        switch (data.type) {
          case 'typing':
            setIsTyping(true);
            break;

          case 'token':
            if (data.content) {
              currentAssistantMessageRef.current += data.content;
            }
            break;

          case 'citation':
            if (data.citations) {
              currentCitationsRef.current = data.citations;
            }
            break;

          case 'done':
            setIsTyping(false);
            if (currentAssistantMessageRef.current) {
              const newMessage: RAGMessage = {
                id: `msg-${Date.now()}`,
                role: 'assistant',
                content: currentAssistantMessageRef.current,
                timestamp: new Date().toISOString(),
                citations: currentCitationsRef.current.length > 0
                  ? currentCitationsRef.current
                  : undefined,
                sentiment: data.sentiment || null,
                intent: data.intent || null,
                quality_score: data.quality_score ?? null,
              };
              setMessages((prev) => [...prev, newMessage]);
              currentAssistantMessageRef.current = '';
              currentCitationsRef.current = [];
            }
            break;

          case 'error':
            setIsTyping(false);
            setError(data.error || 'An error occurred');
            currentAssistantMessageRef.current = '';
            currentCitationsRef.current = [];
            break;
        }
      };

      ws.onerror = () => {
        setError('Connection error');
        setConnectionState('disconnected');
      };

      ws.onclose = () => {
        setConnectionState('disconnected');

        // Attempt reconnect with exponential backoff
        if (
          wsRef.current === ws &&
          reconnectAttemptsRef.current < MAX_RECONNECT_ATTEMPTS
        ) {
          const delay = getBackoffDelay(reconnectAttemptsRef.current);
          reconnectAttemptsRef.current += 1;
          reconnectTimeoutRef.current = setTimeout(() => {
            connect();
          }, delay);
        } else if (reconnectAttemptsRef.current >= MAX_RECONNECT_ATTEMPTS) {
          setError('Connection lost. Please refresh the page.');
        }
      };

      wsRef.current = ws;
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Connection failed');
      setConnectionState('disconnected');
    }
  }, [conversationId, kbId]);

  useEffect(() => {
    connect();

    return () => {
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
        reconnectTimeoutRef.current = null;
      }
      if (wsRef.current) {
        wsRef.current.close();
        wsRef.current = null;
      }
    };
  }, [connect]);

  const sendMessage = useCallback(
    (content: string) => {
      if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) {
        setError('Not connected');
        return;
      }

      // Add user message to UI
      const userMessage: RAGMessage = {
        id: `msg-${Date.now()}`,
        role: 'user',
        content,
        timestamp: new Date().toISOString(),
      };
      setMessages((prev) => [...prev, userMessage]);

      // Send to WebSocket
      wsRef.current.send(
        JSON.stringify({
          message: content,
          conversation_id: conversationId,
          kb_id: kbId,
        })
      );

      setError(null);
    },
    [conversationId, kbId]
  );

  const sendFeedback = useCallback(
    async (messageId: string, feedback: 'positive' | 'negative') => {
      try {
        await fetch(
          `${process.env.NEXT_PUBLIC_API_URL || ""}/api/v1/messages/${messageId}/feedback`,
          {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            credentials: 'include',
            body: JSON.stringify({ feedback }),
          }
        );

        // Update local message
        setMessages((prev) =>
          prev.map((msg) =>
            msg.id === messageId ? { ...msg, feedback } : msg
          )
        );
      } catch (err) {
        console.error('Failed to send feedback:', err);
      }
    },
    []
  );

  return {
    messages,
    isConnected: connectionState === 'connected',
    connectionState,
    isTyping,
    error,
    sendMessage,
    sendFeedback,
  };
}

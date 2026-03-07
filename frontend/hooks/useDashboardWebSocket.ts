"use client";

import { useCallback, useEffect, useRef, useState } from "react";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "";
const WS_BASE = API_BASE.replace(/^http/, "ws");

export type ConnectionState = "connecting" | "connected" | "disconnected" | "reconnecting";

export interface DashboardEvent {
  type: "message" | "conversation_started" | "escalation" | "metrics" | "metrics_update";
  priority?: number;
  conversation_id?: string;
  preview?: string;
  sentiment?: string;
  quality_score?: number;
  intent?: string;
  channel?: string;
  reason?: string;
  active_conversations?: number;
  messages_last_minute?: number;
}

export interface LiveMetrics {
  activeConversations: number;
  pendingEscalations: number;
  messagesPerMinute: number;
}

export interface FeedMessage {
  id: string;
  conversationId: string;
  preview: string;
  sentiment: string | null;
  timestamp: Date;
}

const MAX_FEED = 20;
const MAX_RECONNECT = 10;
const INITIAL_DELAY = 1000;
const MAX_DELAY = 30000;

function backoffDelay(attempt: number): number {
  const base = Math.min(INITIAL_DELAY * Math.pow(2, attempt), MAX_DELAY);
  const jitter = base * 0.25 * (Math.random() * 2 - 1); // +/- 25%
  return base + jitter;
}

export function useDashboardWebSocket() {
  const [connectionState, setConnectionState] = useState<ConnectionState>("disconnected");
  const [metrics, setMetrics] = useState<LiveMetrics>({
    activeConversations: 0,
    pendingEscalations: 0,
    messagesPerMinute: 0,
  });
  const [feed, setFeed] = useState<FeedMessage[]>([]);

  const wsRef = useRef<WebSocket | null>(null);
  const attemptRef = useRef(0);
  const reconnectTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const mountedRef = useRef(true);
  const messageTimestamps = useRef<number[]>([]);

  const fetchWSToken = useCallback(async (): Promise<string> => {
    const response = await fetch(`${API_BASE}/api/v1/auth/ws-token`, {
      credentials: "include",
    });
    if (!response.ok) throw new Error("Failed to fetch WebSocket token");
    const data = await response.json();
    return data.token;
  }, []);

  const processEvent = useCallback((event: DashboardEvent) => {
    if (event.type === "metrics" || event.type === "metrics_update") {
      setMetrics((prev) => ({
        ...prev,
        activeConversations: event.active_conversations ?? prev.activeConversations,
        messagesPerMinute: event.messages_last_minute ?? prev.messagesPerMinute,
      }));
    } else if (event.type === "message") {
      // Track messages/minute
      const now = Date.now();
      messageTimestamps.current.push(now);
      messageTimestamps.current = messageTimestamps.current.filter(
        (t) => now - t < 60000
      );
      setMetrics((prev) => ({
        ...prev,
        messagesPerMinute: messageTimestamps.current.length,
      }));

      // Add to feed
      if (event.preview) {
        const msg: FeedMessage = {
          id: `${event.conversation_id}-${now}`,
          conversationId: event.conversation_id || "",
          preview: event.preview,
          sentiment: event.sentiment || null,
          timestamp: new Date(),
        };
        setFeed((prev) => [msg, ...prev].slice(0, MAX_FEED));
      }
    } else if (event.type === "conversation_started") {
      setMetrics((prev) => ({
        ...prev,
        activeConversations: prev.activeConversations + 1,
      }));
    } else if (event.type === "escalation") {
      setMetrics((prev) => ({
        ...prev,
        pendingEscalations: prev.pendingEscalations + 1,
      }));
    }
  }, []);

  const connect = useCallback(async () => {
    if (!mountedRef.current) return;

    setConnectionState(attemptRef.current > 0 ? "reconnecting" : "connecting");

    try {
      const token = await fetchWSToken();
      const ws = new WebSocket(`${WS_BASE}/api/v1/dashboard/live?token=${token}`);

      ws.onopen = () => {
        if (!mountedRef.current) {
          ws.close();
          return;
        }
        attemptRef.current = 0;
        setConnectionState("connected");
      };

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data) as DashboardEvent;
          processEvent(data);
        } catch {
          // Ignore non-JSON messages (pong, etc.)
        }
      };

      ws.onclose = () => {
        if (!mountedRef.current) return;
        setConnectionState("disconnected");
        wsRef.current = null;

        if (attemptRef.current < MAX_RECONNECT) {
          const delay = backoffDelay(attemptRef.current);
          attemptRef.current += 1;
          reconnectTimerRef.current = setTimeout(() => {
            connect();
          }, delay);
        }
      };

      ws.onerror = () => {
        ws.close();
      };

      wsRef.current = ws;
    } catch {
      setConnectionState("disconnected");
      if (attemptRef.current < MAX_RECONNECT) {
        const delay = backoffDelay(attemptRef.current);
        attemptRef.current += 1;
        reconnectTimerRef.current = setTimeout(() => {
          connect();
        }, delay);
      }
    }
  }, [fetchWSToken, processEvent]);

  useEffect(() => {
    mountedRef.current = true;
    connect();

    // Ping keepalive every 25s
    const pingInterval = setInterval(() => {
      if (wsRef.current?.readyState === WebSocket.OPEN) {
        wsRef.current.send("ping");
      }
    }, 25000);

    return () => {
      mountedRef.current = false;
      clearInterval(pingInterval);
      if (reconnectTimerRef.current) {
        clearTimeout(reconnectTimerRef.current);
      }
      if (wsRef.current) {
        wsRef.current.close();
        wsRef.current = null;
      }
    };
  }, [connect]);

  return { connectionState, metrics, feed };
}

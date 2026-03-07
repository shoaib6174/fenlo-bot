/**
 * WebSocket Client with Reconnection
 *
 * Features:
 * - Exponential backoff (1s → 30s)
 * - ±25% jitter to prevent thundering herd
 * - Max 10 reconnection attempts
 * - HMAC authentication via query param
 * - Graceful degradation to SSE (TODO: Phase 5)
 */

export type ConnectionState = 'connecting' | 'connected' | 'disconnected' | 'reconnecting';

export interface WSMessage {
  type: 'message' | 'error' | 'status';
  content?: string;
  error?: string;
  conversationId?: string;
}

export interface WSClientConfig {
  url: string;
  hmac: string;
  hmacTimestamp?: number;
  workspaceId: string;
  onMessage: (message: WSMessage) => void;
  onStateChange: (state: ConnectionState) => void;
}

export class WSClient {
  private ws: WebSocket | null = null;
  private config: WSClientConfig;
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 10;
  private reconnectTimer: number | null = null;
  private state: ConnectionState = 'disconnected';
  private pingInterval: number | null = null;

  constructor(config: WSClientConfig) {
    this.config = config;
  }

  /**
   * Connect to WebSocket server with HMAC authentication
   */
  connect(): void {
    if (this.ws?.readyState === WebSocket.OPEN || this.ws?.readyState === WebSocket.CONNECTING) {
      return;
    }

    this.updateState('connecting');

    try {
      // Build WebSocket URL with HMAC auth
      const wsUrl = new URL(this.config.url);
      wsUrl.searchParams.set('hmac', this.config.hmac);
      wsUrl.searchParams.set('workspace_id', this.config.workspaceId);

      // Add HMAC timestamp if provided (from embed code)
      if (this.config.hmacTimestamp) {
        wsUrl.searchParams.set('hmac_timestamp', this.config.hmacTimestamp.toString());
      }

      this.ws = new WebSocket(wsUrl.toString());

      this.ws.onopen = this.handleOpen.bind(this);
      this.ws.onmessage = this.handleMessage.bind(this);
      this.ws.onerror = this.handleError.bind(this);
      this.ws.onclose = this.handleClose.bind(this);
    } catch (error) {
      console.error('[WSClient] Connection error:', error);
      this.scheduleReconnect();
    }
  }

  /**
   * Send message to server
   */
  send(message: string): boolean {
    if (this.ws?.readyState !== WebSocket.OPEN) {
      console.warn('[WSClient] Cannot send message: not connected');
      return false;
    }

    try {
      this.ws.send(JSON.stringify({ message }));
      return true;
    } catch (error) {
      console.error('[WSClient] Send error:', error);
      return false;
    }
  }

  /**
   * Disconnect and clean up
   */
  disconnect(): void {
    this.clearReconnectTimer();
    this.clearPingInterval();

    if (this.ws) {
      this.ws.onclose = null; // Prevent reconnection
      this.ws.close();
      this.ws = null;
    }

    this.updateState('disconnected');
  }

  /**
   * Get current connection state
   */
  getState(): ConnectionState {
    return this.state;
  }

  // --- Private Methods ---

  private handleOpen(): void {
    console.log('[WSClient] Connected');
    this.reconnectAttempts = 0;
    this.updateState('connected');
    this.startPingInterval();
  }

  private handleMessage(event: MessageEvent): void {
    try {
      const data = JSON.parse(event.data);
      this.config.onMessage(data);
    } catch (error) {
      console.error('[WSClient] Message parse error:', error);
    }
  }

  private handleError(event: Event): void {
    console.error('[WSClient] WebSocket error:', event);
  }

  private handleClose(event: CloseEvent): void {
    console.log('[WSClient] Disconnected:', event.code, event.reason);
    this.clearPingInterval();

    // Don't reconnect if closed cleanly
    if (event.code === 1000) {
      this.updateState('disconnected');
      return;
    }

    // Schedule reconnection
    this.scheduleReconnect();
  }

  private scheduleReconnect(): void {
    if (this.reconnectAttempts >= this.maxReconnectAttempts) {
      console.error('[WSClient] Max reconnection attempts reached');
      this.updateState('disconnected');
      return;
    }

    this.updateState('reconnecting');
    this.reconnectAttempts++;

    // Exponential backoff: 1s, 2s, 4s, 8s, 16s, 30s (capped)
    const baseDelay = Math.min(1000 * Math.pow(2, this.reconnectAttempts - 1), 30000);

    // Add ±25% jitter
    const jitter = baseDelay * 0.25 * (Math.random() * 2 - 1);
    const delay = Math.max(1000, baseDelay + jitter);

    console.log(
      `[WSClient] Reconnecting in ${(delay / 1000).toFixed(1)}s (attempt ${this.reconnectAttempts}/${this.maxReconnectAttempts})`
    );

    this.reconnectTimer = window.setTimeout(() => {
      this.connect();
    }, delay);
  }

  private clearReconnectTimer(): void {
    if (this.reconnectTimer !== null) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }
  }

  private startPingInterval(): void {
    // Send ping every 30 seconds to keep connection alive
    this.pingInterval = window.setInterval(() => {
      if (this.ws?.readyState === WebSocket.OPEN) {
        try {
          this.ws.send(JSON.stringify({ type: 'ping' }));
        } catch (error) {
          console.error('[WSClient] Ping error:', error);
        }
      }
    }, 30000);
  }

  private clearPingInterval(): void {
    if (this.pingInterval !== null) {
      clearInterval(this.pingInterval);
      this.pingInterval = null;
    }
  }

  private updateState(newState: ConnectionState): void {
    if (this.state !== newState) {
      this.state = newState;
      this.config.onStateChange(newState);
    }
  }
}

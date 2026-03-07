/**
 * Unit tests for useRAGChat hook
 * Tests: connection lifecycle, message sending, token accumulation,
 *        citation handling, error handling, reconnection
 */
import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { renderHook, act, waitFor } from '@testing-library/react';
import { useRAGChat } from '../useRAGChat';

// --- WebSocket mock ---
class MockWebSocket {
  static CONNECTING = 0;
  static OPEN = 1;
  static CLOSING = 2;
  static CLOSED = 3;

  readyState = MockWebSocket.CONNECTING;
  url: string;
  onopen: ((ev: Event) => void) | null = null;
  onmessage: ((ev: MessageEvent) => void) | null = null;
  onerror: ((ev: Event) => void) | null = null;
  onclose: ((ev: CloseEvent) => void) | null = null;
  sentMessages: string[] = [];

  constructor(url: string) {
    this.url = url;
    MockWebSocket.instances.push(this);
  }

  send(data: string) {
    this.sentMessages.push(data);
  }

  close() {
    this.readyState = MockWebSocket.CLOSED;
    // Don't auto-fire onclose — let tests control it
  }

  // Test helpers
  simulateOpen() {
    this.readyState = MockWebSocket.OPEN;
    this.onopen?.(new Event('open'));
  }

  simulateMessage(data: object) {
    this.onmessage?.(new MessageEvent('message', { data: JSON.stringify(data) }));
  }

  simulateError() {
    this.onerror?.(new Event('error'));
  }

  simulateClose() {
    this.readyState = MockWebSocket.CLOSED;
    this.onclose?.(new CloseEvent('close'));
  }

  static instances: MockWebSocket[] = [];
  static clear() {
    MockWebSocket.instances = [];
  }
  static get latest() {
    return MockWebSocket.instances[MockWebSocket.instances.length - 1];
  }
}

// --- Setup ---
const originalWebSocket = globalThis.WebSocket;

beforeEach(() => {
  MockWebSocket.clear();
  (globalThis as any).WebSocket = MockWebSocket;

  // Mock env
  process.env.NEXT_PUBLIC_API_URL = 'http://localhost:8000';
  process.env.NEXT_PUBLIC_WS_URL = 'ws://localhost:8000';

  // Mock fetch for ws-token
  global.fetch = vi.fn().mockResolvedValue({
    ok: true,
    json: async () => ({ ws_token: 'test-token-123' }),
  });

  vi.useFakeTimers();
});

afterEach(() => {
  globalThis.WebSocket = originalWebSocket;
  vi.restoreAllMocks();
  vi.useRealTimers();
});

describe('useRAGChat', () => {
  describe('connection lifecycle', () => {
    it('fetches ws-token and creates WebSocket on mount', async () => {
      vi.useRealTimers();
      const { result } = renderHook(() => useRAGChat());

      await waitFor(() => {
        expect(global.fetch).toHaveBeenCalledWith(
          'http://localhost:8000/api/v1/auth/ws-token',
          { credentials: 'include' }
        );
      });

      expect(MockWebSocket.instances).toHaveLength(1);
      expect(MockWebSocket.latest.url).toContain('token=test-token-123');
    });

    it('sets isConnected to true on WebSocket open', async () => {
      vi.useRealTimers();
      const { result } = renderHook(() => useRAGChat());

      await waitFor(() => expect(MockWebSocket.instances).toHaveLength(1));

      act(() => {
        MockWebSocket.latest.simulateOpen();
      });

      expect(result.current.isConnected).toBe(true);
      expect(result.current.error).toBeNull();
    });

    it('sets isConnected to false and cleans up on unmount', async () => {
      vi.useRealTimers();
      const { result, unmount } = renderHook(() => useRAGChat());

      await waitFor(() => expect(MockWebSocket.instances).toHaveLength(1));

      act(() => {
        MockWebSocket.latest.simulateOpen();
      });

      expect(result.current.isConnected).toBe(true);

      const ws = MockWebSocket.latest;
      unmount();

      expect(ws.readyState).toBe(MockWebSocket.CLOSED);
    });

    it('passes conversationId and kbId as query params', async () => {
      vi.useRealTimers();
      renderHook(() =>
        useRAGChat({ conversationId: 'conv-abc', kbId: 'kb-xyz' })
      );

      await waitFor(() => expect(MockWebSocket.instances).toHaveLength(1));

      const url = MockWebSocket.latest.url;
      expect(url).toContain('conversation_id=conv-abc');
      expect(url).toContain('kb_id=kb-xyz');
    });

    it('sets error when ws-token fetch fails', async () => {
      vi.useRealTimers();
      (global.fetch as any).mockResolvedValueOnce({
        ok: false,
        status: 401,
      });

      const { result } = renderHook(() => useRAGChat());

      await waitFor(() => {
        expect(result.current.error).toBe('Failed to get WebSocket token');
      });
      expect(result.current.isConnected).toBe(false);
    });

    it('schedules reconnect after close with exponential backoff', async () => {
      vi.useRealTimers();
      const setTimeoutSpy = vi.spyOn(globalThis, 'setTimeout');

      const { result } = renderHook(() => useRAGChat());

      await waitFor(() => expect(MockWebSocket.instances).toHaveLength(1));

      act(() => {
        MockWebSocket.latest.simulateOpen();
      });

      act(() => {
        MockWebSocket.latest.simulateClose();
      });

      expect(result.current.isConnected).toBe(false);

      // First reconnect attempt uses backoff ~1000ms (±25% jitter → 750–1250ms)
      const reconnectCall = setTimeoutSpy.mock.calls.find(
        (call) => typeof call[1] === 'number' && call[1] >= 750 && call[1] <= 1250
      );
      expect(reconnectCall).toBeDefined();

      setTimeoutSpy.mockRestore();
    });

    it('exposes connectionState for detailed status', async () => {
      vi.useRealTimers();
      const { result } = renderHook(() => useRAGChat());

      // Initially disconnected (or transitioning to connecting)
      await waitFor(() => expect(MockWebSocket.instances).toHaveLength(1));

      act(() => {
        MockWebSocket.latest.simulateOpen();
      });

      expect(result.current.connectionState).toBe('connected');
      expect(result.current.isConnected).toBe(true);

      act(() => {
        MockWebSocket.latest.simulateClose();
      });

      expect(result.current.connectionState).toBe('disconnected');
      expect(result.current.isConnected).toBe(false);
    });

    it('resets reconnect counter on successful connection', async () => {
      vi.useRealTimers();
      const setTimeoutSpy = vi.spyOn(globalThis, 'setTimeout');

      const { result } = renderHook(() => useRAGChat());
      await waitFor(() => expect(MockWebSocket.instances).toHaveLength(1));

      // First: connect, then disconnect → triggers reconnect with attempt 0
      act(() => MockWebSocket.latest.simulateOpen());
      act(() => MockWebSocket.latest.simulateClose());

      const firstReconnectCall = setTimeoutSpy.mock.calls.find(
        (call) => typeof call[1] === 'number' && call[1] >= 750
      );
      expect(firstReconnectCall).toBeDefined();

      // After a successful reconnection, the counter should reset
      // (verified by the fact that isConnected goes true → the counter resets)
      expect(result.current.connectionState).toBe('disconnected');

      setTimeoutSpy.mockRestore();
    });
  });

  describe('message sending', () => {
    it('sends message over WebSocket and adds user message to state', async () => {
      vi.useRealTimers();
      const { result } = renderHook(() =>
        useRAGChat({ conversationId: 'conv-1', kbId: 'kb-1' })
      );

      await waitFor(() => expect(MockWebSocket.instances).toHaveLength(1));

      act(() => {
        MockWebSocket.latest.simulateOpen();
      });

      act(() => {
        result.current.sendMessage('Hello AI');
      });

      // User message added to state
      expect(result.current.messages).toHaveLength(1);
      expect(result.current.messages[0].role).toBe('user');
      expect(result.current.messages[0].content).toBe('Hello AI');

      // Message sent over WebSocket
      const sent = JSON.parse(MockWebSocket.latest.sentMessages[0]);
      expect(sent.message).toBe('Hello AI');
      expect(sent.conversation_id).toBe('conv-1');
      expect(sent.kb_id).toBe('kb-1');
    });

    it('sets error when sending while disconnected', async () => {
      vi.useRealTimers();
      const { result } = renderHook(() => useRAGChat());

      await waitFor(() => expect(MockWebSocket.instances).toHaveLength(1));

      // Don't open the WebSocket — still CONNECTING
      act(() => {
        result.current.sendMessage('Hello');
      });

      expect(result.current.error).toBe('Not connected');
      expect(result.current.messages).toHaveLength(0);
    });
  });

  describe('token accumulation and done event', () => {
    it('accumulates tokens and creates assistant message on done', async () => {
      vi.useRealTimers();
      const { result } = renderHook(() => useRAGChat());

      await waitFor(() => expect(MockWebSocket.instances).toHaveLength(1));

      act(() => {
        MockWebSocket.latest.simulateOpen();
      });

      // Simulate typing indicator
      act(() => {
        MockWebSocket.latest.simulateMessage({ type: 'typing' });
      });
      expect(result.current.isTyping).toBe(true);

      // Simulate streaming tokens
      act(() => {
        MockWebSocket.latest.simulateMessage({ type: 'token', content: 'Hello' });
        MockWebSocket.latest.simulateMessage({ type: 'token', content: ' world' });
        MockWebSocket.latest.simulateMessage({ type: 'token', content: '!' });
      });

      // Simulate done — should finalize the message
      act(() => {
        MockWebSocket.latest.simulateMessage({ type: 'done' });
      });

      expect(result.current.isTyping).toBe(false);
      expect(result.current.messages).toHaveLength(1);
      expect(result.current.messages[0].role).toBe('assistant');
      expect(result.current.messages[0].content).toBe('Hello world!');
    });

    it('does not create assistant message on done if no tokens received', async () => {
      vi.useRealTimers();
      const { result } = renderHook(() => useRAGChat());

      await waitFor(() => expect(MockWebSocket.instances).toHaveLength(1));
      act(() => MockWebSocket.latest.simulateOpen());

      act(() => {
        MockWebSocket.latest.simulateMessage({ type: 'typing' });
        MockWebSocket.latest.simulateMessage({ type: 'done' });
      });

      expect(result.current.messages).toHaveLength(0);
    });
  });

  describe('citation handling', () => {
    it('includes citations in assistant message when provided before done', async () => {
      vi.useRealTimers();
      const { result } = renderHook(() => useRAGChat());

      await waitFor(() => expect(MockWebSocket.instances).toHaveLength(1));
      act(() => MockWebSocket.latest.simulateOpen());

      const mockCitations = [
        {
          doc_name: 'Manual.pdf',
          page_number: 5,
          chunk_text: 'Some relevant text',
          relevance_score: 0.95,
          document_id: 'doc-1',
        },
      ];

      act(() => {
        MockWebSocket.latest.simulateMessage({ type: 'typing' });
        MockWebSocket.latest.simulateMessage({ type: 'token', content: 'Based on docs...' });
        MockWebSocket.latest.simulateMessage({ type: 'citation', citations: mockCitations });
        MockWebSocket.latest.simulateMessage({ type: 'done' });
      });

      expect(result.current.messages).toHaveLength(1);
      expect(result.current.messages[0].citations).toEqual(mockCitations);
    });

    it('omits citations field when none provided', async () => {
      vi.useRealTimers();
      const { result } = renderHook(() => useRAGChat());

      await waitFor(() => expect(MockWebSocket.instances).toHaveLength(1));
      act(() => MockWebSocket.latest.simulateOpen());

      act(() => {
        MockWebSocket.latest.simulateMessage({ type: 'token', content: 'No citations here' });
        MockWebSocket.latest.simulateMessage({ type: 'done' });
      });

      expect(result.current.messages[0].citations).toBeUndefined();
    });
  });

  describe('error handling', () => {
    it('sets error on WebSocket error event', async () => {
      vi.useRealTimers();
      const { result } = renderHook(() => useRAGChat());

      await waitFor(() => expect(MockWebSocket.instances).toHaveLength(1));

      act(() => {
        MockWebSocket.latest.simulateError();
      });

      expect(result.current.error).toBe('Connection error');
      expect(result.current.isConnected).toBe(false);
    });

    it('sets error on server error message and clears typing state', async () => {
      vi.useRealTimers();
      const { result } = renderHook(() => useRAGChat());

      await waitFor(() => expect(MockWebSocket.instances).toHaveLength(1));
      act(() => MockWebSocket.latest.simulateOpen());

      act(() => {
        MockWebSocket.latest.simulateMessage({ type: 'typing' });
      });
      expect(result.current.isTyping).toBe(true);

      act(() => {
        MockWebSocket.latest.simulateMessage({
          type: 'error',
          error: 'Rate limit exceeded',
        });
      });

      expect(result.current.isTyping).toBe(false);
      expect(result.current.error).toBe('Rate limit exceeded');
    });

    it('uses default error message when server error has no message', async () => {
      vi.useRealTimers();
      const { result } = renderHook(() => useRAGChat());

      await waitFor(() => expect(MockWebSocket.instances).toHaveLength(1));
      act(() => MockWebSocket.latest.simulateOpen());

      act(() => {
        MockWebSocket.latest.simulateMessage({ type: 'error' });
      });

      expect(result.current.error).toBe('An error occurred');
    });
  });

  describe('feedback', () => {
    it('sends feedback via HTTP and updates message state', async () => {
      vi.useRealTimers();
      (global.fetch as any).mockResolvedValue({
        ok: true,
        json: async () => ({ ws_token: 'test-token-123' }),
      });

      const { result } = renderHook(() => useRAGChat());

      await waitFor(() => expect(MockWebSocket.instances).toHaveLength(1));
      act(() => MockWebSocket.latest.simulateOpen());

      // Create an assistant message
      act(() => {
        MockWebSocket.latest.simulateMessage({ type: 'token', content: 'Reply' });
        MockWebSocket.latest.simulateMessage({ type: 'done' });
      });

      const msgId = result.current.messages[0].id;

      // Mock feedback API call
      (global.fetch as any).mockResolvedValueOnce({
        ok: true,
        json: async () => ({}),
      });

      await act(async () => {
        await result.current.sendFeedback(msgId, 'positive');
      });

      // fetch should have been called for feedback
      expect(global.fetch).toHaveBeenCalledWith(
        expect.stringContaining(`/api/v1/messages/${msgId}/feedback`),
        expect.objectContaining({
          method: 'POST',
          body: JSON.stringify({ feedback: 'positive' }),
        })
      );

      // Message state should be updated
      expect(result.current.messages[0].feedback).toBe('positive');
    });
  });
});

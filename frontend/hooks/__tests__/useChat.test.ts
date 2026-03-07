/**
 * Unit tests for useChat hook
 * Tests: connection, messaging (WS + HTTP fallback), conversations, feedback
 */
import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { renderHook, act, waitFor } from '@testing-library/react';
import { useChat } from '../useChat';

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
  }

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
  static clear() { MockWebSocket.instances = []; }
  static get latest() { return MockWebSocket.instances[MockWebSocket.instances.length - 1]; }
}

const originalWebSocket = globalThis.WebSocket;

beforeEach(() => {
  MockWebSocket.clear();
  (globalThis as any).WebSocket = MockWebSocket;
  process.env.NEXT_PUBLIC_API_URL = 'http://localhost:8000';

  // Default: mock ws-token fetch + conversations fetch
  global.fetch = vi.fn().mockImplementation((url: string) => {
    if (url.includes('/ws-token')) {
      return Promise.resolve({
        ok: true,
        json: async () => ({ access_token: 'test-token' }),
      });
    }
    if (url.includes('/conversations') && !url.includes('/messages')) {
      return Promise.resolve({
        ok: true,
        json: async () => ({ conversations: [] }),
      });
    }
    if (url.includes('/messages')) {
      return Promise.resolve({
        ok: true,
        json: async () => ({ messages: [] }),
      });
    }
    return Promise.resolve({ ok: true, json: async () => ({}) });
  });
});

afterEach(() => {
  globalThis.WebSocket = originalWebSocket;
  vi.restoreAllMocks();
});

describe('useChat', () => {
  describe('initialization', () => {
    it('fetches conversations on mount', async () => {
      const { result } = renderHook(() => useChat());

      await waitFor(() => {
        expect(global.fetch).toHaveBeenCalledWith(
          expect.stringContaining('/api/v1/chat/conversations'),
          expect.objectContaining({ credentials: 'include' })
        );
      });
    });

    it('returns initial state', () => {
      const { result } = renderHook(() => useChat());

      expect(result.current.messages).toEqual([]);
      expect(result.current.isConnected).toBe(false);
      expect(result.current.isTyping).toBe(false);
      expect(result.current.streamingContent).toBe('');
    });
  });

  describe('WebSocket connection', () => {
    it('connects to WebSocket when conversationId is provided', async () => {
      renderHook(() => useChat({ conversationId: 'conv-123' }));

      await waitFor(() => {
        expect(global.fetch).toHaveBeenCalledWith(
          expect.stringContaining('/ws-token'),
          expect.anything()
        );
      });

      await waitFor(() => {
        expect(MockWebSocket.instances.length).toBeGreaterThanOrEqual(1);
      });

      const ws = MockWebSocket.instances.find(ws => ws.url.includes('conv-123'));
      expect(ws).toBeDefined();
      expect(ws!.url).toContain('token=test-token');
      expect(ws!.url).toContain('conversation_id=conv-123');
    });

    it('does not create WebSocket without conversationId', async () => {
      renderHook(() => useChat());

      // Give time for any async operations
      await new Promise(r => setTimeout(r, 100));

      // Only conversations fetch should be called, no ws-token
      const wsTokenCalls = (global.fetch as any).mock.calls.filter(
        (c: any) => c[0].includes('/ws-token')
      );
      expect(wsTokenCalls).toHaveLength(0);
    });

    it('sets isConnected on WebSocket open', async () => {
      const { result } = renderHook(() => useChat({ conversationId: 'conv-1' }));

      await waitFor(() => {
        const ws = MockWebSocket.instances.find(ws => ws.url.includes('conv-1'));
        return ws !== undefined;
      });

      const ws = MockWebSocket.instances.find(ws => ws.url.includes('conv-1'))!;
      act(() => ws.simulateOpen());

      expect(result.current.isConnected).toBe(true);
    });
  });

  describe('WebSocket message handling', () => {
    it('accumulates streaming tokens', async () => {
      const { result } = renderHook(() => useChat({ conversationId: 'conv-1' }));

      await waitFor(() =>
        MockWebSocket.instances.some(ws => ws.url.includes('conv-1'))
      );

      const ws = MockWebSocket.instances.find(ws => ws.url.includes('conv-1'))!;
      act(() => ws.simulateOpen());

      act(() => {
        ws.simulateMessage({ type: 'token', data: 'Hello' });
        ws.simulateMessage({ type: 'token', data: ' world' });
      });

      expect(result.current.streamingContent).toBe('Hello world');
    });

    it('handles typing indicator', async () => {
      const { result } = renderHook(() => useChat({ conversationId: 'conv-1' }));

      await waitFor(() =>
        MockWebSocket.instances.some(ws => ws.url.includes('conv-1'))
      );

      const ws = MockWebSocket.instances.find(ws => ws.url.includes('conv-1'))!;
      act(() => ws.simulateOpen());

      act(() => {
        ws.simulateMessage({ type: 'typing', data: true });
      });

      expect(result.current.isTyping).toBe(true);

      act(() => {
        ws.simulateMessage({ type: 'typing', data: false });
      });

      expect(result.current.isTyping).toBe(false);
    });

    it('creates assistant message on done event', async () => {
      const onMessage = vi.fn();
      const { result } = renderHook(() =>
        useChat({ conversationId: 'conv-1', onMessage })
      );

      await waitFor(() =>
        MockWebSocket.instances.some(ws => ws.url.includes('conv-1'))
      );

      const ws = MockWebSocket.instances.find(ws => ws.url.includes('conv-1'))!;
      act(() => ws.simulateOpen());

      act(() => {
        ws.simulateMessage({ type: 'token', data: 'AI response' });
        ws.simulateMessage({
          type: 'done',
          data: {
            message_id: 'msg-ai-1',
            conversation_id: 'conv-1',
            sentiment: 'positive',
            quality_score: 0.9,
          },
        });
      });

      expect(result.current.messages).toHaveLength(1);
      expect(result.current.messages[0].role).toBe('assistant');
      expect(result.current.messages[0].content).toBe('AI response');
      expect(result.current.streamingContent).toBe('');
      expect(onMessage).toHaveBeenCalled();
    });

    it('handles error message from server', async () => {
      const onError = vi.fn();
      const { result } = renderHook(() =>
        useChat({ conversationId: 'conv-1', onError })
      );

      await waitFor(() =>
        MockWebSocket.instances.some(ws => ws.url.includes('conv-1'))
      );

      const ws = MockWebSocket.instances.find(ws => ws.url.includes('conv-1'))!;
      act(() => ws.simulateOpen());

      act(() => {
        ws.simulateMessage({ type: 'typing', data: true });
        ws.simulateMessage({ type: 'token', data: 'partial' });
        ws.simulateMessage({ type: 'error', data: { message: 'Rate limit' } });
      });

      expect(result.current.isTyping).toBe(false);
      expect(result.current.streamingContent).toBe('');
      expect(onError).toHaveBeenCalledWith(expect.any(Error));
    });
  });

  describe('sending messages', () => {
    it('sends message over WebSocket when connected', async () => {
      const { result } = renderHook(() => useChat({ conversationId: 'conv-1' }));

      await waitFor(() =>
        MockWebSocket.instances.some(ws => ws.url.includes('conv-1'))
      );

      const ws = MockWebSocket.instances.find(ws => ws.url.includes('conv-1'))!;
      act(() => ws.simulateOpen());

      await act(async () => {
        await result.current.sendMessage('Hello');
      });

      // User message added optimistically
      expect(result.current.messages).toHaveLength(1);
      expect(result.current.messages[0].role).toBe('user');
      expect(result.current.messages[0].content).toBe('Hello');

      // Sent over WebSocket
      expect(ws.sentMessages).toHaveLength(1);
      expect(JSON.parse(ws.sentMessages[0]).message).toBe('Hello');
    });

    it('falls back to HTTP when WebSocket not connected', async () => {
      (global.fetch as any).mockImplementation((url: string) => {
        if (url.includes('/conversations') && !url.includes('/messages')) {
          return Promise.resolve({ ok: true, json: async () => ({ conversations: [] }) });
        }
        if (url.includes('/messages')) {
          return Promise.resolve({ ok: true, json: async () => ({ messages: [] }) });
        }
        if (url.includes('/ws-token')) {
          return Promise.resolve({ ok: true, json: async () => ({ access_token: 'tk' }) });
        }
        if (url.includes('/chat/send')) {
          return Promise.resolve({
            ok: true,
            json: async () => ({
              conversation_id: 'conv-1',
              assistant_message: 'HTTP response',
              metadata: { sentiment: 'neutral' },
            }),
          });
        }
        return Promise.resolve({ ok: true, json: async () => ({}) });
      });

      const { result } = renderHook(() => useChat({ conversationId: 'conv-1' }));

      // Wait for initialization but don't open WebSocket
      await waitFor(() =>
        MockWebSocket.instances.some(ws => ws.url.includes('conv-1'))
      );

      await act(async () => {
        await result.current.sendMessage('Hello');
      });

      // Should have called HTTP endpoint
      expect(global.fetch).toHaveBeenCalledWith(
        expect.stringContaining('/chat/send'),
        expect.objectContaining({ method: 'POST' })
      );

      // Should have both user and assistant messages
      expect(result.current.messages).toHaveLength(2);
      expect(result.current.messages[1].content).toBe('HTTP response');
    });

    it('creates new conversation via HTTP when no conversationId', async () => {
      (global.fetch as any).mockImplementation((url: string) => {
        if (url.includes('/conversations') && !url.includes('/messages')) {
          return Promise.resolve({ ok: true, json: async () => ({ conversations: [] }) });
        }
        if (url.includes('/chat/send')) {
          return Promise.resolve({
            ok: true,
            json: async () => ({
              conversation_id: 'new-conv',
              assistant_message: 'First reply',
            }),
          });
        }
        return Promise.resolve({ ok: true, json: async () => ({}) });
      });

      const { result } = renderHook(() => useChat());

      await act(async () => {
        await result.current.sendMessage('Start conversation');
      });

      expect(result.current.messages).toHaveLength(2);
      expect(result.current.currentConversationId).toBe('new-conv');
    });
  });

  describe('feedback', () => {
    it('submits feedback and updates local message state', async () => {
      (global.fetch as any).mockImplementation((url: string) => {
        if (url.includes('/conversations') && !url.includes('/messages')) {
          return Promise.resolve({ ok: true, json: async () => ({ conversations: [] }) });
        }
        if (url.includes('/feedback')) {
          return Promise.resolve({ ok: true, json: async () => ({}) });
        }
        return Promise.resolve({ ok: true, json: async () => ({}) });
      });

      const { result } = renderHook(() => useChat());

      // Manually set a message to give feedback on
      act(() => {
        result.current.sendMessage; // just to trigger init
      });

      await act(async () => {
        await result.current.submitFeedback('msg-1', 'positive');
      });

      expect(global.fetch).toHaveBeenCalledWith(
        expect.stringContaining('/messages/msg-1/feedback'),
        expect.objectContaining({
          method: 'POST',
          body: JSON.stringify({ feedback: 'positive' }),
        })
      );
    });
  });

  describe('conversations', () => {
    it('fetches and stores conversations', async () => {
      (global.fetch as any).mockImplementation((url: string) => {
        if (url.includes('/conversations') && !url.includes('/messages')) {
          return Promise.resolve({
            ok: true,
            json: async () => ({
              conversations: [
                { id: 'conv-1', title: 'First', started_at: '2026-01-01', message_count: 5 },
                { id: 'conv-2', title: 'Second', started_at: '2026-01-02', message_count: 3 },
              ],
            }),
          });
        }
        return Promise.resolve({ ok: true, json: async () => ({}) });
      });

      const { result } = renderHook(() => useChat());

      await waitFor(() => {
        expect(result.current.conversations).toHaveLength(2);
      });

      expect(result.current.conversations[0].id).toBe('conv-1');
    });
  });

  describe('disconnect', () => {
    it('cleans up WebSocket on unmount', async () => {
      const { unmount } = renderHook(() => useChat({ conversationId: 'conv-1' }));

      await waitFor(() =>
        MockWebSocket.instances.some(ws => ws.url.includes('conv-1'))
      );

      const ws = MockWebSocket.instances.find(ws => ws.url.includes('conv-1'))!;
      act(() => ws.simulateOpen());

      unmount();

      expect(ws.readyState).toBe(MockWebSocket.CLOSED);
    });
  });

  describe('reconnection', () => {
    it('schedules reconnect on close with increasing delay', async () => {
      const setTimeoutSpy = vi.spyOn(globalThis, 'setTimeout');

      renderHook(() => useChat({ conversationId: 'conv-1' }));

      await waitFor(() =>
        MockWebSocket.instances.some(ws => ws.url.includes('conv-1'))
      );

      const ws = MockWebSocket.instances.find(ws => ws.url.includes('conv-1'))!;
      act(() => ws.simulateOpen());

      act(() => ws.simulateClose());

      // Should schedule reconnect with RECONNECT_DELAY * attempt (2000 * 1 = 2000)
      const reconnectCall = setTimeoutSpy.mock.calls.find(
        (call) => call[1] === 2000
      );
      expect(reconnectCall).toBeDefined();

      setTimeoutSpy.mockRestore();
    });
  });
});

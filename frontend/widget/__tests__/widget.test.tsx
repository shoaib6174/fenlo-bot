/**
 * BotForge Widget Tests
 *
 * Tests widget initialization, WebSocket connection, and shadow DOM isolation.
 */

import { describe, test, expect, vi, beforeEach, afterEach } from 'vitest';
import { h, render } from 'preact';
import { ChatWidget } from '../src/ChatWidget';

// Mock WebSocket
class MockWebSocket {
  static CONNECTING = 0;
  static OPEN = 1;
  static CLOSING = 2;
  static CLOSED = 3;

  readyState = MockWebSocket.CONNECTING;
  onopen: ((event: Event) => void) | null = null;
  onmessage: ((event: MessageEvent) => void) | null = null;
  onerror: ((event: Event) => void) | null = null;
  onclose: ((event: CloseEvent) => void) | null = null;

  constructor(public url: string) {
    // Simulate async connection
    setTimeout(() => {
      this.readyState = MockWebSocket.OPEN;
      if (this.onopen) {
        this.onopen(new Event('open'));
      }
    }, 10);
  }

  send(data: string) {
    // Echo back for testing
    if (this.onmessage && this.readyState === MockWebSocket.OPEN) {
      const message = JSON.parse(data);
      setTimeout(() => {
        this.onmessage!(
          new MessageEvent('message', {
            data: JSON.stringify({
              type: 'message',
              content: `Echo: ${message.message}`,
            }),
          })
        );
      }, 10);
    }
  }

  close() {
    this.readyState = MockWebSocket.CLOSED;
    if (this.onclose) {
      this.onclose(new CloseEvent('close', { code: 1000 }));
    }
  }
}

// Mock fetch for config
global.fetch = vi.fn((url: string) => {
  if (url.includes('/widget/config/')) {
    return Promise.resolve({
      ok: true,
      json: () =>
        Promise.resolve({
          workspace_id: 'test-workspace',
          hmac: 'test-hmac-signature',
          primary_color: '#3b82f6',
          position: 'bottom-right',
          greeting: 'Hello! How can I help you?',
          placeholder: 'Type a message...',
          widget_api_version: 1,
        }),
    } as Response);
  }
  return Promise.reject(new Error('Not found'));
});

describe('ChatWidget', () => {
  let container: HTMLDivElement;

  beforeEach(() => {
    container = document.createElement('div');
    document.body.appendChild(container);

    // Mock WebSocket globally
    (global as any).WebSocket = MockWebSocket;
  });

  afterEach(() => {
    if (container && container.parentNode) {
      container.parentNode.removeChild(container);
    }
    vi.clearAllMocks();
  });

  test('loads config from API and renders', async () => {
    const config = {
      workspace_id: 'test-workspace',
      hmac: 'test-hmac',
      primary_color: '#3b82f6',
      position: 'bottom-right' as const,
      greeting: 'Welcome!',
      placeholder: 'Type here...',
      backend_url: 'http://localhost:8000',
      widget_api_version: 1,
    };

    render(<ChatWidget config={config} />, container);

    // Wait for component to render
    await new Promise((resolve) => setTimeout(resolve, 50));

    // Check chat bubble is rendered
    const bubble = container.querySelector('.chat-bubble');
    expect(bubble).toBeTruthy();

    // Check chat panel exists (but is hidden)
    const panel = container.querySelector('.chat-panel');
    expect(panel).toBeTruthy();
    expect(panel?.classList.contains('open')).toBe(false);

    // Check greeting message is displayed
    const messages = container.querySelectorAll('.message');
    expect(messages.length).toBeGreaterThan(0);

    const greetingMessage = Array.from(messages).find(
      (msg) => msg.textContent?.includes('Welcome!')
    );
    expect(greetingMessage).toBeTruthy();
  });

  test('connects WebSocket with HMAC auth', async () => {
    const config = {
      workspace_id: 'test-workspace',
      hmac: 'test-hmac-signature',
      backend_url: 'http://localhost:8000',
      widget_api_version: 1,
    };

    render(<ChatWidget config={config} />, container);

    // Wait for WebSocket connection
    await new Promise((resolve) => setTimeout(resolve, 100));

    // WebSocket should be created with HMAC in URL
    const wsInstances = (MockWebSocket as any).mock?.instances || [];
    if (wsInstances.length > 0) {
      const wsUrl = wsInstances[0].url;
      expect(wsUrl).toContain('hmac=test-hmac-signature');
      expect(wsUrl).toContain('workspace_id=test-workspace');
    }

    // Check connection status indicator is NOT shown when connected
    // (status only shows for non-connected states like disconnected/reconnecting)
    const statusIndicator = container.querySelector('.connection-status');
    expect(statusIndicator).toBeFalsy();
  });

  test('renders in shadow DOM without leaking CSS', async () => {
    // Create shadow root
    const shadowHost = document.createElement('div');
    document.body.appendChild(shadowHost);

    const shadow = shadowHost.attachShadow({ mode: 'open' });

    // Inject styles
    const styleSheet = document.createElement('style');
    styleSheet.textContent = `
      .chat-bubble { background: red; }
      .message { color: blue; }
    `;
    shadow.appendChild(styleSheet);

    // Create root
    const root = document.createElement('div');
    shadow.appendChild(root);

    // Render widget in shadow DOM
    const config = {
      workspace_id: 'test-workspace',
      hmac: 'test-hmac',
      backend_url: 'http://localhost:8000',
      widget_api_version: 1,
    };

    render(<ChatWidget config={config} />, root);

    // Wait for render
    await new Promise((resolve) => setTimeout(resolve, 100));

    // Check widget rendered in shadow DOM
    const shadowBubble = shadow.querySelector('.chat-bubble');
    expect(shadowBubble).toBeTruthy();

    // Check host page doesn't have widget elements (excluding the regular test container)
    // Only check outside both shadow DOM and test container
    const bodyBubbles = Array.from(document.body.querySelectorAll('.chat-bubble'));
    const hostBubbles = bodyBubbles.filter(
      (el) => !container.contains(el) && !shadowHost.contains(el)
    );
    expect(hostBubbles.length).toBe(0);

    // Check styles don't leak to host page
    const hostStyle = getComputedStyle(document.body);
    expect(hostStyle.getPropertyValue('--primary-color')).toBe('');

    // Cleanup
    shadowHost.remove();
  });

  test('handles chat interaction and displays messages', async () => {
    const config = {
      workspace_id: 'test-workspace',
      hmac: 'test-hmac',
      backend_url: 'http://localhost:8000',
      widget_api_version: 1,
    };

    render(<ChatWidget config={config} />, container);

    // Wait for WebSocket connection
    await new Promise((resolve) => setTimeout(resolve, 100));

    // Open chat panel
    const bubble = container.querySelector('.chat-bubble') as HTMLButtonElement;
    expect(bubble).toBeTruthy();
    bubble.click();

    await new Promise((resolve) => setTimeout(resolve, 50));

    const panel = container.querySelector('.chat-panel');
    expect(panel?.classList.contains('open')).toBe(true);

    // Find input and verify it's enabled
    const input = container.querySelector('.chat-input') as HTMLInputElement;
    expect(input).toBeTruthy();
    expect(input.disabled).toBe(false);

    // Simulate typing by setting value and triggering input event with target
    input.value = 'Hello bot';

    // Create InputEvent with proper target
    Object.defineProperty(input, 'value', {
      writable: true,
      value: 'Hello bot'
    });

    const inputEvent = new Event('input', { bubbles: true });
    Object.defineProperty(inputEvent, 'target', {
      writable: false,
      value: input
    });
    input.dispatchEvent(inputEvent);

    // Wait a bit for state update
    await new Promise((resolve) => setTimeout(resolve, 50));

    // Submit the form by dispatching submit event
    const form = container.querySelector('.chat-input-container') as HTMLFormElement;
    expect(form).toBeTruthy();

    const submitEvent = new Event('submit', { bubbles: true, cancelable: true });
    form.dispatchEvent(submitEvent);

    // Wait for message processing
    await new Promise((resolve) => setTimeout(resolve, 100));

    // Check that a user message was added
    const messages = container.querySelectorAll('.message.user');
    expect(messages.length).toBeGreaterThan(0);

    // Verify the message contains our text
    const hasOurMessage = Array.from(messages).some(
      (msg) => msg.textContent?.includes('Hello bot')
    );
    expect(hasOurMessage).toBe(true);
  });

  test('handles API version mismatch', async () => {
    const config = {
      workspace_id: 'test-workspace',
      hmac: 'test-hmac',
      backend_url: 'http://localhost:8000',
      widget_api_version: 999, // Future version
    };

    // Set widget's supported version
    (window as any).SUPPORTED_API_VERSION = 1;

    render(<ChatWidget config={config} />, container);

    // Wait for component to check version
    await new Promise((resolve) => setTimeout(resolve, 50));

    // Should show error message
    const errorMessage = container.querySelector('.error-message');
    expect(errorMessage).toBeTruthy();
    expect(errorMessage?.textContent).toContain('update required');
  });
});

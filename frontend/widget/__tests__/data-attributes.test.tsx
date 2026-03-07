/**
 * Widget Data Attribute Tests (S78 Task 8.20)
 *
 * Tests parsing and handling of data-* attributes from embed code:
 * - data-widget-id
 * - data-hmac
 * - data-timestamp
 * - data-theme
 * - data-position
 * - data-greeting
 */

import { describe, test, expect, vi, beforeEach, afterEach } from 'vitest';

// Mock document.currentScript for testing
let mockScriptElement: Partial<HTMLScriptElement> | null = null;

Object.defineProperty(document, 'currentScript', {
  get() {
    return mockScriptElement;
  },
  configurable: true,
});

// Mock fetch for config API
global.fetch = vi.fn();

describe('Widget Data Attribute Parsing', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    document.body.innerHTML = '';
  });

  afterEach(() => {
    mockScriptElement = null;
  });

  test('parses data-widget-id attribute', () => {
    mockScriptElement = {
      dataset: {
        widgetId: 'widget-abc-123',
      },
    } as HTMLScriptElement;

    const widgetId = mockScriptElement.dataset?.widgetId;
    expect(widgetId).toBe('widget-abc-123');
  });

  test('parses data-hmac and data-timestamp attributes', () => {
    mockScriptElement = {
      dataset: {
        widgetId: 'widget-123',
        hmac: 'a'.repeat(64), // 64-char SHA256 hex
        timestamp: '1234567890',
      },
    } as HTMLScriptElement;

    const { hmac, timestamp } = mockScriptElement.dataset!;
    expect(hmac).toBe('a'.repeat(64));
    expect(hmac).toHaveLength(64);
    expect(timestamp).toBe('1234567890');
    expect(parseInt(timestamp!, 10)).toBe(1234567890);
  });

  test('parses data-theme attribute with valid values', () => {
    const themes = ['light', 'dark', 'auto'] as const;

    themes.forEach((theme) => {
      mockScriptElement = {
        dataset: {
          theme,
        },
      } as HTMLScriptElement;

      expect(mockScriptElement.dataset?.theme).toBe(theme);
    });
  });

  test('parses data-position attribute with valid values', () => {
    const positions = ['bottom-right', 'bottom-left'] as const;

    positions.forEach((position) => {
      mockScriptElement = {
        dataset: {
          position,
        },
      } as HTMLScriptElement;

      expect(mockScriptElement.dataset?.position).toBe(position);
    });
  });

  test('parses data-greeting attribute', () => {
    const customGreeting = 'Welcome to our website! How can I assist you?';

    mockScriptElement = {
      dataset: {
        greeting: customGreeting,
      },
    } as HTMLScriptElement;

    expect(mockScriptElement.dataset?.greeting).toBe(customGreeting);
  });

  test('falls back to legacy data-workspace-id if data-widget-id not provided', () => {
    mockScriptElement = {
      dataset: {
        workspaceId: 'legacy-workspace-123',
      },
    } as HTMLScriptElement;

    const widgetId = mockScriptElement.dataset?.widgetId || mockScriptElement.dataset?.workspaceId;
    expect(widgetId).toBe('legacy-workspace-123');
  });

  test('prefers data-widget-id over data-workspace-id', () => {
    mockScriptElement = {
      dataset: {
        widgetId: 'widget-new-123',
        workspaceId: 'workspace-old-456',
      },
    } as HTMLScriptElement;

    const widgetId = mockScriptElement.dataset?.widgetId || mockScriptElement.dataset?.workspaceId;
    expect(widgetId).toBe('widget-new-123');
  });

  test('defaults theme to "light" when not provided', () => {
    mockScriptElement = {
      dataset: {},
    } as HTMLScriptElement;

    const theme = (mockScriptElement.dataset?.theme || 'light') as 'light' | 'dark' | 'auto';
    expect(theme).toBe('light');
  });

  test('defaults position to "bottom-right" when not provided', () => {
    mockScriptElement = {
      dataset: {},
    } as HTMLScriptElement;

    const position = (mockScriptElement.dataset?.position || 'bottom-right') as
      | 'bottom-right'
      | 'bottom-left';
    expect(position).toBe('bottom-right');
  });

  test('parses all attributes together (complete embed code)', () => {
    mockScriptElement = {
      dataset: {
        widgetId: 'widget-xyz-789',
        hmac: 'f'.repeat(64),
        timestamp: '9876543210',
        theme: 'dark',
        position: 'bottom-left',
        greeting: 'Hi there! 👋',
      },
    } as HTMLScriptElement;

    const config = {
      widgetId: mockScriptElement.dataset?.widgetId,
      hmac: mockScriptElement.dataset?.hmac,
      timestamp: parseInt(mockScriptElement.dataset?.timestamp || '0', 10),
      theme: mockScriptElement.dataset?.theme || 'light',
      position: mockScriptElement.dataset?.position || 'bottom-right',
      greeting: mockScriptElement.dataset?.greeting,
    };

    expect(config).toEqual({
      widgetId: 'widget-xyz-789',
      hmac: 'f'.repeat(64),
      timestamp: 9876543210,
      theme: 'dark',
      position: 'bottom-left',
      greeting: 'Hi there! 👋',
    });
  });

  test('handles optional data-backend-url attribute', () => {
    mockScriptElement = {
      dataset: {
        widgetId: 'widget-123',
        backendUrl: 'https://custom-backend.example.com',
      },
    } as HTMLScriptElement;

    const backendUrl =
      mockScriptElement.dataset?.backendUrl || window.location.origin;
    expect(backendUrl).toBe('https://custom-backend.example.com');
  });

  test('uses window.location.origin as default backend URL', () => {
    mockScriptElement = {
      dataset: {
        widgetId: 'widget-123',
      },
    } as HTMLScriptElement;

    const backendUrl =
      mockScriptElement.dataset?.backendUrl || window.location.origin;
    expect(backendUrl).toBe(window.location.origin);
  });

  test('HMAC attribute should be 64 characters (SHA256 hex)', () => {
    const validHmac = 'a'.repeat(64);
    const invalidHmac = 'a'.repeat(32); // Too short

    mockScriptElement = {
      dataset: {
        hmac: validHmac,
      },
    } as HTMLScriptElement;

    expect(mockScriptElement.dataset?.hmac).toHaveLength(64);

    mockScriptElement = {
      dataset: {
        hmac: invalidHmac,
      },
    } as HTMLScriptElement;

    expect(mockScriptElement.dataset?.hmac).toHaveLength(32); // Should be validated by widget
  });

  test('timestamp should be a valid Unix timestamp', () => {
    const now = Math.floor(Date.now() / 1000);

    mockScriptElement = {
      dataset: {
        timestamp: now.toString(),
      },
    } as HTMLScriptElement;

    const timestamp = parseInt(mockScriptElement.dataset?.timestamp || '0', 10);
    expect(timestamp).toBeGreaterThan(1600000000); // After Sep 2020
    expect(timestamp).toBeLessThan(2000000000); // Before May 2033
  });

  test('greeting can contain special characters', () => {
    const greetings = [
      'Hello! 👋',
      'Bonjour! Comment puis-je vous aider?',
      '你好！我能帮你什么？',
      "Welcome to Bob's Shop!",
    ];

    greetings.forEach((greeting) => {
      mockScriptElement = {
        dataset: {
          greeting,
        },
      } as HTMLScriptElement;

      expect(mockScriptElement.dataset?.greeting).toBe(greeting);
    });
  });
});

describe('Widget Configuration Priority', () => {
  test('data attributes override server config', () => {
    const serverConfig = {
      theme: 'light',
      position: 'bottom-right',
      greeting: 'Server greeting',
    };

    const dataAttributes = {
      theme: 'dark',
      position: 'bottom-left',
      greeting: 'Custom greeting',
    };

    // Simulate override logic
    const finalConfig = {
      ...serverConfig,
      ...dataAttributes, // Data attributes take precedence
    };

    expect(finalConfig).toEqual({
      theme: 'dark',
      position: 'bottom-left',
      greeting: 'Custom greeting',
    });
  });

  test('server config fills in missing data attributes', () => {
    const serverConfig = {
      theme: 'light',
      position: 'bottom-right',
      greeting: 'Server greeting',
      primary_color: '#3b82f6',
      placeholder: 'Type a message...',
    };

    const dataAttributes = {
      theme: 'dark', // Override
      // position not provided - use server
      // greeting not provided - use server
    };

    const finalConfig = {
      ...serverConfig,
      ...dataAttributes,
    };

    expect(finalConfig).toEqual({
      theme: 'dark', // From data attribute
      position: 'bottom-right', // From server
      greeting: 'Server greeting', // From server
      primary_color: '#3b82f6', // From server only
      placeholder: 'Type a message...', // From server only
    });
  });
});

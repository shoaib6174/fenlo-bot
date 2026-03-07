/**
 * BotForge Widget Entry Point
 *
 * Initializes the widget with Shadow DOM for complete style isolation.
 * Loads configuration from backend and renders the chat widget.
 *
 * Usage:
 * <script src="https://cdn.botforge.ai/widget.{hash}.js" data-workspace-id="YOUR_WORKSPACE_ID"></script>
 */

import { h, render } from 'preact';
import { ChatWidget } from './ChatWidget';
import stylesCSS from './styles.css';

interface WidgetConfig {
  workspace_id?: string; // Legacy support
  widget_id: string;
  hmac: string;
  hmac_timestamp?: number;
  primary_color?: string;
  position?: 'bottom-right' | 'bottom-left';
  greeting?: string;
  placeholder?: string;
  theme?: 'light' | 'dark' | 'auto';
  backend_url: string;
  widget_api_version?: number;
}

/**
 * Fetch widget configuration from backend
 */
async function fetchConfig(workspaceId: string, backendUrl: string): Promise<WidgetConfig> {
  const configUrl = `${backendUrl}/api/v1/widget/config/${workspaceId}`;

  try {
    const response = await fetch(configUrl);

    if (!response.ok) {
      throw new Error(`Config fetch failed: ${response.status}`);
    }

    const config = await response.json();

    // Add backend_url to config for WebSocket construction
    return {
      ...config,
      backend_url: backendUrl,
    };
  } catch (error) {
    console.error('[BotForge] Failed to load config:', error);
    throw error;
  }
}

/**
 * Create shadow DOM container and inject styles
 */
function createShadowRoot(container: HTMLElement): ShadowRoot {
  const shadow = container.attachShadow({ mode: 'open' });

  // Inject styles into shadow DOM
  const styleSheet = document.createElement('style');
  styleSheet.textContent = stylesCSS;
  shadow.appendChild(styleSheet);

  // Create root element for Preact
  const root = document.createElement('div');
  root.id = 'botforge-root';
  shadow.appendChild(root);

  return shadow;
}

/**
 * Initialize the BotForge widget
 */
async function initWidget() {
  try {
    // Get configuration from script tag data attributes
    const scriptTag = document.currentScript as HTMLScriptElement;

    // Support both new (data-widget-id) and legacy (data-workspace-id) attributes
    const widgetId = scriptTag?.dataset?.widgetId || scriptTag?.dataset?.workspaceId;
    const hmac = scriptTag?.dataset?.hmac;
    const hmacTimestamp = scriptTag?.dataset?.timestamp;

    if (!widgetId) {
      throw new Error('Missing data-widget-id attribute on script tag');
    }

    // Get optional customization attributes
    const theme = (scriptTag?.dataset?.theme || 'light') as 'light' | 'dark' | 'auto';
    const position = (scriptTag?.dataset?.position || 'bottom-right') as 'bottom-right' | 'bottom-left';
    const greeting = scriptTag?.dataset?.greeting;

    // Get backend URL (default to current origin or from data attribute)
    const backendUrl =
      scriptTag?.dataset?.backendUrl ||
      window.location.origin;

    console.log('[BotForge] Initializing widget...', {
      widgetId,
      theme,
      position,
      hasHmac: !!hmac,
      backendUrl,
      version: (window as any).WIDGET_VERSION,
    });

    // Build config from data attributes or fetch from backend
    let config: WidgetConfig;

    if (hmac && hmacTimestamp) {
      // Use embedded HMAC (from embed code generator)
      config = {
        widget_id: widgetId,
        hmac,
        hmac_timestamp: parseInt(hmacTimestamp, 10),
        theme,
        position,
        greeting,
        backend_url: backendUrl,
      };

      // Optionally fetch additional config from backend to get colors, placeholder, etc.
      try {
        const serverConfig = await fetchConfig(widgetId, backendUrl);
        config = {
          ...serverConfig,
          ...config, // Data attributes override server config
        };
      } catch (error) {
        console.warn('[BotForge] Failed to fetch server config, using data attributes only:', error);
      }
    } else {
      // Legacy: fetch full config from backend (backward compatibility)
      config = await fetchConfig(widgetId, backendUrl);

      // Override with data attributes if provided
      if (theme) config.theme = theme;
      if (position) config.position = position;
      if (greeting) config.greeting = greeting;
    }

    // Create container
    const container = document.createElement('div');
    container.id = 'botforge-widget-container';
    document.body.appendChild(container);

    // Create shadow DOM for style isolation
    const shadow = createShadowRoot(container);
    const root = shadow.getElementById('botforge-root');

    if (!root) {
      throw new Error('Failed to create shadow root element');
    }

    // Render widget
    render(<ChatWidget config={config} />, root);

    console.log('[BotForge] Widget initialized successfully');

    // Expose widget API for programmatic control (optional)
    (window as any).BotForgeWidget = {
      version: (window as any).WIDGET_VERSION,
      widgetId,
      // Future: open(), close(), sendMessage(), etc.
    };
  } catch (error) {
    console.error('[BotForge] Widget initialization failed:', error);

    // Show minimal error UI (doesn't break host page)
    const container = document.createElement('div');
    container.style.cssText = `
      position: fixed;
      bottom: 20px;
      right: 20px;
      padding: 12px 16px;
      background: #fee2e2;
      color: #991b1b;
      border-radius: 8px;
      font-family: system-ui, sans-serif;
      font-size: 13px;
      box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
      z-index: 2147483647;
      max-width: 300px;
    `;
    container.textContent = 'Chat widget failed to load. Please refresh the page.';
    document.body.appendChild(container);

    // Auto-hide error after 10 seconds
    setTimeout(() => {
      container.remove();
    }, 10000);
  }
}

// Auto-initialize when DOM is ready
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', initWidget);
} else {
  initWidget();
}

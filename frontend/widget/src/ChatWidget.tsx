/**
 * BotForge Chat Widget Component
 *
 * Main widget UI built with Preact for minimal bundle size.
 * Features token-by-token streaming, configurable appearance, and error boundaries.
 */

import { h, Component } from 'preact';
import { WSClient, ConnectionState, WSMessage } from './ws-client';

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

interface Message {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp: number;
}

interface ChatWidgetProps {
  config: WidgetConfig;
}

interface ChatWidgetState {
  isOpen: boolean;
  messages: Message[];
  inputValue: string;
  isTyping: boolean;
  connectionState: ConnectionState;
  error: string | null;
  streamingContent: string;
}

export class ChatWidget extends Component<ChatWidgetProps, ChatWidgetState> {
  private wsClient: WSClient | null = null;
  private messagesEndRef: HTMLDivElement | null = null;
  private messageIdCounter = 0;

  state: ChatWidgetState = {
    isOpen: false,
    messages: [],
    inputValue: '',
    isTyping: false,
    connectionState: 'disconnected',
    error: null,
    streamingContent: '',
  };

  componentDidMount() {
    // Check API version compatibility
    this.checkApiVersion();

    // Add greeting message
    if (this.props.config.greeting) {
      this.addMessage({
        role: 'assistant',
        content: this.props.config.greeting,
      });
    }

    // Initialize WebSocket client
    this.initializeWebSocket();
  }

  componentWillUnmount() {
    if (this.wsClient) {
      this.wsClient.disconnect();
    }
  }

  componentDidUpdate(prevProps: ChatWidgetProps, prevState: ChatWidgetState) {
    // Auto-scroll to bottom when new messages arrive
    if (prevState.messages.length !== this.state.messages.length ||
        prevState.streamingContent !== this.state.streamingContent) {
      this.scrollToBottom();
    }
  }

  private checkApiVersion() {
    const serverVersion = this.props.config.widget_api_version || 1;
    const supportedVersion = (window as any).SUPPORTED_API_VERSION || 1;

    if (serverVersion > supportedVersion) {
      this.setState({
        error: 'Widget update required. Please contact your administrator.',
      });
    }
  }

  private initializeWebSocket() {
    const { backend_url, widget_id, workspace_id, hmac, hmac_timestamp } = this.props.config;

    // Use widget_id (new) or workspace_id (legacy) for backward compatibility
    const widgetIdOrWorkspaceId = widget_id || workspace_id;

    if (!widgetIdOrWorkspaceId) {
      this.setState({
        error: 'Widget configuration error: missing widget ID',
      });
      return;
    }

    // Convert HTTP to WS protocol
    const wsProtocol = backend_url.startsWith('https') ? 'wss' : 'ws';
    const wsUrl = backend_url.replace(/^https?/, wsProtocol) + '/api/v1/widget/stream';

    this.wsClient = new WSClient({
      url: wsUrl,
      hmac,
      hmacTimestamp: hmac_timestamp,
      workspaceId: widgetIdOrWorkspaceId, // Use widget_id (new) or workspace_id (legacy)
      onMessage: this.handleWSMessage.bind(this),
      onStateChange: this.handleStateChange.bind(this),
    });

    this.wsClient.connect();
  }

  private handleWSMessage(message: WSMessage) {
    if (message.type === 'error') {
      this.setState({
        error: message.error || 'An error occurred',
        isTyping: false,
        streamingContent: '',
      });
      return;
    }

    if (message.type === 'message') {
      // Token-by-token streaming
      const content = message.content || '';

      if (content === '[DONE]') {
        // Streaming complete - add message and reset
        if (this.state.streamingContent) {
          this.addMessage({
            role: 'assistant',
            content: this.state.streamingContent,
          });
        }
        this.setState({
          isTyping: false,
          streamingContent: '',
        });
      } else {
        // Accumulate streaming content
        this.setState((prevState) => ({
          streamingContent: prevState.streamingContent + content,
        }));
      }
    }
  }

  private handleStateChange(state: ConnectionState) {
    this.setState({ connectionState: state });

    if (state === 'disconnected') {
      this.addMessage({
        role: 'system',
        content: 'Connection lost. Trying to reconnect...',
      });
    } else if (state === 'connected') {
      // Remove disconnect messages
      this.setState((prevState) => ({
        messages: prevState.messages.filter((m) => m.role !== 'system'),
      }));
    }
  }

  private addMessage(msg: Partial<Message>) {
    const message: Message = {
      id: `msg-${++this.messageIdCounter}`,
      role: msg.role || 'user',
      content: msg.content || '',
      timestamp: Date.now(),
    };

    this.setState((prevState) => ({
      messages: [...prevState.messages, message],
    }));
  }

  private toggleOpen = () => {
    this.setState((prevState) => ({ isOpen: !prevState.isOpen }));
  };

  private handleSubmit = (e: Event) => {
    e.preventDefault();

    const { inputValue } = this.state;
    if (!inputValue.trim() || !this.wsClient) return;

    // Add user message
    this.addMessage({
      role: 'user',
      content: inputValue,
    });

    // Send to server
    const sent = this.wsClient.send(inputValue);

    if (sent) {
      this.setState({
        inputValue: '',
        isTyping: true,
        streamingContent: '',
        error: null,
      });
    } else {
      this.setState({
        error: 'Failed to send message. Please check your connection.',
      });
    }
  };

  private handleInputChange = (e: Event) => {
    const target = e.target as HTMLInputElement;
    this.setState({ inputValue: target.value });
  };

  private scrollToBottom() {
    if (this.messagesEndRef) {
      this.messagesEndRef.scrollIntoView({ behavior: 'smooth' });
    }
  }

  private renderChatBubble() {
    return (
      <button
        class="chat-bubble"
        onClick={this.toggleOpen}
        aria-label="Open chat"
      >
        <svg fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path
            stroke-linecap="round"
            stroke-linejoin="round"
            stroke-width={2}
            d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z"
          />
        </svg>
      </button>
    );
  }

  private renderMessages() {
    const { messages, streamingContent, isTyping } = this.state;

    return (
      <div class="chat-messages">
        {messages.map((msg) => (
          <div key={msg.id} class={`message ${msg.role}`}>
            {msg.content}
          </div>
        ))}

        {streamingContent && (
          <div class="message assistant">
            {streamingContent}
          </div>
        )}

        {isTyping && !streamingContent && (
          <div class="typing-indicator">
            <div class="typing-dot"></div>
            <div class="typing-dot"></div>
            <div class="typing-dot"></div>
          </div>
        )}

        <div ref={(el) => (this.messagesEndRef = el)} />
      </div>
    );
  }

  private renderConnectionStatus() {
    const { connectionState } = this.state;

    if (connectionState === 'connected') {
      return null;
    }

    const statusText = {
      connecting: 'Connecting...',
      disconnected: 'Disconnected',
      reconnecting: 'Reconnecting...',
    }[connectionState];

    return (
      <div class={`connection-status ${connectionState}`}>
        {statusText}
      </div>
    );
  }

  private renderChatPanel() {
    const { isOpen, inputValue, error, connectionState } = this.state;
    const { config } = this.props;

    return (
      <div class={`chat-panel ${isOpen ? 'open' : ''}`}>
        <div class="chat-header">
          <h3>Chat with us</h3>
          <button
            class="close-button"
            onClick={this.toggleOpen}
            aria-label="Close chat"
          >
            <svg fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path
                stroke-linecap="round"
                stroke-linejoin="round"
                stroke-width={2}
                d="M6 18L18 6M6 6l12 12"
              />
            </svg>
          </button>
        </div>

        {this.renderConnectionStatus()}

        {error && <div class="error-message">{error}</div>}

        {this.renderMessages()}

        <form class="chat-input-container" onSubmit={this.handleSubmit}>
          <div class="chat-input-form">
            <input
              type="text"
              class="chat-input"
              value={inputValue}
              onInput={this.handleInputChange}
              placeholder={config.placeholder || 'Type a message...'}
              disabled={connectionState !== 'connected'}
            />
            <button
              type="submit"
              class="send-button"
              disabled={!inputValue.trim() || connectionState !== 'connected'}
            >
              Send
            </button>
          </div>
        </form>

        <div class="chat-footer">
          Powered by <a href="https://bot.fenloai.com" target="_blank" rel="noopener">Fenlo AI</a>
        </div>
      </div>
    );
  }

  render() {
    const { config } = this.props;
    const position = config.position || 'bottom-right';

    // Apply custom colors via CSS variables
    const style = config.primary_color
      ? `--primary-color: ${config.primary_color}; --primary-color-dark: ${this.darkenColor(config.primary_color, 10)}`
      : '';

    return (
      <div id="botforge-widget" class={`position-${position}`} style={style}>
        {this.renderChatBubble()}
        {this.renderChatPanel()}
      </div>
    );
  }

  // Utility: Darken a hex color by percentage
  private darkenColor(hex: string, percent: number): string {
    const num = parseInt(hex.replace('#', ''), 16);
    const amt = Math.round(2.55 * percent);
    const R = (num >> 16) - amt;
    const G = ((num >> 8) & 0x00ff) - amt;
    const B = (num & 0x0000ff) - amt;
    return (
      '#' +
      (
        0x1000000 +
        (R < 255 ? (R < 1 ? 0 : R) : 255) * 0x10000 +
        (G < 255 ? (G < 1 ? 0 : G) : 255) * 0x100 +
        (B < 255 ? (B < 1 ? 0 : B) : 255)
      )
        .toString(16)
        .slice(1)
    );
  }
}

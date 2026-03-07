/**
 * Unit tests for ChatWindow component
 */
import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { ChatWindow } from '../ChatWindow';
import React from 'react';

// Mock useChat hook
vi.mock('@/hooks/useChat', () => ({
  useChat: () => ({
    messages: [],
    conversations: [],
    isConnected: false,
    isTyping: false,
    streamingContent: '',
    currentConversationId: undefined,
    setCurrentConversationId: vi.fn(),
    sendMessage: vi.fn(),
    submitFeedback: vi.fn(),
    fetchConversations: vi.fn(),
  }),
}));

describe('ChatWindow', () => {
  it('renders empty state when no messages', () => {
    render(<ChatWindow />);
    expect(screen.getByText('Start a conversation')).toBeInTheDocument();
    expect(screen.getByText(/Ask me anything/)).toBeInTheDocument();
  });

  it('renders chat input', () => {
    render(<ChatWindow />);
    expect(screen.getByPlaceholderText('Type a message...')).toBeInTheDocument();
  });

  it('renders conversation sidebar when showSidebar is true', () => {
    render(<ChatWindow showSidebar />);
    expect(screen.getByText('New Chat')).toBeInTheDocument();
  });

  it('hides conversation sidebar when showSidebar is false', () => {
    render(<ChatWindow showSidebar={false} />);
    expect(screen.queryByText('New Chat')).not.toBeInTheDocument();
  });

  it('renders send button', () => {
    render(<ChatWindow />);
    expect(screen.getByLabelText('Send message')).toBeInTheDocument();
  });
});

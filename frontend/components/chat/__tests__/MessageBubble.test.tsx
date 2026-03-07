/**
 * Unit tests for chat MessageBubble component (components/chat/MessageBubble.tsx)
 */
import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { MessageBubble } from '../MessageBubble';
import type { Message } from '@/lib/chat';
import React from 'react';

const userMessage: Message = {
  id: 'msg-1',
  conversation_id: 'conv-1',
  role: 'user',
  content: 'What is BotForge?',
  created_at: '2026-02-12T14:30:00Z',
};

const assistantMessage: Message = {
  id: 'msg-2',
  conversation_id: 'conv-1',
  role: 'assistant',
  content: 'BotForge is an AI chatbot platform.',
  created_at: '2026-02-12T14:30:05Z',
};

const messageWithCitations: Message = {
  id: 'msg-3',
  conversation_id: 'conv-1',
  role: 'assistant',
  content: 'According to the documentation...',
  created_at: '2026-02-12T14:30:10Z',
  metadata: {
    citations: [
      {
        doc_name: 'Guide.pdf',
        page_number: 3,
        chunk_text: 'BotForge provides unified chatbot capabilities across multiple channels.',
        relevance_score: 0.95,
      },
    ],
  },
};

describe('MessageBubble (chat)', () => {
  it('renders user message content', () => {
    render(<MessageBubble message={userMessage} />);
    expect(screen.getByText('What is BotForge?')).toBeInTheDocument();
  });

  it('renders assistant message content', () => {
    render(<MessageBubble message={assistantMessage} />);
    expect(screen.getByText('BotForge is an AI chatbot platform.')).toBeInTheDocument();
  });

  it('renders timestamp', () => {
    render(<MessageBubble message={userMessage} />);
    // date-fns format HH:mm
    expect(screen.getByText(/\d{2}:\d{2}/)).toBeInTheDocument();
  });

  it('does not show feedback buttons for user messages', () => {
    render(<MessageBubble message={userMessage} onFeedback={vi.fn()} />);
    expect(screen.queryByLabelText('Thumbs up')).not.toBeInTheDocument();
  });

  it('shows feedback buttons for assistant messages when onFeedback provided', () => {
    render(<MessageBubble message={assistantMessage} onFeedback={vi.fn()} />);
    expect(screen.getByLabelText('Thumbs up')).toBeInTheDocument();
    expect(screen.getByLabelText('Thumbs down')).toBeInTheDocument();
  });

  it('does not show feedback buttons when onFeedback not provided', () => {
    render(<MessageBubble message={assistantMessage} />);
    expect(screen.queryByLabelText('Thumbs up')).not.toBeInTheDocument();
  });

  it('calls onFeedback with positive', () => {
    const onFeedback = vi.fn();
    render(<MessageBubble message={assistantMessage} onFeedback={onFeedback} />);

    fireEvent.click(screen.getByLabelText('Thumbs up'));
    expect(onFeedback).toHaveBeenCalledWith('msg-2', 'positive');
  });

  it('calls onFeedback with negative', () => {
    const onFeedback = vi.fn();
    render(<MessageBubble message={assistantMessage} onFeedback={onFeedback} />);

    fireEvent.click(screen.getByLabelText('Thumbs down'));
    expect(onFeedback).toHaveBeenCalledWith('msg-2', 'negative');
  });

  it('renders citations from metadata', () => {
    render(<MessageBubble message={messageWithCitations} />);

    expect(screen.getByText('Sources:')).toBeInTheDocument();
    expect(screen.getByText(/Guide\.pdf/)).toBeInTheDocument();
  });

  it('does not render citations section when no citations', () => {
    render(<MessageBubble message={assistantMessage} />);
    expect(screen.queryByText('Sources:')).not.toBeInTheDocument();
  });
});

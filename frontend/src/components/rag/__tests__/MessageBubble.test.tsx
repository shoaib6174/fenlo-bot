/**
 * Unit tests for MessageBubble component
 */
import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { MessageBubble } from '../MessageBubble';
import type { RAGMessage } from '@/types/rag';
import React from 'react';

const userMessage: RAGMessage = {
  id: 'msg-1',
  role: 'user',
  content: 'What is RAG?',
  timestamp: '2026-02-12T10:30:00Z',
};

const assistantMessage: RAGMessage = {
  id: 'msg-2',
  role: 'assistant',
  content: 'RAG stands for Retrieval-Augmented Generation.',
  timestamp: '2026-02-12T10:30:05Z',
};

const messageWithCitations: RAGMessage = {
  id: 'msg-3',
  role: 'assistant',
  content: 'Based on the documentation...',
  timestamp: '2026-02-12T10:30:10Z',
  citations: [
    {
      doc_name: 'RAG Guide.pdf',
      page_number: 1,
      chunk_text: 'RAG is a technique...',
      relevance_score: 0.92,
      document_id: 'doc-1',
    },
    {
      doc_name: 'AI Handbook.pdf',
      chunk_text: 'Generation with retrieval...',
      relevance_score: 0.85,
      document_id: 'doc-2',
    },
  ],
};

describe('MessageBubble', () => {
  it('renders user message content', () => {
    render(<MessageBubble message={userMessage} />);
    expect(screen.getByText('What is RAG?')).toBeInTheDocument();
  });

  it('renders assistant message content', () => {
    render(<MessageBubble message={assistantMessage} />);
    expect(screen.getByText('RAG stands for Retrieval-Augmented Generation.')).toBeInTheDocument();
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

  it('does not show feedback buttons when onFeedback is not provided', () => {
    render(<MessageBubble message={assistantMessage} />);
    expect(screen.queryByLabelText('Thumbs up')).not.toBeInTheDocument();
  });

  it('calls onFeedback with positive when thumbs up clicked', () => {
    const onFeedback = vi.fn();
    render(<MessageBubble message={assistantMessage} onFeedback={onFeedback} />);

    fireEvent.click(screen.getByLabelText('Thumbs up'));

    expect(onFeedback).toHaveBeenCalledWith('msg-2', 'positive');
  });

  it('calls onFeedback with negative when thumbs down clicked', () => {
    const onFeedback = vi.fn();
    render(<MessageBubble message={assistantMessage} onFeedback={onFeedback} />);

    fireEvent.click(screen.getByLabelText('Thumbs down'));

    expect(onFeedback).toHaveBeenCalledWith('msg-2', 'negative');
  });

  it('renders citations for assistant messages', () => {
    render(<MessageBubble message={messageWithCitations} />);

    expect(screen.getByText('Sources (2):')).toBeInTheDocument();
    expect(screen.getByText('RAG Guide.pdf')).toBeInTheDocument();
    expect(screen.getByText('AI Handbook.pdf')).toBeInTheDocument();
  });

  it('does not render citations section for user messages', () => {
    const userWithCitations = { ...userMessage, citations: messageWithCitations.citations };
    render(<MessageBubble message={userWithCitations} />);
    expect(screen.queryByText(/Sources/)).not.toBeInTheDocument();
  });

  it('does not render citations section when citations is empty', () => {
    const noCtMsg = { ...assistantMessage, citations: [] };
    render(<MessageBubble message={noCtMsg} />);
    expect(screen.queryByText(/Sources/)).not.toBeInTheDocument();
  });

  it('renders timestamp', () => {
    render(<MessageBubble message={userMessage} />);
    // toLocaleTimeString output varies by env, just check something time-like rendered
    const timeEl = screen.getByText(/\d{1,2}:\d{2}/);
    expect(timeEl).toBeInTheDocument();
  });
});

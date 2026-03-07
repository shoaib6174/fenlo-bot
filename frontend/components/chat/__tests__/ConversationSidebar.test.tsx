/**
 * Unit tests for ConversationSidebar component
 */
import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { ConversationSidebar } from '../ConversationSidebar';
import type { Conversation } from '@/lib/chat';
import React from 'react';

const conversations: Conversation[] = [
  {
    id: 'conv-1',
    title: 'Product Questions',
    lead_score: 75,
    started_at: '2026-02-10T10:00:00Z',
    message_count: 5,
  },
  {
    id: 'conv-2',
    title: 'Support Request',
    lead_score: 40,
    started_at: '2026-02-11T09:00:00Z',
    message_count: 3,
  },
  {
    id: 'conv-3',
    title: 'Cold Lead',
    lead_score: 10,
    started_at: '2026-02-12T08:00:00Z',
    message_count: 1,
  },
];

describe('ConversationSidebar', () => {
  it('renders New Chat button', () => {
    render(
      <ConversationSidebar
        conversations={[]}
        onSelectConversation={vi.fn()}
        onNewConversation={vi.fn()}
      />
    );
    expect(screen.getByText('New Chat')).toBeInTheDocument();
  });

  it('renders search input', () => {
    render(
      <ConversationSidebar
        conversations={[]}
        onSelectConversation={vi.fn()}
        onNewConversation={vi.fn()}
      />
    );
    expect(screen.getByPlaceholderText('Search conversations...')).toBeInTheDocument();
  });

  it('renders empty state when no conversations', () => {
    render(
      <ConversationSidebar
        conversations={[]}
        onSelectConversation={vi.fn()}
        onNewConversation={vi.fn()}
      />
    );
    expect(screen.getByText('No conversations yet')).toBeInTheDocument();
  });

  it('renders conversation titles', () => {
    render(
      <ConversationSidebar
        conversations={conversations}
        onSelectConversation={vi.fn()}
        onNewConversation={vi.fn()}
      />
    );
    expect(screen.getByText('Product Questions')).toBeInTheDocument();
    expect(screen.getByText('Support Request')).toBeInTheDocument();
    expect(screen.getByText('Cold Lead')).toBeInTheDocument();
  });

  it('renders lead score badges', () => {
    render(
      <ConversationSidebar
        conversations={conversations}
        onSelectConversation={vi.fn()}
        onNewConversation={vi.fn()}
      />
    );
    expect(screen.getByText('Hot')).toBeInTheDocument();   // 75
    expect(screen.getByText('Warm')).toBeInTheDocument();  // 40
    expect(screen.getByText('Cold')).toBeInTheDocument();  // 10
  });

  it('renders message counts', () => {
    render(
      <ConversationSidebar
        conversations={conversations}
        onSelectConversation={vi.fn()}
        onNewConversation={vi.fn()}
      />
    );
    expect(screen.getByText('5 messages')).toBeInTheDocument();
    expect(screen.getByText('3 messages')).toBeInTheDocument();
    expect(screen.getByText('1 message')).toBeInTheDocument();
  });

  it('calls onSelectConversation when conversation clicked', () => {
    const onSelect = vi.fn();
    render(
      <ConversationSidebar
        conversations={conversations}
        onSelectConversation={onSelect}
        onNewConversation={vi.fn()}
      />
    );

    fireEvent.click(screen.getByText('Product Questions'));
    expect(onSelect).toHaveBeenCalledWith('conv-1');
  });

  it('calls onNewConversation when New Chat clicked', () => {
    const onNew = vi.fn();
    render(
      <ConversationSidebar
        conversations={[]}
        onSelectConversation={vi.fn()}
        onNewConversation={onNew}
      />
    );

    fireEvent.click(screen.getByText('New Chat'));
    expect(onNew).toHaveBeenCalled();
  });

  it('filters conversations by search query', () => {
    render(
      <ConversationSidebar
        conversations={conversations}
        onSelectConversation={vi.fn()}
        onNewConversation={vi.fn()}
      />
    );

    const search = screen.getByPlaceholderText('Search conversations...');
    fireEvent.change(search, { target: { value: 'Product' } });

    expect(screen.getByText('Product Questions')).toBeInTheDocument();
    expect(screen.queryByText('Support Request')).not.toBeInTheDocument();
  });

  it('shows "No conversations found" when search has no results', () => {
    render(
      <ConversationSidebar
        conversations={conversations}
        onSelectConversation={vi.fn()}
        onNewConversation={vi.fn()}
      />
    );

    const search = screen.getByPlaceholderText('Search conversations...');
    fireEvent.change(search, { target: { value: 'nonexistent' } });

    expect(screen.getByText('No conversations found')).toBeInTheDocument();
  });

  it('highlights active conversation', () => {
    const { container } = render(
      <ConversationSidebar
        conversations={conversations}
        currentConversationId="conv-1"
        onSelectConversation={vi.fn()}
        onNewConversation={vi.fn()}
      />
    );

    const activeButton = screen.getByText('Product Questions').closest('button');
    expect(activeButton?.className).toContain('bg-blue-50');
  });
});

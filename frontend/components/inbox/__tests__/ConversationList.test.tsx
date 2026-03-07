/**
 * Unit tests for ConversationList component
 */
import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { ConversationList } from '../ConversationList';
import type { InboxConversation } from '@/lib/api';
import React from 'react';

const makeConversation = (overrides: Partial<InboxConversation> = {}): InboxConversation => ({
  id: 'conv-1',
  workspace_id: 'ws-1',
  channel: 'widget',
  contact_name: 'Alice Smith',
  contact_identifier: 'alice@example.com',
  status: 'active',
  lead_score: 5.0,
  last_message_at: new Date().toISOString(),
  last_message_preview: 'How do I reset my password?',
  created_at: '2026-02-10T12:00:00Z',
  ...overrides,
});

const conversations: InboxConversation[] = [
  makeConversation({ id: 'conv-1', contact_name: 'Alice Smith', lead_score: 7.5 }),
  makeConversation({
    id: 'conv-2',
    contact_name: 'Bob Jones',
    channel: 'whatsapp',
    status: 'escalated',
    lead_score: 3.0,
    last_message_preview: 'I need help with my order',
  }),
  makeConversation({
    id: 'conv-3',
    contact_name: undefined,
    contact_identifier: '+1234567890',
    channel: 'voice',
    status: 'closed',
    lead_score: 0,
    call_log: {
      id: 'cl-1',
      direction: 'inbound',
      status: 'ended',
      duration_sec: 125,
      phone_from: '+1234567890',
      phone_to: '+1987654321',
      summary: 'Customer asked about shipping',
      sentiment: null,
    },
  }),
];

describe('ConversationList', () => {
  it('renders empty state when no conversations', () => {
    render(
      <ConversationList conversations={[]} selectedId={null} onSelect={vi.fn()} />
    );
    expect(screen.getByText('No conversations found')).toBeInTheDocument();
  });

  it('renders all conversations', () => {
    render(
      <ConversationList conversations={conversations} selectedId={null} onSelect={vi.fn()} />
    );
    expect(screen.getByText('Alice Smith')).toBeInTheDocument();
    expect(screen.getByText('Bob Jones')).toBeInTheDocument();
  });

  it('shows message preview', () => {
    render(
      <ConversationList conversations={conversations} selectedId={null} onSelect={vi.fn()} />
    );
    expect(screen.getByText('How do I reset my password?')).toBeInTheDocument();
    expect(screen.getByText('I need help with my order')).toBeInTheDocument();
  });

  it('displays lead score badges', () => {
    render(
      <ConversationList conversations={conversations} selectedId={null} onSelect={vi.fn()} />
    );
    expect(screen.getByText('7.5')).toBeInTheDocument();
    expect(screen.getByText('3.0')).toBeInTheDocument();
  });

  it('displays status badges', () => {
    render(
      <ConversationList conversations={conversations} selectedId={null} onSelect={vi.fn()} />
    );
    expect(screen.getByText('Active')).toBeInTheDocument();
    expect(screen.getByText('Escalated')).toBeInTheDocument();
    expect(screen.getByText('Closed')).toBeInTheDocument();
  });

  it('calls onSelect when conversation is clicked', () => {
    const onSelect = vi.fn();
    render(
      <ConversationList conversations={conversations} selectedId={null} onSelect={onSelect} />
    );
    fireEvent.click(screen.getByText('Bob Jones'));
    expect(onSelect).toHaveBeenCalledWith('conv-2');
  });

  it('highlights selected conversation', () => {
    render(
      <ConversationList conversations={conversations} selectedId="conv-1" onSelect={vi.fn()} />
    );
    const buttons = screen.getAllByRole('button');
    expect(buttons[0].className).toContain('bg-blue-50');
    expect(buttons[1].className).not.toContain('bg-blue-50');
  });

  it('renders voice call with phone number', () => {
    render(
      <ConversationList conversations={conversations} selectedId={null} onSelect={vi.fn()} />
    );
    expect(screen.getByText('+1234567890')).toBeInTheDocument();
  });

  it('renders voice call summary as preview', () => {
    render(
      <ConversationList conversations={conversations} selectedId={null} onSelect={vi.fn()} />
    );
    expect(screen.getByText('Customer asked about shipping')).toBeInTheDocument();
  });

  it('shows voice call duration and status', () => {
    render(
      <ConversationList conversations={conversations} selectedId={null} onSelect={vi.fn()} />
    );
    expect(screen.getByText('Ended')).toBeInTheDocument();
    expect(screen.getByText('- 2m 5s')).toBeInTheDocument();
  });
});

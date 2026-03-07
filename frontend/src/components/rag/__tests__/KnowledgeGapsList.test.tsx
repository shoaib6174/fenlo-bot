/**
 * Unit tests for KnowledgeGapsList component
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { KnowledgeGapsList } from '../KnowledgeGapsList';
import type { KnowledgeGap } from '@/types/rag';
import React from 'react';

const gap1: KnowledgeGap = {
  id: 'gap-1',
  query_text: 'What is the return policy?',
  occurrence_count: 5,
  first_asked_at: '2026-02-01T10:00:00Z',
  last_asked_at: '2026-02-10T15:00:00Z',
  status: 'active',
  kb_id: 'kb-1',
  workspace_id: 'ws-1',
};

const gap2: KnowledgeGap = {
  id: 'gap-2',
  query_text: 'How do I contact support?',
  occurrence_count: 12,
  first_asked_at: '2026-01-20T08:00:00Z',
  last_asked_at: '2026-02-12T09:00:00Z',
  status: 'active',
  kb_id: 'kb-1',
  workspace_id: 'ws-1',
};

const dismissedGap: KnowledgeGap = {
  id: 'gap-3',
  query_text: 'Old question',
  occurrence_count: 1,
  first_asked_at: '2026-01-01T00:00:00Z',
  last_asked_at: '2026-01-01T00:00:00Z',
  status: 'dismissed',
  kb_id: 'kb-1',
  workspace_id: 'ws-1',
};

beforeEach(() => {
  vi.clearAllMocks();
  process.env.NEXT_PUBLIC_API_URL = 'http://localhost:8000';
  global.fetch = vi.fn();
});

describe('KnowledgeGapsList', () => {
  it('renders empty state when no active gaps', () => {
    render(<KnowledgeGapsList gaps={[]} />);
    expect(screen.getByText('No Knowledge Gaps!')).toBeInTheDocument();
    expect(screen.getByText(/Your chatbot can answer all common questions/)).toBeInTheDocument();
  });

  it('renders empty state when all gaps are dismissed', () => {
    render(<KnowledgeGapsList gaps={[dismissedGap]} />);
    expect(screen.getByText('No Knowledge Gaps!')).toBeInTheDocument();
  });

  it('renders active gaps with their query text', () => {
    render(<KnowledgeGapsList gaps={[gap1, gap2]} />);
    expect(screen.getByText(/What is the return policy/)).toBeInTheDocument();
    expect(screen.getByText(/How do I contact support/)).toBeInTheDocument();
  });

  it('renders occurrence count badges', () => {
    render(<KnowledgeGapsList gaps={[gap1, gap2]} />);
    expect(screen.getByText('5x')).toBeInTheDocument();
    expect(screen.getByText('12x')).toBeInTheDocument();
  });

  it('sorts gaps by occurrence count (highest first)', () => {
    render(<KnowledgeGapsList gaps={[gap1, gap2]} />);

    const badges = screen.getAllByText(/\dx/);
    // gap2 (12x) should come before gap1 (5x)
    expect(badges[0].textContent).toBe('12x');
    expect(badges[1].textContent).toBe('5x');
  });

  it('shows warning banner when active gaps exist', () => {
    render(<KnowledgeGapsList gaps={[gap1]} />);
    expect(screen.getByText('Knowledge Gaps Detected')).toBeInTheDocument();
  });

  it('renders "Add to KB" button for each gap', () => {
    render(<KnowledgeGapsList gaps={[gap1, gap2]} />);
    const addButtons = screen.getAllByText('Add to KB');
    expect(addButtons).toHaveLength(2);
  });

  it('calls onAddress when "Add to KB" button clicked', () => {
    const onAddress = vi.fn();
    render(<KnowledgeGapsList gaps={[gap1]} onAddress={onAddress} />);

    fireEvent.click(screen.getByText('Add to KB'));
    expect(onAddress).toHaveBeenCalledWith('gap-1', 'What is the return policy?');
  });

  it('calls API on dismiss and invokes onDismiss callback', async () => {
    (global.fetch as any).mockResolvedValueOnce({ ok: true });
    const onDismiss = vi.fn();

    render(<KnowledgeGapsList gaps={[gap1]} onDismiss={onDismiss} />);

    // The dismiss button has an X icon, find it by title
    const dismissBtn = screen.getByTitle('Dismiss this gap');
    fireEvent.click(dismissBtn);

    await waitFor(() => {
      expect(global.fetch).toHaveBeenCalledWith(
        'http://localhost:8000/api/v1/kb/gaps/gap-1/dismiss',
        expect.objectContaining({ method: 'POST', credentials: 'include' })
      );
    });

    await waitFor(() => {
      expect(onDismiss).toHaveBeenCalledWith('gap-1');
    });
  });

  it('filters out dismissed gaps from display', () => {
    render(<KnowledgeGapsList gaps={[gap1, dismissedGap]} />);
    expect(screen.getByText(/What is the return policy/)).toBeInTheDocument();
    expect(screen.queryByText(/Old question/)).not.toBeInTheDocument();
  });
});

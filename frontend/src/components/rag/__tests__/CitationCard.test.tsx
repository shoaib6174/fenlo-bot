/**
 * Unit tests for CitationCard component
 */
import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { CitationCard } from '../CitationCard';
import type { Citation } from '@/types/rag';
import React from 'react';

const baseCitation: Citation = {
  doc_name: 'Technical Manual.pdf',
  page_number: 42,
  chunk_text: 'This is the relevant chunk text from the document that was matched.',
  relevance_score: 0.95,
  document_id: 'doc-123',
};

describe('CitationCard', () => {
  it('renders document name', () => {
    render(<CitationCard citation={baseCitation} index={0} />);
    expect(screen.getByText('Technical Manual.pdf')).toBeInTheDocument();
  });

  it('renders 1-based index number', () => {
    render(<CitationCard citation={baseCitation} index={0} />);
    expect(screen.getByText('1')).toBeInTheDocument();
  });

  it('renders page number when provided', () => {
    render(<CitationCard citation={baseCitation} index={0} />);
    expect(screen.getByText('(Page 42)')).toBeInTheDocument();
  });

  it('does not render page number when not provided', () => {
    const noPgCitation = { ...baseCitation, page_number: undefined };
    render(<CitationCard citation={noPgCitation} index={0} />);
    expect(screen.queryByText(/Page/)).not.toBeInTheDocument();
  });

  it('renders chunk text', () => {
    render(<CitationCard citation={baseCitation} index={0} />);
    expect(screen.getByText(baseCitation.chunk_text)).toBeInTheDocument();
  });

  it('renders relevance score as percentage', () => {
    render(<CitationCard citation={baseCitation} index={0} />);
    expect(screen.getByText('Relevance: 95%')).toBeInTheDocument();
  });

  it('handles low relevance score', () => {
    const lowScore = { ...baseCitation, relevance_score: 0.123 };
    render(<CitationCard citation={lowScore} index={0} />);
    expect(screen.getByText('Relevance: 12%')).toBeInTheDocument();
  });

  it('renders correct index for non-zero index', () => {
    render(<CitationCard citation={baseCitation} index={4} />);
    expect(screen.getByText('5')).toBeInTheDocument();
  });
});

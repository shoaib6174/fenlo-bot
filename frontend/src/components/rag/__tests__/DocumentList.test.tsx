/**
 * Unit tests for DocumentList component
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { DocumentList } from '../DocumentList';
import type { Document } from '@/types/rag';
import React from 'react';

const readyDoc: Document = {
  id: 'doc-1',
  filename: 'Manual.pdf',
  file_type: 'pdf',
  file_size: 1024000,
  status: 'ready',
  kb_id: 'kb-1',
  chunk_count: 25,
  metadata_: null,
  created_at: '2026-02-10T10:00:00Z',
  processed_at: '2026-02-10T10:01:00Z',
};

const processingDoc: Document = {
  id: 'doc-2',
  filename: 'Report.docx',
  file_type: 'docx',
  file_size: 512000,
  status: 'processing',
  kb_id: 'kb-1',
  chunk_count: null,
  metadata_: null,
  created_at: '2026-02-11T09:00:00Z',
  processed_at: null,
};

const failedDoc: Document = {
  id: 'doc-3',
  filename: 'Corrupt.pdf',
  file_type: 'pdf',
  file_size: 100,
  status: 'failed',
  kb_id: 'kb-1',
  chunk_count: null,
  metadata_: { error: 'PDF parsing failed: corrupted file' },
  created_at: '2026-02-11T10:00:00Z',
  processed_at: null,
};

beforeEach(() => {
  vi.clearAllMocks();
  global.fetch = vi.fn();
  global.confirm = vi.fn(() => true);
});

describe('DocumentList', () => {
  it('renders empty state when no documents', () => {
    render(<DocumentList documents={[]} />);
    expect(screen.getByText('No documents uploaded yet')).toBeInTheDocument();
  });

  it('renders document filenames', () => {
    render(<DocumentList documents={[readyDoc, processingDoc]} />);
    expect(screen.getByText('Manual.pdf')).toBeInTheDocument();
    expect(screen.getByText('Report.docx')).toBeInTheDocument();
  });

  it('renders correct status badges', () => {
    render(<DocumentList documents={[readyDoc, processingDoc, failedDoc]} />);
    expect(screen.getByText('ready')).toBeInTheDocument();
    expect(screen.getByText('processing')).toBeInTheDocument();
    expect(screen.getByText('failed')).toBeInTheDocument();
  });

  it('shows chunk count for ready documents', () => {
    render(<DocumentList documents={[readyDoc]} />);
    expect(screen.getByText('25 chunks indexed')).toBeInTheDocument();
  });

  it('shows error message for failed documents', () => {
    render(<DocumentList documents={[failedDoc]} />);
    expect(screen.getByText('Error: PDF parsing failed: corrupted file')).toBeInTheDocument();
  });

  it('shows retry button only for failed documents', () => {
    render(<DocumentList documents={[readyDoc, failedDoc]} />);
    const retryButtons = screen.getAllByText('Retry');
    expect(retryButtons).toHaveLength(1);
  });

  it('shows delete button for all documents', () => {
    render(<DocumentList documents={[readyDoc, processingDoc, failedDoc]} />);
    const deleteButtons = screen.getAllByText('Delete');
    expect(deleteButtons).toHaveLength(3);
  });

  it('calls confirm and API on delete, then invokes onDelete callback', async () => {
    (global.fetch as any).mockResolvedValueOnce({ ok: true });
    const onDelete = vi.fn();

    render(<DocumentList documents={[readyDoc]} onDelete={onDelete} />);
    fireEvent.click(screen.getByText('Delete'));

    expect(global.confirm).toHaveBeenCalled();

    await waitFor(() => {
      expect(global.fetch).toHaveBeenCalledWith(
        expect.stringContaining('/api/v1/docs/doc-1'),
        expect.objectContaining({ method: 'DELETE' })
      );
    });

    await waitFor(() => {
      expect(onDelete).toHaveBeenCalledWith('doc-1');
    });
  });

  it('does not delete when confirm is cancelled', () => {
    (global.confirm as any).mockReturnValueOnce(false);
    const onDelete = vi.fn();

    render(<DocumentList documents={[readyDoc]} onDelete={onDelete} />);
    fireEvent.click(screen.getByText('Delete'));

    expect(global.fetch).not.toHaveBeenCalled();
    expect(onDelete).not.toHaveBeenCalled();
  });

  it('calls API on retry and invokes onRetry callback', async () => {
    (global.fetch as any).mockResolvedValueOnce({ ok: true });
    const onRetry = vi.fn();

    render(<DocumentList documents={[failedDoc]} onRetry={onRetry} />);
    fireEvent.click(screen.getByText('Retry'));

    await waitFor(() => {
      expect(global.fetch).toHaveBeenCalledWith(
        expect.stringContaining('/api/v1/docs/doc-3/retry'),
        expect.objectContaining({ method: 'POST' })
      );
    });

    await waitFor(() => {
      expect(onRetry).toHaveBeenCalledWith('doc-3');
    });
  });

  it('shows file type in uppercase', () => {
    render(<DocumentList documents={[readyDoc]} />);
    expect(screen.getByText(/PDF/)).toBeInTheDocument();
  });
});

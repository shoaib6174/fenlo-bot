/**
 * Unit tests for DocumentUpload component
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { DocumentUpload } from '../DocumentUpload';
import React from 'react';

beforeEach(() => {
  vi.clearAllMocks();
  process.env.NEXT_PUBLIC_API_URL = 'http://localhost:8000';
  global.fetch = vi.fn();
});

function createFile(name: string, type: string, size = 1024): File {
  const content = new Uint8Array(size);
  return new File([content], name, { type });
}

describe('DocumentUpload', () => {
  it('renders drop zone with instructions', () => {
    render(<DocumentUpload kbId="kb-1" />);
    expect(screen.getByText('Drop files here or click to browse')).toBeInTheDocument();
    expect(screen.getByText(/PDF, DOCX, and TXT/)).toBeInTheDocument();
  });

  it('renders hidden file input with correct accept types', () => {
    render(<DocumentUpload kbId="kb-1" />);
    const input = document.querySelector('input[type="file"]') as HTMLInputElement;
    expect(input).toBeTruthy();
    expect(input.accept).toBe('.pdf,.docx,.txt');
    expect(input.multiple).toBe(true);
    expect(input.className).toContain('hidden');
  });

  it('uploads file via fetch on file select', async () => {
    (global.fetch as any).mockResolvedValueOnce({ ok: true, json: async () => ({}) });
    const onComplete = vi.fn();

    render(<DocumentUpload kbId="kb-1" onUploadComplete={onComplete} />);

    const input = document.querySelector('input[type="file"]') as HTMLInputElement;
    const file = createFile('test.pdf', 'application/pdf');

    fireEvent.change(input, { target: { files: [file] } });

    await waitFor(() => {
      expect(global.fetch).toHaveBeenCalledWith(
        'http://localhost:8000/api/v1/docs/upload',
        expect.objectContaining({
          method: 'POST',
          credentials: 'include',
        })
      );
    });

    // Check FormData was sent (fetch was called with FormData body)
    const callArgs = (global.fetch as any).mock.calls[0];
    expect(callArgs[1].body).toBeInstanceOf(FormData);

    await waitFor(() => {
      expect(onComplete).toHaveBeenCalled();
    });
  });

  it('shows success status after upload', async () => {
    (global.fetch as any).mockResolvedValueOnce({ ok: true, json: async () => ({}) });

    render(<DocumentUpload kbId="kb-1" />);

    const input = document.querySelector('input[type="file"]') as HTMLInputElement;
    const file = createFile('test.pdf', 'application/pdf');

    fireEvent.change(input, { target: { files: [file] } });

    await waitFor(() => {
      expect(screen.getByText('test.pdf')).toBeInTheDocument();
    });
  });

  it('shows error status when upload fails', async () => {
    (global.fetch as any).mockResolvedValueOnce({
      ok: false,
      json: async () => ({ detail: 'File too large' }),
    });

    render(<DocumentUpload kbId="kb-1" />);

    const input = document.querySelector('input[type="file"]') as HTMLInputElement;
    const file = createFile('big.pdf', 'application/pdf');

    fireEvent.change(input, { target: { files: [file] } });

    await waitFor(() => {
      expect(screen.getByText('File too large')).toBeInTheDocument();
    });
  });

  it('handles drag over styling', () => {
    render(<DocumentUpload kbId="kb-1" />);
    const dropZone = screen.getByText('Drop files here or click to browse').closest('div')!;

    fireEvent.dragOver(dropZone, { dataTransfer: { files: [] } });
    // After dragOver, the component should have isDragging state
    // The outer div class should contain the blue styling
    expect(dropZone.className).toContain('border-blue-500');
  });

  it('handles drag leave', () => {
    render(<DocumentUpload kbId="kb-1" />);
    const dropZone = screen.getByText('Drop files here or click to browse').closest('div')!;

    fireEvent.dragOver(dropZone, { dataTransfer: { files: [] } });
    fireEvent.dragLeave(dropZone);

    expect(dropZone.className).not.toContain('border-blue-500');
  });
});

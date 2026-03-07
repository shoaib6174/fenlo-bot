/**
 * Unit tests for WidgetSetup component (S78)
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { WidgetSetup } from '../WidgetSetup';
import { channelApi, type ChannelConfig } from '@/lib/api';
import React from 'react';

// Mock the API
vi.mock('@/lib/api', () => ({
  channelApi: {
    getEmbedCode: vi.fn(),
  },
  useCreateChannel: vi.fn(() => ({
    mutateAsync: vi.fn(),
    isPending: false,
  })),
  useUpdateChannel: vi.fn(() => ({
    mutateAsync: vi.fn(),
    isPending: false,
  })),
}));

// Mock useCreateChannel and useUpdateChannel hooks
vi.mock('@/hooks/useChannels', () => ({
  useCreateChannel: () => ({
    mutateAsync: vi.fn(),
    isPending: false,
  }),
  useUpdateChannel: () => ({
    mutateAsync: vi.fn(),
    isPending: false,
  }),
}));

// Mock sonner toast
vi.mock('sonner', () => ({
  toast: {
    success: vi.fn(),
    error: vi.fn(),
  },
}));

const mockChannel: ChannelConfig = {
  id: 'widget-123',
  workspace_id: 'ws-456',
  channel: 'widget',
  provider: null,
  config: {
    primary_color: '#3b82f6',
    position: 'bottom-right',
    greeting: 'Hello! How can I help?',
    allowed_domains: ['example.com'],
  },
  is_active: true,
  created_at: '2026-02-16T12:00:00Z',
};

const mockEmbedCodeResponse = {
  html: '<script src="https://bot.fenloai.com/widget.js" data-widget-id="widget-123" data-hmac="abc123..." data-timestamp="1234567890" data-theme="light" data-position="bottom-right"></script>',
  widget_id: 'widget-123',
  widget_url: 'https://bot.fenloai.com/widget.js',
};

// Mock clipboard writeText function
const mockWriteText = vi.fn(() => Promise.resolve());

// Mock clipboard API (do this once globally for the test suite)
Object.defineProperty(navigator, 'clipboard', {
  value: {
    writeText: mockWriteText,
  },
  writable: false,
  configurable: true,
});

describe('WidgetSetup - Embed Code', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockWriteText.mockClear();
  });

  it('fetches and displays embed code when channel is provided', async () => {
    vi.mocked(channelApi.getEmbedCode).mockResolvedValue(mockEmbedCodeResponse);

    render(<WidgetSetup channel={mockChannel} workspaceId="ws-456" />);

    // Wait for embed code to load
    await waitFor(() => {
      expect(channelApi.getEmbedCode).toHaveBeenCalledWith('widget-123');
    });

    // Check embed code is displayed
    await waitFor(() => {
      expect(screen.getByText(/data-widget-id="widget-123"/)).toBeInTheDocument();
    });
  });

  it('shows loading state while fetching embed code', async () => {
    vi.mocked(channelApi.getEmbedCode).mockImplementation(
      () => new Promise((resolve) => setTimeout(() => resolve(mockEmbedCodeResponse), 100))
    );

    render(<WidgetSetup channel={mockChannel} workspaceId="ws-456" />);

    // Should show loading message
    expect(screen.getByText('Loading embed code...')).toBeInTheDocument();

    // Wait for loading to complete
    await waitFor(() => {
      expect(screen.queryByText('Loading embed code...')).not.toBeInTheDocument();
    });
  });

  it('shows error message when embed code fetch fails', async () => {
    vi.mocked(channelApi.getEmbedCode).mockRejectedValue(new Error('Network error'));

    render(<WidgetSetup channel={mockChannel} workspaceId="ws-456" />);

    // Wait for error state
    await waitFor(() => {
      expect(
        screen.getByText('Failed to load embed code. Please refresh the page.')
      ).toBeInTheDocument();
    });
  });

  it('shows success message when Copy button is clicked', async () => {
    vi.mocked(channelApi.getEmbedCode).mockResolvedValue(mockEmbedCodeResponse);
    const user = userEvent.setup();

    render(<WidgetSetup channel={mockChannel} workspaceId="ws-456" />);

    // Wait for embed code to load
    await waitFor(() => {
      expect(screen.getByText(/data-widget-id/)).toBeInTheDocument();
    });

    // Wait for copy button to be enabled
    const copyButton = await screen.findByRole('button', { name: /copy/i });
    await waitFor(() => {
      expect(copyButton).not.toBeDisabled();
    });

    // Click copy button
    await user.click(copyButton);

    // Verify button shows success state (clipboard copy succeeded)
    await waitFor(() => {
      expect(screen.getByText(/copied!/i)).toBeInTheDocument();
    });
  });

  it('disables copy button when embed code is not loaded', () => {
    vi.mocked(channelApi.getEmbedCode).mockImplementation(
      () => new Promise(() => {}) // Never resolves
    );

    render(<WidgetSetup channel={mockChannel} workspaceId="ws-456" />);

    const copyButton = screen.getByRole('button', { name: /copy/i });
    expect(copyButton).toBeDisabled();
  });

  it('displays embed code with HMAC authentication note', async () => {
    vi.mocked(channelApi.getEmbedCode).mockResolvedValue(mockEmbedCodeResponse);

    render(<WidgetSetup channel={mockChannel} workspaceId="ws-456" />);

    await waitFor(() => {
      expect(
        screen.getByText(/The embed code includes HMAC authentication/i)
      ).toBeInTheDocument();
    });
  });

  it('displays installation instructions', async () => {
    vi.mocked(channelApi.getEmbedCode).mockResolvedValue(mockEmbedCodeResponse);

    render(<WidgetSetup channel={mockChannel} workspaceId="ws-456" />);

    await waitFor(() => {
      expect(screen.getByText(/Paste this code into your website/i)).toBeInTheDocument();
      expect(screen.getByText(/<\/body>/)).toBeInTheDocument();
    });
  });

  it('does not show embed code section when channel is not provided', () => {
    render(<WidgetSetup workspaceId="ws-456" />);

    expect(screen.queryByText('Embed Code')).not.toBeInTheDocument();
  });

  it('includes data-hmac attribute in embed code', async () => {
    vi.mocked(channelApi.getEmbedCode).mockResolvedValue(mockEmbedCodeResponse);

    render(<WidgetSetup channel={mockChannel} workspaceId="ws-456" />);

    await waitFor(() => {
      const codeElement = screen.getByText(/data-hmac/);
      expect(codeElement.textContent).toContain('data-hmac');
      expect(codeElement.textContent).toContain('data-timestamp');
    });
  });

  it('includes theme and position attributes in embed code', async () => {
    vi.mocked(channelApi.getEmbedCode).mockResolvedValue(mockEmbedCodeResponse);

    render(<WidgetSetup channel={mockChannel} workspaceId="ws-456" />);

    await waitFor(() => {
      const codeElement = screen.getByText(/data-theme/);
      expect(codeElement.textContent).toContain('data-theme="light"');
      expect(codeElement.textContent).toContain('data-position="bottom-right"');
    });
  });
});

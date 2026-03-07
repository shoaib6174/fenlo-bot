/**
 * Unit tests for ConnectionStatus component
 * Tests: status display for connecting/disconnected/reconnecting, hidden when connected, error display
 */
import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { ConnectionStatus } from '../ConnectionStatus';

describe('ConnectionStatus', () => {
  it('returns null when connected (no banner shown)', () => {
    const { container } = render(<ConnectionStatus state="connected" />);
    expect(container.firstChild).toBeNull();
  });

  it('shows "Connecting..." banner when connecting', () => {
    render(<ConnectionStatus state="connecting" />);
    expect(screen.getByText('Connecting...')).toBeInTheDocument();
  });

  it('shows "Disconnected" banner when disconnected', () => {
    render(<ConnectionStatus state="disconnected" />);
    expect(screen.getByText('Disconnected')).toBeInTheDocument();
  });

  it('shows "Reconnecting..." banner when reconnecting', () => {
    render(<ConnectionStatus state="reconnecting" />);
    expect(screen.getByText('Reconnecting...')).toBeInTheDocument();
  });

  it('shows error detail when disconnected with error', () => {
    render(<ConnectionStatus state="disconnected" error="Connection lost. Please refresh the page." />);
    expect(screen.getByText('Disconnected')).toBeInTheDocument();
    expect(screen.getByText(/Connection lost/)).toBeInTheDocument();
  });

  it('does not show error when connecting (only when disconnected)', () => {
    render(<ConnectionStatus state="connecting" error="Some error" />);
    expect(screen.getByText('Connecting...')).toBeInTheDocument();
    expect(screen.queryByText(/Some error/)).not.toBeInTheDocument();
  });

  it('applies correct CSS classes for each state', () => {
    const { rerender, container } = render(<ConnectionStatus state="connecting" />);
    expect(container.firstChild).toHaveClass('bg-yellow-50');

    rerender(<ConnectionStatus state="disconnected" />);
    expect(container.firstChild).toHaveClass('bg-red-50');

    rerender(<ConnectionStatus state="reconnecting" />);
    expect(container.firstChild).toHaveClass('bg-amber-50');
  });
});

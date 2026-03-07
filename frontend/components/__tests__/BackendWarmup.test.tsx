/**
 * Unit tests for BackendWarmup component
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render } from '@testing-library/react';
import { BackendWarmup } from '../BackendWarmup';
import React from 'react';

beforeEach(() => {
  vi.clearAllMocks();
  global.fetch = vi.fn().mockResolvedValue({ ok: true });
});

afterEach(() => {
  vi.restoreAllMocks();
});

describe('BackendWarmup', () => {
  it('renders nothing', () => {
    vi.stubEnv('NODE_ENV', 'test');
    const { container } = render(<BackendWarmup />);
    expect(container.innerHTML).toBe('');
  });

  it('does not ping in non-production without ENABLE_WARMUP', () => {
    vi.stubEnv('NODE_ENV', 'test');
    delete process.env.NEXT_PUBLIC_ENABLE_WARMUP;
    render(<BackendWarmup />);
    expect(global.fetch).not.toHaveBeenCalled();
  });

  it('pings health endpoint when ENABLE_WARMUP is set', async () => {
    process.env.NEXT_PUBLIC_ENABLE_WARMUP = 'true';
    process.env.NEXT_PUBLIC_API_URL = 'http://localhost:8000';

    render(<BackendWarmup />);

    // useEffect fires async
    await vi.waitFor(() => {
      expect(global.fetch).toHaveBeenCalledWith(
        'http://localhost:8000/api/health/live',
        expect.objectContaining({ method: 'GET', credentials: 'omit' })
      );
    });

    delete process.env.NEXT_PUBLIC_ENABLE_WARMUP;
  });

  it('silently handles fetch failure', async () => {
    process.env.NEXT_PUBLIC_ENABLE_WARMUP = 'true';
    (global.fetch as any).mockRejectedValueOnce(new Error('Network error'));

    // Should not throw — errors are silently swallowed
    render(<BackendWarmup />);

    await vi.waitFor(() => {
      expect(global.fetch).toHaveBeenCalled();
    });

    delete process.env.NEXT_PUBLIC_ENABLE_WARMUP;
  });
});

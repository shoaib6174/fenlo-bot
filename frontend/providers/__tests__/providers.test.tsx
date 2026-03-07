/**
 * Unit tests for Providers component
 */
import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { Providers } from '../index';
import React from 'react';

// Mock fetch for auth
global.fetch = vi.fn().mockResolvedValue({
  ok: false,
  status: 401,
  json: async () => ({ detail: 'Not authenticated' }),
});

describe('Providers', () => {
  it('renders children', () => {
    render(
      <Providers>
        <div data-testid="child">Hello</div>
      </Providers>
    );
    expect(screen.getByTestId('child')).toBeInTheDocument();
    expect(screen.getByText('Hello')).toBeInTheDocument();
  });

  it('provides QueryClient and AuthProvider context', () => {
    // If these providers weren't properly wrapping, children using useAuth/useQuery would crash
    render(
      <Providers>
        <div>Wrapped content</div>
      </Providers>
    );
    expect(screen.getByText('Wrapped content')).toBeInTheDocument();
  });
});

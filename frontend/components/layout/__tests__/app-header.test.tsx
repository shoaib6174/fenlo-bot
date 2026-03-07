/**
 * Unit tests for AppHeader component
 */
import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { AppHeader } from '../app-header';
import React from 'react';

// Mock Next.js navigation
let mockPathname = '/dashboard';
vi.mock('next/navigation', () => ({
  usePathname: () => mockPathname,
}));

describe('AppHeader', () => {
  it('renders hamburger menu button', () => {
    render(<AppHeader />);
    expect(screen.getByLabelText('Open menu')).toBeInTheDocument();
  });

  it('calls onMenuClick when hamburger clicked', () => {
    const onMenuClick = vi.fn();
    render(<AppHeader onMenuClick={onMenuClick} />);

    fireEvent.click(screen.getByLabelText('Open menu'));
    expect(onMenuClick).toHaveBeenCalled();
  });

  it('renders breadcrumbs for dashboard', () => {
    mockPathname = '/dashboard';
    render(<AppHeader />);
    expect(screen.getByText('Dashboard')).toBeInTheDocument();
  });

  it('renders breadcrumbs for chat with parent', () => {
    mockPathname = '/chat';
    render(<AppHeader />);
    expect(screen.getAllByText('Dashboard')).toHaveLength(1); // parent crumb
    expect(screen.getByText('Chat')).toBeInTheDocument();
  });

  it('renders breadcrumbs for kb', () => {
    mockPathname = '/kb';
    render(<AppHeader />);
    expect(screen.getByText('Knowledge Base')).toBeInTheDocument();
  });

  it('renders breadcrumbs for settings', () => {
    mockPathname = '/settings';
    render(<AppHeader />);
    expect(screen.getByText('Settings')).toBeInTheDocument();
  });

  it('falls back to Dashboard for unknown paths', () => {
    mockPathname = '/unknown';
    render(<AppHeader />);
    expect(screen.getByText('Dashboard')).toBeInTheDocument();
  });
});

/**
 * Unit tests for AppSidebar component
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { AppSidebar } from '../app-sidebar';
import React from 'react';

// Mock Next.js navigation
const mockPush = vi.fn();
vi.mock('next/navigation', () => ({
  usePathname: () => '/dashboard',
  useRouter: () => ({ push: mockPush }),
}));

// Mock auth provider
const mockLogout = vi.fn().mockResolvedValue(undefined);
vi.mock('@/providers/auth', () => ({
  useAuth: () => ({
    user: { name: 'Test User', email: 'test@example.com', role: 'admin' },
    logout: mockLogout,
  }),
}));

// Mock next/link to render as <a>
vi.mock('next/link', () => ({
  default: ({ children, href, onClick, className }: any) => (
    <a href={href} onClick={onClick} className={className}>
      {children}
    </a>
  ),
}));

beforeEach(() => {
  vi.clearAllMocks();
});

describe('AppSidebar', () => {
  it('renders BotForge header', () => {
    render(<AppSidebar />);
    expect(screen.getByText('BotForge')).toBeInTheDocument();
    expect(screen.getByText('AI Chatbot Platform')).toBeInTheDocument();
  });

  it('renders core nav items', () => {
    render(<AppSidebar />);
    expect(screen.getByText('Dashboard')).toBeInTheDocument();
    expect(screen.getByText('Chat')).toBeInTheDocument();
    expect(screen.getByText('Knowledge Base')).toBeInTheDocument();
  });

  it('renders product section with all features live', () => {
    render(<AppSidebar />);
    expect(screen.getByText('Products')).toBeInTheDocument();
    expect(screen.getByText('Voice')).toBeInTheDocument();
    expect(screen.getByText('Channels')).toBeInTheDocument();
    expect(screen.getByText('Analytics')).toBeInTheDocument();
  });

  it('renders system section with Settings', () => {
    render(<AppSidebar />);
    expect(screen.getByText('System')).toBeInTheDocument();
    expect(screen.getByText('Settings')).toBeInTheDocument();
  });

  it('renders user info', () => {
    render(<AppSidebar />);
    expect(screen.getByText('Test User')).toBeInTheDocument();
    expect(screen.getByText('admin')).toBeInTheDocument();
  });

  it('calls logout and redirects on logout click', async () => {
    render(<AppSidebar />);
    const logoutBtn = screen.getByLabelText('Logout');

    fireEvent.click(logoutBtn);

    expect(mockLogout).toHaveBeenCalled();
    // Wait for async logout
    await vi.waitFor(() => {
      expect(mockPush).toHaveBeenCalledWith('/');
    });
  });

  it('renders correct nav links with hrefs', () => {
    render(<AppSidebar />);
    const dashboardLink = screen.getByText('Dashboard').closest('a');
    expect(dashboardLink).toHaveAttribute('href', '/dashboard');

    const chatLink = screen.getByText('Chat').closest('a');
    expect(chatLink).toHaveAttribute('href', '/chat');

    const kbLink = screen.getByText('Knowledge Base').closest('a');
    expect(kbLink).toHaveAttribute('href', '/kb');
  });

  describe('mobile mode', () => {
    it('renders close button in mobile mode', () => {
      render(<AppSidebar isMobile isOpen onClose={vi.fn()} />);
      expect(screen.getByLabelText('Close sidebar')).toBeInTheDocument();
    });

    it('does not render close button in desktop mode', () => {
      render(<AppSidebar />);
      expect(screen.queryByLabelText('Close sidebar')).not.toBeInTheDocument();
    });

    it('calls onClose when close button clicked', () => {
      const onClose = vi.fn();
      render(<AppSidebar isMobile isOpen onClose={onClose} />);

      fireEvent.click(screen.getByLabelText('Close sidebar'));
      expect(onClose).toHaveBeenCalled();
    });

    it('calls onClose when backdrop clicked', () => {
      const onClose = vi.fn();
      const { container } = render(<AppSidebar isMobile isOpen onClose={onClose} />);

      // The backdrop is the first child div with bg-black
      const backdrop = container.querySelector('.bg-black');
      if (backdrop) {
        fireEvent.click(backdrop);
        expect(onClose).toHaveBeenCalled();
      }
    });

    it('calls onClose when nav item clicked in mobile', () => {
      const onClose = vi.fn();
      render(<AppSidebar isMobile isOpen onClose={onClose} />);

      fireEvent.click(screen.getByText('Chat'));
      expect(onClose).toHaveBeenCalled();
    });
  });
});

/**
 * Unit tests for ChannelCard component
 */
import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { ChannelCard } from '../ChannelCard';
import type { ChannelConfig } from '@/lib/api';
import React from 'react';

const baseChannel: ChannelConfig = {
  id: 'ch-1',
  workspace_id: 'ws-1',
  channel: 'widget',
  provider: null,
  config: { position: 'bottom-right' },
  is_active: true,
  created_at: '2026-02-10T12:00:00Z',
};

describe('ChannelCard', () => {
  it('renders widget channel with title and subtitle', () => {
    render(<ChannelCard channel={baseChannel} />);
    expect(screen.getByText('Website Widget')).toBeInTheDocument();
    expect(screen.getByText('Embeddable chat widget')).toBeInTheDocument();
  });

  it('shows Active badge when channel is active', () => {
    render(<ChannelCard channel={baseChannel} />);
    expect(screen.getByText('Active')).toBeInTheDocument();
  });

  it('shows Inactive badge when channel is not active', () => {
    render(<ChannelCard channel={{ ...baseChannel, is_active: false }} />);
    expect(screen.getByText('Inactive')).toBeInTheDocument();
  });

  it('renders whatsapp channel correctly', () => {
    const whatsappChannel: ChannelConfig = {
      ...baseChannel,
      channel: 'whatsapp',
      provider: 'twilio',
      config: { phone: '+1234567890' },
    };
    render(<ChannelCard channel={whatsappChannel} />);
    expect(screen.getByText('WhatsApp')).toBeInTheDocument();
    expect(screen.getByText('Twilio WhatsApp Business')).toBeInTheDocument();
    expect(screen.getByText('Phone: +1234567890')).toBeInTheDocument();
  });

  it('renders voice channel correctly', () => {
    const voiceChannel: ChannelConfig = {
      ...baseChannel,
      channel: 'voice',
      config: { phone_number: '+1987654321' },
    };
    render(<ChannelCard channel={voiceChannel} />);
    expect(screen.getByText('Voice')).toBeInTheDocument();
    expect(screen.getByText('Phone calls via Vapi')).toBeInTheDocument();
  });

  it('renders telegram channel correctly', () => {
    const telegramChannel: ChannelConfig = {
      ...baseChannel,
      channel: 'telegram',
      config: { bot_username: 'mybot' },
    };
    render(<ChannelCard channel={telegramChannel} />);
    expect(screen.getByText('Telegram')).toBeInTheDocument();
    expect(screen.getByText('@mybot')).toBeInTheDocument();
  });

  it('links to channel detail page', () => {
    render(<ChannelCard channel={baseChannel} />);
    const link = screen.getByRole('link');
    expect(link).toHaveAttribute('href', '/channels/ch-1');
  });

  it('displays the creation date', () => {
    render(<ChannelCard channel={baseChannel} />);
    // Date formatting is locale-dependent; just check a link exists and date is rendered
    const link = screen.getByRole('link');
    expect(link.textContent).toContain('2026');
  });

  it('shows widget position detail', () => {
    render(<ChannelCard channel={baseChannel} />);
    expect(screen.getByText('Position: bottom-right')).toBeInTheDocument();
  });

  it('renders unknown channel type with fallback', () => {
    const unknownChannel: ChannelConfig = {
      ...baseChannel,
      channel: 'sms' as ChannelConfig['channel'],
      config: {},
    };
    render(<ChannelCard channel={unknownChannel} />);
    expect(screen.getByText('sms')).toBeInTheDocument();
    expect(screen.getByText('Unknown channel type')).toBeInTheDocument();
  });
});

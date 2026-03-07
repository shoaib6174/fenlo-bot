/**
 * Unit tests for ChannelBadge component
 */
import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { ChannelBadge } from '../ChannelBadge';
import React from 'react';

describe('ChannelBadge', () => {
  it('renders WhatsApp badge with correct title', () => {
    render(<ChannelBadge channel="whatsapp" />);
    expect(screen.getByTitle('WhatsApp')).toBeInTheDocument();
  });

  it('renders Widget badge with correct title', () => {
    render(<ChannelBadge channel="widget" />);
    expect(screen.getByTitle('Widget')).toBeInTheDocument();
  });

  it('renders Voice badge with correct title', () => {
    render(<ChannelBadge channel="voice" />);
    expect(screen.getByTitle('Voice')).toBeInTheDocument();
  });

  it('renders Telegram badge with correct title', () => {
    render(<ChannelBadge channel="telegram" />);
    expect(screen.getByTitle('Telegram')).toBeInTheDocument();
  });

  it('renders Web badge with correct title', () => {
    render(<ChannelBadge channel="web" />);
    expect(screen.getByTitle('Web')).toBeInTheDocument();
  });

  it('renders fallback for unknown channel', () => {
    render(<ChannelBadge channel="sms" />);
    expect(screen.getByTitle('sms')).toBeInTheDocument();
  });

  it('renders empty channel with Unknown title', () => {
    render(<ChannelBadge channel="" />);
    expect(screen.getByTitle('Unknown')).toBeInTheDocument();
  });

  it('uses small size classes when size="sm"', () => {
    const { container } = render(<ChannelBadge channel="whatsapp" size="sm" />);
    const badge = container.firstChild as HTMLElement;
    expect(badge.className).toContain('w-6');
    expect(badge.className).toContain('h-6');
  });

  it('uses large size classes when size="lg"', () => {
    const { container } = render(<ChannelBadge channel="whatsapp" size="lg" />);
    const badge = container.firstChild as HTMLElement;
    expect(badge.className).toContain('w-10');
    expect(badge.className).toContain('h-10');
  });

  it('defaults to md size', () => {
    const { container } = render(<ChannelBadge channel="whatsapp" />);
    const badge = container.firstChild as HTMLElement;
    expect(badge.className).toContain('w-8');
    expect(badge.className).toContain('h-8');
  });
});

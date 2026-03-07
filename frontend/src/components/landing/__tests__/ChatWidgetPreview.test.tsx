/**
 * Unit tests for ChatWidgetPreview component (S75)
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import React from 'react';
import ChatWidgetPreview from '../ChatWidgetPreview';

// Mock environment variables — no WIDGET_ID = static mode
vi.stubEnv('NEXT_PUBLIC_HOMEPAGE_WIDGET_ID', '');
vi.stubEnv('NEXT_PUBLIC_API_URL', 'http://localhost:8000');

describe('ChatWidgetPreview', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders greeting message on mount', () => {
    render(<ChatWidgetPreview />);
    expect(
      screen.getByText(/I can answer questions about your business/),
    ).toBeInTheDocument();
  });

  it('renders header with BotForge Assistant', () => {
    render(<ChatWidgetPreview />);
    expect(screen.getByText('BotForge Assistant')).toBeInTheDocument();
    expect(screen.getByText('Online')).toBeInTheDocument();
  });

  it('shows LIVE DEMO label in static mode', () => {
    render(<ChatWidgetPreview />);
    expect(screen.getByText('LIVE DEMO')).toBeInTheDocument();
  });

  it('renders input field with placeholder', () => {
    render(<ChatWidgetPreview />);
    const input = screen.getByPlaceholderText("Try: What's your return policy?");
    expect(input).toBeInTheDocument();
  });

  it('sends user message on submit (static mode)', async () => {
    render(<ChatWidgetPreview />);

    const input = screen.getByPlaceholderText("Try: What's your return policy?");
    fireEvent.change(input, { target: { value: 'What is your return policy?' } });
    fireEvent.keyDown(input, { key: 'Enter' });

    // User message should appear
    await waitFor(() => {
      expect(screen.getByText('What is your return policy?')).toBeInTheDocument();
    });
  });

  it('shows static response for return policy question', async () => {
    render(<ChatWidgetPreview />);

    const input = screen.getByPlaceholderText("Try: What's your return policy?");
    fireEvent.change(input, { target: { value: 'How do I return an item?' } });
    fireEvent.keyDown(input, { key: 'Enter' });

    // Wait for canned response
    await waitFor(
      () => {
        expect(
          screen.getByText(/customers can return items within 30 days/),
        ).toBeInTheDocument();
      },
      { timeout: 3000 },
    );
  });

  it('disables input while typing indicator is shown', async () => {
    render(<ChatWidgetPreview />);

    const input = screen.getByPlaceholderText("Try: What's your return policy?") as HTMLInputElement;
    fireEvent.change(input, { target: { value: 'Hello' } });
    fireEvent.keyDown(input, { key: 'Enter' });

    // Input should be disabled during typing
    expect(input.disabled).toBe(true);
  });

  it('does not send empty message', () => {
    render(<ChatWidgetPreview />);

    const input = screen.getByPlaceholderText("Try: What's your return policy?");
    fireEvent.keyDown(input, { key: 'Enter' });

    // No user message should appear (just the greeting)
    const messages = screen.queryAllByText(/What is your/);
    expect(messages.length).toBe(0);
  });

  it('enforces max length on input', () => {
    render(<ChatWidgetPreview />);
    const input = screen.getByPlaceholderText("Try: What's your return policy?");
    expect(input).toHaveAttribute('maxLength', '500');
  });
});

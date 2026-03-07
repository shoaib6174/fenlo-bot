/**
 * Unit tests for ChatInput component
 */
import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { ChatInput } from '../ChatInput';
import React from 'react';

describe('ChatInput', () => {
  it('renders textarea with placeholder', () => {
    render(<ChatInput onSend={vi.fn()} />);
    expect(screen.getByPlaceholderText('Type a message...')).toBeInTheDocument();
  });

  it('renders custom placeholder', () => {
    render(<ChatInput onSend={vi.fn()} placeholder="Ask a question..." />);
    expect(screen.getByPlaceholderText('Ask a question...')).toBeInTheDocument();
  });

  it('renders send button', () => {
    render(<ChatInput onSend={vi.fn()} />);
    expect(screen.getByLabelText('Send message')).toBeInTheDocument();
  });

  it('send button is disabled when input is empty', () => {
    render(<ChatInput onSend={vi.fn()} />);
    const btn = screen.getByLabelText('Send message');
    expect(btn).toBeDisabled();
  });

  it('send button is enabled when input has text', () => {
    render(<ChatInput onSend={vi.fn()} />);
    const textarea = screen.getByPlaceholderText('Type a message...');
    fireEvent.change(textarea, { target: { value: 'Hello' } });
    const btn = screen.getByLabelText('Send message');
    expect(btn).not.toBeDisabled();
  });

  it('calls onSend with trimmed message on form submit', () => {
    const onSend = vi.fn();
    render(<ChatInput onSend={onSend} />);

    const textarea = screen.getByPlaceholderText('Type a message...');
    fireEvent.change(textarea, { target: { value: '  Hello World  ' } });
    fireEvent.submit(textarea.closest('form')!);

    expect(onSend).toHaveBeenCalledWith('Hello World');
  });

  it('clears input after sending', () => {
    render(<ChatInput onSend={vi.fn()} />);

    const textarea = screen.getByPlaceholderText('Type a message...');
    fireEvent.change(textarea, { target: { value: 'Hello' } });
    fireEvent.submit(textarea.closest('form')!);

    expect(textarea).toHaveValue('');
  });

  it('sends on Enter key (without Shift)', () => {
    const onSend = vi.fn();
    render(<ChatInput onSend={onSend} />);

    const textarea = screen.getByPlaceholderText('Type a message...');
    fireEvent.change(textarea, { target: { value: 'Hello' } });
    fireEvent.keyDown(textarea, { key: 'Enter', shiftKey: false });

    expect(onSend).toHaveBeenCalledWith('Hello');
  });

  it('does not send on Shift+Enter', () => {
    const onSend = vi.fn();
    render(<ChatInput onSend={onSend} />);

    const textarea = screen.getByPlaceholderText('Type a message...');
    fireEvent.change(textarea, { target: { value: 'Hello' } });
    fireEvent.keyDown(textarea, { key: 'Enter', shiftKey: true });

    expect(onSend).not.toHaveBeenCalled();
  });

  it('does not send empty message', () => {
    const onSend = vi.fn();
    render(<ChatInput onSend={onSend} />);

    const textarea = screen.getByPlaceholderText('Type a message...');
    fireEvent.change(textarea, { target: { value: '   ' } });
    fireEvent.submit(textarea.closest('form')!);

    expect(onSend).not.toHaveBeenCalled();
  });

  it('disables textarea when disabled prop is true', () => {
    render(<ChatInput onSend={vi.fn()} disabled />);
    const textarea = screen.getByPlaceholderText('Type a message...');
    expect(textarea).toBeDisabled();
  });
});

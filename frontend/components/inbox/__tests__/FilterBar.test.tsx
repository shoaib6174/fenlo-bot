/**
 * Unit tests for FilterBar component
 */
import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { FilterBar } from '../FilterBar';
import React from 'react';

const defaultProps = {
  channel: 'all',
  status: 'all',
  minLeadScore: 0,
  onChannelChange: vi.fn(),
  onStatusChange: vi.fn(),
  onLeadScoreChange: vi.fn(),
};

describe('FilterBar', () => {
  it('renders channel, status, and lead score filters', () => {
    render(<FilterBar {...defaultProps} />);
    expect(screen.getByText('Channel:')).toBeInTheDocument();
    expect(screen.getByText('Status:')).toBeInTheDocument();
    expect(screen.getByText(/Min Lead Score/)).toBeInTheDocument();
  });

  it('shows current channel selection', () => {
    render(<FilterBar {...defaultProps} channel="whatsapp" />);
    const select = screen.getByDisplayValue('WhatsApp');
    expect(select).toBeInTheDocument();
  });

  it('shows current status selection', () => {
    render(<FilterBar {...defaultProps} status="escalated" />);
    const select = screen.getByDisplayValue('Escalated');
    expect(select).toBeInTheDocument();
  });

  it('calls onChannelChange when channel dropdown changes', () => {
    const onChannelChange = vi.fn();
    render(<FilterBar {...defaultProps} onChannelChange={onChannelChange} />);

    const selects = screen.getAllByRole('combobox');
    fireEvent.change(selects[0], { target: { value: 'widget' } });

    expect(onChannelChange).toHaveBeenCalledWith('widget');
  });

  it('calls onStatusChange when status dropdown changes', () => {
    const onStatusChange = vi.fn();
    render(<FilterBar {...defaultProps} onStatusChange={onStatusChange} />);

    const selects = screen.getAllByRole('combobox');
    fireEvent.change(selects[1], { target: { value: 'closed' } });

    expect(onStatusChange).toHaveBeenCalledWith('closed');
  });

  it('calls onLeadScoreChange when slider changes', () => {
    const onLeadScoreChange = vi.fn();
    render(<FilterBar {...defaultProps} onLeadScoreChange={onLeadScoreChange} />);

    const slider = screen.getByRole('slider');
    fireEvent.change(slider, { target: { value: '5' } });

    expect(onLeadScoreChange).toHaveBeenCalledWith(5);
  });

  it('displays current lead score value', () => {
    render(<FilterBar {...defaultProps} minLeadScore={3.5} />);
    expect(screen.getByText('Min Lead Score: 3.5')).toBeInTheDocument();
  });

  it('has all channel options', () => {
    render(<FilterBar {...defaultProps} />);
    const selects = screen.getAllByRole('combobox');
    const channelSelect = selects[0];
    const options = channelSelect.querySelectorAll('option');
    const values = Array.from(options).map((o) => o.value);
    expect(values).toEqual(['all', 'web', 'whatsapp', 'widget', 'telegram', 'voice']);
  });

  it('has all status options', () => {
    render(<FilterBar {...defaultProps} />);
    const selects = screen.getAllByRole('combobox');
    const statusSelect = selects[1];
    const options = statusSelect.querySelectorAll('option');
    const values = Array.from(options).map((o) => o.value);
    expect(values).toEqual(['all', 'active', 'escalated', 'closed']);
  });
});

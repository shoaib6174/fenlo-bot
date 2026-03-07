/**
 * Unit tests for TypingIndicator component
 */
import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { TypingIndicator } from '../TypingIndicator';
import React from 'react';

describe('TypingIndicator', () => {
  it('renders three animated dots', () => {
    const { container } = render(<TypingIndicator />);
    const dots = container.querySelectorAll('.animate-bounce');
    expect(dots).toHaveLength(3);
  });

  it('renders without crashing', () => {
    const { container } = render(<TypingIndicator />);
    expect(container.firstChild).toBeTruthy();
  });
});

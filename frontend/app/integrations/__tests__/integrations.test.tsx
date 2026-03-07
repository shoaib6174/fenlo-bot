/**
 * Unit tests for Integrations Catalog page (S79)
 */
import { describe, it, expect } from 'vitest';
import { render, screen, within } from '@testing-library/react';
import React from 'react';
import IntegrationsPage from '../page';

describe('IntegrationsPage', () => {
  it('renders the page with heading and category sections', () => {
    render(<IntegrationsPage />);

    // Page heading
    expect(screen.getByRole('heading', { level: 1, name: 'Integrations' })).toBeInTheDocument();

    // All 7 categories should be visible
    const categories = screen.getAllByTestId('integration-category');
    expect(categories.length).toBe(7);

    // Category names
    expect(screen.getByText('AI / LLM')).toBeInTheDocument();
    expect(screen.getByText('Voice')).toBeInTheDocument();
    expect(screen.getByText('Messaging')).toBeInTheDocument();
    expect(screen.getByText('CRM')).toBeInTheDocument();
    expect(screen.getByText('Automation')).toBeInTheDocument();
    expect(screen.getByText('Databases')).toBeInTheDocument();
    expect(screen.getByText('Cloud')).toBeInTheDocument();

    // Status summary badges exist (counts are dynamic based on integration data)
    expect(screen.getByText(/\d+ Connected/)).toBeInTheDocument();
    expect(screen.getByText(/\d+ Available/)).toBeInTheDocument();
    expect(screen.getByText(/\d+ Coming Soon/)).toBeInTheDocument();
  });

  it('renders integration cards with correct status badges', () => {
    render(<IntegrationsPage />);

    // Total card count (24 integrations)
    const cards = screen.getAllByTestId('integration-card');
    expect(cards.length).toBe(24);

    // Connected integration
    const groqCard = cards.find(card => within(card).queryByText('Groq'));
    expect(groqCard).toBeDefined();
    expect(within(groqCard!).getByText('Connected')).toBeInTheDocument();
    expect(within(groqCard!).getByText('Primary LLM provider with ultra-fast inference')).toBeInTheDocument();

    // Available integration
    const claudeCard = cards.find(card => within(card).queryByText('Claude'));
    expect(claudeCard).toBeDefined();
    expect(within(claudeCard!).getByText('Available')).toBeInTheDocument();

    // Coming Soon integration
    const zapierCard = cards.find(card => within(card).queryByText('Zapier'));
    expect(zapierCard).toBeDefined();
    expect(within(zapierCard!).getByText('Coming Soon')).toBeInTheDocument();
  });
});

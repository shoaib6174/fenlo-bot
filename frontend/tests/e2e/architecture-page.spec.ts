/**
 * E2E tests for architecture page
 */
import { test, expect } from '@playwright/test';

test.describe('Architecture Page E2E', () => {
  test('loads architecture page with all sections', async ({ page }) => {
    await page.goto('/architecture');

    // Hero section
    await expect(page.getByText('System Architecture')).toBeVisible();
    await expect(
      page.getByText('Production-Ready AI Platform')
    ).toBeVisible();

    // Message Pipeline section
    await expect(page.getByText('Message Pipeline')).toBeVisible();
    await expect(page.getByText('LoadContextStep')).toBeVisible();
    await expect(page.getByText('PromptGuardStep')).toBeVisible();
    await expect(page.getByText('RAGRetrievalStep')).toBeVisible();
    await expect(page.getByText('LLMStreamStep')).toBeVisible();
    await expect(page.getByText('PersistenceStep')).toBeVisible();

    // Tech Stack section
    await expect(page.getByText('Tech Stack')).toBeVisible();
    await expect(page.getByText('FastAPI')).toBeVisible();
    await expect(page.getByText('Next.js 15')).toBeVisible();
    await expect(page.getByText('PostgreSQL', { exact: true })).toBeVisible();

    // Key Patterns section
    await expect(page.getByText('Key Architectural Patterns')).toBeVisible();
    await expect(
      page.getByRole('heading', { name: 'Pipeline Pattern' })
    ).toBeVisible();
    await expect(
      page.getByRole('heading', { name: 'Circuit Breaker' })
    ).toBeVisible();
    await expect(
      page.getByRole('heading', { name: 'Workspace Isolation' })
    ).toBeVisible();
  });

  test('navigation links work correctly', async ({ page }) => {
    await page.goto('/architecture');

    // Click logo to go home
    await page.getByRole('link', { name: 'BotForge' }).first().click();
    await expect(page).toHaveURL('/');

    // Go back to architecture
    await page.goto('/architecture');

    // Navigation links exist (scope to nav to avoid footer duplicates)
    const nav = page.getByRole('navigation');
    await expect(nav.getByRole('link', { name: 'Products' })).toBeVisible();
    await expect(nav.getByRole('link', { name: 'API Docs' })).toBeVisible();
    await expect(nav.getByRole('link', { name: 'Login' })).toBeVisible();
  });

  test('API docs CTA buttons work', async ({ page }) => {
    await page.goto('/architecture');

    // Scroll to CTA section
    await page.getByText('Explore the API').scrollIntoViewIfNeeded();

    // Verify CTA buttons exist
    await expect(
      page.getByRole('link', { name: /Swagger UI/i })
    ).toBeVisible();
    await expect(
      page.getByRole('link', { name: /ReDoc/i })
    ).toBeVisible();
  });

  test('homepage includes architecture navigation link', async ({ page }) => {
    await page.goto('/');

    // Verify architecture link exists in nav
    const architectureLink = page.getByRole('link', {
      name: 'Architecture',
      exact: true,
    });
    await expect(architectureLink).toBeVisible();

    // Click it and verify navigation
    await architectureLink.click();
    await expect(page).toHaveURL('/architecture');
    await expect(page.getByText('System Architecture')).toBeVisible();
  });

  test('homepage includes API docs navigation link', async ({ page }) => {
    await page.goto('/');

    // Verify API docs link exists in nav
    const apiDocsLink = page.getByRole('link', {
      name: 'API Docs',
      exact: true,
    });
    await expect(apiDocsLink).toBeVisible();
  });

  test('footer links work correctly', async ({ page }) => {
    await page.goto('/architecture');

    // Scroll to footer
    await page.getByText('BotForge', { exact: true }).last().scrollIntoViewIfNeeded();

    // Verify footer links exist
    const footerSection = page.locator('footer');
    await expect(footerSection.getByRole('link', { name: 'Home' })).toBeVisible();
    await expect(footerSection.getByRole('link', { name: 'Products' })).toBeVisible();
    await expect(footerSection.getByRole('link', { name: 'Architecture' })).toBeVisible();
    await expect(footerSection.getByRole('link', { name: 'API Docs' })).toBeVisible();

    // Click home link
    await footerSection.getByRole('link', { name: 'Home' }).click();
    await expect(page).toHaveURL('/');
  });
});

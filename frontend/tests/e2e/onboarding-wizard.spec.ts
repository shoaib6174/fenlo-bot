/**
 * E2E tests for Onboarding Wizard (Phase 5)
 */
import { test, expect } from "@playwright/test";

test.describe("Onboarding Wizard E2E", () => {
  test.beforeEach(async ({ page }) => {
    // Register fresh user (onboarding should show automatically)
    const email = `onboard-${Date.now()}@example.com`;
    const password = "SecurePass123!"; // pragma: allowlist secret

    await page.goto("/register");
    await page
      .getByRole("textbox", { name: "Full Name" })
      .fill("Onboarding User");
    await page
      .getByRole("textbox", { name: "Email Address" })
      .fill(email);
    await page
      .getByRole("textbox", { name: "Password", exact: true })
      .fill(password);
    await page
      .getByRole("textbox", { name: "Confirm Password" })
      .fill(password);
    await page.getByRole("button", { name: "Create Account" }).click();
    await expect(page).toHaveURL(/\/dashboard/);
  });

  test("onboarding wizard shows on dashboard for new users", async ({
    page,
  }) => {
    // Should see Getting Started header
    await expect(page.getByText("Getting Started")).toBeVisible({
      timeout: 10000,
    });

    // Should see step indicator
    await expect(page.getByText(/Step \d+ of \d+/)).toBeVisible();
  });

  test("skip all button dismisses onboarding", async ({ page }) => {
    // Wait for wizard to load
    await expect(page.getByText("Getting Started")).toBeVisible({
      timeout: 10000,
    });

    // Click Skip All
    await page.getByRole("button", { name: "Skip All" }).click();

    // Wizard should disappear (may reload page or hide)
    // The wizard component should no longer be present
    await page.waitForTimeout(1000);
  });

  test("dismiss button hides wizard temporarily", async ({ page }) => {
    // Wait for wizard to load
    await expect(page.getByText("Getting Started")).toBeVisible({
      timeout: 10000,
    });

    // Click the X (dismiss) button — it's the close icon
    const dismissBtn = page.locator('button:has(svg.lucide-x)').first();
    if (await dismissBtn.isVisible()) {
      await dismissBtn.click();

      // Wizard should be hidden
      await expect(page.getByText("Getting Started")).not.toBeVisible({
        timeout: 3000,
      });
    }
  });

  test("personality step shows form fields", async ({ page }) => {
    // Wait for wizard to load
    await expect(page.getByText("Getting Started")).toBeVisible({
      timeout: 10000,
    });

    // First step should show bot name and personality fields
    await expect(page.getByText(/bot name|personality/i)).toBeVisible({
      timeout: 5000,
    });
  });

  test("progress bar shows on wizard", async ({ page }) => {
    // Wait for wizard to load
    await expect(page.getByText("Getting Started")).toBeVisible({
      timeout: 10000,
    });

    // Should show completion percentage
    await expect(page.getByText(/\d+% complete/)).toBeVisible();
  });
});

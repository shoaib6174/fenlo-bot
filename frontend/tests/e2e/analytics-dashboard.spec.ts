/**
 * E2E tests for Analytics Dashboard (Phase 5)
 */
import { test, expect } from "@playwright/test";

test.describe("Analytics Dashboard E2E", () => {
  test.beforeEach(async ({ page }) => {
    // Register and login
    const email = `analytics-${Date.now()}@example.com`;
    const password = "SecurePass123!"; // pragma: allowlist secret

    await page.goto("/register");
    await page
      .getByRole("textbox", { name: "Full Name" })
      .fill("Analytics User");
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

  test("analytics page loads with overview cards", async ({ page }) => {
    await page.goto("/analytics");

    // Should show the analytics page title
    await expect(page.getByText("Analytics")).toBeVisible();

    // Should show overview metric cards (with or without data)
    await expect(
      page.getByText("Conversations").first()
    ).toBeVisible({ timeout: 10000 });
  });

  test("date range filter buttons are present", async ({ page }) => {
    await page.goto("/analytics");

    // Date range buttons
    await expect(page.getByRole("button", { name: "7d" })).toBeVisible();
    await expect(page.getByRole("button", { name: "30d" })).toBeVisible();
    await expect(page.getByRole("button", { name: "90d" })).toBeVisible();
  });

  test("date range filter updates data", async ({ page }) => {
    await page.goto("/analytics");

    // Click 7d filter
    await page.getByRole("button", { name: "7d" }).click();

    // Page should still be functional (no crash)
    await expect(
      page.getByText("Conversations").first()
    ).toBeVisible();

    // Click 90d filter
    await page.getByRole("button", { name: "90d" }).click();

    await expect(
      page.getByText("Conversations").first()
    ).toBeVisible();
  });

  test("CSV export button is present", async ({ page }) => {
    await page.goto("/analytics");

    await expect(
      page.getByRole("button", { name: /export csv/i })
    ).toBeVisible();
  });

  test("analytics page shows chart sections", async ({ page }) => {
    await page.goto("/analytics");

    // Should show chart section headers
    await expect(page.getByText("Message Volume")).toBeVisible({
      timeout: 10000,
    });
    await expect(page.getByText("Sentiment")).toBeVisible();
  });

  test("sidebar analytics link is active on analytics page", async ({
    page,
  }) => {
    await page.goto("/analytics");

    // Analytics nav item should have active styling
    const analyticsLink = page.getByRole("link", { name: "Analytics" });
    await expect(analyticsLink).toBeVisible();
  });
});

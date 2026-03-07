/**
 * E2E tests for Admin Tools (Phase 5)
 */
import { test, expect } from "@playwright/test";

test.describe("Admin Tools E2E", () => {
  test.beforeEach(async ({ page }) => {
    // Register and login
    const email = `admin-${Date.now()}@example.com`;
    const password = "SecurePass123!"; // pragma: allowlist secret

    await page.goto("/register");
    await page
      .getByRole("textbox", { name: "Full Name" })
      .fill("Admin User");
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

  test("admin page loads with tabs", async ({ page }) => {
    await page.goto("/admin");

    // Should show admin page title
    await expect(page.getByText("Admin Tools")).toBeVisible();

    // Should show all 4 tabs
    await expect(page.getByRole("button", { name: "Export" })).toBeVisible();
    await expect(page.getByRole("button", { name: "GDPR" })).toBeVisible();
    await expect(page.getByRole("button", { name: "Storage" })).toBeVisible();
    await expect(
      page.getByRole("button", { name: "Retention" })
    ).toBeVisible();
  });

  test("export tab shows export options", async ({ page }) => {
    await page.goto("/admin");

    // Default tab should be Export
    await expect(page.getByText("Data Export")).toBeVisible();
    await expect(page.getByText("Full Workspace Export")).toBeVisible();
    await expect(page.getByText("Conversations CSV")).toBeVisible();
  });

  test("GDPR tab shows purge controls", async ({ page }) => {
    await page.goto("/admin");

    // Switch to GDPR tab
    await page.getByRole("button", { name: "GDPR" }).click();

    // Should show GDPR section
    await expect(page.getByText("GDPR Compliance")).toBeVisible();
    await expect(page.getByText("Purge Workspace Data")).toBeVisible();
    await expect(
      page.getByRole("button", { name: "Request Data Deletion" })
    ).toBeVisible();
  });

  test("GDPR purge requires confirmation text", async ({ page }) => {
    await page.goto("/admin");
    await page.getByRole("button", { name: "GDPR" }).click();

    // Click request deletion
    await page
      .getByRole("button", { name: "Request Data Deletion" })
      .click();

    // Should show confirmation input
    await expect(page.getByPlaceholder("DELETE ALL DATA")).toBeVisible();

    // Confirm button should be disabled without correct text
    const confirmBtn = page.getByRole("button", { name: "Confirm Purge" });
    await expect(confirmBtn).toBeDisabled();
  });

  test("storage tab shows metrics", async ({ page }) => {
    await page.goto("/admin");

    // Switch to Storage tab
    await page.getByRole("button", { name: "Storage" }).click();

    // Should show storage section
    await expect(page.getByText("Storage Usage")).toBeVisible();
  });

  test("retention tab shows archive controls", async ({ page }) => {
    await page.goto("/admin");

    // Switch to Retention tab
    await page.getByRole("button", { name: "Retention" }).click();

    // Should show retention section
    await expect(page.getByText("Data Retention")).toBeVisible();
    await expect(
      page.getByRole("button", { name: "Archive Now" })
    ).toBeVisible();
  });

  test("sidebar has admin link", async ({ page }) => {
    await page.goto("/dashboard");

    // Admin link should be in sidebar
    const adminLink = page.getByRole("link", { name: "Admin" });
    await expect(adminLink).toBeVisible();

    // Click it
    await adminLink.click();
    await expect(page).toHaveURL(/\/admin/);
  });

  test("settings data tab links to admin", async ({ page }) => {
    await page.goto("/settings");

    // Click Data tab
    await page.getByRole("button", { name: "Data" }).click();

    // Should show Active badge (not TBA)
    await expect(page.getByText("Active").first()).toBeVisible();

    // Should have link to admin tools
    const adminLink = page.getByRole("link", { name: "Open Admin Tools" });
    await expect(adminLink).toBeVisible();
  });
});

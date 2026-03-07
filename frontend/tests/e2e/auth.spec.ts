/**
 * E2E tests for authentication flows
 */
import { test, expect } from "@playwright/test";

test.describe("Authentication E2E", () => {
  test("register → redirect to dashboard", async ({ page }) => {
    await page.goto("/register");

    // Fill registration form
    await page
      .getByRole("textbox", { name: "Full Name" })
      .fill("Test User");
    await page
      .getByRole("textbox", { name: "Email Address" })
      .fill(`test-${Date.now()}@example.com`);
    await page
      .getByRole("textbox", { name: "Password", exact: true })
      .fill("SecurePass123!");
    await page
      .getByRole("textbox", { name: "Confirm Password" })
      .fill("SecurePass123!");

    // Submit form
    await page.getByRole("button", { name: "Create Account" }).click();

    // Should redirect to dashboard
    await expect(page).toHaveURL(/\/dashboard/);
  });

  test("login → redirect to dashboard", async ({ page }) => {
    // First register a user
    const email = `login-test-${Date.now()}@example.com`;
    const password = "SecurePass123!";

    await page.goto("/register");
    await page
      .getByRole("textbox", { name: "Full Name" })
      .fill("Login Test User");
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

    // Logout
    await page.getByRole("button", { name: "Logout" }).click();

    // Now login
    await page.goto("/login");
    await page
      .getByRole("textbox", { name: "Email Address" })
      .fill(email);
    await page
      .getByRole("textbox", { name: "Password" })
      .fill(password);
    await page.getByRole("button", { name: "Sign In" }).click();

    // Should redirect to dashboard
    await expect(page).toHaveURL(/\/dashboard/);
  });

  test("invalid credentials → error", async ({ page }) => {
    await page.goto("/login");

    // Fill with invalid credentials
    await page
      .getByRole("textbox", { name: "Email Address" })
      .fill("nonexistent@example.com");
    await page
      .getByRole("textbox", { name: "Password" })
      .fill("WrongPassword123!");

    // Submit form
    await page.getByRole("button", { name: "Sign In" }).click();

    // Should show error message or stay on login page
    await expect(page).toHaveURL(/\/login/);
  });

  test("unauthenticated → redirect to login", async ({ page, context }) => {
    // Clear cookies to ensure unauthenticated state
    await context.clearCookies();

    // Try to access protected dashboard page
    await page.goto("/dashboard");

    // Should redirect to login
    await expect(page).toHaveURL(/\/login/);
  });

  test("logout → redirect to home", async ({ page }) => {
    // First register and login
    const email = `logout-test-${Date.now()}@example.com`;
    const password = "SecurePass123!";

    await page.goto("/register");
    await page
      .getByRole("textbox", { name: "Full Name" })
      .fill("Logout Test User");
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

    // Should be on dashboard
    await expect(page).toHaveURL(/\/dashboard/);

    // Click logout
    await page.getByRole("button", { name: "Logout" }).click();

    // Should redirect to home
    await expect(page).toHaveURL(/\/$/);
  });
});

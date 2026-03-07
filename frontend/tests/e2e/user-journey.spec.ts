/**
 * E2E tests for critical user journeys (SP.5)
 * Tests the 5 UJ.E2E flows verified in SP.4
 */
import { test, expect, type Page } from "@playwright/test";

// Increase default timeout for registration/login flows
test.setTimeout(60_000);

// Helper: wait for React hydration on a page
async function waitForHydration(page: Page) {
  await page.waitForFunction(
    () => {
      const el = document.querySelector("form") || document.querySelector("[data-hydrated]") || document.querySelector("button");
      if (!el) return false;
      return Object.keys(el).some(
        (k) => k.startsWith("__reactFiber") || k.startsWith("__reactProps")
      );
    },
    { timeout: 10_000 }
  );
}

// Helper: register a fresh user and land on dashboard
async function registerUser(page: Page) {
  const email = `e2e-${Date.now()}-${Math.random().toString(36).slice(2, 6)}@test.com`;
  const password = "TestPass1234"; // pragma: allowlist secret

  await page.goto("/register");
  await waitForHydration(page);

  await page.getByRole("textbox", { name: "Full Name" }).fill("E2E User");
  await page.getByRole("textbox", { name: "Email Address" }).fill(email);
  await page
    .getByRole("textbox", { name: "Password", exact: true })
    .fill(password);
  await page.getByRole("textbox", { name: "Confirm Password" }).fill(password);
  await page.getByRole("button", { name: "Create Account" }).click();

  await page.waitForURL("**/dashboard", { timeout: 30_000 });
  return { email, password };
}

// Helper: login with existing credentials
async function loginUser(page: Page, email: string, password: string) {
  await page.goto("/login");
  await waitForHydration(page);

  await page.getByRole("textbox", { name: "Email Address" }).fill(email);
  await page.getByRole("textbox", { name: "Password" }).fill(password);
  await page.getByRole("button", { name: "Sign In" }).click();
  await page.waitForURL("**/dashboard", { timeout: 30_000 });
}

test.describe("Demo Flow", () => {
  test("landing page loads with key sections", async ({ page }) => {
    await page.goto("/");

    await expect(
      page.getByRole("heading", {
        name: "AI Chatbot That Knows Your Business",
      })
    ).toBeVisible();
    await expect(
      page.getByRole("link", { name: /Start Building Free/i }).first()
    ).toBeVisible();
    await expect(
      page.getByRole("link", { name: /Login to Dashboard/i }).first()
    ).toBeVisible();

    // Live demo widget present
    await expect(page.getByText("LIVE DEMO", { exact: true })).toBeVisible();
    await expect(page.getByText("BotForge Assistant")).toBeVisible();
  });

  test("landing → register → dashboard with sidebar", async ({ page }) => {
    await page.goto("/");
    await page
      .getByRole("link", { name: /Start Building Free/i })
      .first()
      .click();
    await expect(page).toHaveURL(/\/register/);

    await registerUser(page);

    // Sidebar visible with all core nav items
    const sidebar = page.getByRole("complementary");
    await expect(
      sidebar.getByRole("link", { name: "Dashboard" })
    ).toBeVisible();
    await expect(sidebar.getByRole("link", { name: "Chat" })).toBeVisible();
    await expect(
      sidebar.getByRole("link", { name: "Knowledge Base" })
    ).toBeVisible();
    await expect(
      sidebar.getByRole("link", { name: "Settings" })
    ).toBeVisible();

    // Dashboard content
    await expect(
      page.getByRole("heading", { name: /Welcome/i })
    ).toBeVisible();
  });
});

test.describe("Auth Flow", () => {
  test("register → dashboard → chat → message input", async ({ page }) => {
    await registerUser(page);

    // Navigate to chat via sidebar
    await page
      .getByRole("complementary")
      .getByRole("link", { name: "Chat" })
      .click();
    await expect(page).toHaveURL(/\/chat/);

    // Chat UI elements present
    await expect(
      page.getByRole("button", { name: "New Chat" })
    ).toBeVisible();
    await expect(
      page.getByRole("textbox", { name: "Type a message..." })
    ).toBeVisible();

    // Send button should be disabled with no message
    await expect(
      page.getByRole("button", { name: "Send message" })
    ).toBeDisabled();

    // Type a message — send button should enable
    await page
      .getByRole("textbox", { name: "Type a message..." })
      .fill("Hello, what can you help me with?");
    await expect(
      page.getByRole("button", { name: "Send message" })
    ).toBeEnabled();
  });

  test("login with redirect preserves destination", async ({
    page,
    context,
  }) => {
    // Register first to create an account
    const { email, password } = await registerUser(page);

    // Logout
    await page.getByRole("button", { name: "Logout" }).click();
    await page.waitForURL("**/", { timeout: 10_000 });

    // Try accessing /dashboard while logged out
    await page.goto("/dashboard");
    await expect(page).toHaveURL(/\/login/);

    // Login
    await loginUser(page, email, password);

    // Should be back on dashboard
    await expect(page).toHaveURL(/\/dashboard/);
  });
});

test.describe("KB Flow", () => {
  test("navigate to KB → see empty state", async ({ page }) => {
    await registerUser(page);

    // Navigate via sidebar
    await page
      .getByRole("complementary")
      .getByRole("link", { name: "Knowledge Base" })
      .click();
    await expect(page).toHaveURL(/\/kb/);

    // Empty state
    await expect(
      page.getByRole("heading", { name: "No Knowledge Base Found" })
    ).toBeVisible();
    await expect(
      page.getByRole("button", { name: "Create Knowledge Base" })
    ).toBeVisible();
  });
});

test.describe("Navigation", () => {
  test("all sidebar links navigate to correct pages", async ({ page }) => {
    await registerUser(page);

    const sidebar = page.getByRole("complementary");

    // Dashboard → Chat
    await sidebar.getByRole("link", { name: "Chat" }).click();
    await expect(page).toHaveURL(/\/chat/);

    // Chat → Knowledge Base
    await sidebar.getByRole("link", { name: "Knowledge Base" }).click();
    await expect(page).toHaveURL(/\/kb/);

    // KB → Settings
    await sidebar.getByRole("link", { name: "Settings" }).click();
    await expect(page).toHaveURL(/\/settings/);
    await expect(
      page.getByRole("heading", { name: "Settings", exact: true })
    ).toBeVisible();

    // Settings → Voice (Coming Soon)
    await sidebar.getByRole("link", { name: /Voice/i }).click();
    await expect(page).toHaveURL(/\/voice/);
    await expect(
      page.getByRole("heading", { name: "VoiceBot Pro" })
    ).toBeVisible();

    // Voice → Channels
    await sidebar.getByRole("link", { name: /Channels/i }).click();
    await expect(page).toHaveURL(/\/channels/);
    await expect(
      page.getByRole("heading", { name: /Multi-Channel/i })
    ).toBeVisible();

    // Channels → Analytics
    await sidebar.getByRole("link", { name: /Analytics/i }).click();
    await expect(page).toHaveURL(/\/analytics/);
    await expect(
      page.getByRole("heading", { name: "Analytics & Insights" })
    ).toBeVisible();

    // Analytics → Dashboard
    await sidebar.getByRole("link", { name: "Dashboard" }).click();
    await expect(page).toHaveURL(/\/dashboard/);
    await expect(
      page.getByRole("heading", { name: /Welcome/i })
    ).toBeVisible();
  });

  test("active route highlighted in sidebar", async ({ page }) => {
    await registerUser(page);

    const sidebar = page.getByRole("complementary");

    // On dashboard — Dashboard link should have active styling (bg-blue-50)
    const dashboardLink = sidebar.getByRole("link", { name: "Dashboard" });
    await expect(dashboardLink).toHaveClass(/bg-blue-50/);

    // Navigate to Chat
    await sidebar.getByRole("link", { name: "Chat" }).click();
    await expect(page).toHaveURL(/\/chat/);

    // Chat link should now be active
    const chatLink = sidebar.getByRole("link", { name: "Chat" });
    await expect(chatLink).toHaveClass(/bg-blue-50/);

    // Dashboard should no longer be active
    await expect(dashboardLink).not.toHaveClass(/bg-blue-50/);
  });

  test("breadcrumbs show correct path", async ({ page }) => {
    await registerUser(page);

    // Dashboard — single breadcrumb
    await expect(page.getByRole("banner").getByText("Dashboard")).toBeVisible();

    // Navigate to chat
    await page
      .getByRole("complementary")
      .getByRole("link", { name: "Chat" })
      .click();

    // Chat breadcrumb: Dashboard > Chat
    const banner = page.getByRole("banner");
    await expect(banner.getByText("Dashboard")).toBeVisible();
    await expect(banner.getByText("Chat")).toBeVisible();
  });
});

test.describe("Mobile Navigation", () => {
  test.use({ viewport: { width: 375, height: 812 } });

  test("hamburger → drawer → navigate → drawer closes", async ({ page }) => {
    await registerUser(page);

    // Hamburger should be visible on mobile
    const hamburger = page.getByRole("button", { name: "Open menu" });
    await expect(hamburger).toBeVisible();

    // Open drawer
    await hamburger.click();

    // Sidebar drawer should show nav items — close button visible
    const closeBtn = page.getByRole("button", { name: "Close sidebar" });
    await expect(closeBtn).toBeVisible();

    // The mobile drawer <aside> should have translate-x-0 (open)
    const mobileDrawer = page.locator("aside.fixed");
    await expect(mobileDrawer).toHaveClass(/translate-x-0/);

    // Navigate via the visible drawer link (click the one that's visible)
    const kbLinks = page.getByRole("link", { name: "Knowledge Base" });
    // The mobile drawer link is the one that's visible when drawer is open
    for (let i = 0; i < (await kbLinks.count()); i++) {
      if (await kbLinks.nth(i).isVisible()) {
        await kbLinks.nth(i).click();
        break;
      }
    }
    await expect(page).toHaveURL(/\/kb/);

    // Drawer should be closed — aside should have -translate-x-full class
    await expect(mobileDrawer).toHaveClass(/-translate-x-full/);

    // Re-open and close via close button
    await hamburger.click();
    await expect(mobileDrawer).toHaveClass(/translate-x-0/);
    await closeBtn.click();
    await expect(mobileDrawer).toHaveClass(/-translate-x-full/);
  });

  test("mobile dashboard content renders", async ({ page }) => {
    await registerUser(page);

    // Dashboard content should render on mobile
    await expect(
      page.getByRole("heading", { name: /Welcome/i })
    ).toBeVisible();
    await expect(page.getByText("Conversations", { exact: true })).toBeVisible();
    await expect(page.getByText("Documents", { exact: true })).toBeVisible();
  });
});

test.describe("Unauthenticated Access", () => {
  test("protected routes redirect to login", async ({ page, context }) => {
    await context.clearCookies();

    const protectedRoutes = [
      "/dashboard",
      "/chat",
      "/kb",
      "/settings",
      "/voice",
      "/channels",
      "/analytics",
    ];

    for (const route of protectedRoutes) {
      await page.goto(route);
      await expect(page).toHaveURL(/\/login/);
    }
  });
});

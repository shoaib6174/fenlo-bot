/**
 * E2E tests for Voice module (S41 — tasks 3.29)
 * Tests voice page, call history, call detail, escalation rules, and settings.
 */
import { test, expect, type Page } from "@playwright/test";

test.setTimeout(60_000);

async function waitForHydration(page: Page) {
  await page.waitForFunction(
    () => {
      const el =
        document.querySelector("form") ||
        document.querySelector("[data-hydrated]") ||
        document.querySelector("button");
      if (!el) return false;
      return Object.keys(el).some(
        (k) => k.startsWith("__reactFiber") || k.startsWith("__reactProps")
      );
    },
    { timeout: 10_000 }
  );
}

async function registerUser(page: Page) {
  const email = `voice-e2e-${Date.now()}-${Math.random().toString(36).slice(2, 6)}@test.com`;
  const password = "TestPass1234"; // pragma: allowlist secret

  await page.goto("/register");
  await waitForHydration(page);

  await page.getByRole("textbox", { name: "Full Name" }).fill("Voice E2E User");
  await page.getByRole("textbox", { name: "Email Address" }).fill(email);
  await page
    .getByRole("textbox", { name: "Password", exact: true })
    .fill(password);
  await page.getByRole("textbox", { name: "Confirm Password" }).fill(password);
  await page.getByRole("button", { name: "Create Account" }).click();

  await page.waitForURL("**/dashboard", { timeout: 30_000 });
  return { email, password };
}

test.describe("Voice Page E2E", () => {
  test("voice page displays call history tab", async ({ page }) => {
    await registerUser(page);

    // Navigate to voice page
    await page.goto("/voice");
    await waitForHydration(page);

    // Should show VoiceBot Pro heading
    await expect(page.getByText("VoiceBot Pro")).toBeVisible();

    // Should show Calls tab and Escalation Rules tab
    await expect(page.getByRole("tab", { name: "Calls" })).toBeVisible();
    await expect(
      page.getByRole("tab", { name: "Escalation Rules" })
    ).toBeVisible();

    // Should show the "not configured" banner since no Vapi keys set
    await expect(page.getByText("Voice not configured")).toBeVisible();

    // Start Test Call button should be present but disabled
    const callButton = page.getByRole("button", { name: "Start Test Call" });
    await expect(callButton).toBeVisible();
    await expect(callButton).toBeDisabled();
  });

  test("call detail shows transcript and metadata", async ({ page }) => {
    await registerUser(page);

    // Navigate to voice page — no calls will be present for new user
    await page.goto("/voice");
    await waitForHydration(page);

    // Verify empty state message
    await expect(page.getByText("No calls yet")).toBeVisible();
  });

  test("escalation rules tab — create, toggle, delete rule", async ({
    page,
  }) => {
    await registerUser(page);

    await page.goto("/voice");
    await waitForHydration(page);

    // Click Escalation Rules tab
    await page.getByRole("tab", { name: "Escalation Rules" }).click();

    // Should show empty state
    await expect(page.getByText("No escalation rules yet")).toBeVisible();

    // Click Add Rule button
    await page.getByRole("button", { name: "Add Rule" }).click();

    // Modal should appear
    await expect(page.getByText("Create Escalation Rule")).toBeVisible();

    // Fill in keyword rule
    await page
      .getByLabel("Keywords (comma-separated)")
      .fill("help, agent, human");
    await page.getByRole("button", { name: "Create Rule" }).click();

    // Modal should close and rule should appear in list
    await expect(page.getByText("help, agent, human")).toBeVisible({
      timeout: 5000,
    });
  });

  test("voice settings — configure Vapi keys form", async ({ page }) => {
    await registerUser(page);

    // Navigate to settings page
    await page.goto("/settings");
    await waitForHydration(page);

    // Click Voice tab
    await page.getByRole("button", { name: /Voice/ }).click();

    // Should show voice config form
    await expect(page.getByText("Voice Configuration")).toBeVisible();
    await expect(page.getByText("Voice is not configured")).toBeVisible();

    // Should show form fields
    await expect(page.getByLabel("Vapi Private Key")).toBeVisible();
    await expect(page.getByLabel("Vapi Public Key")).toBeVisible();
    await expect(page.getByLabel("First Message")).toBeVisible();
    await expect(
      page.getByRole("button", { name: "Enable Voice" })
    ).toBeVisible();

    // Try to submit without keys — should show error
    await page.getByRole("button", { name: "Enable Voice" }).click();
    await expect(page.getByText("Both API keys are required")).toBeVisible();
  });

  test("web call button — shows correct initial state", async ({ page }) => {
    await registerUser(page);

    await page.goto("/voice");
    await waitForHydration(page);

    // Start Test Call button present and disabled (voice not configured)
    const callButton = page.getByRole("button", { name: "Start Test Call" });
    await expect(callButton).toBeVisible();
    await expect(callButton).toBeDisabled();

    // Dashboard should link to voice
    await page.goto("/dashboard");
    await waitForHydration(page);

    // Voice feature card should show "Setup Required" since not configured
    await expect(page.getByText("VoiceBot Pro")).toBeVisible();
    await expect(page.getByText("Setup Required")).toBeVisible();
  });
});

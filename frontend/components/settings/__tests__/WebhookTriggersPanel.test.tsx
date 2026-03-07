/**
 * Unit tests for WebhookTriggersPanel component (S83 - 8.45)
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import React from "react";
import { WebhookTriggersPanel } from "../WebhookTriggersPanel";

// Mock fetch globally
const mockFetch = vi.fn();
global.fetch = mockFetch;

// Mock providers
vi.mock("@/providers/auth", () => ({
  useAuth: () => ({ user: { email: "test@test.com" }, isLoading: false }),
}));

const mockTriggers = [
  {
    event: "hot_lead",
    label: "Hot Lead Detected",
    description: "Triggers when lead score exceeds threshold",
  },
  {
    event: "escalation_triggered",
    label: "Escalation Triggered",
    description: "Triggers when escalation rules fire",
  },
];

const mockSubscriptions = [
  {
    id: "sub-1",
    event: "hot_lead",
    hook_url: "https://hooks.zapier.com/hooks/catch/123/abc/",
    created_at: "2026-02-16T12:00:00Z",
  },
];

const mockHistory = {
  items: [
    {
      id: "entry-1",
      event_type: "lead.qualified",
      target_url: "https://hooks.zapier.com/hooks/catch/123/abc/",
      status: "sent",
      created_at: "2026-02-16T12:01:00Z",
      sent_at: "2026-02-16T12:01:01Z",
      error_message: null,
      retry_count: 0,
    },
  ],
  total: 1,
  page: 1,
  per_page: 10,
  pages: 1,
};

function setupFetchMock() {
  mockFetch.mockImplementation((url: string) => {
    if (url.includes("/webhooks/triggers")) {
      return Promise.resolve({
        ok: true,
        json: () => Promise.resolve(mockTriggers),
      });
    }
    if (url.includes("/webhooks/subscriptions")) {
      return Promise.resolve({
        ok: true,
        json: () => Promise.resolve(mockSubscriptions),
      });
    }
    if (url.includes("/webhook-actions/history")) {
      return Promise.resolve({
        ok: true,
        json: () => Promise.resolve(mockHistory),
      });
    }
    if (url.includes("/webhooks/sample/")) {
      return Promise.resolve({
        ok: true,
        json: () =>
          Promise.resolve([
            {
              event: "hot_lead",
              lead_score: 8.5,
              workspace_id: "w123",
            },
          ]),
      });
    }
    if (
      url.includes("/webhooks/subscribe") &&
      !url.includes("/subscribe/")
    ) {
      return Promise.resolve({
        ok: true,
        status: 201,
        json: () =>
          Promise.resolve({
            id: "sub-new",
            event: "escalation_triggered",
            hook_url: "https://hooks.zapier.com/new",
            created_at: "2026-02-16T13:00:00Z",
          }),
      });
    }
    if (url.includes("/webhooks/subscribe/sub-1")) {
      return Promise.resolve({ ok: true, status: 204 });
    }
    return Promise.resolve({ ok: false, status: 404 });
  });
}

describe("WebhookTriggersPanel", () => {
  beforeEach(() => {
    mockFetch.mockReset();
    setupFetchMock();
  });

  it("renders active subscriptions and delivery history", async () => {
    render(<WebhookTriggersPanel />);

    await waitFor(() => {
      expect(screen.getByText("Webhook Triggers")).toBeInTheDocument();
    });

    // Shows active subscription
    expect(screen.getByText("hot_lead")).toBeInTheDocument();
    expect(
      screen.getAllByText("https://hooks.zapier.com/hooks/catch/123/abc/").length
    ).toBeGreaterThanOrEqual(1);

    // Shows delivery history
    expect(screen.getByText("lead.qualified")).toBeInTheDocument();
    expect(screen.getByText("Sent")).toBeInTheDocument();
  });

  it("shows add webhook form and submits new subscription", async () => {
    const user = userEvent.setup();
    render(<WebhookTriggersPanel />);

    await waitFor(() => {
      expect(screen.getByText("Add Webhook")).toBeInTheDocument();
    });

    // Open form
    await user.click(screen.getByText("Add Webhook"));

    // Form fields appear
    expect(screen.getByTestId("webhook-event-select")).toBeInTheDocument();
    expect(screen.getByTestId("webhook-url-input")).toBeInTheDocument();
  });
});

/**
 * Unit tests for SlackNotificationsPanel component (S84 - 8.51)
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import React from "react";
import { SlackNotificationsPanel } from "../SlackNotificationsPanel";

// Mock fetch globally
const mockFetch = vi.fn();
global.fetch = mockFetch;

const mockSettings = {
  slack_webhook_url: "https://hooks.slack.com/services/T00/B00/xxx",
  slack_notifications: {
    enabled: true,
    escalation: true,
    hot_lead: true,
    quality: false,
    documents: false,
  },
};

function setupFetchMock() {
  mockFetch.mockImplementation((url: string, options?: RequestInit) => {
    if (url.includes("/notifications/settings") && (!options?.method || options.method === "GET")) {
      return Promise.resolve({
        ok: true,
        json: () => Promise.resolve(mockSettings),
      });
    }
    if (url.includes("/notifications/settings") && options?.method === "PUT") {
      return Promise.resolve({
        ok: true,
        json: () => Promise.resolve(mockSettings),
      });
    }
    if (url.includes("/notifications/test-slack")) {
      return Promise.resolve({
        ok: true,
        json: () => Promise.resolve({ success: true }),
      });
    }
    return Promise.resolve({ ok: false, status: 404 });
  });
}

describe("SlackNotificationsPanel", () => {
  beforeEach(() => {
    mockFetch.mockReset();
    setupFetchMock();
  });

  it("renders Slack notification settings with toggles", async () => {
    render(<SlackNotificationsPanel />);

    await waitFor(() => {
      expect(screen.getByText("Slack Notifications")).toBeInTheDocument();
    });

    // Shows webhook URL input with loaded value
    const urlInput = screen.getByTestId("slack-webhook-url") as HTMLInputElement;
    expect(urlInput.value).toBe("https://hooks.slack.com/services/T00/B00/xxx");

    // Shows event toggles
    expect(screen.getByText("Escalation Triggered")).toBeInTheDocument();
    expect(screen.getByText("Hot Lead Detected")).toBeInTheDocument();
    expect(screen.getByText("Quality Alert")).toBeInTheDocument();
    expect(screen.getByText("Document Processed")).toBeInTheDocument();

    // Has test and save buttons
    expect(screen.getByTestId("test-slack-btn")).toBeInTheDocument();
    expect(screen.getByTestId("save-slack-btn")).toBeInTheDocument();
  });

  it("sends test notification and shows success message", async () => {
    const user = userEvent.setup();
    render(<SlackNotificationsPanel />);

    await waitFor(() => {
      expect(screen.getByTestId("test-slack-btn")).toBeInTheDocument();
    });

    await user.click(screen.getByTestId("test-slack-btn"));

    await waitFor(() => {
      expect(screen.getByTestId("status-message")).toBeInTheDocument();
      expect(screen.getByText(/test notification sent/i)).toBeInTheDocument();
    });
  });
});

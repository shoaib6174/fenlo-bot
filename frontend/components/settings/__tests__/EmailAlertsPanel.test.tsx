/**
 * Unit tests for EmailAlertsPanel component (S85 - 8.55)
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import React from "react";
import { EmailAlertsPanel } from "../EmailAlertsPanel";

// Mock fetch globally
const mockFetch = vi.fn();
global.fetch = mockFetch;

const mockSettings = {
  slack_webhook_url: "",
  slack_notifications: {},
  email_alerts: {
    enabled: true,
    recipient_email: "admin@test.com",
    quality_drop: true,
    escalation: true,
    knowledge_gap: false,
    doc_processed: false,
    digest_frequency: "immediate",
    quality_threshold: 0.6,
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
    if (url.includes("/notifications/test-email")) {
      return Promise.resolve({
        ok: true,
        json: () =>
          Promise.resolve({
            subject: "[BotForge] Quality Score Drop",
            html: "<html><body>Test email</body></html>",
            event_type: "quality.alert",
            alert_type: "quality_drop",
            recipient: "admin@test.com",
            created_at: "2026-02-16T12:00:00Z",
          }),
      });
    }
    return Promise.resolve({ ok: false, status: 404 });
  });
}

describe("EmailAlertsPanel", () => {
  beforeEach(() => {
    mockFetch.mockReset();
    setupFetchMock();
  });

  it("renders email alert settings with toggles and threshold", async () => {
    render(<EmailAlertsPanel />);

    await waitFor(() => {
      expect(screen.getByText("Email Alerts")).toBeInTheDocument();
    });

    // Shows recipient email
    const emailInput = screen.getByTestId("email-recipient-input") as HTMLInputElement;
    expect(emailInput.value).toBe("admin@test.com");

    // Shows alert toggles
    expect(screen.getByText("Quality Score Drop")).toBeInTheDocument();
    expect(screen.getByText("Conversation Escalated")).toBeInTheDocument();
    expect(screen.getByText("Knowledge Gap Detected")).toBeInTheDocument();
    expect(screen.getByText("Document Processed")).toBeInTheDocument();

    // Shows threshold slider and frequency buttons
    expect(screen.getByTestId("quality-threshold-slider")).toBeInTheDocument();
    expect(screen.getByText("Immediate")).toBeInTheDocument();
    expect(screen.getByText("Hourly Digest")).toBeInTheDocument();
    expect(screen.getByText("Daily Digest")).toBeInTheDocument();
  });

  it("generates test email preview", async () => {
    const user = userEvent.setup();
    render(<EmailAlertsPanel />);

    await waitFor(() => {
      expect(screen.getByTestId("test-email-btn")).toBeInTheDocument();
    });

    await user.click(screen.getByTestId("test-email-btn"));

    await waitFor(() => {
      expect(screen.getByTestId("email-preview")).toBeInTheDocument();
      expect(screen.getByTestId("email-status-message")).toBeInTheDocument();
    });
  });
});

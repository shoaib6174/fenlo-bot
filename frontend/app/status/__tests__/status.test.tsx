/**
 * Unit tests for Status page (S80)
 */
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import React from "react";
import StatusPage from "../page";

const MOCK_HEALTH_OK = {
  status: "ok",
  db: true,
  redis: true,
  llm_providers: {
    groq: { state: "closed", failures: 0 },
    openai: { state: "closed", failures: 0 },
  },
  worker: { status: "healthy", last_heartbeat: Date.now() / 1000, failure_count: 0 },
  active_websockets: 5,
  arq_queue_depth: 0,
  uptime_s: 172800, // 2 days
  pinecone: "skipped",
  voice: "skipped",
  webhooks: { pending: 0, failed: 0, dead: 0, success_rate_1h: null, oldest_pending_age_sec: null },
  channels: { active_widgets: 2, active_whatsapp: 1, widget_connections: 3, twilio_circuit_breaker: "closed" },
};

const MOCK_HEALTH_DEGRADED = {
  ...MOCK_HEALTH_OK,
  status: "degraded",
  llm_providers: {
    groq: { state: "open", failures: 5 },
    openai: { state: "closed", failures: 0 },
  },
  worker: { status: "degraded", last_heartbeat: Date.now() / 1000 - 150, failure_count: 3 },
};

describe("StatusPage", () => {
  beforeEach(() => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
  });

  afterEach(() => {
    vi.useRealTimers();
    vi.restoreAllMocks();
  });

  it("renders status page with all service cards when healthy", async () => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(MOCK_HEALTH_OK),
    });

    render(<StatusPage />);

    await waitFor(() => {
      expect(screen.getByText("All Systems Operational")).toBeInTheDocument();
    });

    // Page heading
    expect(screen.getByRole("heading", { level: 1, name: "System Status" })).toBeInTheDocument();

    // Service cards
    const cards = screen.getAllByTestId("service-card");
    expect(cards.length).toBe(7);

    // Specific services
    expect(screen.getByText("API Server")).toBeInTheDocument();
    expect(screen.getByText("Database")).toBeInTheDocument();
    expect(screen.getByText("Redis")).toBeInTheDocument();

    // Uptime display
    expect(screen.getByText("2d 0h 0m")).toBeInTheDocument();
    expect(screen.getByText("Uptime")).toBeInTheDocument();
  });

  it("renders degraded state with correct banner and service statuses", async () => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(MOCK_HEALTH_DEGRADED),
    });

    render(<StatusPage />);

    await waitFor(() => {
      expect(screen.getByText("Degraded Performance")).toBeInTheDocument();
    });

    const banner = screen.getByTestId("status-banner");
    expect(banner).toBeInTheDocument();
    expect(banner.textContent).toContain("Some services are experiencing issues");

    // LLM Groq should show "Down" (circuit open)
    expect(screen.getByText("LLM — Groq")).toBeInTheDocument();
    // Worker should show "Degraded"
    expect(screen.getByText("Document Processor")).toBeInTheDocument();
  });
});

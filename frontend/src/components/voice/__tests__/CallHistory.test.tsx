/**
 * Unit tests for CallHistory component
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import { CallHistory } from "../CallHistory";
import React from "react";

const mockCalls = {
  calls: [
    {
      id: "call-1",
      conversation_id: "conv-1",
      direction: "inbound",
      phone_from: "+1234567890",
      phone_to: "+0987654321",
      duration_sec: 120,
      recording_url: null,
      transcript: "Customer: Hello\nAssistant: Hi there",
      summary: "General inquiry",
      sentiment: "positive",
      actions_taken: null,
      created_at: "2026-02-13T10:00:00Z",
    },
    {
      id: "call-2",
      conversation_id: "conv-2",
      direction: "web",
      phone_from: "",
      phone_to: "",
      duration_sec: 60,
      recording_url: null,
      transcript: null,
      summary: null,
      sentiment: "negative",
      actions_taken: [{ action: "escalate" }],
      created_at: "2026-02-13T09:00:00Z",
    },
  ],
  total: 2,
  page: 1,
  page_size: 20,
};

beforeEach(() => {
  vi.clearAllMocks();
  global.fetch = vi.fn();
});

describe("CallHistory", () => {
  it("renders call list after loading", async () => {
    (global.fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
      ok: true,
      json: async () => mockCalls,
    });

    render(<CallHistory onSelectCall={vi.fn()} />);

    await waitFor(() => {
      expect(screen.getByText("2:00")).toBeInTheDocument();
    });
  });

  it("shows sentiment badges", async () => {
    (global.fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
      ok: true,
      json: async () => mockCalls,
    });

    render(<CallHistory onSelectCall={vi.fn()} />);

    await waitFor(() => {
      expect(screen.getByText("positive")).toBeInTheDocument();
      expect(screen.getByText("negative")).toBeInTheDocument();
    });
  });

  it("shows escalation badge when actions_taken contains escalate", async () => {
    (global.fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
      ok: true,
      json: async () => mockCalls,
    });

    render(<CallHistory onSelectCall={vi.fn()} />);

    await waitFor(() => {
      expect(screen.getByText("Escalated")).toBeInTheDocument();
    });
  });

  it("renders empty state when no calls", async () => {
    (global.fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
      ok: true,
      json: async () => ({ calls: [], total: 0, page: 1, page_size: 20 }),
    });

    render(<CallHistory onSelectCall={vi.fn()} />);

    await waitFor(() => {
      expect(screen.getByText("No calls yet")).toBeInTheDocument();
    });
  });
});

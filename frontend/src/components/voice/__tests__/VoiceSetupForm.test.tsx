/**
 * Unit tests for VoiceSetupForm component
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { VoiceSetupForm } from "../VoiceSetupForm";
import React from "react";

beforeEach(() => {
  vi.clearAllMocks();
  global.fetch = vi.fn();
  global.confirm = vi.fn(() => true);
});

describe("VoiceSetupForm", () => {
  it("shows 'not configured' when no voice config", async () => {
    (global.fetch as ReturnType<typeof vi.fn>).mockRejectedValueOnce(
      new Error("Not found")
    );

    render(<VoiceSetupForm />);

    await waitFor(() => {
      expect(
        screen.getByText("Voice is not configured")
      ).toBeInTheDocument();
    });
  });

  it("shows setup form fields when not configured", async () => {
    (global.fetch as ReturnType<typeof vi.fn>).mockRejectedValueOnce(
      new Error("Not found")
    );

    render(<VoiceSetupForm />);

    await waitFor(() => {
      expect(screen.getByLabelText("Vapi Private Key")).toBeInTheDocument();
      expect(screen.getByLabelText("Vapi Public Key")).toBeInTheDocument();
      expect(screen.getByLabelText("First Message")).toBeInTheDocument();
      expect(screen.getByText("Enable Voice")).toBeInTheDocument();
    });
  });

  it("validates that both keys are required", async () => {
    (global.fetch as ReturnType<typeof vi.fn>).mockRejectedValueOnce(
      new Error("Not found")
    );

    render(<VoiceSetupForm />);

    await waitFor(() => {
      expect(screen.getByText("Enable Voice")).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText("Enable Voice"));

    await waitFor(() => {
      expect(
        screen.getByText("Both API keys are required")
      ).toBeInTheDocument();
    });
  });

  it("shows 'enabled' status when configured", async () => {
    (global.fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        voice_enabled: true,
        assistant_id: "asst-123",
        public_key: "pk-123",
        first_message: "Hello!",
        created_at: "2026-02-13T10:00:00Z",
      }),
    });

    render(<VoiceSetupForm />);

    await waitFor(() => {
      expect(screen.getByText("Voice is enabled")).toBeInTheDocument();
      expect(screen.getByText(/asst-123/)).toBeInTheDocument();
    });
  });

  it("shows Disable Voice button when configured", async () => {
    (global.fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        voice_enabled: true,
        assistant_id: "asst-123",
        public_key: "pk-123",
        first_message: "Hello!",
        created_at: "2026-02-13T10:00:00Z",
      }),
    });

    render(<VoiceSetupForm />);

    await waitFor(() => {
      const matches = screen.getAllByText("Disable Voice");
      expect(matches.length).toBeGreaterThanOrEqual(1);
    });
  });
});

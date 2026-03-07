/**
 * Unit tests for CallDetail component
 */
import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { CallDetail } from "../CallDetail";
import type { CallLogResponse } from "@/types/voice";
import React from "react";

const mockCall: CallLogResponse = {
  id: "call-1",
  conversation_id: "conv-1",
  direction: "inbound",
  phone_from: "+1234567890",
  phone_to: "+0987654321",
  duration_sec: 185,
  recording_url: null,
  transcript: "Customer: I need help\nAssistant: Sure, how can I help?",
  summary: "Customer asked for help with their account",
  sentiment: "positive",
  actions_taken: null,
  created_at: "2026-02-13T10:00:00Z",
};

const mockCallWithEscalation: CallLogResponse = {
  ...mockCall,
  id: "call-2",
  actions_taken: [
    { action: "escalate", rule_type: "keyword", matched: "speak to human" },
  ],
};

describe("CallDetail", () => {
  it("displays call metadata", () => {
    render(<CallDetail call={mockCall} onBack={vi.fn()} />);
    expect(screen.getByText("Call Detail")).toBeInTheDocument();
    expect(screen.getByText("Inbound Call")).toBeInTheDocument();
    expect(screen.getByText("3m 5s")).toBeInTheDocument();
    expect(screen.getByText("+1234567890")).toBeInTheDocument();
  });

  it("displays transcript with speaker attribution", () => {
    render(<CallDetail call={mockCall} onBack={vi.fn()} />);
    expect(screen.getByText("I need help")).toBeInTheDocument();
    expect(screen.getByText("Sure, how can I help?")).toBeInTheDocument();
  });

  it("displays summary section", () => {
    render(<CallDetail call={mockCall} onBack={vi.fn()} />);
    expect(screen.getByText("Summary")).toBeInTheDocument();
    expect(
      screen.getByText("Customer asked for help with their account")
    ).toBeInTheDocument();
  });

  it("displays sentiment badge", () => {
    render(<CallDetail call={mockCall} onBack={vi.fn()} />);
    expect(screen.getByText("positive")).toBeInTheDocument();
  });

  it("shows escalation info when present", () => {
    render(<CallDetail call={mockCallWithEscalation} onBack={vi.fn()} />);
    expect(screen.getByText("Escalation Triggered")).toBeInTheDocument();
    expect(screen.getByText("keyword")).toBeInTheDocument();
    expect(screen.getByText("speak to human")).toBeInTheDocument();
  });

  it("does not show escalation section when no escalation", () => {
    render(<CallDetail call={mockCall} onBack={vi.fn()} />);
    expect(
      screen.queryByText("Escalation Triggered")
    ).not.toBeInTheDocument();
  });

  it("shows 'No transcript available' when transcript is null", () => {
    const callWithoutTranscript = { ...mockCall, transcript: null };
    render(<CallDetail call={callWithoutTranscript} onBack={vi.fn()} />);
    expect(
      screen.getByText("No transcript available")
    ).toBeInTheDocument();
  });
});

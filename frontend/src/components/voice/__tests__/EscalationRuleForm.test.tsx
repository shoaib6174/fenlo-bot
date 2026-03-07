/**
 * Unit tests for EscalationRuleForm component
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { EscalationRuleForm } from "../EscalationRuleForm";
import React from "react";

beforeEach(() => {
  vi.clearAllMocks();
  global.fetch = vi.fn();
});

describe("EscalationRuleForm", () => {
  it("renders create form with default values", () => {
    render(
      <EscalationRuleForm
        rule={null}
        onClose={vi.fn()}
        onSaved={vi.fn()}
      />
    );
    expect(
      screen.getByText("Create Escalation Rule")
    ).toBeInTheDocument();
    expect(screen.getByLabelText("Rule Type")).toBeInTheDocument();
    expect(screen.getByLabelText("Action")).toBeInTheDocument();
    expect(screen.getByLabelText("Priority")).toBeInTheDocument();
  });

  it("shows keyword fields when keyword type selected", () => {
    render(
      <EscalationRuleForm
        rule={null}
        onClose={vi.fn()}
        onSaved={vi.fn()}
      />
    );
    // Default type is keyword
    expect(
      screen.getByLabelText("Keywords (comma-separated)")
    ).toBeInTheDocument();
    expect(screen.getByLabelText("Match Mode")).toBeInTheDocument();
  });

  it("validates that keywords are required for keyword type", async () => {
    render(
      <EscalationRuleForm
        rule={null}
        onClose={vi.fn()}
        onSaved={vi.fn()}
      />
    );

    // Submit without filling keywords
    fireEvent.click(screen.getByText("Create Rule"));

    await waitFor(() => {
      expect(
        screen.getByText("At least one keyword is required")
      ).toBeInTheDocument();
    });
  });

  it("calls API on valid submission", async () => {
    (global.fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
      ok: true,
      json: async () => ({ id: "rule-1" }),
    });
    const onSaved = vi.fn();

    render(
      <EscalationRuleForm
        rule={null}
        onClose={vi.fn()}
        onSaved={onSaved}
      />
    );

    fireEvent.change(screen.getByLabelText("Keywords (comma-separated)"), {
      target: { value: "help, agent" },
    });
    fireEvent.click(screen.getByText("Create Rule"));

    await waitFor(() => {
      expect(global.fetch).toHaveBeenCalledWith(
        expect.stringContaining("/api/v1/voice/escalation-rules"),
        expect.objectContaining({ method: "POST" })
      );
    });

    await waitFor(() => {
      expect(onSaved).toHaveBeenCalled();
    });
  });

  it("calls onClose when Cancel is clicked", () => {
    const onClose = vi.fn();
    render(
      <EscalationRuleForm
        rule={null}
        onClose={onClose}
        onSaved={vi.fn()}
      />
    );
    fireEvent.click(screen.getByText("Cancel"));
    expect(onClose).toHaveBeenCalled();
  });

  it("shows edit mode when rule prop is provided", () => {
    const existingRule = {
      id: "rule-1",
      workspace_id: "ws-1",
      rule_type: "sentiment" as const,
      condition: { threshold: "negative" },
      action: "escalate" as const,
      is_active: true,
      priority: 5,
      created_at: "2026-02-13T10:00:00Z",
    };

    render(
      <EscalationRuleForm
        rule={existingRule}
        onClose={vi.fn()}
        onSaved={vi.fn()}
      />
    );
    expect(
      screen.getByText("Edit Escalation Rule")
    ).toBeInTheDocument();
    expect(screen.getByText("Update Rule")).toBeInTheDocument();
  });
});

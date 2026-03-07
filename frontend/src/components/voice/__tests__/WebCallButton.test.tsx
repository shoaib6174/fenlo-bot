/**
 * Unit tests for WebCallButton component
 */
import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { WebCallButton } from "../WebCallButton";
import React from "react";

describe("WebCallButton", () => {
  it("shows 'Start Test Call' in idle state", () => {
    render(
      <WebCallButton callState="idle" onStart={vi.fn()} onEnd={vi.fn()} />
    );
    expect(screen.getByText("Start Test Call")).toBeInTheDocument();
  });

  it("shows 'Connecting...' in connecting state", () => {
    render(
      <WebCallButton
        callState="connecting"
        onStart={vi.fn()}
        onEnd={vi.fn()}
      />
    );
    expect(screen.getByText("Connecting...")).toBeInTheDocument();
  });

  it("shows 'End Call' in active state", () => {
    render(
      <WebCallButton callState="active" onStart={vi.fn()} onEnd={vi.fn()} />
    );
    expect(screen.getByText("End Call")).toBeInTheDocument();
  });

  it("shows 'Call Again' in ended state", () => {
    render(
      <WebCallButton callState="ended" onStart={vi.fn()} onEnd={vi.fn()} />
    );
    expect(screen.getByText("Call Again")).toBeInTheDocument();
  });

  it("calls onStart when idle button is clicked", () => {
    const onStart = vi.fn();
    render(
      <WebCallButton callState="idle" onStart={onStart} onEnd={vi.fn()} />
    );
    fireEvent.click(screen.getByText("Start Test Call"));
    expect(onStart).toHaveBeenCalledTimes(1);
  });

  it("calls onEnd when active button is clicked", () => {
    const onEnd = vi.fn();
    render(
      <WebCallButton callState="active" onStart={vi.fn()} onEnd={onEnd} />
    );
    fireEvent.click(screen.getByText("End Call"));
    expect(onEnd).toHaveBeenCalledTimes(1);
  });

  it("disables button when disabled prop is true", () => {
    render(
      <WebCallButton
        callState="idle"
        onStart={vi.fn()}
        onEnd={vi.fn()}
        disabled
      />
    );
    expect(screen.getByText("Start Test Call").closest("button")).toBeDisabled();
  });

  it("connecting state button is always disabled", () => {
    render(
      <WebCallButton
        callState="connecting"
        onStart={vi.fn()}
        onEnd={vi.fn()}
      />
    );
    expect(
      screen.getByText("Connecting...").closest("button")
    ).toBeDisabled();
  });
});

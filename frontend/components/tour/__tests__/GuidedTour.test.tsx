/**
 * Unit tests for GuidedTour component (S81)
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import React from "react";
import { GuidedTour, TOUR_STEPS } from "../GuidedTour";

// Mock next/navigation
const mockPush = vi.fn();
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: mockPush }),
  usePathname: () => "/dashboard",
}));

// Mock localStorage
const store: Record<string, string> = {};
const localStorageMock = {
  getItem: vi.fn((key: string) => store[key] ?? null),
  setItem: vi.fn((key: string, value: string) => { store[key] = value; }),
  removeItem: vi.fn((key: string) => { delete store[key]; }),
  clear: vi.fn(() => { Object.keys(store).forEach(k => delete store[k]); }),
  length: 0,
  key: vi.fn(() => null),
};
Object.defineProperty(window, "localStorage", { value: localStorageMock });

describe("GuidedTour", () => {
  const onClose = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
    Object.keys(store).forEach(k => delete store[k]);
  });

  it("shows the first step when tour starts", () => {
    render(<GuidedTour isOpen={true} onClose={onClose} initialStep={0} />);

    // Tour card is visible
    expect(screen.getByTestId("tour-card")).toBeInTheDocument();

    // First step content
    expect(screen.getByText("Dashboard")).toBeInTheDocument();
    expect(screen.getByText(TOUR_STEPS[0].description)).toBeInTheDocument();

    // Step counter
    expect(screen.getByText(`Step 1 of ${TOUR_STEPS.length}`)).toBeInTheDocument();

    // No "Back" button on first step
    expect(screen.queryByTestId("tour-prev")).not.toBeInTheDocument();

    // "Next" button is visible
    expect(screen.getByTestId("tour-next")).toBeInTheDocument();
    expect(screen.getByTestId("tour-next").textContent).toContain("Next");
  });

  it("navigates through steps with Next and Back buttons", () => {
    render(<GuidedTour isOpen={true} onClose={onClose} initialStep={0} />);

    // Click Next to go to step 2
    fireEvent.click(screen.getByTestId("tour-next"));
    expect(screen.getByText("RAG Chat")).toBeInTheDocument();
    expect(screen.getByText(`Step 2 of ${TOUR_STEPS.length}`)).toBeInTheDocument();
    expect(mockPush).toHaveBeenCalledWith("/chat");

    // Back button appears
    expect(screen.getByTestId("tour-prev")).toBeInTheDocument();

    // Click Back to return to step 1
    fireEvent.click(screen.getByTestId("tour-prev"));
    expect(screen.getByText("Dashboard")).toBeInTheDocument();
    expect(screen.getByText(`Step 1 of ${TOUR_STEPS.length}`)).toBeInTheDocument();
  });

  it("completes tour and persists to localStorage", () => {
    // Start at the last step
    const lastIndex = TOUR_STEPS.length - 1;
    render(<GuidedTour isOpen={true} onClose={onClose} initialStep={lastIndex} />);

    // Last step should show "Finish" instead of "Next"
    expect(screen.getByText("Settings")).toBeInTheDocument();
    expect(screen.getByTestId("tour-next").textContent).toContain("Finish");

    // Click Finish
    fireEvent.click(screen.getByTestId("tour-next"));

    // Tour should close
    expect(onClose).toHaveBeenCalled();

    // localStorage should be set
    expect(localStorageMock.setItem).toHaveBeenCalledWith("botforge_tour_completed", "true");
  });

  it("does not render when isOpen is false", () => {
    render(<GuidedTour isOpen={false} onClose={onClose} initialStep={0} />);
    expect(screen.queryByTestId("tour-card")).not.toBeInTheDocument();
  });

  it("skips tour and persists to localStorage", () => {
    render(<GuidedTour isOpen={true} onClose={onClose} initialStep={0} />);

    fireEvent.click(screen.getByTestId("tour-skip"));

    expect(onClose).toHaveBeenCalled();
    expect(localStorageMock.setItem).toHaveBeenCalledWith("botforge_tour_completed", "true");
  });
});

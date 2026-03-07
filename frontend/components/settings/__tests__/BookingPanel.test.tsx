/**
 * Unit tests for BookingPanel component (S88 - 8.70)
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import React from "react";
import { BookingPanel } from "../BookingPanel";

// Mock fetch globally
const mockFetch = vi.fn();
global.fetch = mockFetch;

const mockBooking = {
  booking_provider: "calendly",
  booking_url: "https://calendly.com/test/30min",
  booking_prompt: "Book a demo with us!",
  booking_enabled: true,
};

function setupFetchMock(booking = mockBooking) {
  mockFetch.mockImplementation((url: string, options?: RequestInit) => {
    if (url.includes("/booking") && (!options?.method || options.method === "GET")) {
      return Promise.resolve({
        ok: true,
        json: () => Promise.resolve(booking),
      });
    }
    if (url.includes("/booking") && options?.method === "PUT") {
      return Promise.resolve({
        ok: true,
        json: () => Promise.resolve(booking),
      });
    }
    return Promise.resolve({ ok: false, status: 404 });
  });
}

describe("BookingPanel", () => {
  beforeEach(() => {
    mockFetch.mockReset();
    setupFetchMock();
  });

  it("renders booking form with loaded values", async () => {
    render(<BookingPanel />);

    await waitFor(() => {
      expect(screen.getByText("Calendar / Booking Integration")).toBeInTheDocument();
    });

    // Shows provider selector with fetched value
    const providerSelect = screen.getByTestId("booking-provider-select") as HTMLSelectElement;
    expect(providerSelect.value).toBe("calendly");

    // Shows URL input with fetched value
    const urlInput = screen.getByTestId("booking-url-input") as HTMLInputElement;
    expect(urlInput.value).toBe("https://calendly.com/test/30min");

    // Shows save button
    expect(screen.getByTestId("save-booking-btn")).toBeInTheDocument();
  });

  it("renders enable toggle in correct state", async () => {
    render(<BookingPanel />);

    await waitFor(() => {
      expect(screen.getByTestId("booking-enabled-toggle")).toBeInTheDocument();
    });

    const toggle = screen.getByTestId("booking-enabled-toggle");
    expect(toggle.getAttribute("aria-checked")).toBe("true");
  });

  it("saves booking settings and shows success", async () => {
    const user = userEvent.setup();
    render(<BookingPanel />);

    await waitFor(() => {
      expect(screen.getByTestId("save-booking-btn")).toBeInTheDocument();
    });

    await user.click(screen.getByTestId("save-booking-btn"));

    await waitFor(() => {
      expect(screen.getByTestId("booking-status")).toBeInTheDocument();
    });
  });

  it("shows chat preview with booking card", async () => {
    render(<BookingPanel />);

    await waitFor(() => {
      expect(screen.getByText("Chat Preview")).toBeInTheDocument();
    });

    // The preview shows the "Schedule a Meeting" card and "Book Now" button
    expect(screen.getByText("Schedule a Meeting")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Book Now/i })).toBeInTheDocument();
  });
});

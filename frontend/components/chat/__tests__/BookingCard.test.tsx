/**
 * Unit tests for BookingCard chat component (S88 - 8.70)
 */
import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import React from "react";
import { BookingCard } from "../BookingCard";

describe("BookingCard", () => {
  it("renders booking card with provider and link", () => {
    render(
      <BookingCard
        config={{
          provider: "calendly",
          url: "https://calendly.com/test/30min",
          prompt: "Book a meeting!",
        }}
      />
    );

    expect(screen.getByTestId("booking-card")).toBeInTheDocument();
    expect(screen.getByText("Schedule a Meeting")).toBeInTheDocument();
    expect(screen.getByText("Calendly")).toBeInTheDocument();
    expect(screen.getByText("Book Now")).toBeInTheDocument();

    const link = screen.getByTestId("booking-card-link");
    expect(link).toHaveAttribute("href", "https://calendly.com/test/30min");
    expect(link).toHaveAttribute("target", "_blank");
  });

  it("renders with custom_url provider label", () => {
    render(
      <BookingCard
        config={{
          provider: "custom_url",
          url: "https://booking.example.com",
          prompt: "",
        }}
      />
    );

    expect(screen.getByText("Booking")).toBeInTheDocument();
  });
});

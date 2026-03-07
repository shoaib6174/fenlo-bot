/**
 * ROI Calculator tests — math accuracy and rendering
 */

import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import ROICalculator from "../ROICalculator";

describe("ROICalculator", () => {
  it("renders with default values and shows savings", () => {
    render(<ROICalculator />);

    expect(screen.getByText("How Much Will You Save?")).toBeInTheDocument();
    expect(screen.getByText("ROI Calculator")).toBeInTheDocument();

    // Default: 500 tickets × 0.60 × (8/60) hrs × $25 = $1,000/month
    // Check the monthly savings is displayed (animated, so check data-testid)
    const monthlySavings = screen.getByTestId("monthly-savings");
    expect(monthlySavings).toBeInTheDocument();
  });

  it("calculates correct monthly savings for custom inputs", async () => {
    render(<ROICalculator />);

    // Change tickets to 1000
    const ticketSlider = screen.getByLabelText("Support tickets per month");
    fireEvent.change(ticketSlider, { target: { value: "1000" } });

    // Change handle time to 15 minutes
    const handleSlider = screen.getByLabelText(
      "Average handle time in minutes"
    );
    fireEvent.change(handleSlider, { target: { value: "15" } });

    // Change hourly cost to 40
    const costSlider = screen.getByLabelText("Agent hourly cost in dollars");
    fireEvent.change(costSlider, { target: { value: "40" } });

    // Expected: 1000 × 0.60 × (15/60) × 40 = 6,000
    await waitFor(
      () => {
        const monthlySavings = screen.getByTestId("monthly-savings");
        expect(monthlySavings.textContent).toContain("6,000");
      },
      { timeout: 2000 }
    );
  });

  it("shows yearly savings (12× monthly)", async () => {
    render(<ROICalculator />);

    // Default: $1,000/month → $12,000/year
    await waitFor(
      () => {
        const yearlySavings = screen.getByTestId("yearly-savings");
        expect(yearlySavings.textContent).toContain("12,000");
      },
      { timeout: 2000 }
    );
  });

  it("shows hours freed per month", async () => {
    render(<ROICalculator />);

    // Default: 500 × 0.60 × (8/60) = 40 hours
    await waitFor(
      () => {
        const hoursFreed = screen.getByTestId("hours-freed");
        expect(hoursFreed.textContent).toContain("40");
      },
      { timeout: 2000 }
    );
  });

  it("displays the 60% automation rate note", () => {
    render(<ROICalculator />);

    expect(screen.getByText(/60% automation rate/)).toBeInTheDocument();
  });
});

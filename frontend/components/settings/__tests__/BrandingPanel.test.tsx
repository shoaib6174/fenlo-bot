/**
 * Unit tests for BrandingPanel component (S87 - 8.65)
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import React from "react";
import { BrandingPanel } from "../BrandingPanel";

// Mock fetch globally
const mockFetch = vi.fn();
global.fetch = mockFetch;

const mockBranding = {
  brand_name: "Acme Bots",
  logo_url: "https://example.com/logo.png",
  favicon_url: "",
  accent_color: "#7c3aed",
  hide_powered_by: false,
  client_preview_mode: false,
};

function setupFetchMock(branding = mockBranding) {
  mockFetch.mockImplementation((url: string, options?: RequestInit) => {
    if (url.includes("/branding") && (!options?.method || options.method === "GET")) {
      return Promise.resolve({
        ok: true,
        json: () => Promise.resolve(branding),
      });
    }
    if (url.includes("/branding") && options?.method === "PUT") {
      return Promise.resolve({
        ok: true,
        json: () => Promise.resolve(branding),
      });
    }
    return Promise.resolve({ ok: false, status: 404 });
  });
}

describe("BrandingPanel", () => {
  beforeEach(() => {
    mockFetch.mockReset();
    setupFetchMock();
  });

  it("renders branding form with loaded values", async () => {
    render(<BrandingPanel />);

    await waitFor(() => {
      expect(screen.getByText("White-Label Branding")).toBeInTheDocument();
    });

    // Shows brand name input with fetched value
    const nameInput = screen.getByTestId("brand-name-input") as HTMLInputElement;
    expect(nameInput.value).toBe("Acme Bots");

    // Shows accent color
    const colorInput = screen.getByTestId("accent-color-input") as HTMLInputElement;
    expect(colorInput.value).toBe("#7c3aed");

    // Shows save button
    expect(screen.getByTestId("save-branding-btn")).toBeInTheDocument();
  });

  it("renders preview mode toggle", async () => {
    render(<BrandingPanel />);

    await waitFor(() => {
      expect(screen.getByText("Client Preview Mode")).toBeInTheDocument();
    });

    const toggle = screen.getByTestId("preview-mode-toggle");
    expect(toggle).toBeInTheDocument();
    expect(toggle.getAttribute("aria-checked")).toBe("false");
  });

  it("saves branding and shows success message", async () => {
    const user = userEvent.setup();
    const dispatchSpy = vi.spyOn(window, "dispatchEvent");

    render(<BrandingPanel />);

    await waitFor(() => {
      expect(screen.getByTestId("save-branding-btn")).toBeInTheDocument();
    });

    await user.click(screen.getByTestId("save-branding-btn"));

    await waitFor(() => {
      expect(screen.getByTestId("branding-status")).toBeInTheDocument();
    });

    // PUT was called
    const putCalls = mockFetch.mock.calls.filter(
      (c: unknown[]) => (c[1] as RequestInit | undefined)?.method === "PUT"
    );
    expect(putCalls.length).toBe(1);

    // CustomEvent dispatched for sidebar
    expect(dispatchSpy).toHaveBeenCalledWith(
      expect.objectContaining({ type: "branding-updated" })
    );

    dispatchSpy.mockRestore();
  });

  it("renders hide powered-by toggle", async () => {
    render(<BrandingPanel />);

    await waitFor(() => {
      expect(screen.getByTestId("hide-powered-toggle")).toBeInTheDocument();
    });

    const toggle = screen.getByTestId("hide-powered-toggle");
    expect(toggle.getAttribute("aria-checked")).toBe("false");
  });

  it("renders preset color buttons", async () => {
    render(<BrandingPanel />);

    await waitFor(() => {
      expect(screen.getByText("White-Label Branding")).toBeInTheDocument();
    });

    // Check for preset colors
    expect(screen.getByTitle("Blue")).toBeInTheDocument();
    expect(screen.getByTitle("Purple")).toBeInTheDocument();
    expect(screen.getByTitle("Green")).toBeInTheDocument();
    expect(screen.getByTitle("Red")).toBeInTheDocument();
  });
});

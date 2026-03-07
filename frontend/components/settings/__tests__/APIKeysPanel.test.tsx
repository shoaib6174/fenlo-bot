/**
 * Unit tests for APIKeysPanel component (S86 - 8.61)
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import React from "react";
import { APIKeysPanel } from "../APIKeysPanel";

// Mock fetch globally
const mockFetch = vi.fn();
global.fetch = mockFetch;

const mockKeys = [
  {
    id: "key-1",
    name: "Production Server",
    prefix: "bf_live_a1b2...",
    scopes: ["read", "chat"],
    rate_limit: 100,
    is_revoked: false,
    last_used_at: "2026-02-16T10:00:00Z",
    request_count: 42,
    created_at: "2026-02-15T08:00:00Z",
  },
  {
    id: "key-2",
    name: "Old Key",
    prefix: "bf_live_x9y8...",
    scopes: ["read"],
    rate_limit: 50,
    is_revoked: true,
    last_used_at: null,
    request_count: 0,
    created_at: "2026-02-10T08:00:00Z",
  },
];

function setupFetchMock() {
  mockFetch.mockImplementation((url: string, options?: RequestInit) => {
    if (url.includes("/api-keys") && (!options?.method || options.method === "GET")) {
      return Promise.resolve({
        ok: true,
        json: () => Promise.resolve(mockKeys),
      });
    }
    if (url.includes("/api-keys") && options?.method === "POST") {
      return Promise.resolve({
        ok: true,
        json: () =>
          Promise.resolve({
            id: "key-new",
            name: "New Key",
            key: "bf_live_newsecretkey1234567890",
            prefix: "bf_live_news...",
            scopes: ["read", "chat"],
            rate_limit: 100,
            created_at: "2026-02-16T12:00:00Z",
          }),
      });
    }
    if (url.includes("/api-keys/") && options?.method === "DELETE") {
      return Promise.resolve({
        ok: true,
        json: () => Promise.resolve({ message: "API key revoked" }),
      });
    }
    return Promise.resolve({ ok: false, status: 404 });
  });
}

describe("APIKeysPanel", () => {
  beforeEach(() => {
    mockFetch.mockReset();
    setupFetchMock();
  });

  it("renders API keys list with name, prefix, scopes, and usage", async () => {
    render(<APIKeysPanel />);

    await waitFor(() => {
      expect(screen.getByText("API Keys")).toBeInTheDocument();
    });

    // Shows keys
    expect(screen.getByText("Production Server")).toBeInTheDocument();
    expect(screen.getByText("Old Key")).toBeInTheDocument();
    expect(screen.getByText("bf_live_a1b2...")).toBeInTheDocument();
    expect(screen.getByText("Revoked")).toBeInTheDocument();
    expect(screen.getByText("42 requests")).toBeInTheDocument();

    // Shows create button
    expect(screen.getByTestId("create-key-btn")).toBeInTheDocument();
  });

  it("creates a new API key and shows it once", async () => {
    const user = userEvent.setup();
    render(<APIKeysPanel />);

    await waitFor(() => {
      expect(screen.getByTestId("create-key-btn")).toBeInTheDocument();
    });

    // Open create form
    await user.click(screen.getByTestId("create-key-btn"));

    await waitFor(() => {
      expect(screen.getByTestId("create-key-form")).toBeInTheDocument();
    });

    // Fill in name
    await user.type(screen.getByTestId("key-name-input"), "New Key");

    // Submit
    await user.click(screen.getByTestId("confirm-create-btn"));

    // Should show the new key value
    await waitFor(() => {
      expect(screen.getByTestId("new-key-display")).toBeInTheDocument();
      expect(screen.getByTestId("new-key-value")).toBeInTheDocument();
      expect(screen.getByTestId("copy-key-btn")).toBeInTheDocument();
    });

    // Verify the key value is displayed
    expect(screen.getByTestId("new-key-value").textContent).toBe("bf_live_newsecretkey1234567890");
  });
});

/**
 * Unit tests for ThemeProvider and dark mode
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, act } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import React from "react";
import { ThemeProvider, useTheme } from "../theme";

// Custom localStorage mock
const store: Record<string, string> = {};
const localStorageMock = {
  getItem: vi.fn((key: string) => store[key] ?? null),
  setItem: vi.fn((key: string, value: string) => {
    store[key] = value;
  }),
  removeItem: vi.fn((key: string) => {
    delete store[key];
  }),
  clear: vi.fn(() => {
    Object.keys(store).forEach((k) => delete store[k]);
  }),
  length: 0,
  key: vi.fn(() => null),
};
Object.defineProperty(window, "localStorage", { value: localStorageMock });

// Mock matchMedia
let prefersDark = false;
const mediaListeners: Array<() => void> = [];
Object.defineProperty(window, "matchMedia", {
  writable: true,
  value: vi.fn().mockImplementation((query: string) => ({
    matches: query === "(prefers-color-scheme: dark)" ? prefersDark : false,
    media: query,
    onchange: null,
    addListener: vi.fn(),
    removeListener: vi.fn(),
    addEventListener: vi.fn((_: string, handler: () => void) => {
      mediaListeners.push(handler);
    }),
    removeEventListener: vi.fn(),
    dispatchEvent: vi.fn(),
  })),
});

// Test component that exposes theme context
function ThemeDisplay() {
  const { theme, resolvedTheme, toggleTheme, setTheme } = useTheme();
  return (
    <div>
      <span data-testid="theme">{theme}</span>
      <span data-testid="resolved">{resolvedTheme}</span>
      <button data-testid="toggle" onClick={toggleTheme}>
        Toggle
      </button>
      <button data-testid="set-dark" onClick={() => setTheme("dark")}>
        Set Dark
      </button>
      <button data-testid="set-system" onClick={() => setTheme("system")}>
        Set System
      </button>
    </div>
  );
}

describe("ThemeProvider", () => {
  beforeEach(() => {
    localStorageMock.clear();
    localStorageMock.getItem.mockClear();
    localStorageMock.setItem.mockClear();
    prefersDark = false;
    mediaListeners.length = 0;
    document.documentElement.classList.remove("dark");
  });

  it("toggles between light and dark mode", async () => {
    const user = userEvent.setup();

    render(
      <ThemeProvider>
        <ThemeDisplay />
      </ThemeProvider>
    );

    // Default is system → resolves to light (prefersDark = false)
    expect(screen.getByTestId("resolved")).toHaveTextContent("light");
    expect(document.documentElement.classList.contains("dark")).toBe(false);

    // Toggle to dark
    await user.click(screen.getByTestId("toggle"));

    expect(screen.getByTestId("resolved")).toHaveTextContent("dark");
    expect(screen.getByTestId("theme")).toHaveTextContent("dark");
    expect(document.documentElement.classList.contains("dark")).toBe(true);

    // Toggle back to light
    await user.click(screen.getByTestId("toggle"));

    expect(screen.getByTestId("resolved")).toHaveTextContent("light");
    expect(document.documentElement.classList.contains("dark")).toBe(false);
  });

  it("persists theme preference to localStorage", async () => {
    const user = userEvent.setup();

    render(
      <ThemeProvider>
        <ThemeDisplay />
      </ThemeProvider>
    );

    // Set to dark
    await user.click(screen.getByTestId("set-dark"));

    expect(localStorageMock.setItem).toHaveBeenCalledWith(
      "botforge_theme",
      "dark"
    );

    // Verify stored value
    expect(store["botforge_theme"]).toBe("dark");

    // Re-render — should read from localStorage
    const { unmount } = render(
      <ThemeProvider>
        <ThemeDisplay />
      </ThemeProvider>
    );

    // The provider reads from localStorage on mount
    expect(localStorageMock.getItem).toHaveBeenCalledWith("botforge_theme");
    unmount();
  });

  it("respects system preference when set to 'system'", async () => {
    const user = userEvent.setup();

    // Start with system preferring dark
    prefersDark = true;

    render(
      <ThemeProvider>
        <ThemeDisplay />
      </ThemeProvider>
    );

    // Wait for useEffect to run — theme should resolve to dark via system preference
    expect(screen.getByTestId("theme")).toHaveTextContent("system");
    expect(screen.getByTestId("resolved")).toHaveTextContent("dark");
    expect(document.documentElement.classList.contains("dark")).toBe(true);

    // Set explicit light, then back to system
    await user.click(screen.getByTestId("toggle")); // dark → light
    expect(screen.getByTestId("resolved")).toHaveTextContent("light");

    await user.click(screen.getByTestId("set-system"));
    expect(screen.getByTestId("theme")).toHaveTextContent("system");
    // System still prefers dark
    expect(screen.getByTestId("resolved")).toHaveTextContent("dark");
  });
});

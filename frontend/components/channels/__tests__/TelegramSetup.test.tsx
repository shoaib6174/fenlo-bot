/**
 * TelegramSetup component tests
 */

import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { vi, describe, it, expect, beforeEach } from "vitest";
import { TelegramSetup } from "../TelegramSetup";

// Mock sonner
vi.mock("sonner", () => ({
  toast: { success: vi.fn(), error: vi.fn() },
}));

// Mock useChannels hooks
const mockCreateMutateAsync = vi.fn();
const mockUpdateMutateAsync = vi.fn();

vi.mock("@/hooks/useChannels", () => ({
  useCreateChannel: () => ({
    mutateAsync: mockCreateMutateAsync,
    isPending: false,
  }),
  useUpdateChannel: () => ({
    mutateAsync: mockUpdateMutateAsync,
    isPending: false,
  }),
}));

function renderWithProviders(ui: React.ReactElement) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>{ui}</QueryClientProvider>
  );
}

describe("TelegramSetup", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders the setup form with BotFather instructions", () => {
    renderWithProviders(<TelegramSetup />);

    expect(screen.getByText("Add Telegram Channel")).toBeInTheDocument();
    expect(screen.getByText("How to get a Bot Token")).toBeInTheDocument();
    expect(screen.getByText("@BotFather")).toBeInTheDocument();
    expect(screen.getByText("Create Channel")).toBeInTheDocument();
  });

  it("shows test button for connection testing", () => {
    renderWithProviders(<TelegramSetup />);

    expect(screen.getByRole("button", { name: /test/i })).toBeInTheDocument();
  });

  it("submits create channel with bot token", async () => {
    mockCreateMutateAsync.mockResolvedValue({});
    renderWithProviders(<TelegramSetup onSuccess={vi.fn()} />);

    const tokenInput = screen.getByPlaceholderText(/123456789:ABC/);
    fireEvent.change(tokenInput, { target: { value: "999:TESTTOKEN" } });

    const submitButton = screen.getByRole("button", { name: /create channel/i });
    fireEvent.click(submitButton);

    await waitFor(() => {
      expect(mockCreateMutateAsync).toHaveBeenCalledWith({
        channel: "telegram",
        provider: "telegram",
        config: { bot_token: "999:TESTTOKEN" },
        is_active: true,
      });
    });
  });

  it("shows edit mode when channel prop is provided", () => {
    const existingChannel = {
      id: "test-id",
      channel: "telegram" as const,
      provider: "telegram",
      config: { bot_token: "existing:TOKEN" },
      is_active: true,
      workspace_id: "ws-1",
      created_at: "2024-01-01",
      updated_at: "2024-01-01",
    };

    renderWithProviders(<TelegramSetup channel={existingChannel} />);

    expect(screen.getByText("Edit Telegram Channel")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /save changes/i })).toBeInTheDocument();
  });

  it("renders webhook info section", () => {
    renderWithProviders(<TelegramSetup />);

    expect(screen.getByText("Webhook Setup")).toBeInTheDocument();
    expect(
      screen.getByText(/BotForge will automatically register a webhook/)
    ).toBeInTheDocument();
  });
});

/**
 * TelegramSetup Component
 *
 * Form for configuring Telegram Bot channel via @BotFather
 */

"use client";

import { useState } from "react";
import { Send, Save, ExternalLink, CheckCircle, XCircle, Loader2 } from "lucide-react";
import { toast } from "sonner";
import { useCreateChannel, useUpdateChannel } from "@/hooks/useChannels";
import type { ChannelConfig } from "@/lib/api";

interface TelegramSetupProps {
  channel?: ChannelConfig;
  onSuccess?: () => void;
}

type ConnectionStatus = "idle" | "testing" | "success" | "error";

export function TelegramSetup({ channel, onSuccess }: TelegramSetupProps) {
  const isEditing = !!channel;
  const existingConfig = (channel?.config as Record<string, string>) || {};

  const [botToken, setBotToken] = useState(existingConfig.bot_token || "");
  const [connectionStatus, setConnectionStatus] = useState<ConnectionStatus>("idle");
  const [botInfo, setBotInfo] = useState<{ username: string; first_name: string } | null>(null);

  const createChannel = useCreateChannel();
  const updateChannel = useUpdateChannel();

  const testConnection = async () => {
    if (!botToken.trim()) {
      toast.error("Please enter a bot token");
      return;
    }

    setConnectionStatus("testing");
    setBotInfo(null);

    try {
      const response = await fetch(`https://api.telegram.org/bot${botToken}/getMe`);
      const data = await response.json();

      if (data.ok && data.result) {
        setConnectionStatus("success");
        setBotInfo({
          username: data.result.username || "",
          first_name: data.result.first_name || "",
        });
        toast.success(`Connected to @${data.result.username}`);
      } else {
        setConnectionStatus("error");
        toast.error("Invalid bot token");
      }
    } catch {
      setConnectionStatus("error");
      toast.error("Connection failed — check your token");
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!botToken.trim()) {
      toast.error("Please enter a bot token");
      return;
    }

    const configPayload: Record<string, unknown> = {
      bot_token: botToken.trim(),
    };

    if (botInfo) {
      configPayload.bot_username = botInfo.username;
      configPayload.bot_name = botInfo.first_name;
    }

    try {
      if (isEditing) {
        await updateChannel.mutateAsync({
          id: channel.id,
          data: { config: configPayload },
        });
        toast.success("Telegram channel updated successfully");
      } else {
        await createChannel.mutateAsync({
          channel: "telegram",
          provider: "telegram",
          config: configPayload,
          is_active: true,
        });
        toast.success("Telegram channel created successfully");
      }

      onSuccess?.();
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Failed to save channel");
    }
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-6">
      <div className="flex items-center gap-3 pb-4 border-b">
        <div className="p-2 rounded-lg bg-blue-50">
          <Send className="w-6 h-6 text-blue-500" />
        </div>
        <div>
          <h2 className="text-lg font-semibold text-gray-900">
            {isEditing ? "Edit" : "Add"} Telegram Channel
          </h2>
          <p className="text-sm text-gray-600">Connect a Telegram Bot to your chatbot</p>
        </div>
      </div>

      {/* BotFather Instructions */}
      <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
        <h3 className="text-sm font-medium text-blue-900 mb-2">How to get a Bot Token</h3>
        <ol className="text-sm text-blue-800 space-y-1 list-decimal list-inside">
          <li>
            Open{" "}
            <a
              href="https://t.me/BotFather"
              target="_blank"
              rel="noopener noreferrer"
              className="underline font-medium inline-flex items-center gap-1"
            >
              @BotFather <ExternalLink className="w-3 h-3" />
            </a>{" "}
            in Telegram
          </li>
          <li>Send <code className="bg-blue-100 px-1 rounded">/newbot</code> and follow the prompts</li>
          <li>Copy the bot token provided by BotFather</li>
          <li>Paste it below and test the connection</li>
        </ol>
      </div>

      {/* Bot Token */}
      <div className="space-y-2">
        <label className="block text-sm font-medium text-gray-700">
          Bot Token <span className="text-red-500">*</span>
        </label>
        <div className="flex gap-2">
          <input
            type="password"
            required
            value={botToken}
            onChange={(e) => {
              setBotToken(e.target.value);
              setConnectionStatus("idle");
              setBotInfo(null);
            }}
            className="flex-1 px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            placeholder="123456789:ABCdefGHIjklMNOpqrsTUVwxyz"
          />
          <button
            type="button"
            onClick={testConnection}
            disabled={connectionStatus === "testing"}
            className="px-4 py-2 bg-gray-100 text-gray-700 rounded-md hover:bg-gray-200 disabled:opacity-50 flex items-center gap-2 whitespace-nowrap"
          >
            {connectionStatus === "testing" ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : connectionStatus === "success" ? (
              <CheckCircle className="w-4 h-4 text-green-600" />
            ) : connectionStatus === "error" ? (
              <XCircle className="w-4 h-4 text-red-600" />
            ) : null}
            Test
          </button>
        </div>
        <p className="text-xs text-gray-500">
          The token looks like <code className="bg-gray-100 px-1 rounded">123456789:ABCdef...</code>
        </p>
      </div>

      {/* Connection Result */}
      {connectionStatus === "success" && botInfo && (
        <div className="bg-green-50 border border-green-200 rounded-lg p-4 flex items-start gap-3">
          <CheckCircle className="w-5 h-5 text-green-600 mt-0.5" />
          <div>
            <p className="text-sm font-medium text-green-900">Connection successful</p>
            <p className="text-sm text-green-800">
              Bot: <strong>{botInfo.first_name}</strong> (@{botInfo.username})
            </p>
          </div>
        </div>
      )}

      {connectionStatus === "error" && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4 flex items-start gap-3">
          <XCircle className="w-5 h-5 text-red-600 mt-0.5" />
          <div>
            <p className="text-sm font-medium text-red-900">Connection failed</p>
            <p className="text-sm text-red-800">
              Check that the bot token is correct and try again.
            </p>
          </div>
        </div>
      )}

      {/* Webhook Info */}
      <div className="bg-gray-50 border border-gray-200 rounded-lg p-4">
        <h3 className="text-sm font-medium text-gray-900 mb-1">Webhook Setup</h3>
        <p className="text-sm text-gray-600">
          After saving, Fenlo AI will automatically register a webhook with Telegram.
          Messages sent to your bot will be routed through the AI pipeline.
        </p>
      </div>

      {/* Submit */}
      <div className="flex justify-end gap-3 pt-4 border-t">
        <button
          type="submit"
          disabled={createChannel.isPending || updateChannel.isPending}
          className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          <Save className="w-4 h-4" />
          {createChannel.isPending || updateChannel.isPending
            ? "Saving..."
            : isEditing
              ? "Save Changes"
              : "Create Channel"}
        </button>
      </div>
    </form>
  );
}

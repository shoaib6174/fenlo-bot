"use client";

import { useState, useEffect, useCallback } from "react";
import { Phone, CheckCircle, XCircle, AlertTriangle } from "lucide-react";
import { apiClient } from "@/lib/api";
import type { VoiceConfigResponse } from "@/types/voice";

export function VoiceSetupForm() {
  const [config, setConfig] = useState<VoiceConfigResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState<{
    type: "success" | "error";
    text: string;
  } | null>(null);

  // Form fields
  const [privateKey, setPrivateKey] = useState("");
  const [publicKey, setPublicKey] = useState("");
  const [firstMessage, setFirstMessage] = useState(
    "Hello! How can I help you today?"
  );

  const fetchConfig = useCallback(async () => {
    try {
      const data = await apiClient<VoiceConfigResponse>(
        "/api/v1/voice/config"
      );
      setConfig(data);
      if (data.first_message) setFirstMessage(data.first_message);
    } catch {
      // Not configured yet
      setConfig(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchConfig();
  }, [fetchConfig]);

  const handleSetup = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!privateKey.trim() || !publicKey.trim()) {
      setMessage({ type: "error", text: "Both API keys are required" });
      return;
    }

    setSaving(true);
    setMessage(null);

    try {
      await apiClient("/api/v1/voice/setup", {
        method: "POST",
        body: JSON.stringify({
          vapi_private_key: privateKey.trim(),
          vapi_public_key: publicKey.trim(),
          first_message: firstMessage.trim(),
        }),
      });
      setMessage({ type: "success", text: "Voice configured successfully!" });
      setPrivateKey("");
      setPublicKey("");
      fetchConfig();
    } catch (err) {
      setMessage({
        type: "error",
        text: err instanceof Error ? err.message : "Failed to set up voice",
      });
    } finally {
      setSaving(false);
    }
  };

  const handleDisable = async () => {
    if (!confirm("Disable voice? This will remove your Vapi configuration."))
      return;

    setSaving(true);
    setMessage(null);

    try {
      await apiClient("/api/v1/voice/config", { method: "DELETE" });
      setMessage({ type: "success", text: "Voice has been disabled" });
      setConfig(null);
    } catch (err) {
      setMessage({
        type: "error",
        text: err instanceof Error ? err.message : "Failed to disable voice",
      });
    } finally {
      setSaving(false);
    }
  };

  const handleUpdateMessage = async () => {
    setSaving(true);
    setMessage(null);
    try {
      await apiClient("/api/v1/voice/config", {
        method: "PATCH",
        body: JSON.stringify({ first_message: firstMessage.trim() }),
      });
      setMessage({ type: "success", text: "First message updated" });
      fetchConfig();
    } catch (err) {
      setMessage({
        type: "error",
        text:
          err instanceof Error ? err.message : "Failed to update first message",
      });
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <div className="animate-pulse space-y-4">
        <div className="h-8 bg-gray-200 rounded w-1/4" />
        <div className="h-10 bg-gray-200 rounded" />
        <div className="h-10 bg-gray-200 rounded" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Status indicator */}
      <div className="flex items-center gap-3 p-4 bg-gray-50 rounded-lg border border-gray-200">
        {config?.voice_enabled ? (
          <>
            <CheckCircle className="w-5 h-5 text-green-600" />
            <div>
              <p className="text-sm font-medium text-green-800">
                Voice is enabled
              </p>
              <p className="text-xs text-gray-500">
                Assistant ID: {config.assistant_id || "—"}
              </p>
            </div>
          </>
        ) : (
          <>
            <XCircle className="w-5 h-5 text-gray-400" />
            <div>
              <p className="text-sm font-medium text-gray-600">
                Voice is not configured
              </p>
              <p className="text-xs text-gray-500">
                Enter your Vapi API keys below to enable voice
              </p>
            </div>
          </>
        )}
      </div>

      {/* Setup form (shown when not configured) */}
      {!config?.voice_enabled && (
        <form onSubmit={handleSetup} className="space-y-4">
          <div>
            <label
              htmlFor="vapi-private-key"
              className="block text-sm font-medium text-gray-700 mb-1"
            >
              Vapi Private Key
            </label>
            <input
              id="vapi-private-key"
              type="password"
              value={privateKey}
              onChange={(e) => setPrivateKey(e.target.value)}
              placeholder="sk-..."
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
          <div>
            <label
              htmlFor="vapi-public-key"
              className="block text-sm font-medium text-gray-700 mb-1"
            >
              Vapi Public Key
            </label>
            <input
              id="vapi-public-key"
              type="text"
              value={publicKey}
              onChange={(e) => setPublicKey(e.target.value)}
              placeholder="pk-..."
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
          <div>
            <label
              htmlFor="first-message"
              className="block text-sm font-medium text-gray-700 mb-1"
            >
              First Message
            </label>
            <input
              id="first-message"
              type="text"
              value={firstMessage}
              onChange={(e) => setFirstMessage(e.target.value)}
              placeholder="Hello! How can I help you today?"
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
            <p className="text-xs text-gray-500 mt-1">
              The first thing the voice assistant says when a call connects
            </p>
          </div>

          <button
            type="submit"
            disabled={saving}
            className="inline-flex items-center gap-2 px-4 py-2 bg-green-600 text-white font-medium rounded-md hover:bg-green-700 disabled:opacity-50 transition"
          >
            <Phone className="w-4 h-4" />
            {saving ? "Setting up..." : "Enable Voice"}
          </button>
        </form>
      )}

      {/* Configuration management (shown when configured) */}
      {config?.voice_enabled && (
        <div className="space-y-4">
          <div>
            <label
              htmlFor="first-message-edit"
              className="block text-sm font-medium text-gray-700 mb-1"
            >
              First Message
            </label>
            <div className="flex gap-2">
              <input
                id="first-message-edit"
                type="text"
                value={firstMessage}
                onChange={(e) => setFirstMessage(e.target.value)}
                className="flex-1 px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
              <button
                onClick={handleUpdateMessage}
                disabled={saving}
                className="px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-md hover:bg-blue-700 disabled:opacity-50 transition"
              >
                Save
              </button>
            </div>
          </div>

          <div className="pt-4 border-t border-gray-200">
            <div className="flex items-start gap-3">
              <AlertTriangle className="w-5 h-5 text-amber-500 mt-0.5" />
              <div>
                <p className="text-sm font-medium text-gray-700">
                  Disable Voice
                </p>
                <p className="text-xs text-gray-500 mb-3">
                  This will remove your Vapi configuration. You can re-enable
                  later with new keys.
                </p>
                <button
                  onClick={handleDisable}
                  disabled={saving}
                  className="px-4 py-2 bg-red-600 text-white text-sm font-medium rounded-md hover:bg-red-700 disabled:opacity-50 transition"
                >
                  {saving ? "Disabling..." : "Disable Voice"}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Status message */}
      {message && (
        <div
          className={`p-4 rounded-md ${
            message.type === "success"
              ? "bg-green-50 text-green-800 border border-green-200"
              : "bg-red-50 text-red-800 border border-red-200"
          }`}
        >
          {message.text}
        </div>
      )}
    </div>
  );
}

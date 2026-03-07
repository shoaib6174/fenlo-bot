/**
 * HandoffSettingsForm Component
 *
 * Settings form for configuring human handoff:
 * - Provider selector (Generic Webhook / Freshdesk)
 * - Provider-specific config fields
 * - Auto-resolve timeout
 * - Escalation message template
 */

"use client";

import { useState, useEffect } from "react";
import { CheckCircle, XCircle, Loader2 } from "lucide-react";
import { apiClient } from "@/lib/api";

interface HandoffConfig {
  provider: string;
  webhook_url?: string;
  webhook_secret?: string;
  freshdesk_domain?: string;
  freshdesk_api_key?: string;
  freshdesk_default_group_id?: number;
  freshdesk_webhook_token?: string;
  timeout_hours?: number;
  escalation_message?: string;
}

const API_URL = process.env.NEXT_PUBLIC_API_URL || "";

export function HandoffSettingsForm() {
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState<{ type: "success" | "error"; text: string } | null>(null);

  // Form state
  const [provider, setProvider] = useState("generic_webhook");
  const [webhookUrl, setWebhookUrl] = useState("");
  const [webhookSecret, setWebhookSecret] = useState("");
  const [freshdeskDomain, setFreshdeskDomain] = useState("");
  const [freshdeskApiKey, setFreshdeskApiKey] = useState("");
  const [freshdeskGroupId, setFreshdeskGroupId] = useState("");
  const [freshdeskWebhookToken, setFreshdeskWebhookToken] = useState("");
  const [timeoutHours, setTimeoutHours] = useState(24);
  const [escalationMessage, setEscalationMessage] = useState(
    "I'm connecting you with a human agent who can help. Please hold on."
  );

  // Load existing config
  useEffect(() => {
    fetchConfig();
  }, []);

  const fetchConfig = async () => {
    try {
      const response = await fetch(`${API_URL}/api/v1/settings`, {
        credentials: "include",
      });
      if (response.ok) {
        const data = await response.json();
        const handoff = data.settings?.handoff as HandoffConfig | undefined;
        if (handoff) {
          setProvider(handoff.provider || "generic_webhook");
          setWebhookUrl(handoff.webhook_url || "");
          setWebhookSecret(handoff.webhook_secret || "");
          setFreshdeskDomain(handoff.freshdesk_domain || "");
          setFreshdeskApiKey(handoff.freshdesk_api_key || "");
          setFreshdeskGroupId(handoff.freshdesk_default_group_id?.toString() || "");
          setFreshdeskWebhookToken(handoff.freshdesk_webhook_token || "");
          setTimeoutHours(handoff.timeout_hours ?? 24);
          setEscalationMessage(
            handoff.escalation_message ||
              "I'm connecting you with a human agent who can help. Please hold on."
          );
        }
      }
    } catch {
      // Settings not loaded — use defaults
    } finally {
      setLoading(false);
    }
  };

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setMessage(null);

    const handoffConfig: HandoffConfig = {
      provider,
      timeout_hours: timeoutHours,
      escalation_message: escalationMessage,
    };

    if (provider === "generic_webhook") {
      handoffConfig.webhook_url = webhookUrl;
      handoffConfig.webhook_secret = webhookSecret;
    } else if (provider === "freshdesk") {
      handoffConfig.freshdesk_domain = freshdeskDomain;
      handoffConfig.freshdesk_api_key = freshdeskApiKey;
      if (freshdeskGroupId) {
        handoffConfig.freshdesk_default_group_id = parseInt(freshdeskGroupId, 10);
      }
      handoffConfig.freshdesk_webhook_token = freshdeskWebhookToken;
    }

    try {
      await apiClient("/api/v1/settings", {
        method: "PUT",
        body: JSON.stringify({ handoff: handoffConfig }),
      });
      setMessage({ type: "success", text: "Handoff settings saved successfully" });
    } catch (err) {
      setMessage({
        type: "error",
        text: err instanceof Error ? err.message : "Failed to save settings",
      });
    } finally {
      setSaving(false);
    }
  };

  const isConfigured = provider === "generic_webhook" ? !!webhookUrl : !!freshdeskDomain && !!freshdeskApiKey;

  if (loading) {
    return (
      <div className="flex items-center justify-center py-8">
        <Loader2 className="w-5 h-5 animate-spin text-gray-400" />
        <span className="ml-2 text-sm text-gray-500">Loading handoff settings...</span>
      </div>
    );
  }

  return (
    <form onSubmit={handleSave} className="space-y-6">
      {/* Status indicator */}
      <div className="flex items-center gap-2">
        {isConfigured ? (
          <>
            <CheckCircle className="w-5 h-5 text-green-500" />
            <span className="text-sm font-medium text-green-700">Handoff configured</span>
          </>
        ) : (
          <>
            <XCircle className="w-5 h-5 text-gray-400" />
            <span className="text-sm font-medium text-gray-500">Not configured</span>
          </>
        )}
      </div>

      {/* Provider Selector */}
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-2">
          Handoff Provider
        </label>
        <select
          value={provider}
          onChange={(e) => setProvider(e.target.value)}
          className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
        >
          <option value="generic_webhook">Generic Webhook</option>
          <option value="freshdesk">Freshdesk</option>
        </select>
        <p className="text-xs text-gray-500 mt-1">
          {provider === "generic_webhook"
            ? "Send escalation events to a custom webhook URL with HMAC signing"
            : "Create Freshdesk support tickets automatically on escalation"}
        </p>
      </div>

      {/* Generic Webhook Config */}
      {provider === "generic_webhook" && (
        <div className="space-y-4 p-4 bg-gray-50 rounded-lg">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Webhook URL
            </label>
            <input
              type="url"
              value={webhookUrl}
              onChange={(e) => setWebhookUrl(e.target.value)}
              placeholder="https://your-service.com/handoff"
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Webhook Secret (HMAC signing)
            </label>
            <input
              type="password"
              value={webhookSecret}
              onChange={(e) => setWebhookSecret(e.target.value)}
              placeholder="Shared secret for signature verification"
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
            <p className="text-xs text-gray-500 mt-1">
              Used for HMAC-SHA256 signature verification on both incoming and outgoing webhooks
            </p>
          </div>
        </div>
      )}

      {/* Freshdesk Config */}
      {provider === "freshdesk" && (
        <div className="space-y-4 p-4 bg-gray-50 rounded-lg">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Freshdesk Domain
            </label>
            <div className="flex items-center gap-1">
              <span className="text-sm text-gray-500">https://</span>
              <input
                type="text"
                value={freshdeskDomain}
                onChange={(e) => setFreshdeskDomain(e.target.value)}
                placeholder="yourcompany"
                className="flex-1 px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
              <span className="text-sm text-gray-500">.freshdesk.com</span>
            </div>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Freshdesk API Key
            </label>
            <input
              type="password"
              value={freshdeskApiKey}
              onChange={(e) => setFreshdeskApiKey(e.target.value)}
              placeholder="Your Freshdesk API key"
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Default Group ID (optional)
            </label>
            <input
              type="number"
              value={freshdeskGroupId}
              onChange={(e) => setFreshdeskGroupId(e.target.value)}
              placeholder="Agent group for ticket assignment"
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Webhook Token (optional)
            </label>
            <input
              type="password"
              value={freshdeskWebhookToken}
              onChange={(e) => setFreshdeskWebhookToken(e.target.value)}
              placeholder="Token for Freshdesk webhook auth"
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
            <p className="text-xs text-gray-500 mt-1">
              Set in Freshdesk webhook config as X-Freshdesk-Token header
            </p>
          </div>
        </div>
      )}

      {/* Auto-resolve Timeout */}
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-2">
          Auto-resolve Timeout: {timeoutHours}h
        </label>
        <input
          type="range"
          min={1}
          max={72}
          value={timeoutHours}
          onChange={(e) => setTimeoutHours(parseInt(e.target.value, 10))}
          className="w-full"
        />
        <div className="flex justify-between text-xs text-gray-500 mt-1">
          <span>1 hour</span>
          <span>72 hours</span>
        </div>
        <p className="text-xs text-gray-500 mt-1">
          Escalated conversations auto-resolve after this timeout if no agent responds
        </p>
      </div>

      {/* Escalation Message Template */}
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">
          Escalation Message
        </label>
        <textarea
          value={escalationMessage}
          onChange={(e) => setEscalationMessage(e.target.value)}
          rows={3}
          className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
          placeholder="Message shown to user when conversation is escalated"
        />
        <p className="text-xs text-gray-500 mt-1">
          Sent to the user when their conversation is escalated to a human agent
        </p>
      </div>

      {/* Save Button */}
      <button
        type="submit"
        disabled={saving}
        className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50 flex items-center gap-2"
      >
        {saving && <Loader2 className="w-4 h-4 animate-spin" />}
        {saving ? "Saving..." : "Save Handoff Settings"}
      </button>

      {/* Message */}
      {message && (
        <div
          className={`p-3 rounded-md text-sm ${
            message.type === "success"
              ? "bg-green-50 text-green-800 border border-green-200"
              : "bg-red-50 text-red-800 border border-red-200"
          }`}
        >
          {message.text}
        </div>
      )}
    </form>
  );
}

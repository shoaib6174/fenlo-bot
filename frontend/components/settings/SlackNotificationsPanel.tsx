"use client";

import { useState, useEffect } from "react";
import {
  Hash,
  Bell,
  AlertTriangle,
  TrendingUp,
  ShieldAlert,
  FileText,
  Send,
  CheckCircle,
  XCircle,
  Loader2,
  ExternalLink,
} from "lucide-react";
import { apiClient } from "@/lib/api";

interface SlackConfig {
  enabled: boolean;
  escalation: boolean;
  hot_lead: boolean;
  quality: boolean;
  documents: boolean;
}

interface NotificationSettings {
  slack_webhook_url: string;
  slack_notifications: SlackConfig;
}

const DEFAULT_CONFIG: SlackConfig = {
  enabled: false,
  escalation: true,
  hot_lead: true,
  quality: true,
  documents: false,
};

const EVENT_TOGGLES = [
  {
    key: "escalation" as const,
    label: "Escalation Triggered",
    description: "When a conversation is escalated to a human agent",
    icon: AlertTriangle,
    color: "text-red-500",
  },
  {
    key: "hot_lead" as const,
    label: "Hot Lead Detected",
    description: "When a conversation's lead score exceeds the threshold",
    icon: TrendingUp,
    color: "text-orange-500",
  },
  {
    key: "quality" as const,
    label: "Quality Alert",
    description: "When response quality drops below threshold",
    icon: ShieldAlert,
    color: "text-yellow-500",
  },
  {
    key: "documents" as const,
    label: "Document Processed",
    description: "When a document finishes processing in the knowledge base",
    icon: FileText,
    color: "text-green-500",
  },
];

export function SlackNotificationsPanel() {
  const [webhookUrl, setWebhookUrl] = useState("");
  const [config, setConfig] = useState<SlackConfig>(DEFAULT_CONFIG);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [testing, setTesting] = useState(false);
  const [message, setMessage] = useState<{ type: "success" | "error"; text: string } | null>(null);

  useEffect(() => {
    const fetchSettings = async () => {
      try {
        const data = await apiClient<NotificationSettings>("/api/v1/notifications/settings");
        setWebhookUrl(data.slack_webhook_url || "");
        setConfig({ ...DEFAULT_CONFIG, ...data.slack_notifications });
      } catch {
        // Silent fail - shows defaults
      } finally {
        setLoading(false);
      }
    };
    fetchSettings();
  }, []);

  const handleSave = async () => {
    setSaving(true);
    setMessage(null);

    try {
      await apiClient("/api/v1/notifications/settings", {
        method: "PUT",
        body: JSON.stringify({
          slack_webhook_url: webhookUrl,
          slack_notifications: config,
        }),
      });
      setMessage({ type: "success", text: "Slack notification settings saved!" });
    } catch (e) {
      setMessage({ type: "error", text: e instanceof Error ? e.message : "Failed to save settings" });
    } finally {
      setSaving(false);
    }
  };

  const handleTest = async () => {
    if (!webhookUrl) {
      setMessage({ type: "error", text: "Enter a Slack webhook URL first" });
      return;
    }

    setTesting(true);
    setMessage(null);

    try {
      const result = await apiClient<{ success: boolean; error?: string }>("/api/v1/notifications/test-slack", {
        method: "POST",
        body: JSON.stringify({ webhook_url: webhookUrl }),
      });

      if (result.success) {
        setMessage({ type: "success", text: "Test notification sent! Check your Slack channel." });
      } else {
        setMessage({ type: "error", text: result.error || "Test failed" });
      }
    } catch {
      setMessage({ type: "error", text: "Failed to send test notification" });
    } finally {
      setTesting(false);
    }
  };

  const toggleEvent = (key: keyof SlackConfig) => {
    setConfig((prev) => ({ ...prev, [key]: !prev[key] }));
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader2 className="w-6 h-6 animate-spin text-gray-400" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h2 className="text-lg font-semibold text-gray-900 flex items-center gap-2">
          <Hash className="w-5 h-5 text-purple-600" />
          Slack Notifications
        </h2>
        <p className="text-sm text-gray-600 mt-1">
          Get notified in Slack when important events happen in your workspace.
        </p>
      </div>

      {/* Master Enable Toggle */}
      <div className="flex items-center justify-between p-4 bg-gray-50 border border-gray-200 rounded-lg">
        <div className="flex items-center gap-3">
          <Bell className="w-5 h-5 text-gray-600" />
          <div>
            <p className="text-sm font-medium text-gray-900">Enable Slack Notifications</p>
            <p className="text-xs text-gray-500">
              Send event notifications to your Slack channel
            </p>
          </div>
        </div>
        <button
          onClick={() => toggleEvent("enabled")}
          className={`relative inline-flex h-6 w-11 items-center rounded-full transition ${
            config.enabled ? "bg-blue-600" : "bg-gray-300"
          }`}
          role="switch"
          aria-checked={config.enabled}
          data-testid="slack-enable-toggle"
        >
          <span
            className={`inline-block h-4 w-4 transform rounded-full bg-white transition ${
              config.enabled ? "translate-x-6" : "translate-x-1"
            }`}
          />
        </button>
      </div>

      {/* Webhook URL */}
      <div>
        <label htmlFor="slack-url" className="block text-sm font-medium text-gray-700 mb-2">
          Slack Webhook URL
        </label>
        <div className="flex gap-2">
          <input
            id="slack-url"
            type="url"
            value={webhookUrl}
            onChange={(e) => setWebhookUrl(e.target.value)}
            placeholder="https://hooks.slack.com/services/T00000/B00000/XXXX"
            className="flex-1 px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            data-testid="slack-webhook-url"
          />
          <button
            onClick={handleTest}
            disabled={testing || !webhookUrl}
            className="inline-flex items-center gap-1.5 px-3 py-2 bg-white border border-gray-300 rounded-md text-sm font-medium text-gray-700 hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed transition"
            data-testid="test-slack-btn"
          >
            {testing ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <Send className="w-4 h-4" />
            )}
            Test
          </button>
        </div>
        <p className="text-xs text-gray-500 mt-1">
          Create an{" "}
          <a
            href="https://api.slack.com/messaging/webhooks"
            target="_blank"
            rel="noopener noreferrer"
            className="text-blue-600 hover:underline inline-flex items-center gap-0.5"
          >
            Incoming Webhook <ExternalLink className="w-3 h-3" />
          </a>{" "}
          in your Slack workspace, then paste the URL here.
        </p>
      </div>

      {/* Per-Event Toggles */}
      <div>
        <h3 className="text-sm font-medium text-gray-900 mb-3">Event Notifications</h3>
        <div className="space-y-3">
          {EVENT_TOGGLES.map((event) => (
            <div
              key={event.key}
              className="flex items-center justify-between p-3 bg-white border border-gray-200 rounded-lg"
            >
              <div className="flex items-center gap-3">
                <event.icon className={`w-4 h-4 ${event.color}`} />
                <div>
                  <p className="text-sm font-medium text-gray-900">{event.label}</p>
                  <p className="text-xs text-gray-500">{event.description}</p>
                </div>
              </div>
              <button
                onClick={() => toggleEvent(event.key)}
                className={`relative inline-flex h-5 w-9 items-center rounded-full transition ${
                  config[event.key] ? "bg-blue-600" : "bg-gray-300"
                }`}
                role="switch"
                aria-checked={config[event.key]}
                aria-label={`Toggle ${event.label}`}
                data-testid={`toggle-${event.key}`}
              >
                <span
                  className={`inline-block h-3.5 w-3.5 transform rounded-full bg-white transition ${
                    config[event.key] ? "translate-x-4" : "translate-x-0.5"
                  }`}
                />
              </button>
            </div>
          ))}
        </div>
      </div>

      {/* Status Message */}
      {message && (
        <div
          className={`flex items-center gap-2 p-3 rounded-lg text-sm ${
            message.type === "success"
              ? "bg-green-50 text-green-800 border border-green-200"
              : "bg-red-50 text-red-800 border border-red-200"
          }`}
          data-testid="status-message"
        >
          {message.type === "success" ? (
            <CheckCircle className="w-4 h-4 flex-shrink-0" />
          ) : (
            <XCircle className="w-4 h-4 flex-shrink-0" />
          )}
          {message.text}
        </div>
      )}

      {/* Save Button */}
      <div className="flex gap-3">
        <button
          onClick={handleSave}
          disabled={saving}
          className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-md text-sm font-medium transition disabled:opacity-50 disabled:cursor-not-allowed"
          data-testid="save-slack-btn"
        >
          {saving ? "Saving..." : "Save Settings"}
        </button>
      </div>
    </div>
  );
}

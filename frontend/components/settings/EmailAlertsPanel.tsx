"use client";

import { useState } from "react";
import {
  Mail,
  Bell,
  AlertTriangle,
  TrendingDown,
  HelpCircle,
  FileText,
  Send,
  CheckCircle,
  XCircle,
  Loader2,
  Eye,
} from "lucide-react";
import { useSettingsFetch } from "@/hooks/useSettingsFetch";
import { apiClient } from "@/lib/api";

interface EmailConfig {
  enabled: boolean;
  recipient_email: string;
  quality_drop: boolean;
  escalation: boolean;
  knowledge_gap: boolean;
  doc_processed: boolean;
  digest_frequency: string;
  quality_threshold: number;
}

const DEFAULT_CONFIG: EmailConfig = {
  enabled: false,
  recipient_email: "",
  quality_drop: true,
  escalation: true,
  knowledge_gap: true,
  doc_processed: false,
  digest_frequency: "immediate",
  quality_threshold: 0.6,
};

const ALERT_TOGGLES = [
  {
    key: "quality_drop" as const,
    label: "Quality Score Drop",
    description: "When response quality drops below your threshold",
    icon: TrendingDown,
    color: "text-red-500",
  },
  {
    key: "escalation" as const,
    label: "Conversation Escalated",
    description: "When a conversation is escalated to a human agent",
    icon: AlertTriangle,
    color: "text-orange-500",
  },
  {
    key: "knowledge_gap" as const,
    label: "Knowledge Gap Detected",
    description: "When a new knowledge gap is found in your KB",
    icon: HelpCircle,
    color: "text-purple-500",
  },
  {
    key: "doc_processed" as const,
    label: "Document Processed",
    description: "When a document finishes processing",
    icon: FileText,
    color: "text-green-500",
  },
];

export function EmailAlertsPanel() {
  const { data: config, setData: setConfig, loading } = useSettingsFetch<EmailConfig>(
    "/api/v1/notifications/settings",
    DEFAULT_CONFIG,
    (raw: any) => raw?.email_alerts ? { ...DEFAULT_CONFIG, ...raw.email_alerts } : DEFAULT_CONFIG
  );
  const [saving, setSaving] = useState(false);
  const [testing, setTesting] = useState(false);
  const [previewHtml, setPreviewHtml] = useState<string | null>(null);
  const [message, setMessage] = useState<{ type: "success" | "error"; text: string } | null>(null);

  const handleSave = async () => {
    setSaving(true);
    setMessage(null);

    try {
      // First fetch current settings to preserve Slack config
      const current: any = await apiClient("/api/v1/notifications/settings").catch(() => ({}));

      await apiClient("/api/v1/notifications/settings", {
        method: "PUT",
        body: JSON.stringify({
          slack_webhook_url: current.slack_webhook_url || "",
          slack_notifications: current.slack_notifications || {},
          email_alerts: config,
        }),
      });
      setMessage({ type: "success", text: "Email alert settings saved!" });
    } catch {
      setMessage({ type: "error", text: "Failed to save settings" });
    } finally {
      setSaving(false);
    }
  };

  const handleTestEmail = async () => {
    setTesting(true);
    setMessage(null);
    setPreviewHtml(null);

    try {
      const result = await apiClient<{ html: string; subject: string }>("/api/v1/notifications/test-email", {
        method: "POST",
      });
      setPreviewHtml(result.html);
      setMessage({ type: "success", text: `Preview generated: "${result.subject}"` });
    } catch {
      setMessage({ type: "error", text: "Failed to generate test email" });
    } finally {
      setTesting(false);
    }
  };

  const toggleAlert = (key: keyof EmailConfig) => {
    setConfig((prev) => ({ ...prev, [key]: !prev[key] } as EmailConfig));
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
          <Mail className="w-5 h-5 text-blue-600" />
          Email Alerts
        </h2>
        <p className="text-sm text-gray-600 mt-1">
          Receive email notifications when important events occur in your workspace.
        </p>
      </div>

      {/* Master Enable Toggle */}
      <div className="flex items-center justify-between p-4 bg-gray-50 border border-gray-200 rounded-lg">
        <div className="flex items-center gap-3">
          <Bell className="w-5 h-5 text-gray-600" />
          <div>
            <p className="text-sm font-medium text-gray-900">Enable Email Alerts</p>
            <p className="text-xs text-gray-500">
              Receive email notifications for configured events
            </p>
          </div>
        </div>
        <button
          onClick={() => toggleAlert("enabled")}
          className={`relative inline-flex h-6 w-11 items-center rounded-full transition ${
            config.enabled ? "bg-blue-600" : "bg-gray-300"
          }`}
          role="switch"
          aria-checked={config.enabled}
          data-testid="email-enable-toggle"
        >
          <span
            className={`inline-block h-4 w-4 transform rounded-full bg-white transition ${
              config.enabled ? "translate-x-6" : "translate-x-1"
            }`}
          />
        </button>
      </div>

      {/* Recipient Email */}
      <div>
        <label htmlFor="email-recipient" className="block text-sm font-medium text-gray-700 mb-2">
          Recipient Email
        </label>
        <input
          id="email-recipient"
          type="email"
          value={config.recipient_email}
          onChange={(e) => setConfig((prev) => ({ ...prev, recipient_email: e.target.value }))}
          placeholder="admin@yourcompany.com"
          className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          data-testid="email-recipient-input"
        />
        <p className="text-xs text-gray-500 mt-1">
          Alert emails will be sent to this address.
        </p>
      </div>

      {/* Alert Toggles */}
      <div>
        <h3 className="text-sm font-medium text-gray-900 mb-3">Alert Types</h3>
        <div className="space-y-3">
          {ALERT_TOGGLES.map((alert) => (
            <div
              key={alert.key}
              className="flex items-center justify-between p-3 bg-white border border-gray-200 rounded-lg"
            >
              <div className="flex items-center gap-3">
                <alert.icon className={`w-4 h-4 ${alert.color}`} />
                <div>
                  <p className="text-sm font-medium text-gray-900">{alert.label}</p>
                  <p className="text-xs text-gray-500">{alert.description}</p>
                </div>
              </div>
              <button
                onClick={() => toggleAlert(alert.key)}
                className={`relative inline-flex h-5 w-9 items-center rounded-full transition ${
                  config[alert.key] ? "bg-blue-600" : "bg-gray-300"
                }`}
                role="switch"
                aria-checked={config[alert.key] as boolean}
                aria-label={`Toggle ${alert.label}`}
                data-testid={`toggle-email-${alert.key}`}
              >
                <span
                  className={`inline-block h-3.5 w-3.5 transform rounded-full bg-white transition ${
                    config[alert.key] ? "translate-x-4" : "translate-x-0.5"
                  }`}
                />
              </button>
            </div>
          ))}
        </div>
      </div>

      {/* Quality Threshold */}
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-2">
          Quality Alert Threshold
        </label>
        <div className="flex items-center gap-3">
          <input
            type="range"
            min="0"
            max="1"
            step="0.05"
            value={config.quality_threshold}
            onChange={(e) =>
              setConfig((prev) => ({
                ...prev,
                quality_threshold: parseFloat(e.target.value),
              }))
            }
            className="flex-1"
            data-testid="quality-threshold-slider"
          />
          <span className="text-sm font-mono font-medium text-gray-900 w-10 text-right">
            {config.quality_threshold.toFixed(2)}
          </span>
        </div>
        <p className="text-xs text-gray-500 mt-1">
          Alert when quality score drops below this value (default: 0.60)
        </p>
      </div>

      {/* Digest Frequency */}
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-2">
          Delivery Frequency
        </label>
        <div className="flex gap-2">
          {[
            { value: "immediate", label: "Immediate" },
            { value: "hourly", label: "Hourly Digest" },
            { value: "daily", label: "Daily Digest" },
          ].map((option) => (
            <button
              key={option.value}
              onClick={() => setConfig((prev) => ({ ...prev, digest_frequency: option.value }))}
              className={`px-3 py-1.5 rounded-md text-sm font-medium transition ${
                config.digest_frequency === option.value
                  ? "bg-blue-600 text-white"
                  : "bg-gray-100 text-gray-700 hover:bg-gray-200"
              }`}
              data-testid={`freq-${option.value}`}
            >
              {option.label}
            </button>
          ))}
        </div>
      </div>

      {/* Test Email */}
      <div className="flex items-center gap-3">
        <button
          onClick={handleTestEmail}
          disabled={testing}
          className="inline-flex items-center gap-1.5 px-3 py-2 bg-white border border-gray-300 rounded-md text-sm font-medium text-gray-700 hover:bg-gray-50 disabled:opacity-50 transition"
          data-testid="test-email-btn"
        >
          {testing ? <Loader2 className="w-4 h-4 animate-spin" /> : <Eye className="w-4 h-4" />}
          Preview Test Email
        </button>
      </div>

      {/* Email Preview */}
      {previewHtml && (
        <div className="border border-gray-200 rounded-lg overflow-hidden" data-testid="email-preview">
          <div className="px-4 py-2 bg-gray-50 border-b border-gray-200 text-xs font-medium text-gray-600">
            Email Preview
          </div>
          <div
            className="p-4 bg-white"
            dangerouslySetInnerHTML={{ __html: previewHtml }}
          />
        </div>
      )}

      {/* Status Message */}
      {message && (
        <div
          className={`flex items-center gap-2 p-3 rounded-lg text-sm ${
            message.type === "success"
              ? "bg-green-50 text-green-800 border border-green-200"
              : "bg-red-50 text-red-800 border border-red-200"
          }`}
          data-testid="email-status-message"
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
          data-testid="save-email-btn"
        >
          {saving ? "Saving..." : "Save Email Settings"}
        </button>
      </div>
    </div>
  );
}

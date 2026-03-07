"use client";

import { useState } from "react";
import {
  Calendar,
  Link2,
  MessageSquare,
  CheckCircle,
  XCircle,
  Loader2,
} from "lucide-react";
import { useSettingsFetch } from "@/hooks/useSettingsFetch";
import { apiClient } from "@/lib/api";

interface BookingConfig {
  booking_provider: string;
  booking_url: string;
  booking_prompt: string;
  booking_enabled: boolean;
}

const DEFAULT_CONFIG: BookingConfig = {
  booking_provider: "custom_url",
  booking_url: "",
  booking_prompt: "",
  booking_enabled: false,
};

const PROVIDERS = [
  { value: "calendly", label: "Calendly", placeholder: "https://calendly.com/your-name/30min" },
  { value: "cal_com", label: "Cal.com", placeholder: "https://cal.com/your-name/meeting" },
  { value: "google", label: "Google Calendar", placeholder: "https://calendar.google.com/..." },
  { value: "custom_url", label: "Custom URL", placeholder: "https://your-booking-page.com" },
];

export function BookingPanel() {
  const { data: config, setData: setConfig, loading } = useSettingsFetch<BookingConfig>(
    "/api/v1/booking",
    DEFAULT_CONFIG,
    (raw) => ({ ...DEFAULT_CONFIG, ...raw })
  );
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState<{ type: "success" | "error"; text: string } | null>(null);

  const handleSave = async () => {
    setSaving(true);
    setMessage(null);

    try {
      await apiClient("/api/v1/booking", {
        method: "PUT",
        body: JSON.stringify(config),
      });
      setMessage({ type: "success", text: "Booking settings saved!" });
    } catch {
      setMessage({ type: "error", text: "Failed to save booking settings" });
    } finally {
      setSaving(false);
    }
  };

  const updateField = (field: keyof BookingConfig, value: string | boolean) => {
    setConfig((prev) => ({ ...prev, [field]: value }));
  };

  const selectedProvider = PROVIDERS.find((p) => p.value === config.booking_provider) || PROVIDERS[3];

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
          <Calendar className="w-5 h-5 text-blue-600" />
          Calendar / Booking Integration
        </h2>
        <p className="text-sm text-gray-600 mt-1">
          When the bot detects a booking intent, it will show a scheduling card to the user.
        </p>
      </div>

      {/* Enable Toggle */}
      <div className="flex items-center justify-between p-4 bg-gray-50 border border-gray-200 rounded-lg">
        <div className="flex items-center gap-3">
          <Calendar className="w-5 h-5 text-gray-500" />
          <div>
            <p className="text-sm font-medium text-gray-900">Enable Booking Integration</p>
            <p className="text-xs text-gray-500">
              Show a scheduling card when the bot detects booking intent
            </p>
          </div>
        </div>
        <button
          onClick={() => updateField("booking_enabled", !config.booking_enabled)}
          className={`relative inline-flex h-6 w-11 items-center rounded-full transition ${
            config.booking_enabled ? "bg-blue-600" : "bg-gray-300"
          }`}
          role="switch"
          aria-checked={config.booking_enabled}
          data-testid="booking-enabled-toggle"
        >
          <span
            className={`inline-block h-4 w-4 transform rounded-full bg-white transition ${
              config.booking_enabled ? "translate-x-6" : "translate-x-1"
            }`}
          />
        </button>
      </div>

      {/* Provider */}
      <div>
        <label htmlFor="booking-provider" className="block text-sm font-medium text-gray-700 mb-1">
          <div className="flex items-center gap-1.5">
            <Link2 className="w-4 h-4" />
            Booking Provider
          </div>
        </label>
        <select
          id="booking-provider"
          value={config.booking_provider}
          onChange={(e) => updateField("booking_provider", e.target.value)}
          className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          data-testid="booking-provider-select"
        >
          {PROVIDERS.map((p) => (
            <option key={p.value} value={p.value}>
              {p.label}
            </option>
          ))}
        </select>
      </div>

      {/* Booking URL */}
      <div>
        <label htmlFor="booking-url" className="block text-sm font-medium text-gray-700 mb-1">
          <div className="flex items-center gap-1.5">
            <Link2 className="w-4 h-4" />
            Booking URL
          </div>
        </label>
        <input
          id="booking-url"
          type="url"
          value={config.booking_url}
          onChange={(e) => updateField("booking_url", e.target.value)}
          placeholder={selectedProvider.placeholder}
          className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          data-testid="booking-url-input"
        />
        <p className="text-xs text-gray-500 mt-1">
          The scheduling page URL your customers will visit to book a meeting.
        </p>
      </div>

      {/* Custom Prompt */}
      <div>
        <label htmlFor="booking-prompt" className="block text-sm font-medium text-gray-700 mb-1">
          <div className="flex items-center gap-1.5">
            <MessageSquare className="w-4 h-4" />
            Custom Booking Message
          </div>
        </label>
        <textarea
          id="booking-prompt"
          value={config.booking_prompt}
          onChange={(e) => updateField("booking_prompt", e.target.value)}
          placeholder="I'd be happy to help you schedule a meeting! Click the button below to pick a time."
          rows={3}
          className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          data-testid="booking-prompt-input"
        />
        <p className="text-xs text-gray-500 mt-1">
          Optional message shown above the booking card. Leave blank for the default.
        </p>
      </div>

      {/* Preview */}
      <div className="border border-gray-200 rounded-lg overflow-hidden">
        <div className="px-4 py-2 bg-gray-100 text-xs font-medium text-gray-500 uppercase">
          Chat Preview
        </div>
        <div className="p-4 bg-gray-50">
          <div className="max-w-sm">
            <p className="text-sm text-gray-700 mb-3">
              {config.booking_prompt || "I'd be happy to help you schedule a meeting! Click the button below to pick a time."}
            </p>
            <div className="border border-blue-200 bg-white rounded-lg p-4">
              <div className="flex items-center gap-3 mb-3">
                <Calendar className="w-8 h-8 text-blue-600" />
                <div>
                  <p className="text-sm font-semibold text-gray-900">Schedule a Meeting</p>
                  <p className="text-xs text-gray-500">{selectedProvider.label}</p>
                </div>
              </div>
              <button
                className="w-full bg-blue-600 text-white text-sm font-medium py-2 px-4 rounded-md hover:bg-blue-700 transition"
                onClick={() => config.booking_url && window.open(config.booking_url, "_blank")}
                disabled={!config.booking_url}
              >
                Book Now
              </button>
            </div>
          </div>
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
          data-testid="booking-status"
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
          data-testid="save-booking-btn"
        >
          {saving ? "Saving..." : "Save Booking Settings"}
        </button>
      </div>
    </div>
  );
}

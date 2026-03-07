"use client";

import { useState } from "react";
import {
  Palette,
  ImageIcon,
  Type,
  Eye,
  EyeOff,
  CheckCircle,
  XCircle,
  Loader2,
} from "lucide-react";
import { useSettingsFetch } from "@/hooks/useSettingsFetch";
import { apiClient } from "@/lib/api";

interface BrandingConfig {
  brand_name: string;
  logo_url: string;
  favicon_url: string;
  accent_color: string;
  hide_powered_by: boolean;
  client_preview_mode: boolean;
}

const DEFAULT_CONFIG: BrandingConfig = {
  brand_name: "Fenlo AI",
  logo_url: "",
  favicon_url: "",
  accent_color: "#5d6e34",
  hide_powered_by: false,
  client_preview_mode: false,
};

const PRESET_COLORS = [
  { label: "Blue", value: "#2563eb" },
  { label: "Purple", value: "#7c3aed" },
  { label: "Green", value: "#059669" },
  { label: "Red", value: "#dc2626" },
  { label: "Orange", value: "#ea580c" },
  { label: "Indigo", value: "#4f46e5" },
  { label: "Pink", value: "#db2777" },
  { label: "Teal", value: "#0d9488" },
];

export function BrandingPanel() {
  const { data: config, setData: setConfig, loading } = useSettingsFetch<BrandingConfig>(
    "/api/v1/branding",
    DEFAULT_CONFIG,
    (raw) => ({ ...DEFAULT_CONFIG, ...raw })
  );
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState<{ type: "success" | "error"; text: string } | null>(null);

  const handleSave = async () => {
    setSaving(true);
    setMessage(null);

    try {
      await apiClient("/api/v1/branding", {
        method: "PUT",
        body: JSON.stringify(config),
      });
      setMessage({ type: "success", text: "Branding settings saved! Reload to see changes." });
      window.dispatchEvent(new CustomEvent("branding-updated", { detail: config }));
    } catch {
      setMessage({ type: "error", text: "Failed to save branding settings" });
    } finally {
      setSaving(false);
    }
  };

  const updateField = (field: keyof BrandingConfig, value: string | boolean) => {
    setConfig((prev) => ({ ...prev, [field]: value }));
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
          <Palette className="w-5 h-5 text-purple-600" />
          White-Label Branding
        </h2>
        <p className="text-sm text-gray-600 mt-1">
          Customize the platform appearance for your clients. Changes apply across the entire workspace.
        </p>
      </div>

      {/* Brand Name */}
      <div>
        <label htmlFor="brand-name" className="block text-sm font-medium text-gray-700 mb-1">
          <div className="flex items-center gap-1.5">
            <Type className="w-4 h-4" />
            Brand Name
          </div>
        </label>
        <input
          id="brand-name"
          type="text"
          value={config.brand_name}
          onChange={(e) => updateField("brand_name", e.target.value)}
          placeholder="Your Company Name"
          className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          data-testid="brand-name-input"
        />
        <p className="text-xs text-gray-500 mt-1">
          Replaces &quot;Fenlo AI&quot; in the sidebar header and throughout the UI
        </p>
      </div>

      {/* Logo URL */}
      <div>
        <label htmlFor="logo-url" className="block text-sm font-medium text-gray-700 mb-1">
          <div className="flex items-center gap-1.5">
            <ImageIcon className="w-4 h-4" />
            Logo URL
          </div>
        </label>
        <input
          id="logo-url"
          type="url"
          value={config.logo_url}
          onChange={(e) => updateField("logo_url", e.target.value)}
          placeholder="https://example.com/logo.png"
          className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          data-testid="logo-url-input"
        />
        <p className="text-xs text-gray-500 mt-1">
          Displayed in the sidebar header. Recommended: 32x32px or SVG.
        </p>
        {config.logo_url && (
          <div className="mt-2 p-2 bg-gray-50 border border-gray-200 rounded-md inline-block">
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img
              src={config.logo_url}
              alt="Logo preview"
              className="h-8 w-auto"
              onError={(e) => { (e.target as HTMLImageElement).style.display = "none"; }}
            />
          </div>
        )}
      </div>

      {/* Accent Color */}
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-2">
          <div className="flex items-center gap-1.5">
            <Palette className="w-4 h-4" />
            Accent Color
          </div>
        </label>
        <div className="flex items-center gap-3 mb-2">
          <input
            type="color"
            value={config.accent_color}
            onChange={(e) => updateField("accent_color", e.target.value)}
            className="w-10 h-10 rounded cursor-pointer border border-gray-300"
            data-testid="accent-color-picker"
          />
          <input
            type="text"
            value={config.accent_color}
            onChange={(e) => updateField("accent_color", e.target.value)}
            className="w-28 px-3 py-2 border border-gray-300 rounded-md text-sm font-mono focus:outline-none focus:ring-2 focus:ring-blue-500"
            data-testid="accent-color-input"
          />
        </div>
        <div className="flex flex-wrap gap-2">
          {PRESET_COLORS.map((color) => (
            <button
              key={color.value}
              onClick={() => updateField("accent_color", color.value)}
              className={`w-8 h-8 rounded-full border-2 transition ${
                config.accent_color === color.value
                  ? "border-gray-900 scale-110"
                  : "border-gray-200 hover:border-gray-400"
              }`}
              style={{ backgroundColor: color.value }}
              title={color.label}
            />
          ))}
        </div>
      </div>

      {/* Hide Powered By */}
      <div className="flex items-center justify-between p-4 bg-gray-50 border border-gray-200 rounded-lg">
        <div className="flex items-center gap-3">
          {config.hide_powered_by ? (
            <EyeOff className="w-5 h-5 text-gray-500" />
          ) : (
            <Eye className="w-5 h-5 text-gray-500" />
          )}
          <div>
            <p className="text-sm font-medium text-gray-900">Hide &quot;Powered by Fenlo AI&quot;</p>
            <p className="text-xs text-gray-500">
              Remove Fenlo AI branding from the widget and chat interface
            </p>
          </div>
        </div>
        <button
          onClick={() => updateField("hide_powered_by", !config.hide_powered_by)}
          className={`relative inline-flex h-6 w-11 items-center rounded-full transition ${
            config.hide_powered_by ? "bg-blue-600" : "bg-gray-300"
          }`}
          role="switch"
          aria-checked={config.hide_powered_by}
          data-testid="hide-powered-toggle"
        >
          <span
            className={`inline-block h-4 w-4 transform rounded-full bg-white transition ${
              config.hide_powered_by ? "translate-x-6" : "translate-x-1"
            }`}
          />
        </button>
      </div>

      {/* Client Preview Mode */}
      <div className="flex items-center justify-between p-4 bg-purple-50 border border-purple-200 rounded-lg">
        <div className="flex items-center gap-3">
          <Eye className="w-5 h-5 text-purple-600" />
          <div>
            <p className="text-sm font-medium text-gray-900">Client Preview Mode</p>
            <p className="text-xs text-gray-500">
              Hides admin controls (Settings, API Keys, Admin). Shows chat, analytics, and documents as read-only.
            </p>
          </div>
        </div>
        <button
          onClick={() => updateField("client_preview_mode", !config.client_preview_mode)}
          className={`relative inline-flex h-6 w-11 items-center rounded-full transition ${
            config.client_preview_mode ? "bg-purple-600" : "bg-gray-300"
          }`}
          role="switch"
          aria-checked={config.client_preview_mode}
          data-testid="preview-mode-toggle"
        >
          <span
            className={`inline-block h-4 w-4 transform rounded-full bg-white transition ${
              config.client_preview_mode ? "translate-x-6" : "translate-x-1"
            }`}
          />
        </button>
      </div>

      {/* Live Preview */}
      <div className="border border-gray-200 rounded-lg overflow-hidden">
        <div className="px-4 py-2 bg-gray-100 text-xs font-medium text-gray-500 uppercase">
          Live Preview
        </div>
        <div className="p-4 flex items-center gap-3" style={{ borderLeft: `4px solid ${config.accent_color}` }}>
          {config.logo_url ? (
            /* eslint-disable-next-line @next/next/no-img-element */
            <img
              src={config.logo_url}
              alt=""
              className="h-8 w-8 rounded"
              onError={(e) => { (e.target as HTMLImageElement).style.display = "none"; }}
            />
          ) : (
            <div
              className="h-8 w-8 rounded flex items-center justify-center text-white font-bold text-sm"
              style={{ backgroundColor: config.accent_color }}
            >
              {config.brand_name.charAt(0)}
            </div>
          )}
          <div>
            <p className="text-sm font-bold text-gray-900">{config.brand_name || "Fenlo AI"}</p>
            <p className="text-xs text-gray-500">AI Chatbot Platform</p>
          </div>
        </div>
        {!config.hide_powered_by && (
          <div className="px-4 py-2 bg-gray-50 border-t border-gray-200">
            <p className="text-xs text-gray-400">Powered by Fenlo AI</p>
          </div>
        )}
      </div>

      {/* Status Message */}
      {message && (
        <div
          className={`flex items-center gap-2 p-3 rounded-lg text-sm ${
            message.type === "success"
              ? "bg-green-50 text-green-800 border border-green-200"
              : "bg-red-50 text-red-800 border border-red-200"
          }`}
          data-testid="branding-status"
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
          data-testid="save-branding-btn"
        >
          {saving ? "Saving..." : "Save Branding"}
        </button>
      </div>
    </div>
  );
}

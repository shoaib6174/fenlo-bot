/**
 * WidgetSetup Component
 *
 * Form for configuring website widget with embed code generator
 */

"use client";

import { useState, useEffect } from "react";
import { Globe, Save, Copy, Check } from "lucide-react";
import { toast } from "sonner";
import { useCreateChannel, useUpdateChannel } from "@/hooks/useChannels";
import { channelApi, type ChannelConfig } from "@/lib/api";

interface WidgetSetupProps {
  channel?: ChannelConfig;
  workspaceId?: string;
  onSuccess?: () => void;
}

interface WidgetConfig {
  primary_color: string;
  position: "bottom-right" | "bottom-left";
  greeting: string;
  placeholder?: string;
  allowed_domains: string[];
}

const POSITIONS = [
  { value: "bottom-right" as const, label: "Bottom Right" },
  { value: "bottom-left" as const, label: "Bottom Left" },
];

export function WidgetSetup({ channel, workspaceId, onSuccess }: WidgetSetupProps) {
  const isEditing = !!channel;
  const existingConfig = (channel?.config as unknown as WidgetConfig) || {};

  const [formData, setFormData] = useState<WidgetConfig>({
    primary_color: existingConfig.primary_color || "#3b82f6",
    position: existingConfig.position || "bottom-right",
    greeting: existingConfig.greeting || "Hello! How can I help you today?",
    placeholder: existingConfig.placeholder || "Type your message...",
    allowed_domains: existingConfig.allowed_domains || [],
  });

  const [domainInput, setDomainInput] = useState("");
  const [copied, setCopied] = useState(false);
  const [embedCode, setEmbedCode] = useState<string | null>(null);
  const [isLoadingEmbed, setIsLoadingEmbed] = useState(false);

  const createChannel = useCreateChannel();
  const updateChannel = useUpdateChannel();

  // Fetch embed code when editing a widget channel
  useEffect(() => {
    if (!channel?.id) {
      setEmbedCode(null);
      return;
    }

    const fetchEmbedCode = async () => {
      setIsLoadingEmbed(true);
      try {
        const response = await channelApi.getEmbedCode(channel.id);
        setEmbedCode(response.html);
      } catch (error) {
        console.error("Failed to fetch embed code:", error);
        // Don't show error toast - embed code is optional
      } finally {
        setIsLoadingEmbed(false);
      }
    };

    fetchEmbedCode();
  }, [channel?.id]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    // Validation
    if (!formData.greeting) {
      toast.error("Greeting message is required");
      return;
    }

    if (formData.allowed_domains.length === 0) {
      toast.error("At least one allowed domain is required");
      return;
    }

    try {
      if (isEditing) {
        await updateChannel.mutateAsync({
          id: channel.id,
          data: { config: formData as unknown as Record<string, unknown> },
        });
        toast.success("Widget updated successfully");
      } else {
        await createChannel.mutateAsync({
          channel: "widget",
          config: formData as unknown as Record<string, unknown>,
          is_active: true,
        });
        toast.success("Widget created successfully");
      }

      onSuccess?.();
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Failed to save widget");
    }
  };

  const addDomain = () => {
    const domain = domainInput.trim();

    if (!domain) return;

    // Basic validation
    if (formData.allowed_domains.includes(domain)) {
      toast.error("Domain already added");
      return;
    }

    setFormData({
      ...formData,
      allowed_domains: [...formData.allowed_domains, domain],
    });
    setDomainInput("");
  };

  const removeDomain = (domain: string) => {
    setFormData({
      ...formData,
      allowed_domains: formData.allowed_domains.filter((d) => d !== domain),
    });
  };

  const copyEmbedCode = async () => {
    if (!embedCode) return;

    try {
      await navigator.clipboard.writeText(embedCode);
      setCopied(true);
      toast.success("Embed code copied to clipboard");
      setTimeout(() => setCopied(false), 2000);
    } catch (error) {
      toast.error("Failed to copy to clipboard");
    }
  };

  return (
    <div className="space-y-6">
      <form onSubmit={handleSubmit} className="space-y-6">
        <div className="flex items-center gap-3 pb-4 border-b">
          <div className="p-2 rounded-lg bg-blue-50">
            <Globe className="w-6 h-6 text-blue-600" />
          </div>
          <div>
            <h2 className="text-lg font-semibold text-gray-900">
              {isEditing ? "Edit" : "Add"} Website Widget
            </h2>
            <p className="text-sm text-gray-600">Embeddable chat widget for your website</p>
          </div>
        </div>

        {/* Appearance */}
        <div className="space-y-4">
          <h3 className="font-medium text-gray-900">Appearance</h3>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Primary Color
            </label>
            <div className="flex gap-3 items-center">
              <input
                type="color"
                value={formData.primary_color}
                onChange={(e) => setFormData({ ...formData, primary_color: e.target.value })}
                className="h-10 w-20 border border-gray-300 rounded cursor-pointer"
              />
              <input
                type="text"
                value={formData.primary_color}
                onChange={(e) => setFormData({ ...formData, primary_color: e.target.value })}
                className="flex-1 px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                placeholder="#3b82f6"
                pattern="^#[0-9A-Fa-f]{6}$"
              />
            </div>
            <p className="text-xs text-gray-500 mt-1">
              Hex color code for widget theme (e.g., #3b82f6)
            </p>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Position</label>
            <div className="grid grid-cols-2 gap-3">
              {POSITIONS.map((pos) => (
                <button
                  key={pos.value}
                  type="button"
                  onClick={() => setFormData({ ...formData, position: pos.value })}
                  className={`py-2 px-4 rounded-md text-sm font-medium transition-colors ${
                    formData.position === pos.value
                      ? "bg-blue-600 text-white"
                      : "bg-gray-100 text-gray-700 hover:bg-gray-200"
                  }`}
                >
                  {pos.label}
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* Messages */}
        <div className="space-y-4">
          <h3 className="font-medium text-gray-900">Messages</h3>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Greeting Message <span className="text-red-500">*</span>
            </label>
            <textarea
              required
              rows={2}
              value={formData.greeting}
              onChange={(e) => setFormData({ ...formData, greeting: e.target.value })}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              placeholder="Hello! How can I help you today?"
            />
            <p className="text-xs text-gray-500 mt-1">First message shown to visitors</p>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Input Placeholder
            </label>
            <input
              type="text"
              value={formData.placeholder}
              onChange={(e) => setFormData({ ...formData, placeholder: e.target.value })}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              placeholder="Type your message..."
            />
          </div>
        </div>

        {/* Allowed Domains */}
        <div className="space-y-4">
          <h3 className="font-medium text-gray-900">
            Allowed Domains <span className="text-red-500">*</span>
          </h3>
          <p className="text-sm text-gray-600">
            Widget will only work on these domains. Use wildcards for subdomains (e.g.,
            *.example.com).
          </p>

          <div className="flex gap-2">
            <input
              type="text"
              value={domainInput}
              onChange={(e) => setDomainInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter") {
                  e.preventDefault();
                  addDomain();
                }
              }}
              className="flex-1 px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              placeholder="example.com or *.example.com or localhost:3000"
            />
            <button
              type="button"
              onClick={addDomain}
              className="px-4 py-2 bg-gray-100 text-gray-700 rounded-md hover:bg-gray-200"
            >
              Add
            </button>
          </div>

          {formData.allowed_domains.length > 0 && (
            <div className="flex flex-wrap gap-2">
              {formData.allowed_domains.map((domain) => (
                <span
                  key={domain}
                  className="inline-flex items-center gap-1 px-3 py-1 bg-blue-50 text-blue-700 rounded-full text-sm"
                >
                  {domain}
                  <button
                    type="button"
                    onClick={() => removeDomain(domain)}
                    className="ml-1 text-blue-600 hover:text-blue-800"
                  >
                    ×
                  </button>
                </span>
              ))}
            </div>
          )}

          {formData.allowed_domains.length === 0 && (
            <p className="text-sm text-amber-600">
              ⚠️ At least one domain is required
            </p>
          )}
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
                : "Create Widget"}
          </button>
        </div>
      </form>

      {/* Embed Code */}
      {channel && (
        <div className="p-4 bg-gray-50 border border-gray-200 rounded-lg space-y-3">
          <div className="flex items-center justify-between">
            <h3 className="font-medium text-gray-900">Embed Code</h3>
            <button
              onClick={copyEmbedCode}
              disabled={!embedCode || isLoadingEmbed}
              className="flex items-center gap-2 px-3 py-1.5 text-sm bg-white border border-gray-300 rounded-md hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {copied ? (
                <>
                  <Check className="w-4 h-4 text-green-600" />
                  Copied!
                </>
              ) : (
                <>
                  <Copy className="w-4 h-4" />
                  Copy
                </>
              )}
            </button>
          </div>

          {isLoadingEmbed ? (
            <div className="p-6 text-center text-gray-500">
              Loading embed code...
            </div>
          ) : embedCode ? (
            <>
              <pre className="p-3 bg-gray-900 text-green-400 rounded text-xs overflow-x-auto font-mono">
                <code>{embedCode}</code>
              </pre>

              <div className="space-y-2">
                <p className="text-xs text-gray-600">
                  <strong>Installation:</strong> Paste this code into your website&apos;s HTML, just before the closing{" "}
                  <code className="px-1 py-0.5 bg-gray-200 rounded font-mono">&lt;/body&gt;</code> tag.
                </p>
                <p className="text-xs text-gray-600">
                  <strong>Security:</strong> The embed code includes HMAC authentication to prevent unauthorized use.
                </p>
              </div>
            </>
          ) : (
            <div className="p-4 text-center text-gray-500 text-sm">
              Failed to load embed code. Please refresh the page.
            </div>
          )}
        </div>
      )}
    </div>
  );
}

/**
 * WhatsAppSetup Component
 *
 * Form for configuring WhatsApp channel via Twilio or Meta Cloud API
 */

"use client";

import { useState } from "react";
import { MessageCircle, Save } from "lucide-react";
import { toast } from "sonner";
import { useCreateChannel, useUpdateChannel } from "@/hooks/useChannels";
import type { ChannelConfig } from "@/lib/api";

type WhatsAppProvider = "twilio" | "meta";

interface WhatsAppSetupProps {
  channel?: ChannelConfig;
  onSuccess?: () => void;
}

interface TwilioConfig {
  account_sid: string;
  auth_token: string;
  phone: string;
  business_hours: BusinessHours;
}

interface MetaConfig {
  access_token: string;
  phone_number_id: string;
  app_secret: string;
  verify_token: string;
  phone_number: string;
  business_hours: BusinessHours;
}

interface BusinessHours {
  start: string;
  end: string;
  days: number[];
  timezone: string;
  reply_message?: string;
}

const DAYS_OF_WEEK = [
  { value: 1, label: "Mon" },
  { value: 2, label: "Tue" },
  { value: 3, label: "Wed" },
  { value: 4, label: "Thu" },
  { value: 5, label: "Fri" },
  { value: 6, label: "Sat" },
  { value: 0, label: "Sun" },
];

const COMMON_TIMEZONES = [
  "America/New_York",
  "America/Chicago",
  "America/Denver",
  "America/Los_Angeles",
  "America/Toronto",
  "Europe/London",
  "Europe/Paris",
  "Asia/Tokyo",
  "Australia/Sydney",
  "UTC",
];

const DEFAULT_BUSINESS_HOURS: BusinessHours = {
  start: "09:00",
  end: "17:00",
  days: [1, 2, 3, 4, 5],
  timezone: "America/New_York",
  reply_message: "We're currently offline. We'll respond during business hours.",
};

export function WhatsAppSetup({ channel, onSuccess }: WhatsAppSetupProps) {
  const isEditing = !!channel;

  const existingConfig = (channel?.config as Record<string, any>) || {};
  const existingProvider: WhatsAppProvider =
    (channel?.provider as WhatsAppProvider) || (existingConfig.access_token ? "meta" : "twilio");

  const [provider, setProvider] = useState<WhatsAppProvider>(existingProvider);

  const [twilioData, setTwilioData] = useState<TwilioConfig>({
    account_sid: existingConfig.account_sid || "",
    auth_token: existingConfig.auth_token || "",
    phone: existingConfig.phone || "",
    business_hours: {
      ...DEFAULT_BUSINESS_HOURS,
      ...existingConfig.business_hours,
    },
  });

  const [metaData, setMetaData] = useState<MetaConfig>({
    access_token: existingConfig.access_token || "",
    phone_number_id: existingConfig.phone_number_id || "",
    app_secret: existingConfig.app_secret || "",
    verify_token: existingConfig.verify_token || "",
    phone_number: existingConfig.phone_number || "",
    business_hours: {
      ...DEFAULT_BUSINESS_HOURS,
      ...existingConfig.business_hours,
    },
  });

  const createChannel = useCreateChannel();
  const updateChannel = useUpdateChannel();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (provider === "twilio") {
      if (!twilioData.account_sid || !twilioData.auth_token || !twilioData.phone) {
        toast.error("Please fill in all required Twilio fields");
        return;
      }
    } else {
      if (!metaData.access_token || !metaData.phone_number_id || !metaData.app_secret) {
        toast.error("Please fill in all required Meta fields");
        return;
      }
    }

    const configPayload =
      provider === "twilio"
        ? (twilioData as unknown as Record<string, unknown>)
        : (metaData as unknown as Record<string, unknown>);

    try {
      if (isEditing) {
        await updateChannel.mutateAsync({
          id: channel.id,
          data: { config: configPayload, provider },
        });
        toast.success("WhatsApp channel updated successfully");
      } else {
        await createChannel.mutateAsync({
          channel: "whatsapp",
          provider,
          config: configPayload,
          is_active: true,
        });
        toast.success("WhatsApp channel created successfully");
      }

      onSuccess?.();
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Failed to save channel");
    }
  };

  const currentBusinessHours = provider === "twilio" ? twilioData.business_hours : metaData.business_hours;

  const updateBusinessHours = (update: Partial<BusinessHours>) => {
    if (provider === "twilio") {
      setTwilioData({
        ...twilioData,
        business_hours: { ...twilioData.business_hours, ...update },
      });
    } else {
      setMetaData({
        ...metaData,
        business_hours: { ...metaData.business_hours, ...update },
      });
    }
  };

  const toggleDay = (day: number) => {
    const days = currentBusinessHours.days;
    const newDays = days.includes(day)
      ? days.filter((d) => d !== day)
      : [...days, day].sort();
    updateBusinessHours({ days: newDays });
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-6">
      <div className="flex items-center gap-3 pb-4 border-b">
        <div className="p-2 rounded-lg bg-green-50">
          <MessageCircle className="w-6 h-6 text-green-600" />
        </div>
        <div>
          <h2 className="text-lg font-semibold text-gray-900">
            {isEditing ? "Edit" : "Add"} WhatsApp Channel
          </h2>
          <p className="text-sm text-gray-600">Connect WhatsApp to your chatbot</p>
        </div>
      </div>

      {/* Provider Selector */}
      {!isEditing && (
        <div className="space-y-2">
          <label className="block text-sm font-medium text-gray-700">Provider</label>
          <div className="flex rounded-lg border border-gray-300 overflow-hidden">
            <button
              type="button"
              onClick={() => setProvider("twilio")}
              className={`flex-1 py-2.5 px-4 text-sm font-medium transition-colors ${
                provider === "twilio"
                  ? "bg-blue-600 text-white"
                  : "bg-white text-gray-700 hover:bg-gray-50"
              }`}
            >
              Twilio
            </button>
            <button
              type="button"
              onClick={() => setProvider("meta")}
              className={`flex-1 py-2.5 px-4 text-sm font-medium transition-colors border-l ${
                provider === "meta"
                  ? "bg-blue-600 text-white"
                  : "bg-white text-gray-700 hover:bg-gray-50"
              }`}
            >
              Meta Cloud API
            </button>
          </div>
          <p className="text-xs text-gray-500">
            {provider === "twilio"
              ? "Use Twilio as the WhatsApp Business API provider"
              : "Use Meta's WhatsApp Cloud API directly (free tier available)"}
          </p>
        </div>
      )}

      {/* Twilio Credentials */}
      {provider === "twilio" && (
        <div className="space-y-4">
          <h3 className="font-medium text-gray-900">Twilio Credentials</h3>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Account SID <span className="text-red-500">*</span>
            </label>
            <input
              type="text"
              required
              value={twilioData.account_sid}
              onChange={(e) => setTwilioData({ ...twilioData, account_sid: e.target.value })}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              placeholder="ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx" // pragma: allowlist secret
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Auth Token <span className="text-red-500">*</span>
            </label>
            <input
              type="password"
              required
              value={twilioData.auth_token}
              onChange={(e) => setTwilioData({ ...twilioData, auth_token: e.target.value })}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              placeholder="••••••••••••••••••••••••••••••••"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Phone Number <span className="text-red-500">*</span>
            </label>
            <input
              type="tel"
              required
              value={twilioData.phone}
              onChange={(e) => setTwilioData({ ...twilioData, phone: e.target.value })}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              placeholder="+1 555 123 4567"
            />
            <p className="text-xs text-gray-500 mt-1">
              Your Twilio WhatsApp-enabled phone number
            </p>
          </div>
        </div>
      )}

      {/* Meta Cloud API Credentials */}
      {provider === "meta" && (
        <div className="space-y-4">
          <h3 className="font-medium text-gray-900">Meta Cloud API Credentials</h3>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Access Token <span className="text-red-500">*</span>
            </label>
            <input
              type="password"
              required
              value={metaData.access_token}
              onChange={(e) => setMetaData({ ...metaData, access_token: e.target.value })}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              placeholder="••••••••••••••••••••••••••••••••"
            />
            <p className="text-xs text-gray-500 mt-1">
              From Meta Developer Portal &gt; WhatsApp &gt; API Setup
            </p>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Phone Number ID <span className="text-red-500">*</span>
            </label>
            <input
              type="text"
              required
              value={metaData.phone_number_id}
              onChange={(e) => setMetaData({ ...metaData, phone_number_id: e.target.value })}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              placeholder="123456789012345"
            />
            <p className="text-xs text-gray-500 mt-1">
              Found in WhatsApp &gt; API Setup &gt; Phone Number ID
            </p>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              App Secret <span className="text-red-500">*</span>
            </label>
            <input
              type="password"
              required
              value={metaData.app_secret}
              onChange={(e) => setMetaData({ ...metaData, app_secret: e.target.value })}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              placeholder="••••••••••••••••••••••••••••••••"
            />
            <p className="text-xs text-gray-500 mt-1">
              From App Dashboard &gt; Settings &gt; Basic &gt; App Secret
            </p>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Verify Token
            </label>
            <input
              type="text"
              value={metaData.verify_token}
              onChange={(e) => setMetaData({ ...metaData, verify_token: e.target.value })}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              placeholder="my-verify-token"
            />
            <p className="text-xs text-gray-500 mt-1">
              Custom token for webhook verification (set in Meta webhook config)
            </p>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Display Phone Number
            </label>
            <input
              type="tel"
              value={metaData.phone_number}
              onChange={(e) => setMetaData({ ...metaData, phone_number: e.target.value })}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              placeholder="+1 555 123 4567"
            />
            <p className="text-xs text-gray-500 mt-1">
              Your WhatsApp Business phone number (for display purposes)
            </p>
          </div>
        </div>
      )}

      {/* Business Hours */}
      <div className="space-y-4">
        <h3 className="font-medium text-gray-900">Business Hours</h3>

        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Start Time</label>
            <input
              type="time"
              value={currentBusinessHours.start}
              onChange={(e) => updateBusinessHours({ start: e.target.value })}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">End Time</label>
            <input
              type="time"
              value={currentBusinessHours.end}
              onChange={(e) => updateBusinessHours({ end: e.target.value })}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />
          </div>
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">Active Days</label>
          <div className="flex gap-2">
            {DAYS_OF_WEEK.map((day) => (
              <button
                key={day.value}
                type="button"
                onClick={() => toggleDay(day.value)}
                className={`flex-1 py-2 px-3 rounded-md text-sm font-medium transition-colors ${
                  currentBusinessHours.days.includes(day.value)
                    ? "bg-blue-600 text-white"
                    : "bg-gray-100 text-gray-700 hover:bg-gray-200"
                }`}
              >
                {day.label}
              </button>
            ))}
          </div>
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Timezone</label>
          <select
            value={currentBusinessHours.timezone}
            onChange={(e) => updateBusinessHours({ timezone: e.target.value })}
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          >
            {COMMON_TIMEZONES.map((tz) => (
              <option key={tz} value={tz}>
                {tz}
              </option>
            ))}
          </select>
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Off-Hours Reply Message
          </label>
          <textarea
            rows={3}
            value={currentBusinessHours.reply_message}
            onChange={(e) => updateBusinessHours({ reply_message: e.target.value })}
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            placeholder="We're currently offline. We'll respond during business hours."
          />
          <p className="text-xs text-gray-500 mt-1">
            Sent automatically when messages are received outside business hours
          </p>
        </div>
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

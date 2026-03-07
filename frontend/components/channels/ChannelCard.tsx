/**
 * ChannelCard Component
 *
 * Displays a channel configuration as a card with status indicator
 */

import Link from "next/link";
import { MessageCircle, Globe, Send, Phone } from "lucide-react";
import type { ChannelConfig } from "@/lib/api";

interface ChannelCardProps {
  channel: ChannelConfig;
}

export function ChannelCard({ channel }: ChannelCardProps) {
  const channelInfo = getChannelInfo(channel);

  return (
    <Link
      href={`/channels/${channel.id}`}
      className="block bg-white border border-gray-200 rounded-lg p-6 hover:border-blue-300 hover:shadow-md transition-all"
    >
      <div className="flex items-start justify-between">
        <div className="flex items-start gap-4">
          <div className={`p-3 rounded-lg ${channelInfo.bgColor}`}>
            {channelInfo.icon}
          </div>

          <div>
            <h3 className="font-semibold text-gray-900">{channelInfo.title}</h3>
            <p className="text-sm text-gray-600 mt-1">{channelInfo.subtitle}</p>

            <div className="flex items-center gap-2 mt-3">
              <StatusBadge isActive={channel.is_active} />
              {channelInfo.details && (
                <span className="text-xs text-gray-500">{channelInfo.details}</span>
              )}
            </div>
          </div>
        </div>

        <div className="text-xs text-gray-400">
          {new Date(channel.created_at).toLocaleDateString()}
        </div>
      </div>
    </Link>
  );
}

function StatusBadge({ isActive }: { isActive: boolean }) {
  if (isActive) {
    return (
      <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800">
        <span className="w-1.5 h-1.5 rounded-full bg-green-600"></span>
        Active
      </span>
    );
  }

  return (
    <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-600">
      <span className="w-1.5 h-1.5 rounded-full bg-gray-400"></span>
      Inactive
    </span>
  );
}

function getChannelInfo(channel: ChannelConfig) {
  const config = channel.config as any;

  switch (channel.channel) {
    case "whatsapp": {
      const provider = channel.provider;
      const providerLabel = provider === "meta" ? "Meta Cloud API" : "Twilio";
      const phone = provider === "meta" ? config.phone_number : config.phone;
      return {
        icon: <MessageCircle className="w-6 h-6 text-green-600" />,
        title: "WhatsApp",
        subtitle: `${providerLabel} WhatsApp Business`,
        details: phone ? `Phone: ${phone}` : undefined,
        bgColor: "bg-green-50",
      };
    }

    case "widget":
      return {
        icon: <Globe className="w-6 h-6 text-blue-600" />,
        title: "Website Widget",
        subtitle: "Embeddable chat widget",
        details: config.position ? `Position: ${config.position}` : undefined,
        bgColor: "bg-blue-50",
      };

    case "telegram":
      return {
        icon: <Send className="w-6 h-6 text-sky-600" />,
        title: "Telegram",
        subtitle: "Telegram bot",
        details: config.bot_username ? `@${config.bot_username}` : undefined,
        bgColor: "bg-sky-50",
      };

    case "voice":
      return {
        icon: <Phone className="w-6 h-6 text-purple-600" />,
        title: "Voice",
        subtitle: "Phone calls via Vapi",
        details: config.phone_number ? `Number: ${config.phone_number}` : undefined,
        bgColor: "bg-purple-50",
      };

    default:
      return {
        icon: <Globe className="w-6 h-6 text-gray-600" />,
        title: channel.channel,
        subtitle: "Unknown channel type",
        details: undefined,
        bgColor: "bg-gray-50",
      };
  }
}

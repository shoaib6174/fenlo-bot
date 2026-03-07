/**
 * ChannelBadge Component
 *
 * Displays a colored badge with channel icon
 */

import { MessageCircle, MessageSquare, Send, Phone, Globe } from "lucide-react";

interface ChannelBadgeProps {
  channel: string;
  size?: "sm" | "md" | "lg";
}

export function ChannelBadge({ channel, size = "md" }: ChannelBadgeProps) {
  const sizeClasses = {
    sm: "w-6 h-6 p-1",
    md: "w-8 h-8 p-1.5",
    lg: "w-10 h-10 p-2",
  };

  const iconSizes = {
    sm: "w-4 h-4",
    md: "w-5 h-5",
    lg: "w-6 h-6",
  };

  const channelConfig: Record<string, { icon: React.ReactNode; bgColor: string; textColor: string; label: string }> = {
    whatsapp: {
      icon: <MessageCircle className={iconSizes[size]} />,
      bgColor: "bg-green-100",
      textColor: "text-green-600",
      label: "WhatsApp",
    },
    widget: {
      icon: <MessageSquare className={iconSizes[size]} />,
      bgColor: "bg-blue-100",
      textColor: "text-blue-600",
      label: "Widget",
    },
    web: {
      icon: <Globe className={iconSizes[size]} />,
      bgColor: "bg-indigo-100",
      textColor: "text-indigo-600",
      label: "Web",
    },
    telegram: {
      icon: <Send className={iconSizes[size]} />,
      bgColor: "bg-sky-100",
      textColor: "text-sky-600",
      label: "Telegram",
    },
    voice: {
      icon: <Phone className={iconSizes[size]} />,
      bgColor: "bg-purple-100",
      textColor: "text-purple-600",
      label: "Voice",
    },
  };

  const config = channelConfig[channel] || {
    icon: <Globe className={iconSizes[size]} />,
    bgColor: "bg-gray-100",
    textColor: "text-gray-600",
    label: channel || "Unknown",
  };

  return (
    <div
      className={`rounded-lg ${config.bgColor} ${config.textColor} ${sizeClasses[size]} flex items-center justify-center`}
      title={config.label}
    >
      {config.icon}
    </div>
  );
}

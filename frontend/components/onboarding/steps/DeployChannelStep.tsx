"use client";

import { Globe, MessageSquare, Phone } from "lucide-react";
import Link from "next/link";

interface Props {
  onComplete: () => void;
}

const channels = [
  {
    id: "widget",
    label: "Web Widget",
    description: "Embed on your website",
    icon: Globe,
    href: "/channels",
    color: "text-blue-600",
    bg: "bg-blue-50",
  },
  {
    id: "whatsapp",
    label: "WhatsApp",
    description: "Connect via Twilio",
    icon: MessageSquare,
    href: "/channels",
    color: "text-green-600",
    bg: "bg-green-50",
  },
  {
    id: "voice",
    label: "Voice Bot",
    description: "Phone conversations",
    icon: Phone,
    href: "/voice",
    color: "text-purple-600",
    bg: "bg-purple-50",
  },
];

export default function DeployChannelStep({ onComplete }: Props) {
  return (
    <div className="space-y-6">
      <div className="text-center">
        <div className="mx-auto w-12 h-12 bg-purple-100 rounded-full flex items-center justify-center mb-3">
          <Globe className="w-6 h-6 text-purple-600" />
        </div>
        <h2 className="text-lg font-semibold text-gray-900">Deploy a Channel</h2>
        <p className="text-sm text-gray-500 mt-1">
          Choose how users will interact with your bot
        </p>
      </div>

      <div className="space-y-3">
        {channels.map((ch) => {
          const Icon = ch.icon;
          return (
            <Link
              key={ch.id}
              href={ch.href}
              target="_blank"
              className="flex items-center gap-3 p-3 border border-gray-200 rounded-lg hover:border-blue-300 hover:bg-blue-50 transition"
            >
              <div className={`p-2 rounded-lg ${ch.bg}`}>
                <Icon className={`w-5 h-5 ${ch.color}`} />
              </div>
              <div>
                <p className="text-sm font-medium text-gray-900">{ch.label}</p>
                <p className="text-xs text-gray-500">{ch.description}</p>
              </div>
            </Link>
          );
        })}
      </div>

      <button
        onClick={onComplete}
        className="w-full py-2.5 bg-white border border-gray-300 text-gray-700 rounded-lg text-sm font-medium hover:bg-gray-50 transition"
      >
        I&apos;ll Set Up a Channel Later
      </button>
    </div>
  );
}

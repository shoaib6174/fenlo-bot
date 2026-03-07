"use client";

import { Calendar, ExternalLink } from "lucide-react";

interface BookingConfig {
  provider: string;
  url: string;
  prompt: string;
}

const PROVIDER_LABELS: Record<string, string> = {
  calendly: "Calendly",
  cal_com: "Cal.com",
  google: "Google Calendar",
  custom_url: "Booking",
};

interface BookingCardProps {
  config: BookingConfig;
}

export function BookingCard({ config }: BookingCardProps) {
  const providerLabel = PROVIDER_LABELS[config.provider] || "Booking";

  return (
    <div
      className="mt-3 border border-blue-200 bg-blue-50 rounded-lg p-4"
      data-testid="booking-card"
    >
      <div className="flex items-center gap-3 mb-3">
        <Calendar className="w-8 h-8 text-blue-600 flex-shrink-0" />
        <div>
          <p className="text-sm font-semibold text-gray-900">Schedule a Meeting</p>
          <p className="text-xs text-gray-500">{providerLabel}</p>
        </div>
      </div>
      <a
        href={config.url}
        target="_blank"
        rel="noopener noreferrer"
        className="flex items-center justify-center gap-2 w-full bg-blue-600 text-white text-sm font-medium py-2.5 px-4 rounded-md hover:bg-blue-700 transition"
        data-testid="booking-card-link"
      >
        <Calendar className="w-4 h-4" />
        Book Now
        <ExternalLink className="w-3.5 h-3.5" />
      </a>
    </div>
  );
}

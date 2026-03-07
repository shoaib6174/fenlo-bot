"use client";

import { Phone, PhoneOff, Loader2 } from "lucide-react";
import type { CallState } from "@/types/voice";

interface WebCallButtonProps {
  callState: CallState;
  onStart: () => void;
  onEnd: () => void;
  disabled?: boolean;
}

export function WebCallButton({
  callState,
  onStart,
  onEnd,
  disabled = false,
}: WebCallButtonProps) {
  if (callState === "connecting") {
    return (
      <button
        disabled
        className="inline-flex items-center gap-2 px-6 py-3 rounded-full bg-amber-100 text-amber-700 font-medium text-sm cursor-wait"
      >
        <Loader2 className="w-5 h-5 animate-spin" />
        Connecting...
      </button>
    );
  }

  if (callState === "active") {
    return (
      <button
        onClick={onEnd}
        className="inline-flex items-center gap-2 px-6 py-3 rounded-full bg-red-600 text-white font-medium text-sm hover:bg-red-700 transition-colors"
      >
        <PhoneOff className="w-5 h-5" />
        End Call
      </button>
    );
  }

  if (callState === "ended") {
    return (
      <button
        onClick={onStart}
        disabled={disabled}
        className="inline-flex items-center gap-2 px-6 py-3 rounded-full bg-gray-100 text-gray-700 font-medium text-sm hover:bg-gray-200 transition-colors disabled:opacity-50"
      >
        <Phone className="w-5 h-5" />
        Call Again
      </button>
    );
  }

  // idle or error
  return (
    <button
      onClick={onStart}
      disabled={disabled}
      className="inline-flex items-center gap-2 px-6 py-3 rounded-full bg-green-600 text-white font-medium text-sm hover:bg-green-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
    >
      <Phone className="w-5 h-5" />
      Start Test Call
    </button>
  );
}

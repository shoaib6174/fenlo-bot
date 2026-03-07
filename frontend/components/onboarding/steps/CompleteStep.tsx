"use client";

import { PartyPopper, ArrowRight } from "lucide-react";
import Link from "next/link";

export default function CompleteStep() {
  return (
    <div className="space-y-6 text-center">
      <div className="mx-auto w-16 h-16 bg-green-100 rounded-full flex items-center justify-center mb-2">
        <PartyPopper className="w-8 h-8 text-green-600" />
      </div>

      <div>
        <h2 className="text-xl font-bold text-gray-900">You&apos;re All Set!</h2>
        <p className="text-sm text-gray-500 mt-2">
          Your AI chatbot is ready to go. Explore the dashboard to see your
          analytics, manage documents, and fine-tune your bot.
        </p>
      </div>

      <div className="grid grid-cols-2 gap-3 pt-2">
        <Link
          href="/chat"
          className="flex items-center justify-center gap-2 py-2.5 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 transition"
        >
          Start Chatting
          <ArrowRight className="w-4 h-4" />
        </Link>
        <Link
          href="/dashboard"
          className="flex items-center justify-center gap-2 py-2.5 bg-white border border-gray-300 text-gray-700 rounded-lg text-sm font-medium hover:bg-gray-50 transition"
        >
          Go to Dashboard
        </Link>
      </div>
    </div>
  );
}

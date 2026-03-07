"use client";

import { MessageSquare } from "lucide-react";
import Link from "next/link";

interface Props {
  onComplete: () => void;
}

export default function TestChatStep({ onComplete }: Props) {
  return (
    <div className="space-y-6">
      <div className="text-center">
        <div className="mx-auto w-12 h-12 bg-green-100 rounded-full flex items-center justify-center mb-3">
          <MessageSquare className="w-6 h-6 text-green-600" />
        </div>
        <h2 className="text-lg font-semibold text-gray-900">Test Your Bot</h2>
        <p className="text-sm text-gray-500 mt-1">
          Try a conversation to see how your bot responds
        </p>
      </div>

      <div className="bg-gray-50 border border-gray-200 rounded-lg p-4 text-sm text-gray-600 space-y-2">
        <p>Try asking questions about the document you uploaded. For example:</p>
        <ul className="list-disc list-inside space-y-1 text-gray-500">
          <li>&quot;What is this document about?&quot;</li>
          <li>&quot;Summarize the main points&quot;</li>
          <li>&quot;What are the key takeaways?&quot;</li>
        </ul>
      </div>

      <Link
        href="/chat"
        target="_blank"
        className="block w-full py-2.5 bg-green-600 text-white rounded-lg text-sm font-medium text-center hover:bg-green-700 transition"
      >
        Open Chat in New Tab
      </Link>

      <button
        onClick={onComplete}
        className="w-full py-2.5 bg-white border border-gray-300 text-gray-700 rounded-lg text-sm font-medium hover:bg-gray-50 transition"
      >
        I&apos;ve Tested It — Continue
      </button>
    </div>
  );
}

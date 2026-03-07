"use client";

import { useState } from "react";
import { Bot, AlertCircle } from "lucide-react";

interface Props {
  onComplete: () => void;
}

export default function PersonalityStep({ onComplete }: Props) {
  const [botName, setBotName] = useState("");
  const [personality, setPersonality] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  const handleSave = async () => {
    setSaving(true);
    setError("");
    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || "";
      const response = await fetch(`${apiUrl}/api/v1/settings`, {
        method: "PUT",
        credentials: "include",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          settings: {
            bot_name: botName || "Fenlo AI Assistant",
            personality: personality || "helpful and professional",
          },
        }),
      });
      if (!response.ok) {
        const data = await response.json().catch(() => null);
        setError(data?.detail || `Save failed (${response.status})`);
        return;
      }
      onComplete();
    } catch {
      setError("Network error. Please try again.");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="space-y-6">
      <div className="text-center">
        <div className="mx-auto w-12 h-12 bg-blue-100 rounded-full flex items-center justify-center mb-3">
          <Bot className="w-6 h-6 text-blue-600" />
        </div>
        <h2 className="text-lg font-semibold text-gray-900">Name Your Bot</h2>
        <p className="text-sm text-gray-500 mt-1">
          Give your AI assistant a name and personality
        </p>
      </div>

      {error && (
        <div className="flex items-center gap-2 p-3 bg-red-50 border border-red-200 rounded-lg">
          <AlertCircle className="w-4 h-4 text-red-500 shrink-0" />
          <p className="text-sm text-red-700">{error}</p>
        </div>
      )}

      <div className="space-y-4">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Bot Name
          </label>
          <input
            type="text"
            value={botName}
            onChange={(e) => setBotName(e.target.value)}
            placeholder="e.g. Luna, Max, Fenlo AI Assistant"
            className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Personality Description
          </label>
          <textarea
            value={personality}
            onChange={(e) => setPersonality(e.target.value)}
            placeholder="e.g. Friendly, professional, and knowledgeable. Responds concisely with a helpful tone."
            rows={3}
            className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 resize-none"
          />
        </div>
      </div>

      <div className="flex gap-3">
        <button
          onClick={handleSave}
          disabled={saving}
          className="flex-1 py-2.5 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 transition disabled:opacity-50"
        >
          {saving ? "Saving..." : "Save & Continue"}
        </button>
        <button
          onClick={onComplete}
          className="px-4 py-2.5 bg-white border border-gray-300 text-gray-600 rounded-lg text-sm font-medium hover:bg-gray-50 transition"
        >
          Skip
        </button>
      </div>
    </div>
  );
}

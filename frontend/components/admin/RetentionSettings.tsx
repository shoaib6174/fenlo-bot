"use client";

import { useState } from "react";
import { Archive, Clock } from "lucide-react";
import { useArchiveConversations } from "@/hooks/useAdmin";

export default function RetentionSettings() {
  const [retentionDays, setRetentionDays] = useState(90);
  const archive = useArchiveConversations();

  const handleArchive = () => {
    const cutoff = new Date();
    cutoff.setDate(cutoff.getDate() - retentionDays);
    const confirmed = window.confirm(
      `Archive all active conversations older than ${retentionDays} days (before ${cutoff.toLocaleDateString()})?\n\nThis will close them and set an end date. Messages are preserved.`
    );
    if (!confirmed) return;

    archive.mutate(cutoff.toISOString(), {
      onSuccess: (data) => {
        alert(`Archived ${data.archived_count} conversations.`);
      },
      onError: (err) => {
        alert(`Archive failed: ${err.message}`);
      },
    });
  };

  return (
    <div className="space-y-6">
      <div>
        <h3 className="text-base font-semibold text-gray-900 mb-1">
          Data Retention
        </h3>
        <p className="text-sm text-gray-500">
          Configure conversation archiving to keep your workspace tidy.
        </p>
      </div>

      {/* Retention period */}
      <div className="border border-gray-200 rounded-lg p-5">
        <div className="flex items-center gap-3 mb-4">
          <div className="p-2 bg-amber-50 rounded-lg">
            <Clock className="w-5 h-5 text-amber-600" />
          </div>
          <div>
            <h4 className="text-sm font-semibold text-gray-900">
              Retention Period
            </h4>
            <p className="text-xs text-gray-500">
              Archive conversations older than this
            </p>
          </div>
        </div>

        <div className="flex items-center gap-4 mb-4">
          <select
            value={retentionDays}
            onChange={(e) => setRetentionDays(Number(e.target.value))}
            className="px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none"
          >
            <option value={30}>30 days</option>
            <option value={60}>60 days</option>
            <option value={90}>90 days</option>
            <option value={180}>180 days</option>
            <option value={365}>1 year</option>
          </select>
          <span className="text-sm text-gray-500">
            Conversations older than{" "}
            <span className="font-medium text-gray-700">{retentionDays} days</span>{" "}
            will be archived (closed).
          </span>
        </div>

        <button
          onClick={handleArchive}
          disabled={archive.isPending}
          className="flex items-center gap-2 py-2 px-4 bg-amber-600 text-white rounded-lg text-sm font-medium hover:bg-amber-700 disabled:opacity-50 disabled:cursor-not-allowed transition"
        >
          {archive.isPending ? (
            <>
              <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
              Archiving...
            </>
          ) : (
            <>
              <Archive className="w-4 h-4" />
              Archive Now
            </>
          )}
        </button>
      </div>

      {/* Info */}
      <div className="text-xs text-gray-500 space-y-1">
        <p>
          Archiving sets conversations to &quot;closed&quot; status. Messages and
          analytics data are preserved.
        </p>
        <p>
          For automatic daily archiving, configure{" "}
          <code className="px-1 py-0.5 bg-gray-100 rounded text-gray-700">
            auto_archive_enabled
          </code>{" "}
          in your backend environment.
        </p>
      </div>
    </div>
  );
}

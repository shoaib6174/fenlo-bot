"use client";

import { useState } from "react";
import { Trash2, AlertTriangle, ShieldCheck } from "lucide-react";
import { usePurgeWorkspace } from "@/hooks/useAdmin";

interface Props {
  workspaceId: string;
}

export default function GDPRTools({ workspaceId }: Props) {
  const [showConfirm, setShowConfirm] = useState(false);
  const [confirmText, setConfirmText] = useState("");
  const purge = usePurgeWorkspace();

  const canPurge = confirmText === "DELETE ALL DATA";

  const handlePurge = () => {
    if (!canPurge) return;
    purge.mutate(workspaceId, {
      onSuccess: (data) => {
        setShowConfirm(false);
        setConfirmText("");
        alert(
          `Data purged successfully.\n\nDeleted:\n` +
            `- ${data.deleted_records.messages} messages\n` +
            `- ${data.deleted_records.conversations} conversations\n` +
            `- ${data.deleted_records.documents} documents\n` +
            `- ${data.deleted_records.knowledge_bases} knowledge bases\n` +
            `- ${data.deleted_records.channels} channels\n\n` +
            `Duration: ${(data.duration_ms ?? 0).toFixed(0)}ms`
        );
      },
      onError: (err) => {
        alert(`Purge failed: ${err.message}`);
      },
    });
  };

  return (
    <div className="space-y-6">
      <div>
        <h3 className="text-base font-semibold text-gray-900 mb-1">
          GDPR Compliance
        </h3>
        <p className="text-sm text-gray-500">
          Tools for data deletion requests under GDPR Article 17 (Right to
          Erasure).
        </p>
      </div>

      {/* Info banner */}
      <div className="flex items-start gap-3 p-4 bg-blue-50 border border-blue-200 rounded-lg">
        <ShieldCheck className="w-5 h-5 text-blue-600 mt-0.5 flex-shrink-0" />
        <div className="text-sm text-blue-800">
          <p className="font-medium mb-1">Audit Logging Active</p>
          <p className="text-blue-700">
            All export and purge operations are logged to an immutable audit
            trail for compliance purposes.
          </p>
        </div>
      </div>

      {/* Purge section */}
      <div className="border border-red-200 rounded-lg p-5 bg-red-50/30">
        <div className="flex items-center gap-3 mb-3">
          <div className="p-2 bg-red-100 rounded-lg">
            <Trash2 className="w-5 h-5 text-red-600" />
          </div>
          <div>
            <h4 className="text-sm font-semibold text-gray-900">
              Purge Workspace Data
            </h4>
            <p className="text-xs text-red-600 font-medium">
              Permanent &amp; irreversible
            </p>
          </div>
        </div>
        <p className="text-xs text-gray-600 mb-4">
          Permanently deletes all conversations, messages, documents, knowledge
          bases, and channel configurations. Redis cache is also cleared. This
          action cannot be undone.
        </p>

        {!showConfirm ? (
          <button
            onClick={() => setShowConfirm(true)}
            className="flex items-center gap-2 py-2 px-4 bg-white border border-red-300 text-red-700 rounded-lg text-sm font-medium hover:bg-red-50 transition"
          >
            <AlertTriangle className="w-4 h-4" />
            Request Data Deletion
          </button>
        ) : (
          <div className="space-y-3 p-4 bg-white border border-red-200 rounded-lg">
            <p className="text-sm text-gray-700 font-medium">
              Type <span className="font-mono text-red-600">DELETE ALL DATA</span>{" "}
              to confirm:
            </p>
            <input
              type="text"
              value={confirmText}
              onChange={(e) => setConfirmText(e.target.value)}
              placeholder="DELETE ALL DATA"
              className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-red-500 focus:border-red-500 outline-none"
            />
            <div className="flex gap-2">
              <button
                onClick={handlePurge}
                disabled={!canPurge || purge.isPending}
                className="flex items-center gap-2 py-2 px-4 bg-red-600 text-white rounded-lg text-sm font-medium hover:bg-red-700 disabled:opacity-50 disabled:cursor-not-allowed transition"
              >
                {purge.isPending ? (
                  <>
                    <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                    Purging...
                  </>
                ) : (
                  <>
                    <Trash2 className="w-4 h-4" />
                    Confirm Purge
                  </>
                )}
              </button>
              <button
                onClick={() => {
                  setShowConfirm(false);
                  setConfirmText("");
                }}
                className="py-2 px-4 bg-white border border-gray-300 text-gray-700 rounded-lg text-sm font-medium hover:bg-gray-50 transition"
              >
                Cancel
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

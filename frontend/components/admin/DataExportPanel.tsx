"use client";

import { useState } from "react";
import { Download, FileArchive, FileText } from "lucide-react";
import { adminApi, exportApi } from "@/lib/api";

interface Props {
  workspaceId: string;
}

export default function DataExportPanel({ workspaceId }: Props) {
  const [exporting, setExporting] = useState(false);

  const handleFullExport = async () => {
    setExporting(true);
    try {
      const url = adminApi.exportUrl(workspaceId);
      const response = await fetch(url, { credentials: "include" });
      if (!response.ok) throw new Error("Export failed");
      const blob = await response.blob();
      const a = document.createElement("a");
      a.href = URL.createObjectURL(blob);
      a.download = `export_${workspaceId}.zip`;
      a.click();
      URL.revokeObjectURL(a.href);
    } catch {
      alert("Export failed. Please try again.");
    } finally {
      setExporting(false);
    }
  };

  const handleCsvExport = () => {
    window.open(exportApi.csvUrl(), "_blank");
  };

  return (
    <div className="space-y-6">
      <div>
        <h3 className="text-base font-semibold text-gray-900 mb-1">
          Data Export
        </h3>
        <p className="text-sm text-gray-500">
          Download your workspace data for backup or compliance purposes.
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Full workspace export */}
        <div className="border border-gray-200 rounded-lg p-5">
          <div className="flex items-center gap-3 mb-3">
            <div className="p-2 bg-blue-50 rounded-lg">
              <FileArchive className="w-5 h-5 text-blue-600" />
            </div>
            <div>
              <h4 className="text-sm font-semibold text-gray-900">
                Full Workspace Export
              </h4>
              <p className="text-xs text-gray-500">ZIP with JSON files</p>
            </div>
          </div>
          <p className="text-xs text-gray-600 mb-4">
            Includes conversations, messages, documents, channels, and knowledge
            bases. Suitable for GDPR data portability (Art. 20).
          </p>
          <button
            onClick={handleFullExport}
            disabled={exporting}
            className="w-full flex items-center justify-center gap-2 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition"
          >
            {exporting ? (
              <>
                <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                Exporting...
              </>
            ) : (
              <>
                <Download className="w-4 h-4" />
                Export ZIP
              </>
            )}
          </button>
        </div>

        {/* CSV export */}
        <div className="border border-gray-200 rounded-lg p-5">
          <div className="flex items-center gap-3 mb-3">
            <div className="p-2 bg-green-50 rounded-lg">
              <FileText className="w-5 h-5 text-green-600" />
            </div>
            <div>
              <h4 className="text-sm font-semibold text-gray-900">
                Conversations CSV
              </h4>
              <p className="text-xs text-gray-500">Spreadsheet format</p>
            </div>
          </div>
          <p className="text-xs text-gray-600 mb-4">
            Export conversation summaries as CSV for analysis in Excel or Google
            Sheets. Includes channel, status, and lead score.
          </p>
          <button
            onClick={handleCsvExport}
            className="w-full flex items-center justify-center gap-2 py-2 bg-white border border-gray-300 text-gray-700 rounded-lg text-sm font-medium hover:bg-gray-50 transition"
          >
            <Download className="w-4 h-4" />
            Download CSV
          </button>
        </div>
      </div>
    </div>
  );
}

"use client";

import { useState } from "react";
import { useAuth } from "@/providers/auth";
import {
  Download,
  ShieldCheck,
  HardDrive,
  Clock,
} from "lucide-react";
import DataExportPanel from "@/components/admin/DataExportPanel";
import GDPRTools from "@/components/admin/GDPRTools";
import StorageMonitor from "@/components/admin/StorageMonitor";
import RetentionSettings from "@/components/admin/RetentionSettings";

type Tab = "export" | "gdpr" | "storage" | "retention";

const TABS: { key: Tab; label: string; icon: React.ComponentType<{ className?: string }> }[] = [
  { key: "export", label: "Export", icon: Download },
  { key: "gdpr", label: "GDPR", icon: ShieldCheck },
  { key: "storage", label: "Storage", icon: HardDrive },
  { key: "retention", label: "Retention", icon: Clock },
];

export default function AdminPage() {
  const { user, isLoading } = useAuth();
  const [activeTab, setActiveTab] = useState<Tab>("export");

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600" />
      </div>
    );
  }

  const workspaceId = user?.workspace_id;

  return (
    <div className="container mx-auto px-6 py-8 max-w-5xl">
      {/* Header */}
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Admin Tools</h1>
        <p className="text-gray-600 text-sm">
          Data export, GDPR compliance, storage monitoring, and retention
          settings.
        </p>
      </div>

      {/* Tabs */}
      <div className="border-b border-gray-200 mb-6">
        <nav className="flex gap-6 -mb-px">
          {TABS.map(({ key, label, icon: Icon }) => (
            <button
              key={key}
              onClick={() => setActiveTab(key)}
              className={`flex items-center gap-2 pb-3 border-b-2 text-sm font-medium transition-colors ${
                activeTab === key
                  ? "border-blue-600 text-blue-600"
                  : "border-transparent text-gray-500 hover:border-gray-300 hover:text-gray-700"
              }`}
            >
              <Icon className="w-4 h-4" />
              {label}
            </button>
          ))}
        </nav>
      </div>

      {/* Content */}
      <div className="bg-white border border-gray-200 rounded-lg p-6">
        {activeTab === "export" && workspaceId && (
          <DataExportPanel workspaceId={workspaceId} />
        )}
        {activeTab === "gdpr" && workspaceId && (
          <GDPRTools workspaceId={workspaceId} />
        )}
        {activeTab === "storage" && workspaceId && (
          <StorageMonitor workspaceId={workspaceId} />
        )}
        {activeTab === "retention" && <RetentionSettings />}

        {!workspaceId && activeTab !== "retention" && (
          <p className="text-sm text-gray-500">
            Unable to detect workspace. Please reload the page.
          </p>
        )}
      </div>
    </div>
  );
}

"use client";

import {
  MessageSquare,
  FileText,
  Share2,
  BookOpen,
  MessagesSquare,
} from "lucide-react";
import { useStorageUsage } from "@/hooks/useAdmin";

interface Props {
  workspaceId: string;
}

const ITEMS = [
  {
    key: "conversations_count" as const,
    label: "Conversations",
    icon: MessagesSquare,
    color: "text-blue-600",
    bg: "bg-blue-50",
  },
  {
    key: "messages_count" as const,
    label: "Messages",
    icon: MessageSquare,
    color: "text-indigo-600",
    bg: "bg-indigo-50",
  },
  {
    key: "documents_count" as const,
    label: "Documents",
    icon: FileText,
    color: "text-green-600",
    bg: "bg-green-50",
  },
  {
    key: "knowledge_bases_count" as const,
    label: "Knowledge Bases",
    icon: BookOpen,
    color: "text-amber-600",
    bg: "bg-amber-50",
  },
  {
    key: "channels_count" as const,
    label: "Channels",
    icon: Share2,
    color: "text-purple-600",
    bg: "bg-purple-50",
  },
];

export default function StorageMonitor({ workspaceId }: Props) {
  const { data, isLoading } = useStorageUsage(workspaceId);

  if (isLoading) {
    return (
      <div className="space-y-6">
        <div>
          <h3 className="text-base font-semibold text-gray-900 mb-1">
            Storage Usage
          </h3>
          <p className="text-sm text-gray-500">
            Monitor workspace data volume.
          </p>
        </div>
        <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
          {Array.from({ length: 5 }).map((_, i) => (
            <div
              key={i}
              className="border border-gray-200 rounded-lg p-4 animate-pulse"
            >
              <div className="w-8 h-8 bg-gray-100 rounded-lg mb-3" />
              <div className="h-6 w-12 bg-gray-100 rounded mb-1" />
              <div className="h-4 w-16 bg-gray-50 rounded" />
            </div>
          ))}
        </div>
      </div>
    );
  }

  if (!data) return null;

  const total =
    data.conversations_count +
    data.messages_count +
    data.documents_count +
    data.knowledge_bases_count +
    data.channels_count;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-base font-semibold text-gray-900 mb-1">
            Storage Usage
          </h3>
          <p className="text-sm text-gray-500">
            Monitor workspace data volume.
          </p>
        </div>
        <div className="text-right">
          <p className="text-2xl font-bold text-gray-900">
            {total.toLocaleString()}
          </p>
          <p className="text-xs text-gray-500">total records</p>
        </div>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
        {ITEMS.map((item) => {
          const Icon = item.icon;
          const count = data[item.key];
          return (
            <div
              key={item.key}
              className="border border-gray-200 rounded-lg p-4"
            >
              <div className={`p-2 ${item.bg} rounded-lg w-fit mb-3`}>
                <Icon className={`w-4 h-4 ${item.color}`} />
              </div>
              <p className="text-xl font-bold text-gray-900">
                {count.toLocaleString()}
              </p>
              <p className="text-xs text-gray-500">{item.label}</p>
            </div>
          );
        })}
      </div>
    </div>
  );
}

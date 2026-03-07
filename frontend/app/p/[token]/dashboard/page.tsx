"use client";

import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import {
  MessageSquare,
  MessagesSquare,
  FileText,
  AlertTriangle,
  TrendingUp,
  Clock,
} from "lucide-react";
import { publicApi, type PublicDashboardData } from "@/lib/public-api";

function StatCard({
  label,
  value,
  icon: Icon,
  color,
  bgColor,
}: {
  label: string;
  value: string | number;
  icon: React.ComponentType<{ className?: string }>;
  color: string;
  bgColor: string;
}) {
  return (
    <div className="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-xl p-5">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-sm text-gray-500 dark:text-gray-400 mb-1">{label}</p>
          <p className="text-2xl font-bold text-gray-900 dark:text-white">{value}</p>
        </div>
        <div className={`p-2.5 rounded-xl ${bgColor}`}>
          <Icon className={`w-5 h-5 ${color}`} />
        </div>
      </div>
    </div>
  );
}

function Skeleton() {
  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        {[1, 2, 3, 4, 5, 6].map((i) => (
          <div
            key={i}
            className="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-xl p-5 animate-pulse"
          >
            <div className="flex items-center justify-between">
              <div className="space-y-2">
                <div className="h-4 w-24 bg-gray-200 dark:bg-gray-700 rounded" />
                <div className="h-8 w-16 bg-gray-200 dark:bg-gray-700 rounded" />
              </div>
              <div className="h-10 w-10 bg-gray-100 dark:bg-gray-800 rounded-xl" />
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

export default function PublicDashboardPage() {
  const { token } = useParams<{ token: string }>();
  const [data, setData] = useState<PublicDashboardData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    publicApi
      .dashboard(token)
      .then(setData)
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, [token]);

  if (loading) return <Skeleton />;

  if (error) {
    return (
      <div className="flex items-center justify-center h-[50vh]">
        <div className="text-center">
          <AlertTriangle className="w-12 h-12 text-gray-300 dark:text-gray-600 mx-auto mb-4" />
          <p className="text-gray-500 dark:text-gray-400">{error}</p>
        </div>
      </div>
    );
  }

  if (!data) return null;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
          {data.workspace_name}
        </h1>
        <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
          Real-time performance dashboard
        </p>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        <StatCard
          label="Conversations"
          value={data.conversations_count.toLocaleString()}
          icon={MessageSquare}
          color="text-blue-600 dark:text-blue-400"
          bgColor="bg-blue-50 dark:bg-blue-900/30"
        />
        <StatCard
          label="Messages"
          value={data.messages_count.toLocaleString()}
          icon={MessagesSquare}
          color="text-indigo-600 dark:text-indigo-400"
          bgColor="bg-indigo-50 dark:bg-indigo-900/30"
        />
        <StatCard
          label="Documents"
          value={data.documents_count.toLocaleString()}
          icon={FileText}
          color="text-emerald-600 dark:text-emerald-400"
          bgColor="bg-emerald-50 dark:bg-emerald-900/30"
        />
        <StatCard
          label="Knowledge Gaps"
          value={data.knowledge_gaps_count.toLocaleString()}
          icon={AlertTriangle}
          color="text-amber-600 dark:text-amber-400"
          bgColor="bg-amber-50 dark:bg-amber-900/30"
        />
        <StatCard
          label="Quality Score"
          value={
            data.avg_quality_score
              ? `${Math.round(data.avg_quality_score * 100)}%`
              : "N/A"
          }
          icon={TrendingUp}
          color="text-green-600 dark:text-green-400"
          bgColor="bg-green-50 dark:bg-green-900/30"
        />
        <StatCard
          label="Active Since"
          value={
            data.recent_conversations.length > 0 && data.recent_conversations[data.recent_conversations.length - 1].started_at
              ? new Date(data.recent_conversations[data.recent_conversations.length - 1].started_at!).toLocaleDateString()
              : "N/A"
          }
          icon={Clock}
          color="text-purple-600 dark:text-purple-400"
          bgColor="bg-purple-50 dark:bg-purple-900/30"
        />
      </div>

      {/* Recent Activity */}
      {data.recent_conversations.length > 0 && (
        <div className="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-xl p-6">
          <h3 className="text-sm font-semibold text-gray-900 dark:text-white mb-4">
            Recent Conversations
          </h3>
          <div className="space-y-3">
            {data.recent_conversations.map((conv) => (
              <div
                key={conv.id}
                className="flex items-center justify-between py-2 border-b border-gray-100 dark:border-gray-800 last:border-0"
              >
                <div className="flex items-center gap-3">
                  <div className="w-8 h-8 rounded-lg bg-gray-100 dark:bg-gray-800 flex items-center justify-center">
                    <MessageSquare className="w-4 h-4 text-gray-400" />
                  </div>
                  <div>
                    <p className="text-sm text-gray-700 dark:text-gray-300">
                      Conversation
                    </p>
                    <p className="text-xs text-gray-400">
                      {conv.started_at
                        ? new Date(conv.started_at).toLocaleDateString("en-US", {
                            month: "short",
                            day: "numeric",
                            hour: "2-digit",
                            minute: "2-digit",
                          })
                        : "Unknown"}
                    </p>
                  </div>
                </div>
                {conv.lead_score !== null && conv.lead_score > 0 && (
                  <span className="text-xs font-medium px-2 py-1 rounded-full bg-sky-50 dark:bg-sky-900/30 text-sky-600 dark:text-sky-400">
                    Score: {conv.lead_score}
                  </span>
                )}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

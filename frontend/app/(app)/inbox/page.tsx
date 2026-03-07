/**
 * Unified Inbox Page
 *
 * Multi-channel conversation inbox with handoff panel
 */

"use client";

import { useState } from "react";
import { Inbox as InboxIcon, AlertTriangle, CheckCircle } from "lucide-react";
import { toast } from "sonner";
import { FilterBar } from "@/components/inbox/FilterBar";
import { ConversationList } from "@/components/inbox/ConversationList";
import { ConversationView } from "@/components/inbox/ConversationView";
import { HandoffPanel } from "@/components/inbox/HandoffPanel";
import { HandoffTimeline } from "@/components/inbox/HandoffTimeline";
import {
  useInboxConversations,
  useInboxConversation,
  useEscalateConversation,
} from "@/hooks/useInbox";

export default function InboxPage() {
  const [selectedConversationId, setSelectedConversationId] = useState<string | null>(null);
  const [channel, setChannel] = useState("all");
  const [status, setStatus] = useState("all");
  const [minLeadScore, setMinLeadScore] = useState(0);

  // Fetch conversations with filters
  const { data: conversationsData, isLoading: conversationsLoading } = useInboxConversations({
    channel: channel as any,
    status: status as any,
    min_lead_score: minLeadScore,
    per_page: 50,
  });

  // Fetch selected conversation details
  const { data: conversationDetail, isLoading: conversationLoading } =
    useInboxConversation(selectedConversationId);

  const escalateMutation = useEscalateConversation();

  const conversations = conversationsData?.items || [];
  const selectedConversation = conversationDetail;

  const handleEscalate = async () => {
    if (!selectedConversationId) return;
    try {
      await escalateMutation.mutateAsync(selectedConversationId);
      toast.success("Conversation escalated to human agent");
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Failed to escalate");
    }
  };

  return (
    <div className="h-screen flex flex-col">
      {/* Header */}
      <div className="bg-white border-b border-gray-200 px-6 py-4">
        <div className="flex items-center gap-3">
          <InboxIcon className="w-6 h-6 text-gray-700" />
          <h1 className="text-2xl font-bold text-gray-900">Inbox</h1>
          {conversationsData && (
            <span className="text-sm text-gray-600">
              ({conversationsData.total} conversations)
            </span>
          )}
        </div>
      </div>

      {/* Filters */}
      <FilterBar
        channel={channel}
        status={status}
        minLeadScore={minLeadScore}
        onChannelChange={setChannel}
        onStatusChange={setStatus}
        onLeadScoreChange={setMinLeadScore}
      />

      {/* Main Content: Split Pane */}
      <div className="flex-1 flex overflow-hidden">
        {/* Left: Conversation List */}
        <div className="w-80 border-r border-gray-200 bg-white overflow-hidden flex flex-col">
          {conversationsLoading ? (
            <div className="flex items-center justify-center h-full">
              <p className="text-gray-500">Loading conversations...</p>
            </div>
          ) : (
            <ConversationList
              conversations={conversations}
              selectedId={selectedConversationId}
              onSelect={setSelectedConversationId}
            />
          )}
        </div>

        {/* Right: Conversation Detail */}
        <div className="flex-1 flex flex-col overflow-hidden">
          {!selectedConversationId ? (
            <div className="flex items-center justify-center h-full bg-gray-50">
              <div className="text-center">
                <InboxIcon className="w-16 h-16 text-gray-400 mx-auto mb-4" />
                <p className="text-gray-600">Select a conversation to view messages</p>
              </div>
            </div>
          ) : conversationLoading ? (
            <div className="flex items-center justify-center h-full bg-gray-50">
              <p className="text-gray-500">Loading conversation...</p>
            </div>
          ) : selectedConversation ? (
            <>
              {/* Action Bar */}
              <div className="bg-white border-b border-gray-200 px-4 py-2 flex items-center justify-between">
                <div className="flex items-center gap-2">
                  {selectedConversation.status === "escalated" && (
                    <span className="inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs font-medium bg-red-100 text-red-800">
                      <AlertTriangle className="w-3 h-3" />
                      Escalated
                    </span>
                  )}
                  {selectedConversation.status === "active" && (
                    <span className="inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs font-medium bg-green-100 text-green-800">
                      <CheckCircle className="w-3 h-3" />
                      Active
                    </span>
                  )}
                </div>
                <div className="flex items-center gap-2">
                  {selectedConversation.status === "active" && (
                    <button
                      onClick={handleEscalate}
                      disabled={escalateMutation.isPending}
                      className="px-3 py-1.5 text-xs font-medium text-red-700 bg-red-50 border border-red-200 rounded-md hover:bg-red-100 disabled:opacity-50"
                    >
                      {escalateMutation.isPending ? "Escalating..." : "Escalate to Human"}
                    </button>
                  )}
                </div>
              </div>

              {/* Messages */}
              <div className="flex-1 overflow-hidden">
                <ConversationView
                  messages={selectedConversation.messages}
                  conversationId={selectedConversation.id}
                  channel={selectedConversation.channel}
                  callLog={selectedConversation.call_log}
                />
              </div>

              {/* Handoff Panel + Timeline (only for escalated conversations) */}
              {selectedConversation.status === "escalated" && (
                <div className="max-h-96 overflow-y-auto border-t">
                  <HandoffTimeline conversationId={selectedConversation.id} />
                  <HandoffPanel conversationId={selectedConversation.id} />
                </div>
              )}
            </>
          ) : (
            <div className="flex items-center justify-center h-full bg-gray-50">
              <p className="text-red-600">Conversation not found</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

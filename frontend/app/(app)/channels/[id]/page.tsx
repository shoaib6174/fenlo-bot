/**
 * Channel Detail Page
 *
 * View and edit a specific channel configuration
 */

"use client";

import { useParams, useRouter } from "next/navigation";
import { ArrowLeft, Trash2 } from "lucide-react";
import { toast } from "sonner";
import { WhatsAppSetup } from "@/components/channels/WhatsAppSetup";
import { WidgetSetup } from "@/components/channels/WidgetSetup";
import { useChannel, useDeleteChannel } from "@/hooks/useChannels";

export default function ChannelDetailPage() {
  const params = useParams();
  const router = useRouter();
  const channelId = params.id as string;

  const { data: channel, isLoading } = useChannel(channelId);
  const deleteChannel = useDeleteChannel();

  const handleDelete = async () => {
    if (!confirm("Are you sure you want to delete this channel?")) {
      return;
    }

    try {
      await deleteChannel.mutateAsync(channelId);
      toast.success("Channel deleted successfully");
      router.push("/channels");
    } catch (error) {
      toast.error("Failed to delete channel");
    }
  };

  if (isLoading) {
    return (
      <div className="container mx-auto px-6 py-8">
        <div className="text-center py-12">
          <p className="text-gray-500">Loading channel...</p>
        </div>
      </div>
    );
  }

  if (!channel) {
    return (
      <div className="container mx-auto px-6 py-8">
        <div className="text-center py-12">
          <p className="text-red-600">Channel not found</p>
        </div>
      </div>
    );
  }

  return (
    <div className="container mx-auto px-6 py-8 max-w-4xl">
      {/* Header */}
      <div className="mb-6">
        <button
          onClick={() => router.push("/channels")}
          className="inline-flex items-center gap-2 text-sm text-gray-600 hover:text-gray-900 mb-4"
        >
          <ArrowLeft className="w-4 h-4" />
          Back to Channels
        </button>

        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold text-gray-900 mb-1">
              {channel.channel === "whatsapp" && "WhatsApp Channel"}
              {channel.channel === "widget" && "Website Widget"}
              {channel.channel === "telegram" && "Telegram Bot"}
              {channel.channel === "voice" && "Voice Channel"}
            </h1>
            <p className="text-gray-600">Configure channel settings</p>
          </div>

          <button
            onClick={handleDelete}
            disabled={deleteChannel.isPending}
            className="flex items-center gap-2 px-4 py-2 text-red-600 border border-red-300 rounded-md hover:bg-red-50 disabled:opacity-50"
          >
            <Trash2 className="w-4 h-4" />
            Delete
          </button>
        </div>
      </div>

      {/* Channel Form */}
      <div className="bg-white border border-gray-200 rounded-lg p-6">
        {channel.channel === "whatsapp" && (
          <WhatsAppSetup
            channel={channel}
            onSuccess={() => {
              toast.success("Channel updated");
              router.push("/channels");
            }}
          />
        )}

        {channel.channel === "widget" && (
          <WidgetSetup
            channel={channel}
            workspaceId={channel.workspace_id}
            onSuccess={() => {
              toast.success("Widget updated");
              router.push("/channels");
            }}
          />
        )}

        {channel.channel !== "whatsapp" && channel.channel !== "widget" && (
          <p className="text-gray-600">
            This channel type does not support editing through the UI yet.
          </p>
        )}
      </div>
    </div>
  );
}

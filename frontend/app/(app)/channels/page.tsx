/**
 * Channels Page
 *
 * Manage WhatsApp, Widget, and Webhook integrations
 */

"use client";

import { useState } from "react";
import { Plus, X, Webhook } from "lucide-react";
import { ChannelCard } from "@/components/channels/ChannelCard";
import { WhatsAppSetup } from "@/components/channels/WhatsAppSetup";
import { WidgetSetup } from "@/components/channels/WidgetSetup";
import { TelegramSetup } from "@/components/channels/TelegramSetup";
import { WebhookActionForm } from "@/components/channels/WebhookActionForm";
import { WebhookHistory } from "@/components/channels/WebhookHistory";
import { useChannels } from "@/hooks/useChannels";
import { useWebhookActions } from "@/hooks/useWebhookActions";

type ChannelType = "whatsapp" | "widget" | "telegram" | "webhook" | null;

export default function ChannelsPage() {
  const { data: channels, isLoading: channelsLoading } = useChannels();
  const { data: webhookActions, isLoading: actionsLoading } = useWebhookActions();

  const [showDialog, setShowDialog] = useState(false);
  const [selectedType, setSelectedType] = useState<ChannelType>(null);

  const openDialog = (type: ChannelType) => {
    setSelectedType(type);
    setShowDialog(true);
  };

  const closeDialog = () => {
    setShowDialog(false);
    setSelectedType(null);
  };

  if (channelsLoading) {
    return (
      <div className="container mx-auto px-6 py-8">
        <div className="text-center py-12">
          <p className="text-gray-500">Loading channels...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="container mx-auto px-6 py-8 max-w-6xl">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900 mb-2">Channels</h1>
        <p className="text-gray-600">
          Manage WhatsApp, Telegram, website widget, and webhook integrations
        </p>
      </div>

      {/* Add Channel Actions */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-8">
        <button
          onClick={() => openDialog("whatsapp")}
          className="p-4 border-2 border-dashed border-gray-300 rounded-lg hover:border-blue-400 hover:bg-blue-50 transition-colors text-left"
        >
          <Plus className="w-5 h-5 text-gray-400 mb-2" />
          <p className="font-medium text-gray-900">Add WhatsApp</p>
          <p className="text-sm text-gray-600">Connect via Twilio</p>
        </button>

        <button
          onClick={() => openDialog("telegram")}
          className="p-4 border-2 border-dashed border-gray-300 rounded-lg hover:border-blue-400 hover:bg-blue-50 transition-colors text-left"
        >
          <Plus className="w-5 h-5 text-gray-400 mb-2" />
          <p className="font-medium text-gray-900">Add Telegram</p>
          <p className="text-sm text-gray-600">Connect via BotFather</p>
        </button>

        <button
          onClick={() => openDialog("widget")}
          className="p-4 border-2 border-dashed border-gray-300 rounded-lg hover:border-blue-400 hover:bg-blue-50 transition-colors text-left"
        >
          <Plus className="w-5 h-5 text-gray-400 mb-2" />
          <p className="font-medium text-gray-900">Add Widget</p>
          <p className="text-sm text-gray-600">Embeddable chat</p>
        </button>

        <button
          onClick={() => openDialog("webhook")}
          className="p-4 border-2 border-dashed border-gray-300 rounded-lg hover:border-blue-400 hover:bg-blue-50 transition-colors text-left"
        >
          <Plus className="w-5 h-5 text-gray-400 mb-2" />
          <p className="font-medium text-gray-900">Add Webhook</p>
          <p className="text-sm text-gray-600">Custom integration</p>
        </button>
      </div>

      {/* Active Channels */}
      {channels && channels.length > 0 && (
        <div className="mb-12">
          <h2 className="text-xl font-semibold text-gray-900 mb-4">Active Channels</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {channels.map((channel) => (
              <ChannelCard key={channel.id} channel={channel} />
            ))}
          </div>
        </div>
      )}

      {/* Webhook Actions */}
      {!actionsLoading && webhookActions && webhookActions.length > 0 && (
        <div className="mb-12">
          <h2 className="text-xl font-semibold text-gray-900 mb-4">Webhook Actions</h2>
          <div className="bg-white border border-gray-200 rounded-lg overflow-hidden">
            <table className="w-full">
              <thead className="bg-gray-50 border-b border-gray-200">
                <tr>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                    Event
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                    Target URL
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                    Status
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200">
                {webhookActions.map((action) => (
                  <tr key={action.id} className="hover:bg-gray-50">
                    <td className="px-4 py-3 text-sm text-gray-900">{action.event_type}</td>
                    <td className="px-4 py-3 text-sm text-gray-600 font-mono truncate max-w-md">
                      {action.target_url}
                    </td>
                    <td className="px-4 py-3">
                      {action.is_active ? (
                        <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800">
                          Active
                        </span>
                      ) : (
                        <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-600">
                          Inactive
                        </span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Webhook Delivery History */}
      {!actionsLoading && webhookActions && webhookActions.length > 0 && (
        <WebhookHistory />
      )}

      {/* Empty State */}
      {channels && channels.length === 0 && (!webhookActions || webhookActions.length === 0) && (
        <div className="text-center py-12">
          <Webhook className="w-16 h-16 text-gray-400 mx-auto mb-4" />
          <h3 className="text-lg font-medium text-gray-900 mb-2">No channels configured</h3>
          <p className="text-gray-600 mb-6">
            Get started by adding your first channel integration
          </p>
        </div>
      )}

      {/* Dialog */}
      {showDialog && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-lg max-w-2xl w-full max-h-[90vh] overflow-y-auto">
            <div className="sticky top-0 bg-white border-b border-gray-200 px-6 py-4 flex items-center justify-between">
              <h2 className="text-lg font-semibold text-gray-900">
                {selectedType === "whatsapp" && "Add WhatsApp Channel"}
                {selectedType === "telegram" && "Add Telegram Channel"}
                {selectedType === "widget" && "Add Website Widget"}
                {selectedType === "webhook" && "Add Webhook Action"}
              </h2>
              <button
                onClick={closeDialog}
                className="text-gray-400 hover:text-gray-600"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="p-6">
              {selectedType === "whatsapp" && <WhatsAppSetup onSuccess={closeDialog} />}
              {selectedType === "telegram" && <TelegramSetup onSuccess={closeDialog} />}
              {selectedType === "widget" && <WidgetSetup onSuccess={closeDialog} />}
              {selectedType === "webhook" && <WebhookActionForm onSuccess={closeDialog} />}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

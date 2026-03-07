/**
 * WebhookActionForm Component
 *
 * Form for creating/editing webhook actions
 */

"use client";

import { useState } from "react";
import { Webhook, Save } from "lucide-react";
import { toast } from "sonner";
import {
  useCreateWebhookAction,
  useUpdateWebhookAction,
} from "@/hooks/useWebhookActions";
import type { WebhookAction } from "@/lib/api";

interface WebhookActionFormProps {
  action?: WebhookAction;
  onSuccess?: () => void;
}

const EVENT_TYPES = [
  { value: "conversation.created", label: "Conversation Created" },
  { value: "conversation.escalated", label: "Conversation Escalated" },
  { value: "conversation.closed", label: "Conversation Closed" },
  { value: "lead.qualified", label: "Lead Qualified" },
  { value: "message.received", label: "Message Received" },
  { value: "message.sent", label: "Message Sent" },
];

const DEFAULT_PAYLOAD_TEMPLATE = `{
  "event": "{event_type}",
  "workspace": "{workspace_id}",
  "conversation": "{conversation_id}",
  "lead_score": {lead_score},
  "timestamp": "{timestamp}"
}`;

export function WebhookActionForm({ action, onSuccess }: WebhookActionFormProps) {
  const isEditing = !!action;

  const [formData, setFormData] = useState({
    event_type: action?.event_type || "",
    target_url: action?.target_url || "",
    headers: action?.headers || {},
    payload_template: action?.payload_template || DEFAULT_PAYLOAD_TEMPLATE,
    is_active: action?.is_active !== undefined ? action.is_active : true,
  });

  const [headerKey, setHeaderKey] = useState("");
  const [headerValue, setHeaderValue] = useState("");

  const createAction = useCreateWebhookAction();
  const updateAction = useUpdateWebhookAction();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!formData.event_type || !formData.target_url) {
      toast.error("Event type and target URL are required");
      return;
    }

    try {
      if (isEditing) {
        await updateAction.mutateAsync({
          id: action.id,
          data: formData,
        });
        toast.success("Webhook action updated");
      } else {
        await createAction.mutateAsync(formData);
        toast.success("Webhook action created");
      }

      onSuccess?.();
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Failed to save webhook action");
    }
  };

  const addHeader = () => {
    if (!headerKey.trim()) return;

    setFormData({
      ...formData,
      headers: { ...formData.headers, [headerKey]: headerValue },
    });
    setHeaderKey("");
    setHeaderValue("");
  };

  const removeHeader = (key: string) => {
    const { [key]: _, ...rest } = formData.headers;
    setFormData({ ...formData, headers: rest });
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-6">
      <div className="flex items-center gap-3 pb-4 border-b">
        <div className="p-2 rounded-lg bg-purple-50">
          <Webhook className="w-6 h-6 text-purple-600" />
        </div>
        <div>
          <h2 className="text-lg font-semibold text-gray-900">
            {isEditing ? "Edit" : "Add"} Webhook Action
          </h2>
          <p className="text-sm text-gray-600">Trigger webhooks on specific events</p>
        </div>
      </div>

      {/* Event Type */}
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">
          Event Type <span className="text-red-500">*</span>
        </label>
        <select
          required
          value={formData.event_type}
          onChange={(e) => setFormData({ ...formData, event_type: e.target.value })}
          className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent"
        >
          <option value="">Select an event...</option>
          {EVENT_TYPES.map((event) => (
            <option key={event.value} value={event.value}>
              {event.label}
            </option>
          ))}
        </select>
      </div>

      {/* Target URL */}
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">
          Target URL <span className="text-red-500">*</span>
        </label>
        <input
          type="url"
          required
          value={formData.target_url}
          onChange={(e) => setFormData({ ...formData, target_url: e.target.value })}
          className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          placeholder="https://hooks.example.com/webhook"
        />
      </div>

      {/* Headers */}
      <div className="space-y-3">
        <label className="block text-sm font-medium text-gray-700">Headers (Optional)</label>

        <div className="flex gap-2">
          <input
            type="text"
            value={headerKey}
            onChange={(e) => setHeaderKey(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter") {
                e.preventDefault();
                addHeader();
              }
            }}
            className="flex-1 px-3 py-2 border border-gray-300 rounded-md text-sm"
            placeholder="Header name (e.g., Authorization)"
          />
          <input
            type="text"
            value={headerValue}
            onChange={(e) => setHeaderValue(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter") {
                e.preventDefault();
                addHeader();
              }
            }}
            className="flex-1 px-3 py-2 border border-gray-300 rounded-md text-sm"
            placeholder="Header value"
          />
          <button
            type="button"
            onClick={addHeader}
            className="px-4 py-2 bg-gray-100 text-gray-700 rounded-md hover:bg-gray-200 text-sm"
          >
            Add
          </button>
        </div>

        {Object.keys(formData.headers).length > 0 && (
          <div className="bg-gray-50 border border-gray-200 rounded-md p-3 space-y-2">
            {Object.entries(formData.headers).map(([key, value]) => (
              <div key={key} className="flex items-center justify-between text-sm">
                <code className="text-xs bg-white px-2 py-1 rounded border">
                  {key}: {value}
                </code>
                <button
                  type="button"
                  onClick={() => removeHeader(key)}
                  className="text-red-600 hover:text-red-800"
                >
                  Remove
                </button>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Payload Template */}
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">
          Payload Template (Optional)
        </label>
        <textarea
          rows={8}
          value={formData.payload_template}
          onChange={(e) => setFormData({ ...formData, payload_template: e.target.value })}
          className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent font-mono text-sm"
          placeholder={DEFAULT_PAYLOAD_TEMPLATE}
        />
        <p className="text-xs text-gray-500 mt-1">
          Available variables: {"{event_type}"}, {"{workspace_id}"}, {"{conversation_id}"},{" "}
          {"{lead_score}"}, {"{timestamp}"}, {"{message_content}"}, {"{sentiment}"},{" "}
          {"{intent}"}
        </p>
      </div>

      {/* Active Toggle */}
      <div className="flex items-center gap-3">
        <input
          type="checkbox"
          id="is_active"
          checked={formData.is_active}
          onChange={(e) => setFormData({ ...formData, is_active: e.target.checked })}
          className="w-4 h-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500"
        />
        <label htmlFor="is_active" className="text-sm font-medium text-gray-700">
          Active (send webhooks for this action)
        </label>
      </div>

      {/* Submit */}
      <div className="flex justify-end gap-3 pt-4 border-t">
        <button
          type="submit"
          disabled={createAction.isPending || updateAction.isPending}
          className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          <Save className="w-4 h-4" />
          {createAction.isPending || updateAction.isPending
            ? "Saving..."
            : isEditing
              ? "Save Changes"
              : "Create Action"}
        </button>
      </div>
    </form>
  );
}

"use client";

import { useState, useEffect, useCallback } from "react";
import {
  Zap,
  Plus,
  Trash2,
  Send,
  CheckCircle,
  XCircle,
  Loader2,
  ExternalLink,
  Clock,
} from "lucide-react";

interface TriggerInfo {
  event: string;
  label: string;
  description: string;
}

interface Subscription {
  id: string;
  event: string;
  hook_url: string;
  created_at: string;
}

interface DeliveryEntry {
  id: string;
  event_type: string;
  target_url: string;
  status: string;
  created_at: string;
  sent_at: string | null;
  error_message: string | null;
  retry_count: number;
}

const API_URL = process.env.NEXT_PUBLIC_API_URL || "";

export function WebhookTriggersPanel() {
  const [triggers, setTriggers] = useState<TriggerInfo[]>([]);
  const [subscriptions, setSubscriptions] = useState<Subscription[]>([]);
  const [history, setHistory] = useState<DeliveryEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [showAddForm, setShowAddForm] = useState(false);
  const [newEvent, setNewEvent] = useState("");
  const [newUrl, setNewUrl] = useState("");
  const [adding, setAdding] = useState(false);
  const [testingId, setTestingId] = useState<string | null>(null);
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [message, setMessage] = useState<{
    type: "success" | "error";
    text: string;
  } | null>(null);

  const fetchData = useCallback(async () => {
    try {
      const [triggersRes, subsRes, historyRes] = await Promise.all([
        fetch(`${API_URL}/api/v1/webhooks/triggers`, {
          credentials: "include",
        }),
        fetch(`${API_URL}/api/v1/webhooks/subscriptions`, {
          credentials: "include",
        }),
        fetch(`${API_URL}/api/v1/webhook-actions/history?per_page=10`, {
          credentials: "include",
        }),
      ]);

      if (triggersRes.ok) {
        setTriggers(await triggersRes.json());
      }
      if (subsRes.ok) {
        setSubscriptions(await subsRes.json());
      }
      if (historyRes.ok) {
        const data = await historyRes.json();
        setHistory(data.items || []);
      }
    } catch {
      // Silent fail — panel shows empty state
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const handleAdd = async () => {
    if (!newEvent || !newUrl) return;
    setAdding(true);
    setMessage(null);

    try {
      const res = await fetch(`${API_URL}/api/v1/webhooks/subscribe`, {
        method: "POST",
        credentials: "include",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ hookUrl: newUrl, event: newEvent }),
      });

      if (res.ok) {
        setMessage({ type: "success", text: "Webhook subscription created" });
        setShowAddForm(false);
        setNewEvent("");
        setNewUrl("");
        await fetchData();
      } else {
        const err = await res.json();
        setMessage({
          type: "error",
          text: err?.detail?.error?.message || "Failed to create subscription",
        });
      }
    } catch {
      setMessage({ type: "error", text: "Network error" });
    } finally {
      setAdding(false);
    }
  };

  const handleDelete = async (id: string) => {
    setDeletingId(id);
    try {
      const res = await fetch(`${API_URL}/api/v1/webhooks/subscribe/${id}`, {
        method: "DELETE",
        credentials: "include",
      });

      if (res.ok || res.status === 204) {
        setMessage({ type: "success", text: "Subscription removed" });
        await fetchData();
      } else {
        setMessage({ type: "error", text: "Failed to remove subscription" });
      }
    } catch {
      setMessage({ type: "error", text: "Network error" });
    } finally {
      setDeletingId(null);
    }
  };

  const handleTest = async (sub: Subscription) => {
    setTestingId(sub.id);
    setMessage(null);

    try {
      const sampleRes = await fetch(
        `${API_URL}/api/v1/webhooks/sample/${sub.event}`,
        { credentials: "include" }
      );

      if (sampleRes.ok) {
        setMessage({
          type: "success",
          text: `Sample payload fetched for "${sub.event}". In production, this would POST to your URL.`,
        });
      } else {
        setMessage({ type: "error", text: "Failed to fetch sample payload" });
      }
    } catch {
      setMessage({ type: "error", text: "Network error" });
    } finally {
      setTestingId(null);
    }
  };

  const statusBadge = (status: string) => {
    switch (status) {
      case "sent":
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 bg-green-50 text-green-700 rounded-full text-xs font-medium">
            <CheckCircle className="w-3 h-3" />
            Sent
          </span>
        );
      case "failed":
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 bg-red-50 text-red-700 rounded-full text-xs font-medium">
            <XCircle className="w-3 h-3" />
            Failed
          </span>
        );
      case "dead":
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 bg-gray-100 text-gray-600 rounded-full text-xs font-medium">
            <XCircle className="w-3 h-3" />
            Dead
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 bg-yellow-50 text-yellow-700 rounded-full text-xs font-medium">
            <Clock className="w-3 h-3" />
            Pending
          </span>
        );
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader2 className="w-6 h-6 animate-spin text-gray-400" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-lg font-semibold text-gray-900">
            Webhook Triggers
          </h2>
          <p className="text-sm text-gray-600 mt-1">
            Connect Fenlo AI events to external services like Zapier, Make, or
            custom webhooks.
          </p>
        </div>
        <button
          onClick={() => setShowAddForm(!showAddForm)}
          className="inline-flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 transition"
        >
          <Plus className="w-4 h-4" />
          Add Webhook
        </button>
      </div>

      {/* Message */}
      {message && (
        <div
          className={`p-3 rounded-lg text-sm ${
            message.type === "success"
              ? "bg-green-50 text-green-700 border border-green-200"
              : "bg-red-50 text-red-700 border border-red-200"
          }`}
        >
          {message.text}
        </div>
      )}

      {/* Add Form */}
      {showAddForm && (
        <div className="bg-gray-50 border border-gray-200 rounded-lg p-4 space-y-4">
          <h3 className="text-sm font-semibold text-gray-900">
            New Webhook Subscription
          </h3>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Trigger Event
            </label>
            <select
              value={newEvent}
              onChange={(e) => setNewEvent(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              data-testid="webhook-event-select"
            >
              <option value="">Select an event...</option>
              {triggers.map((t) => (
                <option key={t.event} value={t.event}>
                  {t.label} — {t.description}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Webhook URL
            </label>
            <input
              type="url"
              value={newUrl}
              onChange={(e) => setNewUrl(e.target.value)}
              placeholder="https://hooks.zapier.com/hooks/catch/..."
              className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              data-testid="webhook-url-input"
            />
          </div>

          <div className="flex gap-2">
            <button
              onClick={handleAdd}
              disabled={adding || !newEvent || !newUrl}
              className="inline-flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 transition disabled:opacity-50"
              data-testid="webhook-add-button"
            >
              {adding ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <Zap className="w-4 h-4" />
              )}
              Subscribe
            </button>
            <button
              onClick={() => {
                setShowAddForm(false);
                setNewEvent("");
                setNewUrl("");
              }}
              className="px-4 py-2 text-gray-600 hover:text-gray-800 text-sm transition"
            >
              Cancel
            </button>
          </div>
        </div>
      )}

      {/* Active Subscriptions */}
      <div>
        <h3 className="text-sm font-semibold text-gray-900 mb-3">
          Active Subscriptions ({subscriptions.length})
        </h3>

        {subscriptions.length === 0 ? (
          <div className="text-center py-8 bg-gray-50 rounded-lg border border-gray-200">
            <Zap className="w-8 h-8 text-gray-300 mx-auto mb-2" />
            <p className="text-sm text-gray-500">No webhook subscriptions yet</p>
            <p className="text-xs text-gray-400 mt-1">
              Add a webhook to start receiving events
            </p>
          </div>
        ) : (
          <div className="space-y-2">
            {subscriptions.map((sub) => (
              <div
                key={sub.id}
                className="flex items-center justify-between p-3 bg-white border border-gray-200 rounded-lg"
                data-testid={`subscription-${sub.id}`}
              >
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1">
                    <span className="inline-flex items-center gap-1 px-2 py-0.5 bg-blue-50 text-blue-700 rounded text-xs font-medium">
                      <Zap className="w-3 h-3" />
                      {sub.event}
                    </span>
                    <span className="text-xs text-gray-400">
                      {new Date(sub.created_at).toLocaleDateString()}
                    </span>
                  </div>
                  <p className="text-xs text-gray-500 truncate">{sub.hook_url}</p>
                </div>
                <div className="flex items-center gap-1 ml-3">
                  <button
                    onClick={() => handleTest(sub)}
                    disabled={testingId === sub.id}
                    className="p-1.5 text-gray-400 hover:text-blue-600 hover:bg-blue-50 rounded transition"
                    title="Test trigger"
                    data-testid={`test-${sub.id}`}
                  >
                    {testingId === sub.id ? (
                      <Loader2 className="w-4 h-4 animate-spin" />
                    ) : (
                      <Send className="w-4 h-4" />
                    )}
                  </button>
                  <button
                    onClick={() => handleDelete(sub.id)}
                    disabled={deletingId === sub.id}
                    className="p-1.5 text-gray-400 hover:text-red-600 hover:bg-red-50 rounded transition"
                    title="Remove subscription"
                    data-testid={`delete-${sub.id}`}
                  >
                    {deletingId === sub.id ? (
                      <Loader2 className="w-4 h-4 animate-spin" />
                    ) : (
                      <Trash2 className="w-4 h-4" />
                    )}
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Recent Deliveries */}
      <div>
        <h3 className="text-sm font-semibold text-gray-900 mb-3">
          Recent Deliveries
        </h3>

        {history.length === 0 ? (
          <p className="text-sm text-gray-500 py-4 text-center bg-gray-50 rounded-lg border border-gray-200">
            No deliveries yet
          </p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-200">
                  <th className="text-left py-2 px-3 text-xs font-medium text-gray-500 uppercase">
                    Event
                  </th>
                  <th className="text-left py-2 px-3 text-xs font-medium text-gray-500 uppercase">
                    Status
                  </th>
                  <th className="text-left py-2 px-3 text-xs font-medium text-gray-500 uppercase">
                    URL
                  </th>
                  <th className="text-left py-2 px-3 text-xs font-medium text-gray-500 uppercase">
                    Time
                  </th>
                </tr>
              </thead>
              <tbody>
                {history.map((entry) => (
                  <tr
                    key={entry.id}
                    className="border-b border-gray-100 hover:bg-gray-50"
                  >
                    <td className="py-2 px-3 text-gray-700 font-medium">
                      {entry.event_type}
                    </td>
                    <td className="py-2 px-3">{statusBadge(entry.status)}</td>
                    <td className="py-2 px-3 text-gray-500 truncate max-w-[200px]">
                      {entry.target_url}
                    </td>
                    <td className="py-2 px-3 text-gray-400 whitespace-nowrap">
                      {new Date(entry.created_at).toLocaleString()}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Zapier integration hint */}
      <div className="bg-amber-50 border border-amber-200 rounded-lg p-4 flex items-start gap-3">
        <Zap className="w-5 h-5 text-amber-600 flex-shrink-0 mt-0.5" />
        <div>
          <p className="text-sm font-medium text-amber-800">
            Works with Zapier, Make, and custom webhooks
          </p>
          <p className="text-xs text-amber-600 mt-1">
            Use the subscribe endpoint to connect Fenlo AI events to 5000+ apps.
            Each event delivers a JSON payload to your webhook URL.
          </p>
          <a
            href="/docs/zapier-integration"
            className="inline-flex items-center gap-1 text-xs text-amber-700 hover:text-amber-900 font-medium mt-2 transition"
          >
            View Integration Guide
            <ExternalLink className="w-3 h-3" />
          </a>
        </div>
      </div>
    </div>
  );
}

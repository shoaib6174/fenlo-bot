"use client";

import { useState } from "react";
import {
  Key,
  Plus,
  Copy,
  Trash2,
  CheckCircle,
  XCircle,
  Loader2,
  Shield,
  Eye,
  MessageSquare,
  Clock,
} from "lucide-react";
import { useSettingsFetch } from "@/hooks/useSettingsFetch";
import { apiClient } from "@/lib/api";

interface APIKeyItem {
  id: string;
  name: string;
  prefix: string;
  scopes: string[];
  rate_limit: number;
  is_revoked: boolean;
  last_used_at: string | null;
  request_count: number;
  created_at: string;
}

interface NewKeyResponse {
  id: string;
  name: string;
  key: string;
  prefix: string;
  scopes: string[];
  rate_limit: number;
  created_at: string;
}

const SCOPE_INFO = [
  { key: "read", label: "Read", description: "View conversations, analytics, and documents", icon: Eye },
  { key: "chat", label: "Chat", description: "Send messages and create conversations", icon: MessageSquare },
  { key: "admin", label: "Admin", description: "Full access including settings and key management", icon: Shield },
];

export function APIKeysPanel() {
  const { data: keys, setData: setKeys, loading, refetch: fetchKeys } = useSettingsFetch<APIKeyItem[]>(
    "/api/v1/api-keys",
    []
  );
  const [creating, setCreating] = useState(false);
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [newKeyName, setNewKeyName] = useState("");
  const [newKeyScopes, setNewKeyScopes] = useState<string[]>(["read", "chat"]);
  const [newKeyResult, setNewKeyResult] = useState<NewKeyResponse | null>(null);
  const [copied, setCopied] = useState(false);
  const [message, setMessage] = useState<{ type: "success" | "error"; text: string } | null>(null);
  const [confirmRevoke, setConfirmRevoke] = useState<string | null>(null);

  const handleCreate = async () => {
    if (!newKeyName.trim()) {
      setMessage({ type: "error", text: "Enter a name for the API key" });
      return;
    }

    setCreating(true);
    setMessage(null);

    try {
      const data = await apiClient<NewKeyResponse>("/api/v1/api-keys", {
        method: "POST",
        body: JSON.stringify({
          name: newKeyName.trim(),
          scopes: newKeyScopes,
        }),
      });
      setNewKeyResult(data);
      setMessage({ type: "success", text: "API key created! Copy it now — it won't be shown again." });
      await fetchKeys();
    } catch (e) {
      setMessage({ type: "error", text: e instanceof Error ? e.message : "Failed to create API key" });
    } finally {
      setCreating(false);
    }
  };

  const handleCopy = async (key: string) => {
    try {
      await navigator.clipboard.writeText(key);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // Fallback for non-HTTPS
      const input = document.createElement("input");
      input.value = key;
      document.body.appendChild(input);
      input.select();
      document.execCommand("copy");
      document.body.removeChild(input);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  const handleRevoke = async (keyId: string) => {
    try {
      await apiClient(`/api/v1/api-keys/${keyId}`, { method: "DELETE" });
      setMessage({ type: "success", text: "API key revoked" });
      setConfirmRevoke(null);
      await fetchKeys();
    } catch {
      setMessage({ type: "error", text: "Failed to revoke API key" });
    }
  };

  const toggleScope = (scope: string) => {
    setNewKeyScopes((prev) =>
      prev.includes(scope) ? prev.filter((s) => s !== scope) : [...prev, scope]
    );
  };

  const resetCreateForm = () => {
    setShowCreateForm(false);
    setNewKeyName("");
    setNewKeyScopes(["read", "chat"]);
    setNewKeyResult(null);
    setMessage(null);
  };

  const formatDate = (iso: string) => {
    return new Date(iso).toLocaleDateString("en-US", {
      month: "short",
      day: "numeric",
      year: "numeric",
    });
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
          <h2 className="text-lg font-semibold text-gray-900 flex items-center gap-2">
            <Key className="w-5 h-5 text-blue-600" />
            API Keys
          </h2>
          <p className="text-sm text-gray-600 mt-1">
            Create API keys for programmatic access via Postman, curl, or custom integrations.
          </p>
        </div>
        {!showCreateForm && (
          <button
            onClick={() => setShowCreateForm(true)}
            className="inline-flex items-center gap-1.5 px-3 py-2 bg-blue-600 text-white rounded-md text-sm font-medium hover:bg-blue-700 transition"
            data-testid="create-key-btn"
          >
            <Plus className="w-4 h-4" />
            Create Key
          </button>
        )}
      </div>

      {/* Create Key Form */}
      {showCreateForm && (
        <div className="border border-blue-200 bg-blue-50 rounded-lg p-4 space-y-4" data-testid="create-key-form">
          {!newKeyResult ? (
            <>
              <h3 className="text-sm font-semibold text-gray-900">Create New API Key</h3>

              <div>
                <label htmlFor="key-name" className="block text-sm font-medium text-gray-700 mb-1">
                  Key Name
                </label>
                <input
                  id="key-name"
                  type="text"
                  value={newKeyName}
                  onChange={(e) => setNewKeyName(e.target.value)}
                  placeholder="e.g., Production Server, Postman Testing"
                  className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent bg-white"
                  data-testid="key-name-input"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Access Scopes
                </label>
                <div className="space-y-2">
                  {SCOPE_INFO.map((scope) => (
                    <label
                      key={scope.key}
                      className="flex items-center gap-3 p-2 bg-white border border-gray-200 rounded-md cursor-pointer hover:bg-gray-50"
                    >
                      <input
                        type="checkbox"
                        checked={newKeyScopes.includes(scope.key)}
                        onChange={() => toggleScope(scope.key)}
                        className="w-4 h-4 text-blue-600 rounded border-gray-300"
                      />
                      <scope.icon className="w-4 h-4 text-gray-500" />
                      <div>
                        <span className="text-sm font-medium text-gray-900">{scope.label}</span>
                        <span className="text-xs text-gray-500 ml-2">{scope.description}</span>
                      </div>
                    </label>
                  ))}
                </div>
              </div>

              <div className="flex gap-2">
                <button
                  onClick={handleCreate}
                  disabled={creating || !newKeyName.trim()}
                  className="inline-flex items-center gap-1.5 px-3 py-2 bg-blue-600 text-white rounded-md text-sm font-medium hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition"
                  data-testid="confirm-create-btn"
                >
                  {creating ? <Loader2 className="w-4 h-4 animate-spin" /> : <Key className="w-4 h-4" />}
                  {creating ? "Creating..." : "Create Key"}
                </button>
                <button
                  onClick={resetCreateForm}
                  className="px-3 py-2 text-gray-700 bg-white border border-gray-300 rounded-md text-sm font-medium hover:bg-gray-50 transition"
                >
                  Cancel
                </button>
              </div>
            </>
          ) : (
            /* New Key Created — Show Once */
            <div className="space-y-3" data-testid="new-key-display">
              <h3 className="text-sm font-semibold text-green-800">
                API Key Created Successfully
              </h3>
              <p className="text-xs text-amber-700 bg-amber-50 border border-amber-200 p-2 rounded">
                Copy this key now. For security, it will not be shown again.
              </p>

              <div className="flex items-center gap-2">
                <code
                  className="flex-1 px-3 py-2 bg-gray-900 text-green-400 rounded-md text-sm font-mono select-all"
                  data-testid="new-key-value"
                >
                  {newKeyResult.key}
                </code>
                <button
                  onClick={() => handleCopy(newKeyResult.key)}
                  className={`inline-flex items-center gap-1.5 px-3 py-2 rounded-md text-sm font-medium transition ${
                    copied
                      ? "bg-green-600 text-white"
                      : "bg-white border border-gray-300 text-gray-700 hover:bg-gray-50"
                  }`}
                  data-testid="copy-key-btn"
                >
                  {copied ? <CheckCircle className="w-4 h-4" /> : <Copy className="w-4 h-4" />}
                  {copied ? "Copied!" : "Copy"}
                </button>
              </div>

              <button
                onClick={resetCreateForm}
                className="text-sm text-blue-600 hover:underline"
              >
                Done
              </button>
            </div>
          )}
        </div>
      )}

      {/* Status Message */}
      {message && !showCreateForm && (
        <div
          className={`flex items-center gap-2 p-3 rounded-lg text-sm ${
            message.type === "success"
              ? "bg-green-50 text-green-800 border border-green-200"
              : "bg-red-50 text-red-800 border border-red-200"
          }`}
          data-testid="api-key-status"
        >
          {message.type === "success" ? (
            <CheckCircle className="w-4 h-4 flex-shrink-0" />
          ) : (
            <XCircle className="w-4 h-4 flex-shrink-0" />
          )}
          {message.text}
        </div>
      )}

      {/* Keys List */}
      {keys.length === 0 ? (
        <div className="text-center py-12 bg-gray-50 border border-gray-200 rounded-lg" data-testid="empty-keys">
          <Key className="w-10 h-10 text-gray-300 mx-auto mb-3" />
          <p className="text-sm text-gray-500">No API keys created yet</p>
          <p className="text-xs text-gray-400 mt-1">Create a key to access the API programmatically</p>
        </div>
      ) : (
        <div className="space-y-3" data-testid="keys-list">
          {keys.map((key) => (
            <div
              key={key.id}
              className={`p-4 border rounded-lg ${
                key.is_revoked
                  ? "bg-gray-50 border-gray-200 opacity-60"
                  : "bg-white border-gray-200"
              }`}
              data-testid={`key-item-${key.id}`}
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <Key className={`w-4 h-4 ${key.is_revoked ? "text-gray-400" : "text-blue-500"}`} />
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="text-sm font-medium text-gray-900">{key.name}</span>
                      {key.is_revoked && (
                        <span className="px-1.5 py-0.5 bg-red-100 text-red-700 text-xs rounded font-medium">
                          Revoked
                        </span>
                      )}
                    </div>
                    <div className="flex items-center gap-3 mt-0.5">
                      <code className="text-xs text-gray-500 font-mono">{key.prefix}</code>
                      <span className="text-xs text-gray-400 flex items-center gap-1">
                        <Clock className="w-3 h-3" />
                        Created {formatDate(key.created_at)}
                      </span>
                      {key.last_used_at && (
                        <span className="text-xs text-gray-400">
                          Last used {formatDate(key.last_used_at)}
                        </span>
                      )}
                      <span className="text-xs text-gray-400">
                        {key.request_count.toLocaleString()} requests
                      </span>
                    </div>
                  </div>
                </div>

                <div className="flex items-center gap-2">
                  {/* Scope badges */}
                  <div className="flex gap-1">
                    {key.scopes.map((scope) => (
                      <span
                        key={scope}
                        className="px-2 py-0.5 bg-blue-50 text-blue-700 text-xs rounded-full font-medium"
                      >
                        {scope}
                      </span>
                    ))}
                  </div>

                  {/* Revoke button */}
                  {!key.is_revoked && (
                    <>
                      {confirmRevoke === key.id ? (
                        <div className="flex items-center gap-1">
                          <button
                            onClick={() => handleRevoke(key.id)}
                            className="px-2 py-1 bg-red-600 text-white text-xs rounded font-medium hover:bg-red-700 transition"
                            data-testid={`confirm-revoke-${key.id}`}
                          >
                            Confirm
                          </button>
                          <button
                            onClick={() => setConfirmRevoke(null)}
                            className="px-2 py-1 bg-gray-200 text-gray-700 text-xs rounded font-medium hover:bg-gray-300 transition"
                          >
                            Cancel
                          </button>
                        </div>
                      ) : (
                        <button
                          onClick={() => setConfirmRevoke(key.id)}
                          className="p-1.5 text-gray-400 hover:text-red-600 hover:bg-red-50 rounded transition"
                          title="Revoke key"
                          data-testid={`revoke-btn-${key.id}`}
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      )}
                    </>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Usage Info */}
      <div className="text-xs text-gray-500 space-y-1 border-t border-gray-200 pt-4">
        <p>
          <strong>Authentication:</strong> Pass your API key as{" "}
          <code className="bg-gray-100 px-1 py-0.5 rounded">Authorization: Bearer bf_live_xxx</code>{" "}
          or <code className="bg-gray-100 px-1 py-0.5 rounded">X-API-Key: bf_live_xxx</code>
        </p>
        <p>
          <strong>Rate limit:</strong> 100 requests/minute per key.{" "}
          <strong>Format:</strong> <code className="bg-gray-100 px-1 py-0.5 rounded">bf_live_</code> + 24 characters.
        </p>
      </div>
    </div>
  );
}

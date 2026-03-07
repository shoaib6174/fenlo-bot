"use client";

import { useState, useEffect, useCallback } from "react";
import {
  AlertTriangle,
  Plus,
  Pencil,
  Trash2,
  Shield,
} from "lucide-react";
import { apiClient } from "@/lib/api";
import type { EscalationRuleResponse } from "@/types/voice";

interface EscalationRulesListProps {
  onEdit: (rule: EscalationRuleResponse) => void;
  onCreate: () => void;
  refreshKey?: number;
}

function RuleTypeBadge({ type }: { type: string }) {
  const colors: Record<string, string> = {
    keyword: "bg-blue-100 text-blue-700",
    sentiment: "bg-purple-100 text-purple-700",
    confidence: "bg-amber-100 text-amber-700",
    intent: "bg-green-100 text-green-700",
    business_hours: "bg-gray-100 text-gray-700",
  };
  return (
    <span
      className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${
        colors[type] || "bg-gray-100 text-gray-600"
      }`}
    >
      {type.replace("_", " ")}
    </span>
  );
}

function ActionBadge({ action }: { action: string }) {
  const colors: Record<string, string> = {
    escalate: "bg-red-100 text-red-700",
    notify: "bg-amber-100 text-amber-700",
    log: "bg-gray-100 text-gray-600",
  };
  return (
    <span
      className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${
        colors[action] || "bg-gray-100 text-gray-600"
      }`}
    >
      {action}
    </span>
  );
}

function conditionSummary(rule: EscalationRuleResponse): string {
  const c = rule.condition;
  switch (rule.rule_type) {
    case "keyword": {
      const kw = c.keywords as string[] | undefined;
      return kw ? kw.join(", ") : "—";
    }
    case "sentiment":
      return `threshold: ${String(c.threshold || "—")}`;
    case "confidence":
      return `min: ${String(c.min_confidence ?? "—")}`;
    case "intent": {
      const intents = c.intents as string[] | undefined;
      return intents ? intents.join(", ") : "—";
    }
    case "business_hours":
      return `${String(c.start || "?")}–${String(c.end || "?")} ${String(c.timezone || "")}`;
    default:
      return JSON.stringify(c);
  }
}

export function EscalationRulesList({
  onEdit,
  onCreate,
  refreshKey,
}: EscalationRulesListProps) {
  const [rules, setRules] = useState<EscalationRuleResponse[]>([]);
  const [loading, setLoading] = useState(true);

  const fetchRules = useCallback(async () => {
    try {
      const data = await apiClient<EscalationRuleResponse[]>(
        "/api/v1/voice/escalation-rules"
      );
      // Sort by priority descending
      data.sort((a, b) => b.priority - a.priority);
      setRules(data);
    } catch {
      setRules([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchRules();
  }, [fetchRules, refreshKey]);

  const handleToggle = async (rule: EscalationRuleResponse) => {
    try {
      await apiClient(`/api/v1/voice/escalation-rules/${rule.id}`, {
        method: "PATCH",
        body: JSON.stringify({ is_active: !rule.is_active }),
      });
      fetchRules();
    } catch (err) {
      console.error("Failed to toggle rule:", err);
    }
  };

  const handleDelete = async (rule: EscalationRuleResponse) => {
    if (!confirm("Delete this escalation rule?")) return;
    try {
      await apiClient(`/api/v1/voice/escalation-rules/${rule.id}`, {
        method: "DELETE",
      });
      fetchRules();
    } catch (err) {
      console.error("Failed to delete rule:", err);
    }
  };

  if (loading) {
    return (
      <div className="space-y-3 mt-4">
        {[1, 2, 3].map((i) => (
          <div
            key={i}
            className="bg-white border border-gray-200 rounded-lg p-4 animate-pulse"
          >
            <div className="h-4 bg-gray-200 rounded w-1/3 mb-2" />
            <div className="h-3 bg-gray-200 rounded w-2/3" />
          </div>
        ))}
      </div>
    );
  }

  return (
    <div className="mt-4 space-y-4">
      {/* Header with Create button */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Shield className="w-5 h-5 text-gray-500" />
          <h3 className="text-sm font-semibold text-gray-900">
            Escalation Rules ({rules.length})
          </h3>
        </div>
        <button
          onClick={onCreate}
          className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700 transition"
        >
          <Plus className="w-4 h-4" />
          Add Rule
        </button>
      </div>

      {rules.length === 0 ? (
        <div className="bg-white border border-gray-200 rounded-lg p-8 text-center">
          <AlertTriangle className="w-8 h-8 text-gray-300 mx-auto mb-3" />
          <p className="text-sm text-gray-500 mb-1">No escalation rules yet</p>
          <p className="text-xs text-gray-400">
            Create rules to automatically escalate calls based on keywords,
            sentiment, or other conditions.
          </p>
        </div>
      ) : (
        <div className="bg-white border border-gray-200 rounded-lg divide-y divide-gray-200">
          {rules.map((rule) => (
            <div
              key={rule.id}
              className="flex items-center gap-4 p-4 hover:bg-gray-50 transition"
            >
              {/* Active toggle */}
              <button
                onClick={() => handleToggle(rule)}
                className={`relative w-10 h-5 rounded-full transition-colors ${
                  rule.is_active ? "bg-green-500" : "bg-gray-300"
                }`}
                title={rule.is_active ? "Active" : "Inactive"}
              >
                <span
                  className={`absolute top-0.5 left-0.5 w-4 h-4 bg-white rounded-full shadow transition-transform ${
                    rule.is_active ? "translate-x-5" : ""
                  }`}
                />
              </button>

              {/* Rule info */}
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 mb-1">
                  <RuleTypeBadge type={rule.rule_type} />
                  <ActionBadge action={rule.action} />
                  <span className="text-xs text-gray-400">
                    Priority: {rule.priority}
                  </span>
                </div>
                <p className="text-sm text-gray-600 truncate">
                  {conditionSummary(rule)}
                </p>
              </div>

              {/* Actions */}
              <div className="flex items-center gap-1">
                <button
                  onClick={() => onEdit(rule)}
                  className="p-1.5 text-gray-400 hover:text-blue-600 hover:bg-blue-50 rounded transition"
                  title="Edit"
                >
                  <Pencil className="w-4 h-4" />
                </button>
                <button
                  onClick={() => handleDelete(rule)}
                  className="p-1.5 text-gray-400 hover:text-red-600 hover:bg-red-50 rounded transition"
                  title="Delete"
                >
                  <Trash2 className="w-4 h-4" />
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

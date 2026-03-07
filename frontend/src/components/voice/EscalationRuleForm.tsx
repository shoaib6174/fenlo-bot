"use client";

import { useState, useEffect } from "react";
import { X } from "lucide-react";
import { apiClient } from "@/lib/api";
import type {
  EscalationRuleResponse,
  EscalationRuleCreate,
  EscalationRuleUpdate,
} from "@/types/voice";

interface EscalationRuleFormProps {
  rule: EscalationRuleResponse | null; // null = create mode
  onClose: () => void;
  onSaved: () => void;
}

const RULE_TYPES = [
  { value: "keyword", label: "Keyword" },
  { value: "sentiment", label: "Sentiment" },
  { value: "confidence", label: "Confidence" },
  { value: "intent", label: "Intent" },
  { value: "business_hours", label: "Business Hours" },
];

const ACTIONS = [
  { value: "escalate", label: "Escalate" },
  { value: "notify", label: "Notify" },
  { value: "log", label: "Log" },
];

export function EscalationRuleForm({
  rule,
  onClose,
  onSaved,
}: EscalationRuleFormProps) {
  const isEdit = !!rule;
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Form fields
  type RuleType = "keyword" | "sentiment" | "confidence" | "intent" | "business_hours";
  type ActionType = "escalate" | "notify" | "log";
  const [ruleType, setRuleType] = useState<RuleType>(rule?.rule_type || "keyword");
  const [action, setAction] = useState<ActionType>(rule?.action || "escalate");
  const [priority, setPriority] = useState(rule?.priority ?? 0);
  const [isActive, setIsActive] = useState(rule?.is_active ?? true);

  // Condition fields — keyword
  const [keywords, setKeywords] = useState("");
  const [matchMode, setMatchMode] = useState("any");

  // Condition fields — sentiment
  const [sentimentThreshold, setSentimentThreshold] = useState("negative");

  // Condition fields — confidence
  const [minConfidence, setMinConfidence] = useState(0.3);

  // Condition fields — intent
  const [intents, setIntents] = useState("");

  // Condition fields — business_hours
  const [timezone, setTimezone] = useState("America/New_York");
  const [startTime, setStartTime] = useState("09:00");
  const [endTime, setEndTime] = useState("17:00");

  // Pre-fill condition fields when editing
  useEffect(() => {
    if (!rule) return;
    const c = rule.condition;
    switch (rule.rule_type) {
      case "keyword":
        setKeywords((c.keywords as string[])?.join(", ") || "");
        setMatchMode((c.match_mode as string) || "any");
        break;
      case "sentiment":
        setSentimentThreshold((c.threshold as string) || "negative");
        break;
      case "confidence":
        setMinConfidence((c.min_confidence as number) ?? 0.3);
        break;
      case "intent":
        setIntents((c.intents as string[])?.join(", ") || "");
        break;
      case "business_hours":
        setTimezone((c.timezone as string) || "America/New_York");
        setStartTime((c.start as string) || "09:00");
        setEndTime((c.end as string) || "17:00");
        break;
    }
  }, [rule]);

  function buildCondition(): Record<string, unknown> {
    switch (ruleType) {
      case "keyword":
        return {
          keywords: keywords
            .split(",")
            .map((k) => k.trim())
            .filter(Boolean),
          match_mode: matchMode,
        };
      case "sentiment":
        return { threshold: sentimentThreshold };
      case "confidence":
        return { min_confidence: minConfidence };
      case "intent":
        return {
          intents: intents
            .split(",")
            .map((i) => i.trim())
            .filter(Boolean),
        };
      case "business_hours":
        return {
          timezone,
          start: startTime,
          end: endTime,
          days: [0, 1, 2, 3, 4], // Mon-Fri default
        };
      default:
        return {};
    }
  }

  function validate(): string | null {
    switch (ruleType) {
      case "keyword": {
        const kw = keywords
          .split(",")
          .map((k) => k.trim())
          .filter(Boolean);
        if (kw.length === 0) return "At least one keyword is required";
        break;
      }
      case "intent": {
        const ints = intents
          .split(",")
          .map((i) => i.trim())
          .filter(Boolean);
        if (ints.length === 0) return "At least one intent is required";
        break;
      }
      case "confidence":
        if (minConfidence < 0 || minConfidence > 1)
          return "Confidence must be between 0 and 1";
        break;
      case "business_hours":
        if (!timezone) return "Timezone is required";
        if (!startTime || !endTime) return "Start and end times are required";
        break;
    }
    return null;
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const validationError = validate();
    if (validationError) {
      setError(validationError);
      return;
    }

    setSaving(true);
    setError(null);

    try {
      const condition = buildCondition();
      if (isEdit) {
        const body: EscalationRuleUpdate = {
          rule_type: ruleType,
          condition,
          action,
          priority,
          is_active: isActive,
        };
        await apiClient(`/api/v1/voice/escalation-rules/${rule.id}`, {
          method: "PATCH",
          body: JSON.stringify(body),
        });
      } else {
        const body: EscalationRuleCreate = {
          rule_type: ruleType,
          condition,
          action,
          priority,
          is_active: isActive,
        };
        await apiClient("/api/v1/voice/escalation-rules", {
          method: "POST",
          body: JSON.stringify(body),
        });
      }
      onSaved();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to save rule");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50">
      <div className="bg-white rounded-lg shadow-xl w-full max-w-lg mx-4 max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200">
          <h2 className="text-lg font-semibold text-gray-900">
            {isEdit ? "Edit Escalation Rule" : "Create Escalation Rule"}
          </h2>
          <button
            onClick={onClose}
            className="p-1 text-gray-400 hover:text-gray-600 rounded transition"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit} className="px-6 py-4 space-y-4">
          {/* Rule type */}
          <div>
            <label
              htmlFor="rule-type"
              className="block text-sm font-medium text-gray-700 mb-1"
            >
              Rule Type
            </label>
            <select
              id="rule-type"
              value={ruleType}
              onChange={(e) => setRuleType(e.target.value as RuleType)}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              {RULE_TYPES.map((rt) => (
                <option key={rt.value} value={rt.value}>
                  {rt.label}
                </option>
              ))}
            </select>
          </div>

          {/* Dynamic condition fields */}
          {ruleType === "keyword" && (
            <>
              <div>
                <label
                  htmlFor="keywords"
                  className="block text-sm font-medium text-gray-700 mb-1"
                >
                  Keywords (comma-separated)
                </label>
                <input
                  id="keywords"
                  type="text"
                  value={keywords}
                  onChange={(e) => setKeywords(e.target.value)}
                  placeholder="speak to human, agent, help"
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
              <div>
                <label
                  htmlFor="match-mode"
                  className="block text-sm font-medium text-gray-700 mb-1"
                >
                  Match Mode
                </label>
                <select
                  id="match-mode"
                  value={matchMode}
                  onChange={(e) => setMatchMode(e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                >
                  <option value="any">Any keyword</option>
                  <option value="all">All keywords</option>
                </select>
              </div>
            </>
          )}

          {ruleType === "sentiment" && (
            <div>
              <label
                htmlFor="sentiment-threshold"
                className="block text-sm font-medium text-gray-700 mb-1"
              >
                Sentiment Threshold
              </label>
              <select
                id="sentiment-threshold"
                value={sentimentThreshold}
                onChange={(e) => setSentimentThreshold(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option value="negative">Negative</option>
                <option value="very_negative">Very Negative</option>
              </select>
            </div>
          )}

          {ruleType === "confidence" && (
            <div>
              <label
                htmlFor="min-confidence"
                className="block text-sm font-medium text-gray-700 mb-1"
              >
                Minimum Confidence: {minConfidence.toFixed(2)}
              </label>
              <input
                id="min-confidence"
                type="range"
                min="0"
                max="1"
                step="0.05"
                value={minConfidence}
                onChange={(e) => setMinConfidence(parseFloat(e.target.value))}
                className="w-full"
              />
              <p className="text-xs text-gray-500 mt-1">
                Escalate when AI confidence falls below this threshold
              </p>
            </div>
          )}

          {ruleType === "intent" && (
            <div>
              <label
                htmlFor="intents"
                className="block text-sm font-medium text-gray-700 mb-1"
              >
                Intents (comma-separated)
              </label>
              <input
                id="intents"
                type="text"
                value={intents}
                onChange={(e) => setIntents(e.target.value)}
                placeholder="cancel_subscription, refund_request"
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
          )}

          {ruleType === "business_hours" && (
            <>
              <div>
                <label
                  htmlFor="timezone"
                  className="block text-sm font-medium text-gray-700 mb-1"
                >
                  Timezone
                </label>
                <input
                  id="timezone"
                  type="text"
                  value={timezone}
                  onChange={(e) => setTimezone(e.target.value)}
                  placeholder="America/New_York"
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label
                    htmlFor="start-time"
                    className="block text-sm font-medium text-gray-700 mb-1"
                  >
                    Start Time
                  </label>
                  <input
                    id="start-time"
                    type="time"
                    value={startTime}
                    onChange={(e) => setStartTime(e.target.value)}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                </div>
                <div>
                  <label
                    htmlFor="end-time"
                    className="block text-sm font-medium text-gray-700 mb-1"
                  >
                    End Time
                  </label>
                  <input
                    id="end-time"
                    type="time"
                    value={endTime}
                    onChange={(e) => setEndTime(e.target.value)}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                </div>
              </div>
            </>
          )}

          {/* Action */}
          <div>
            <label
              htmlFor="action"
              className="block text-sm font-medium text-gray-700 mb-1"
            >
              Action
            </label>
            <select
              id="action"
              value={action}
              onChange={(e) => setAction(e.target.value as ActionType)}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              {ACTIONS.map((a) => (
                <option key={a.value} value={a.value}>
                  {a.label}
                </option>
              ))}
            </select>
          </div>

          {/* Priority */}
          <div>
            <label
              htmlFor="priority"
              className="block text-sm font-medium text-gray-700 mb-1"
            >
              Priority
            </label>
            <input
              id="priority"
              type="number"
              min="0"
              max="100"
              value={priority}
              onChange={(e) => setPriority(parseInt(e.target.value, 10) || 0)}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
            <p className="text-xs text-gray-500 mt-1">
              Higher priority rules are evaluated first
            </p>
          </div>

          {/* Active */}
          <div className="flex items-center gap-2">
            <input
              id="is-active"
              type="checkbox"
              checked={isActive}
              onChange={(e) => setIsActive(e.target.checked)}
              className="w-4 h-4 text-blue-600 rounded border-gray-300"
            />
            <label htmlFor="is-active" className="text-sm text-gray-700">
              Rule is active
            </label>
          </div>

          {/* Error */}
          {error && (
            <div className="p-3 bg-red-50 border border-red-200 rounded-md text-sm text-red-700">
              {error}
            </div>
          )}

          {/* Buttons */}
          <div className="flex justify-end gap-3 pt-2">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50 transition"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={saving}
              className="px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-md hover:bg-blue-700 disabled:opacity-50 transition"
            >
              {saving ? "Saving..." : isEdit ? "Update Rule" : "Create Rule"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

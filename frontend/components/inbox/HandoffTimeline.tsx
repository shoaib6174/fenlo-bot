/**
 * HandoffTimeline Component
 *
 * Displays the handoff event timeline:
 * escalated -> forwarded -> replied -> resolved
 */

"use client";

import { useHandoffStatus } from "@/hooks/useInbox";
import {
  AlertTriangle,
  ArrowRight,
  MessageSquare,
  CheckCircle,
  Clock,
  User,
} from "lucide-react";

interface HandoffTimelineProps {
  conversationId: string;
}

const eventConfig: Record<string, { icon: typeof AlertTriangle; color: string; label: string }> = {
  escalated: {
    icon: AlertTriangle,
    color: "text-red-600 bg-red-100",
    label: "Escalated",
  },
  message_forwarded: {
    icon: ArrowRight,
    color: "text-blue-600 bg-blue-100",
    label: "Message Forwarded",
  },
  agent_replied: {
    icon: MessageSquare,
    color: "text-green-600 bg-green-100",
    label: "Agent Replied",
  },
  resolved: {
    icon: CheckCircle,
    color: "text-green-600 bg-green-100",
    label: "Resolved",
  },
  auto_resolved: {
    icon: Clock,
    color: "text-orange-600 bg-orange-100",
    label: "Auto-Resolved",
  },
};

export function HandoffTimeline({ conversationId }: HandoffTimelineProps) {
  const { data: status, isLoading } = useHandoffStatus(conversationId);

  if (isLoading || !status || !status.events || status.events.length === 0) {
    return null;
  }

  return (
    <div className="bg-white p-4 space-y-3">
      <h4 className="text-sm font-semibold text-gray-900 flex items-center gap-2">
        <Clock className="w-4 h-4 text-gray-500" />
        Handoff Timeline
      </h4>

      {/* Provider & ticket info */}
      {(status.handoff_provider || status.external_ticket_id) && (
        <div className="flex flex-wrap gap-3 text-xs text-gray-500">
          {status.handoff_provider && (
            <span>
              Provider: <span className="font-medium text-gray-700">{status.handoff_provider}</span>
            </span>
          )}
          {status.external_ticket_id && (
            <span>
              Ticket: <span className="font-medium text-gray-700">#{status.external_ticket_id}</span>
            </span>
          )}
        </div>
      )}

      {/* Event timeline */}
      <div className="space-y-2">
        {status.events.map((event, idx) => {
          const config = eventConfig[event.event_type] || {
            icon: User,
            color: "text-gray-600 bg-gray-100",
            label: event.event_type,
          };
          const Icon = config.icon;

          return (
            <div key={idx} className="flex items-start gap-3">
              <div className={`p-1 rounded-full ${config.color} flex-shrink-0 mt-0.5`}>
                <Icon className="w-3 h-3" />
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-center justify-between">
                  <span className="text-sm font-medium text-gray-900">
                    {config.label}
                  </span>
                  {event.created_at && (
                    <span className="text-xs text-gray-500">
                      {new Date(event.created_at).toLocaleString()}
                    </span>
                  )}
                </div>
                {event.actor && (
                  <p className="text-xs text-gray-500">by {event.actor}</p>
                )}
                {event.payload && event.event_type === "escalated" && (
                  <p className="text-xs text-gray-500 mt-0.5">
                    {`Reason: ${JSON.stringify((event.payload as Record<string, unknown>).reason ?? "")}`}
                  </p>
                )}
                {event.payload && "message" in (event.payload as Record<string, unknown>) && (
                  <p className="text-xs text-gray-600 mt-0.5 truncate">
                    {String((event.payload as Record<string, unknown>).message).slice(0, 100)}</p>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

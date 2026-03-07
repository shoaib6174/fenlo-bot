/**
 * FilterBar Component
 *
 * Filters for inbox conversations: channel, status, lead score
 */

"use client";

interface FilterBarProps {
  channel: string;
  status: string;
  minLeadScore: number;
  onChannelChange: (channel: string) => void;
  onStatusChange: (status: string) => void;
  onLeadScoreChange: (score: number) => void;
}

export function FilterBar({
  channel,
  status,
  minLeadScore,
  onChannelChange,
  onStatusChange,
  onLeadScoreChange,
}: FilterBarProps) {
  return (
    <div className="bg-white border-b border-gray-200 px-6 py-4">
      <div className="flex flex-wrap gap-4 items-center">
        {/* Channel Filter */}
        <div className="flex items-center gap-2">
          <label className="text-sm font-medium text-gray-700">Channel:</label>
          <select
            value={channel}
            onChange={(e) => onChannelChange(e.target.value)}
            className="px-3 py-1.5 border border-gray-300 rounded-md text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          >
            <option value="all">All Channels</option>
            <option value="web">Web</option>
            <option value="whatsapp">WhatsApp</option>
            <option value="widget">Widget</option>
            <option value="telegram">Telegram</option>
            <option value="voice">Voice</option>
          </select>
        </div>

        {/* Status Filter */}
        <div className="flex items-center gap-2">
          <label className="text-sm font-medium text-gray-700">Status:</label>
          <select
            value={status}
            onChange={(e) => onStatusChange(e.target.value)}
            className="px-3 py-1.5 border border-gray-300 rounded-md text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          >
            <option value="all">All Status</option>
            <option value="active">Active</option>
            <option value="escalated">Escalated</option>
            <option value="closed">Closed</option>
          </select>
        </div>

        {/* Lead Score Filter */}
        <div className="flex items-center gap-2 min-w-[200px]">
          <label className="text-sm font-medium text-gray-700">
            Min Lead Score: {minLeadScore.toFixed(1)}
          </label>
          <input
            type="range"
            min="0"
            max="10"
            step="0.5"
            value={minLeadScore}
            onChange={(e) => onLeadScoreChange(parseFloat(e.target.value))}
            className="flex-1"
          />
        </div>
      </div>
    </div>
  );
}

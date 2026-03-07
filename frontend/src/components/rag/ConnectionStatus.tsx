'use client';

import { Wifi, WifiOff, Loader2, RefreshCw } from 'lucide-react';
import type { ConnectionState } from '@/src/hooks/useRAGChat';

interface ConnectionStatusProps {
  state: ConnectionState;
  error?: string | null;
}

const statusConfig: Record<ConnectionState, { icon: typeof Wifi; label: string; className: string }> = {
  connecting: {
    icon: Loader2,
    label: 'Connecting...',
    className: 'bg-yellow-50 text-yellow-700 border-yellow-200',
  },
  connected: {
    icon: Wifi,
    label: 'Connected',
    className: 'bg-green-50 text-green-700 border-green-200',
  },
  disconnected: {
    icon: WifiOff,
    label: 'Disconnected',
    className: 'bg-red-50 text-red-700 border-red-200',
  },
  reconnecting: {
    icon: RefreshCw,
    label: 'Reconnecting...',
    className: 'bg-amber-50 text-amber-700 border-amber-200',
  },
};

export function ConnectionStatus({ state, error }: ConnectionStatusProps) {
  // Don't show banner when connected (clean UI)
  if (state === 'connected') return null;

  const config = statusConfig[state];
  const Icon = config.icon;
  const isAnimated = state === 'connecting' || state === 'reconnecting';

  return (
    <div className={`flex items-center gap-2 px-3 py-2 text-sm border rounded-lg ${config.className}`}>
      <Icon className={`w-4 h-4 flex-shrink-0 ${isAnimated ? 'animate-spin' : ''}`} />
      <span className="font-medium">{config.label}</span>
      {error && state === 'disconnected' && (
        <span className="text-xs opacity-75 ml-1">— {error}</span>
      )}
    </div>
  );
}

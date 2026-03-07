'use client';

import { useState, useEffect } from 'react';
import { Inbox, Check, MessageSquare, Globe, Link2 } from 'lucide-react';

interface ChannelMessage {
  channel: 'whatsapp' | 'widget' | 'webhook';
  sender: string;
  message: string;
  time: string;
  responded: boolean;
}

const CHANNEL_CONFIG = {
  whatsapp: { label: 'WhatsApp', color: 'text-green-600', bg: 'bg-green-50', border: 'border-green-200', icon: Globe },
  widget: { label: 'Widget', color: 'text-blue-600', bg: 'bg-blue-50', border: 'border-blue-200', icon: MessageSquare },
  webhook: { label: 'Webhook', color: 'text-purple-600', bg: 'bg-purple-50', border: 'border-purple-200', icon: Link2 },
};

const DEMO_MESSAGES: ChannelMessage[] = [
  { channel: 'whatsapp', sender: 'Maria G.', message: 'When will my order ship?', time: '2m ago', responded: false },
  { channel: 'widget', sender: 'Visitor #847', message: 'Do you have this in size L?', time: '5m ago', responded: false },
  { channel: 'webhook', sender: 'Order #4521', message: 'Delivery status update requested', time: '12m ago', responded: false },
];

export default function OmniChannelPreview() {
  const [messages, setMessages] = useState<ChannelMessage[]>([]);
  const [synced, setSynced] = useState(false);
  const [cycle, setCycle] = useState(0);

  useEffect(() => {
    const timers: ReturnType<typeof setTimeout>[] = [];

    // Step 1 (1.5s): WhatsApp message slides in
    timers.push(
      setTimeout(() => {
        setMessages([DEMO_MESSAGES[0]]);
      }, 1500)
    );

    // Step 2 (3.5s): Widget message slides in
    timers.push(
      setTimeout(() => {
        setMessages([DEMO_MESSAGES[0], DEMO_MESSAGES[1]]);
      }, 3500)
    );

    // Step 3 (5.5s): Webhook message slides in
    timers.push(
      setTimeout(() => {
        setMessages([DEMO_MESSAGES[0], DEMO_MESSAGES[1], DEMO_MESSAGES[2]]);
      }, 5500)
    );

    // Step 4 (7.5s): First message gets AI responded
    timers.push(
      setTimeout(() => {
        setMessages((prev) =>
          prev.map((m, i) => (i === 0 ? { ...m, responded: true } : m))
        );
      }, 7500)
    );

    // Step 5 (9s): All synced
    timers.push(
      setTimeout(() => {
        setMessages((prev) => prev.map((m) => ({ ...m, responded: true })));
        setSynced(true);
      }, 9000)
    );

    // Step 6 (13s): Reset and loop
    timers.push(
      setTimeout(() => {
        setMessages([]);
        setSynced(false);
        setCycle((c) => c + 1);
      }, 13000)
    );

    return () => timers.forEach(clearTimeout);
  }, [cycle]);

  return (
    <div className="w-full max-w-sm mx-auto">
      <div className="rounded-2xl shadow-2xl border border-gray-200 overflow-hidden bg-white">
        {/* Header */}
        <div className="bg-purple-600 px-4 py-3 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 bg-white/20 rounded-full flex items-center justify-center">
              <Inbox className="w-4 h-4 text-white" />
            </div>
            <div>
              <p className="text-white text-sm font-semibold">Unified Inbox</p>
              <div className="flex items-center gap-1">
                <span className="w-2 h-2 bg-green-400 rounded-full" />
                <span className="text-white/80 text-xs">All channels</span>
              </div>
            </div>
          </div>
          <div className="flex items-center gap-2">
            {messages.length > 0 && (
              <span className="bg-white/20 text-white text-xs font-bold w-5 h-5 rounded-full flex items-center justify-center">
                {messages.length}
              </span>
            )}
            <span className="text-white/40 text-xs font-medium">LIVE DEMO</span>
          </div>
        </div>

        {/* Messages list */}
        <div className="h-64 overflow-y-auto bg-gray-50">
          {messages.length === 0 && (
            <div className="flex flex-col items-center justify-center h-full text-gray-400">
              <Inbox className="w-8 h-8 mb-2 opacity-30" />
              <p className="text-xs">Waiting for messages...</p>
            </div>
          )}
          {messages.map((msg, i) => {
            const config = CHANNEL_CONFIG[msg.channel];
            const IconComponent = config.icon;
            return (
              <div
                key={`${msg.channel}-${i}`}
                className="px-4 py-3 border-b border-gray-100 bg-white hover:bg-gray-50 transition-all animate-slideIn"
                style={{ animationDelay: `${i * 0.1}s` }}
              >
                <div className="flex items-start gap-3">
                  <div className={`w-8 h-8 ${config.bg} rounded-full flex items-center justify-center flex-shrink-0`}>
                    <IconComponent className={`w-4 h-4 ${config.color}`} />
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center justify-between gap-2 mb-0.5">
                      <div className="flex items-center gap-2">
                        <span className={`text-xs font-semibold px-1.5 py-0.5 rounded ${config.bg} ${config.color}`}>
                          {config.label}
                        </span>
                        <span className="text-xs font-medium text-gray-700 truncate">{msg.sender}</span>
                      </div>
                      <span className="text-xs text-gray-400 flex-shrink-0">{msg.time}</span>
                    </div>
                    <p className="text-sm text-gray-600 truncate">{msg.message}</p>
                    {msg.responded && (
                      <div className="flex items-center gap-1 mt-1">
                        <Check className="w-3 h-3 text-green-500" />
                        <span className="text-xs text-green-600 font-medium">AI responded</span>
                      </div>
                    )}
                  </div>
                </div>
              </div>
            );
          })}
        </div>

        {/* Footer — Sync status */}
        <div className="px-4 py-3 border-t border-gray-100 bg-white flex items-center justify-between">
          <div className="flex items-center gap-1.5">
            {synced ? (
              <>
                <Check className="w-3.5 h-3.5 text-green-500" />
                <span className="text-xs text-green-600 font-medium">All channels synced</span>
              </>
            ) : (
              <>
                <span className="w-1.5 h-1.5 bg-blue-400 rounded-full animate-pulse" />
                <span className="text-xs text-gray-500">Monitoring channels...</span>
              </>
            )}
          </div>
          <span className="text-xs text-gray-400">
            {messages.length} conversation{messages.length !== 1 ? 's' : ''} active
          </span>
        </div>
      </div>

      <style jsx>{`
        @keyframes slideIn {
          from {
            opacity: 0;
            transform: translateY(-8px);
          }
          to {
            opacity: 1;
            transform: translateY(0);
          }
        }
        .animate-slideIn {
          animation: slideIn 0.3s ease-out forwards;
        }
      `}</style>
    </div>
  );
}

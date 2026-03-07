'use client';

import { useState, useEffect } from 'react';
import { Phone, AlertTriangle } from 'lucide-react';

type CallState = 'ringing' | 'connected' | 'escalating';

interface TranscriptLine {
  speaker: 'caller' | 'ai' | 'system';
  text: string;
}

export default function VoiceCallPreview() {
  const [callState, setCallState] = useState<CallState>('ringing');
  const [duration, setDuration] = useState(0);
  const [transcript, setTranscript] = useState<TranscriptLine[]>([]);
  const [sentiment, setSentiment] = useState<'positive' | 'neutral' | 'negative'>('neutral');
  const [showEscalation, setShowEscalation] = useState(false);
  const [cycle, setCycle] = useState(0);

  // Auto-play demo sequence
  useEffect(() => {
    const timers: ReturnType<typeof setTimeout>[] = [];

    // Step 1 (1.5s): Connected
    timers.push(
      setTimeout(() => {
        setCallState('connected');
      }, 1500)
    );

    // Step 2 (3s): First transcript — caller asks about order
    timers.push(
      setTimeout(() => {
        setTranscript([
          { speaker: 'caller', text: 'Hi, I ordered a dress last week and it hasn\'t arrived yet...' },
        ]);
      }, 3000)
    );

    // Step 3 (5s): AI response
    timers.push(
      setTimeout(() => {
        setTranscript((prev) => [
          ...prev,
          { speaker: 'ai', text: 'I\'d be happy to help! Let me look up your order. Can you share your order number?' },
        ]);
      }, 5000)
    );

    // Step 4 (7s): Caller escalation request
    timers.push(
      setTimeout(() => {
        setTranscript((prev) => [
          ...prev,
          { speaker: 'caller', text: 'This is the third time I\'ve called! I want to speak to a manager!' },
        ]);
        setSentiment('negative');
      }, 7000)
    );

    // Step 5 (8.5s): Escalation triggered
    timers.push(
      setTimeout(() => {
        setShowEscalation(true);
      }, 8500)
    );

    // Step 6 (10s): Escalating state
    timers.push(
      setTimeout(() => {
        setCallState('escalating');
        setTranscript((prev) => [
          ...prev,
          { speaker: 'system', text: 'Escalating to human agent...' },
        ]);
      }, 10000)
    );

    // Step 7 (14s): Reset and loop
    timers.push(
      setTimeout(() => {
        setCallState('ringing');
        setDuration(0);
        setTranscript([]);
        setSentiment('neutral');
        setShowEscalation(false);
        setCycle((c) => c + 1);
      }, 14000)
    );

    return () => timers.forEach(clearTimeout);
  }, [cycle]);

  // Duration timer when connected
  useEffect(() => {
    if (callState !== 'connected' && callState !== 'escalating') return;
    const timer = setInterval(() => {
      setDuration((d) => d + 1);
    }, 1000);
    return () => clearInterval(timer);
  }, [callState]);

  const formatDuration = (s: number) => {
    const mins = Math.floor(s / 60);
    const secs = s % 60;
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  const sentimentConfig = {
    positive: { label: 'Positive', color: 'text-green-400', bg: 'bg-green-400/10' },
    neutral: { label: 'Neutral', color: 'text-yellow-400', bg: 'bg-yellow-400/10' },
    negative: { label: 'Negative', color: 'text-red-400', bg: 'bg-red-400/10' },
  };

  return (
    <div className="w-full max-w-sm mx-auto">
      <div className="rounded-2xl shadow-2xl border border-gray-200 overflow-hidden bg-white">
        {/* Header */}
        <div className="bg-emerald-600 px-4 py-3 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 bg-white/20 rounded-full flex items-center justify-center">
              <Phone className="w-4 h-4 text-white" />
            </div>
            <div>
              <p className="text-white text-sm font-semibold">VoiceBot Pro</p>
              <div className="flex items-center gap-1">
                <span
                  className={`w-2 h-2 rounded-full ${
                    callState === 'ringing'
                      ? 'bg-yellow-400 animate-pulse'
                      : callState === 'escalating'
                      ? 'bg-orange-400 animate-pulse'
                      : 'bg-green-400'
                  }`}
                />
                <span className="text-white/80 text-xs">
                  {callState === 'ringing'
                    ? 'Incoming Call...'
                    : callState === 'escalating'
                    ? 'Escalating...'
                    : 'Active Call'}
                </span>
              </div>
            </div>
          </div>
          <span className="text-white/40 text-xs font-medium">LIVE DEMO</span>
        </div>

        {/* Call Info */}
        <div className="px-4 py-3 border-b border-gray-100 bg-gray-50">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-xs text-gray-500 font-medium">Caller</p>
              <p className="text-sm font-semibold text-gray-900">Sarah Johnson</p>
              <p className="text-xs text-gray-400">+1 (555) 867-5309</p>
            </div>
            <div className="text-right">
              <p className="text-xs text-gray-500 font-medium">Duration</p>
              <p className="text-lg font-mono font-semibold text-gray-900">
                {callState === 'ringing' ? '--:--' : formatDuration(duration)}
              </p>
            </div>
          </div>
        </div>

        {/* Waveform */}
        <div className="px-4 py-3 flex items-center justify-center gap-[3px] bg-white">
          {Array.from({ length: 24 }).map((_, i) => (
            <div
              key={i}
              className={`w-[3px] rounded-full transition-all ${
                callState === 'ringing'
                  ? 'bg-gray-200 h-1'
                  : callState === 'escalating'
                  ? 'bg-orange-300 animate-pulse h-2'
                  : 'bg-emerald-400'
              }`}
              style={
                callState === 'connected'
                  ? {
                      height: `${8 + Math.sin(i * 0.8) * 6 + Math.cos(i * 1.3) * 4}px`,
                      animation: `waveform ${0.4 + (i % 5) * 0.1}s ease-in-out infinite alternate`,
                      animationDelay: `${i * 0.05}s`,
                    }
                  : undefined
              }
            />
          ))}
          <style jsx>{`
            @keyframes waveform {
              from {
                transform: scaleY(0.4);
              }
              to {
                transform: scaleY(1);
              }
            }
          `}</style>
        </div>

        {/* Transcript */}
        <div className="px-4 py-2 h-36 overflow-y-auto bg-gray-50 space-y-2">
          <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide">Live Transcript</p>
          {transcript.length === 0 && callState === 'ringing' && (
            <p className="text-xs text-gray-400 italic">Waiting for connection...</p>
          )}
          {transcript.length === 0 && callState === 'connected' && (
            <p className="text-xs text-gray-400 italic">Listening...</p>
          )}
          {transcript.map((line, i) => (
            <div key={i} className="flex gap-2">
              <span
                className={`text-xs font-semibold flex-shrink-0 w-12 ${
                  line.speaker === 'caller'
                    ? 'text-blue-500'
                    : line.speaker === 'ai'
                    ? 'text-emerald-500'
                    : 'text-orange-500'
                }`}
              >
                {line.speaker === 'caller' ? 'Caller' : line.speaker === 'ai' ? 'AI' : 'System'}
              </span>
              <p
                className={`text-xs leading-relaxed ${
                  line.speaker === 'system' ? 'text-orange-600 font-medium italic' : 'text-gray-700'
                }`}
              >
                {line.text}
              </p>
            </div>
          ))}
        </div>

        {/* Footer — Sentiment + Escalation */}
        <div className="px-4 py-3 border-t border-gray-100 bg-white flex items-center justify-between">
          <div className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium ${sentimentConfig[sentiment].bg} ${sentimentConfig[sentiment].color}`}>
            <span className="w-1.5 h-1.5 rounded-full bg-current" />
            Sentiment: {sentimentConfig[sentiment].label}
          </div>
          {showEscalation && (
            <div className="inline-flex items-center gap-1 px-2.5 py-1 bg-red-50 text-red-600 rounded-full text-xs font-medium animate-pulse">
              <AlertTriangle className="w-3 h-3" />
              Escalate
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

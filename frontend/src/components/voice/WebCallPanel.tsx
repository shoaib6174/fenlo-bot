"use client";

import { useState, useEffect, useRef } from "react";
import { Mic, MicOff, PhoneOff, Volume2 } from "lucide-react";
import type { CallState, TranscriptEntry } from "@/types/voice";

interface WebCallPanelProps {
  callState: CallState;
  isSpeaking: boolean;
  transcript: TranscriptEntry[];
  onEnd: () => void;
  error: string | null;
}

function formatDuration(seconds: number): string {
  const m = Math.floor(seconds / 60);
  const s = seconds % 60;
  return `${m}:${s.toString().padStart(2, "0")}`;
}

export function WebCallPanel({
  callState,
  isSpeaking,
  transcript,
  onEnd,
  error,
}: WebCallPanelProps) {
  const [isMuted, setIsMuted] = useState(false);
  const [duration, setDuration] = useState(0);
  const transcriptEndRef = useRef<HTMLDivElement>(null);

  // Duration timer
  useEffect(() => {
    if (callState !== "active") {
      setDuration(0);
      return;
    }
    const interval = setInterval(() => setDuration((d) => d + 1), 1000);
    return () => clearInterval(interval);
  }, [callState]);

  // Auto-scroll transcript
  useEffect(() => {
    transcriptEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [transcript]);

  if (callState === "idle") return null;

  return (
    <div className="bg-white border border-gray-200 rounded-lg shadow-sm overflow-hidden">
      {/* Call header */}
      <div className="px-4 py-3 bg-gray-50 border-b border-gray-200 flex items-center justify-between">
        <div className="flex items-center gap-3">
          {callState === "active" && (
            <>
              <span className="relative flex h-3 w-3">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-green-400 opacity-75" />
                <span className="relative inline-flex rounded-full h-3 w-3 bg-green-500" />
              </span>
              <span className="text-sm font-medium text-gray-900">
                {formatDuration(duration)}
              </span>
            </>
          )}
          {callState === "connecting" && (
            <span className="text-sm text-amber-600 font-medium">
              Connecting...
            </span>
          )}
          {callState === "ended" && (
            <span className="text-sm text-gray-500 font-medium">
              Call Ended &middot; {formatDuration(duration)}
            </span>
          )}
          {callState === "error" && (
            <span className="text-sm text-red-600 font-medium">
              {error || "Call failed"}
            </span>
          )}
        </div>

        {isSpeaking && callState === "active" && (
          <div className="flex items-center gap-1 text-xs text-blue-600">
            <Volume2 className="w-4 h-4" />
            <span>Speaking</span>
          </div>
        )}
      </div>

      {/* Transcript */}
      <div className="p-4 max-h-64 overflow-y-auto min-h-[120px]">
        {transcript.length === 0 && callState === "active" && (
          <p className="text-sm text-gray-400 text-center py-4">
            Waiting for conversation...
          </p>
        )}
        {transcript.length === 0 && callState === "ended" && (
          <p className="text-sm text-gray-400 text-center py-4">
            No transcript available
          </p>
        )}
        <div className="space-y-2">
          {transcript.map((entry, i) => (
            <div
              key={i}
              className={`text-sm ${
                entry.role === "user"
                  ? "text-gray-800"
                  : "text-blue-700"
              }`}
            >
              <span className="font-medium capitalize">{entry.role}: </span>
              {entry.text}
            </div>
          ))}
          <div ref={transcriptEndRef} />
        </div>
      </div>

      {/* Controls */}
      {callState === "active" && (
        <div className="px-4 py-3 border-t border-gray-200 flex items-center justify-center gap-4">
          <button
            onClick={() => setIsMuted(!isMuted)}
            className={`p-3 rounded-full transition-colors ${
              isMuted
                ? "bg-red-100 text-red-600 hover:bg-red-200"
                : "bg-gray-100 text-gray-600 hover:bg-gray-200"
            }`}
            title={isMuted ? "Unmute" : "Mute"}
          >
            {isMuted ? (
              <MicOff className="w-5 h-5" />
            ) : (
              <Mic className="w-5 h-5" />
            )}
          </button>
          <button
            onClick={onEnd}
            className="p-3 rounded-full bg-red-600 text-white hover:bg-red-700 transition-colors"
            title="End Call"
          >
            <PhoneOff className="w-5 h-5" />
          </button>
        </div>
      )}
    </div>
  );
}

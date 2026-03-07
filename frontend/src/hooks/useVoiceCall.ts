"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import type { CallState, TranscriptEntry } from "@/types/voice";

interface UseVoiceCallOptions {
  publicKey: string | null;
  assistantId: string | null;
}

interface UseVoiceCallReturn {
  callState: CallState;
  startCall: () => void;
  endCall: () => void;
  isSpeaking: boolean;
  transcript: TranscriptEntry[];
  error: string | null;
}

export function useVoiceCall({
  publicKey,
  assistantId,
}: UseVoiceCallOptions): UseVoiceCallReturn {
  const [callState, setCallState] = useState<CallState>("idle");
  const [isSpeaking, setIsSpeaking] = useState(false);
  const [transcript, setTranscript] = useState<TranscriptEntry[]>([]);
  const [error, setError] = useState<string | null>(null);
  const vapiRef = useRef<{ start: (id: string) => void; stop: () => void } | null>(null);

  useEffect(() => {
    if (!publicKey) return;

    async function createVapi() {
      const { default: Vapi } = await import("@vapi-ai/web");
      const vapi = new Vapi(publicKey!);

      vapi.on("call-start", () => {
        setCallState("active");
        setError(null);
      });

      vapi.on("call-end", () => {
        setCallState("ended");
        setIsSpeaking(false);
      });

      vapi.on("speech-start", () => {
        setIsSpeaking(true);
      });

      vapi.on("speech-end", () => {
        setIsSpeaking(false);
      });

      vapi.on("message", (message: Record<string, string>) => {
        if (message.type === "transcript" && message.transcriptType === "final") {
          setTranscript((prev) => [
            ...prev,
            { role: message.role as "user" | "assistant", text: message.transcript },
          ]);
        }
      });

      vapi.on("error", (err: Record<string, string>) => {
        console.error("Vapi error:", err);
        setError(err?.message || "Voice call error");
        setCallState("error");
      });

      vapiRef.current = vapi;
      return vapi;
    }

    createVapi();

    return () => {
      if (vapiRef.current) {
        vapiRef.current.stop();
        vapiRef.current = null;
      }
    };
  }, [publicKey]);

  const startCall = useCallback(() => {
    if (!vapiRef.current || !assistantId) {
      setError("Voice not configured");
      return;
    }
    setCallState("connecting");
    setTranscript([]);
    setError(null);
    vapiRef.current.start(assistantId);
  }, [assistantId]);

  const endCall = useCallback(() => {
    if (vapiRef.current) {
      vapiRef.current.stop();
    }
  }, []);

  return { callState, startCall, endCall, isSpeaking, transcript, error };
}

/** Voice module TypeScript interfaces — mirrors backend schemas/voice.py */

// --- Call Logs ---

export interface CallLogResponse {
  id: string;
  conversation_id: string;
  direction: "inbound" | "outbound" | "web";
  phone_from: string;
  phone_to: string;
  duration_sec: number | null;
  recording_url: string | null;
  transcript: string | null;
  summary: string | null;
  sentiment: "positive" | "neutral" | "negative" | null;
  actions_taken: Record<string, unknown>[] | null;
  created_at: string;
}

export interface CallListResponse {
  calls: CallLogResponse[];
  total: number;
  page: number;
  page_size: number;
}

export interface CallStatsResponse {
  total_calls: number;
  avg_duration_sec: number;
  escalation_rate: number;
  sentiment_distribution: {
    positive: number;
    neutral: number;
    negative: number;
  };
}

// --- Escalation Rules ---

export interface EscalationRuleResponse {
  id: string;
  workspace_id: string;
  rule_type: "keyword" | "sentiment" | "confidence" | "intent" | "business_hours";
  condition: Record<string, unknown>;
  action: "escalate" | "notify" | "log";
  is_active: boolean;
  priority: number;
  created_at: string;
}

export interface EscalationRuleCreate {
  rule_type: string;
  condition: Record<string, unknown>;
  action: string;
  priority?: number;
  is_active?: boolean;
}

export interface EscalationRuleUpdate {
  rule_type?: string;
  condition?: Record<string, unknown>;
  action?: string;
  priority?: number;
  is_active?: boolean;
}

// --- Voice Config ---

export interface VoiceConfigResponse {
  voice_enabled: boolean;
  assistant_id: string | null;
  public_key: string | null;
  first_message: string | null;
  created_at: string | null;
}

// --- Voice Setup ---

export interface VoiceSetupRequest {
  vapi_private_key: string;
  vapi_public_key: string;
  first_message?: string;
  system_prompt?: string;
}

// --- Transcripts ---

export interface TranscriptEntry {
  role: "user" | "assistant";
  text: string;
}

// --- Web Call ---

export type CallState = "idle" | "connecting" | "active" | "ended" | "error";

export interface WebTokenResponse {
  public_key: string | null;
  assistant_id: string | null;
}

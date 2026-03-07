const API_URL = process.env.NEXT_PUBLIC_API_URL || "";

interface ApiOptions extends RequestInit {
  credentials?: RequestCredentials;
}

export async function apiClient<T>(
  endpoint: string,
  options: ApiOptions = {}
): Promise<T> {
  const url = `${API_URL}${endpoint}`;

  const config: RequestInit = {
    ...options,
    credentials: "include", // Send httpOnly cookies
    headers: {
      "Content-Type": "application/json",
      ...options.headers,
    },
  };

  const response = await fetch(url, config);

  if (!response.ok) {
    const error = await response.json().catch(() => ({
      message: "An error occurred",
    }));
    throw new Error(error.error?.message || error.detail || error.message || `HTTP ${response.status}`);
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return response.json();
}

// ========================================
// Channel Management API
// ========================================

export interface ChannelConfig {
  id: string;
  workspace_id: string;
  channel: "whatsapp" | "widget" | "telegram" | "voice";
  provider?: string | null;
  config: Record<string, unknown>;
  is_active: boolean;
  created_at: string;
  updated_at?: string;
}

export interface CreateChannelRequest {
  channel: "whatsapp" | "widget" | "telegram" | "voice";
  provider?: string;
  config: Record<string, unknown>;
  is_active?: boolean;
}

export interface UpdateChannelRequest {
  config?: Record<string, unknown>;
  is_active?: boolean;
  provider?: string;
}

export interface EmbedCodeResponse {
  html: string;
  widget_id: string;
  widget_url: string;
}

export const channelApi = {
  list: () => apiClient<ChannelConfig[]>("/api/v1/channels"),

  get: (id: string) => apiClient<ChannelConfig>(`/api/v1/channels/${id}`),

  create: (data: CreateChannelRequest) =>
    apiClient<ChannelConfig>("/api/v1/channels", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  update: (id: string, data: UpdateChannelRequest) =>
    apiClient<ChannelConfig>(`/api/v1/channels/${id}`, {
      method: "PUT",
      body: JSON.stringify(data),
    }),

  delete: (id: string) =>
    apiClient<void>(`/api/v1/channels/${id}`, {
      method: "DELETE",
    }),

  getEmbedCode: (id: string) =>
    apiClient<EmbedCodeResponse>(`/api/v1/channels/${id}/embed-code`),
};

// ========================================
// Webhook Actions API
// ========================================

export interface WebhookAction {
  id: string;
  workspace_id: string;
  event_type: string;
  target_url: string;
  headers?: Record<string, string>;
  payload_template?: string;
  is_active: boolean;
  created_at: string;
}

export interface CreateWebhookActionRequest {
  event_type: string;
  target_url: string;
  headers?: Record<string, string>;
  payload_template?: string;
  is_active?: boolean;
}

export interface UpdateWebhookActionRequest {
  event_type?: string;
  target_url?: string;
  headers?: Record<string, string>;
  payload_template?: string;
  is_active?: boolean;
}

export interface WebhookOutboxEntry {
  id: string;
  action_id: string;
  event_type: string;
  target_url: string;
  payload: Record<string, unknown>;
  status: "pending" | "sent" | "failed" | "dead";
  retry_count: number;
  error_message?: string;
  sent_at?: string;
  created_at: string;
  next_retry_at?: string;
}

export interface WebhookHistoryResponse {
  items: WebhookOutboxEntry[];
  total: number;
  page: number;
  per_page: number;
}

export const webhookActionApi = {
  list: () => apiClient<WebhookAction[]>("/api/v1/webhook-actions"),

  create: (data: CreateWebhookActionRequest) =>
    apiClient<WebhookAction>("/api/v1/webhook-actions", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  update: (id: string, data: UpdateWebhookActionRequest) =>
    apiClient<WebhookAction>(`/api/v1/webhook-actions/${id}`, {
      method: "PUT",
      body: JSON.stringify(data),
    }),

  delete: (id: string) =>
    apiClient<void>(`/api/v1/webhook-actions/${id}`, {
      method: "DELETE",
    }),

  history: (params?: { page?: number; per_page?: number; status?: string }) => {
    const searchParams = new URLSearchParams();
    if (params?.page) searchParams.set("page", params.page.toString());
    if (params?.per_page) searchParams.set("per_page", params.per_page.toString());
    if (params?.status) searchParams.set("status", params.status);

    const query = searchParams.toString();
    const endpoint = `/api/v1/webhook-actions/history${query ? `?${query}` : ""}`;

    return apiClient<WebhookHistoryResponse>(endpoint);
  },
};

// ========================================
// Inbox API
// ========================================

export interface InboxMessage {
  id: string;
  conversation_id: string;
  role: "user" | "assistant";
  content: string;
  sentiment?: "positive" | "neutral" | "negative";
  intent?: "faq" | "booking" | "sales" | "support" | "escalation" | "other";
  quality_score?: number;
  created_at: string;
}

export interface CallLogSummary {
  id: string;
  status: string;
  direction: string;
  duration_sec: number | null;
  phone_from: string;
  phone_to: string;
  summary: string | null;
  sentiment: string | null;
}

export interface CallLogDetail extends CallLogSummary {
  vapi_call_id: string | null;
  recording_url: string | null;
  transcript: string | null;
  actions_taken: Array<{ action_type: string; timestamp: string; details: string }> | null;
  created_at: string;
}

export interface InboxConversation {
  id: string;
  workspace_id: string;
  channel: "whatsapp" | "widget" | "telegram" | "voice";
  contact_name?: string;
  contact_identifier: string;
  status: "active" | "escalated" | "closed";
  lead_score: number;
  last_message_at: string;
  last_message_preview?: string;
  created_at: string;
  updated_at?: string;
  call_log?: CallLogSummary;
}

export interface InboxConversationDetail extends InboxConversation {
  messages: InboxMessage[];
  call_log?: CallLogDetail;
}

export interface HandoffContext {
  conversation_id: string;
  rag_contexts: Array<{
    content: string;
    source: string;
    score: number;
  }>;
  quality_scores: Array<{
    timestamp: string;
    score: number;
  }>;
  intent_history: Array<{
    timestamp: string;
    intent: string;
  }>;
  sentiment_timeline: Array<{
    timestamp: string;
    sentiment: string;
  }>;
}

export interface InboxListParams {
  page?: number;
  per_page?: number;
  channel?: "whatsapp" | "widget" | "telegram" | "voice" | "all";
  status?: "active" | "escalated" | "closed" | "all";
  min_lead_score?: number;
}

export interface InboxListResponse {
  items: InboxConversation[];
  total: number;
  page: number;
  per_page: number;
}

export interface SendReplyRequest {
  content: string;
}

// ========================================
// Handoff API
// ========================================

export interface HandoffStatusResponse {
  conversation_id: string;
  status: string;
  escalated_at: string | null;
  resolved_at: string | null;
  external_ticket_id: string | null;
  handoff_provider: string | null;
  events: Array<{
    event_type: string;
    actor: string | null;
    payload: Record<string, unknown> | null;
    created_at: string | null;
  }>;
}

export const handoffApi = {
  status: (conversationId: string) =>
    apiClient<HandoffStatusResponse>(`/api/v1/handoff/status/${conversationId}`),

  escalate: (conversationId: string) =>
    apiClient<{ status: string; message: string; external_ticket_id: string | null }>(
      `/api/v1/handoff/escalate/${conversationId}`,
      { method: "POST" }
    ),
};

export const inboxApi = {
  list: (params?: InboxListParams) => {
    const searchParams = new URLSearchParams();
    if (params?.page) searchParams.set("page", params.page.toString());
    if (params?.per_page) searchParams.set("per_page", params.per_page.toString());
    if (params?.channel && params.channel !== "all")
      searchParams.set("channel", params.channel);
    if (params?.status && params.status !== "all")
      searchParams.set("status", params.status);
    if (params?.min_lead_score !== undefined)
      searchParams.set("min_lead_score", params.min_lead_score.toString());

    const query = searchParams.toString();
    const endpoint = `/api/v1/inbox/conversations${query ? `?${query}` : ""}`;

    return apiClient<InboxListResponse>(endpoint);
  },

  get: (id: string) =>
    apiClient<InboxConversationDetail>(`/api/v1/inbox/conversations/${id}`),

  handoff: (conversationId: string) =>
    apiClient<HandoffContext>(`/api/v1/inbox/handoff/${conversationId}`),

  reply: (conversationId: string, data: SendReplyRequest) =>
    apiClient<void>(`/api/v1/inbox/reply/${conversationId}`, {
      method: "POST",
      body: JSON.stringify(data),
    }),
};

// ========================================
// Analytics API
// ========================================

export interface AnalyticsOverview {
  total_conversations: number;
  total_messages: number;
  avg_response_time_ms: number;
  avg_quality_score: number;
  sentiment_distribution: {
    positive: number;
    neutral: number;
    negative: number;
  };
}

export interface VolumeDataPoint {
  date: string;
  message_count: number;
  conversation_count: number;
}

export interface TopQuestion {
  question: string;
  count: number;
}

export interface SentimentDataPoint {
  date: string;
  positive: number;
  neutral: number;
  negative: number;
}

export interface ChannelBreakdownData {
  [channel: string]: {
    count: number;
    avg_quality: number;
  };
}

export interface LeadScoreData {
  buckets: {
    "0-3": number;
    "4-6": number;
    "7-10": number;
  };
}

export interface WeeklyInsightData {
  id: string;
  period: string;
  summary: string;
  metrics: Record<string, unknown>;
  recommendations: string[];
  created_at: string | null;
}

export interface InsightHistoryItem {
  id: string;
  period: string;
  summary: string;
  week_start: string | null;
  created_at: string | null;
}

export const analyticsApi = {
  overview: (params?: { start_date?: string; end_date?: string }) => {
    const sp = new URLSearchParams();
    if (params?.start_date) sp.set("start_date", params.start_date);
    if (params?.end_date) sp.set("end_date", params.end_date);
    const q = sp.toString();
    return apiClient<AnalyticsOverview>(`/api/v1/analytics/overview${q ? `?${q}` : ""}`);
  },

  volume: (params?: { period?: string; start_date?: string; end_date?: string }) => {
    const sp = new URLSearchParams();
    if (params?.period) sp.set("period", params.period);
    if (params?.start_date) sp.set("start_date", params.start_date);
    if (params?.end_date) sp.set("end_date", params.end_date);
    const q = sp.toString();
    return apiClient<VolumeDataPoint[]>(`/api/v1/analytics/volume${q ? `?${q}` : ""}`);
  },

  topQuestions: (limit = 10) =>
    apiClient<TopQuestion[]>(`/api/v1/analytics/top-questions?limit=${limit}`),

  sentiment: (params?: { period?: string; start_date?: string; end_date?: string }) => {
    const sp = new URLSearchParams();
    if (params?.period) sp.set("period", params.period);
    if (params?.start_date) sp.set("start_date", params.start_date);
    if (params?.end_date) sp.set("end_date", params.end_date);
    const q = sp.toString();
    return apiClient<SentimentDataPoint[]>(`/api/v1/analytics/sentiment${q ? `?${q}` : ""}`);
  },

  channels: () => apiClient<ChannelBreakdownData>("/api/v1/analytics/channels"),

  leadScores: () => apiClient<LeadScoreData>("/api/v1/analytics/lead-scores"),
};

export const insightsApi = {
  weekly: (week?: string) => {
    const q = week ? `?week=${week}` : "";
    return apiClient<WeeklyInsightData>(`/api/v1/insights/weekly${q}`);
  },

  history: (limit = 10) =>
    apiClient<InsightHistoryItem[]>(`/api/v1/insights/history?limit=${limit}`),

  generate: (week?: string) => {
    const q = week ? `?week=${week}` : "";
    return apiClient<{ id: string; period: string; status: string }>(
      `/api/v1/insights/generate${q}`,
      { method: "POST" }
    );
  },
};

export const exportApi = {
  csvUrl: (params?: { channel?: string; status?: string }) => {
    const sp = new URLSearchParams();
    if (params?.channel) sp.set("channel", params.channel);
    if (params?.status) sp.set("status", params.status);
    const q = sp.toString();
    return `${API_URL}/api/v1/export/conversations/csv${q ? `?${q}` : ""}`;
  },

  transcriptUrl: (conversationId: string) =>
    `${API_URL}/api/v1/export/conversations/${conversationId}/transcript`,
};

// ========================================
// Onboarding API
// ========================================

export interface OnboardingProgress {
  workspace_id: string;
  step_completed: Record<string, boolean>;
  current_step: string | null;
  completion_pct: number;
  completed_at: string | null;
}

export interface StepCompleteResponse {
  success: boolean;
  step: string;
  next_step: string | null;
  completion_pct: number;
}

// ========================================
// Admin API (GDPR, Export, Storage)
// ========================================

export interface PurgeResponse {
  success: boolean;
  deleted_records: {
    messages: number;
    conversations: number;
    documents: number;
    knowledge_bases: number;
    channels: number;
  };
  duration_ms: number;
}

export interface ArchiveResponse {
  success: boolean;
  archived_count: number;
}

export interface StorageUsage {
  workspace_id: string;
  conversations_count: number;
  messages_count: number;
  documents_count: number;
  channels_count: number;
  knowledge_bases_count: number;
}

export const adminApi = {
  /** Download full workspace data as ZIP (binary) */
  exportUrl: (workspaceId: string) =>
    `${API_URL}/api/v1/admin/export/${workspaceId}`,

  /** Purge all workspace data (GDPR Art. 17) */
  purge: (workspaceId: string) =>
    apiClient<PurgeResponse>(
      `/api/v1/admin/workspace/${workspaceId}/data`,
      { method: "DELETE" }
    ),

  /** Archive old conversations before a cutoff date */
  archive: (before: string) =>
    apiClient<ArchiveResponse>(
      `/api/v1/admin/archive?before=${encodeURIComponent(before)}`,
      { method: "POST" }
    ),

  /** Get storage usage for workspace */
  storage: (workspaceId: string) =>
    apiClient<StorageUsage>(`/api/v1/admin/storage/${workspaceId}`),
};

export const onboardingApi = {
  getProgress: () =>
    apiClient<OnboardingProgress>("/api/v1/onboarding/progress"),

  completeStep: (stepName: string) =>
    apiClient<StepCompleteResponse>(`/api/v1/onboarding/step/${stepName}`, {
      method: "PUT",
    }),

  skip: () =>
    apiClient<{ success: boolean; completion_pct: number }>(
      "/api/v1/onboarding/skip",
      { method: "POST" }
    ),

  complete: () =>
    apiClient<{ success: boolean; completed_at: string; completion_pct: number }>(
      "/api/v1/onboarding/complete",
      { method: "POST" }
    ),
};

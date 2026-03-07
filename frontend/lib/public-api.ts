/**
 * Public API client — fetches data via share_token (no auth required).
 */

const API_URL = process.env.NEXT_PUBLIC_API_URL || "";

async function publicFetch<T>(endpoint: string): Promise<T> {
  const url = `${API_URL}${endpoint}`;
  const response = await fetch(url, {
    headers: { "Content-Type": "application/json" },
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({
      message: "An error occurred",
    }));
    throw new Error(
      error.detail || error.error?.message || error.message || `HTTP ${response.status}`
    );
  }

  if (response.status === 204) return undefined as T;
  return response.json();
}

// Types
export interface PublicWorkspaceInfo {
  name: string;
  brand_name: string;
  logo_url: string;
  accent_color: string;
}

export interface PublicDashboardData {
  workspace_name: string;
  conversations_count: number;
  messages_count: number;
  documents_count: number;
  knowledge_gaps_count: number;
  avg_quality_score: number | null;
  recent_conversations: Array<{
    id: string;
    started_at: string | null;
    lead_score: number | null;
  }>;
}

export interface PublicAnalyticsOverview {
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

export interface PublicVolumePoint {
  date: string;
  message_count: number;
  conversation_count: number;
}

export interface PublicSentimentPoint {
  date: string;
  positive: number;
  neutral: number;
  negative: number;
}

export interface PublicTopQuestion {
  question: string;
  count: number;
}

export interface PublicConversation {
  id: string;
  title: string | null;
  channel: string;
  status: string;
  message_count: number;
  started_at: string | null;
  lead_score: number | null;
}

export interface PublicMessage {
  id: string;
  role: "user" | "assistant" | "system";
  content: string;
  citations: Array<{
    doc_name: string;
    page_number?: number;
    chunk_text: string;
    relevance_score: number;
  }> | null;
  sentiment: string | null;
  quality_score: number | null;
  created_at: string | null;
}

export interface PublicConversationDetail {
  id: string;
  title: string | null;
  channel: string;
  status: string;
  started_at: string | null;
  lead_score: number | null;
  messages: PublicMessage[];
}

export interface PublicKBDocument {
  id: string;
  filename: string;
  file_type: string;
  file_size: number;
  status: "processing" | "ready" | "failed";
  chunk_count: number | null;
  created_at: string | null;
}

export interface PublicKBGap {
  id: string;
  query_text: string;
  occurrence_count: number;
  status: string;
  last_asked_at: string | null;
}

export interface PublicKnowledgeBase {
  id: string;
  name: string;
  description: string | null;
  created_at: string | null;
  documents: PublicKBDocument[];
  gaps: PublicKBGap[];
}

// API functions
export const publicApi = {
  info: (token: string) =>
    publicFetch<PublicWorkspaceInfo>(`/api/v1/public/${token}/info`),

  dashboard: (token: string) =>
    publicFetch<PublicDashboardData>(`/api/v1/public/${token}/dashboard`),

  analyticsOverview: (token: string, params?: { start_date?: string; end_date?: string }) => {
    const sp = new URLSearchParams();
    if (params?.start_date) sp.set("start_date", params.start_date);
    if (params?.end_date) sp.set("end_date", params.end_date);
    const q = sp.toString();
    return publicFetch<PublicAnalyticsOverview>(
      `/api/v1/public/${token}/analytics/overview${q ? `?${q}` : ""}`
    );
  },

  analyticsVolume: (token: string, params?: { period?: string; start_date?: string; end_date?: string }) => {
    const sp = new URLSearchParams();
    if (params?.period) sp.set("period", params.period);
    if (params?.start_date) sp.set("start_date", params.start_date);
    if (params?.end_date) sp.set("end_date", params.end_date);
    const q = sp.toString();
    return publicFetch<PublicVolumePoint[]>(
      `/api/v1/public/${token}/analytics/volume${q ? `?${q}` : ""}`
    );
  },

  analyticsSentiment: (token: string, params?: { period?: string; start_date?: string; end_date?: string }) => {
    const sp = new URLSearchParams();
    if (params?.period) sp.set("period", params.period);
    if (params?.start_date) sp.set("start_date", params.start_date);
    if (params?.end_date) sp.set("end_date", params.end_date);
    const q = sp.toString();
    return publicFetch<PublicSentimentPoint[]>(
      `/api/v1/public/${token}/analytics/sentiment${q ? `?${q}` : ""}`
    );
  },

  analyticsTopQuestions: (token: string, limit = 10) =>
    publicFetch<PublicTopQuestion[]>(
      `/api/v1/public/${token}/analytics/top-questions?limit=${limit}`
    ),

  widgetId: (token: string) =>
    publicFetch<{ widget_id: string }>(`/api/v1/public/${token}/widget-id`),

  conversations: (token: string, limit = 50) =>
    publicFetch<PublicConversation[]>(
      `/api/v1/public/${token}/conversations?limit=${limit}`
    ),

  conversation: (token: string, id: string) =>
    publicFetch<PublicConversationDetail>(
      `/api/v1/public/${token}/conversations/${id}`
    ),

  knowledgeBase: (token: string) =>
    publicFetch<PublicKnowledgeBase[]>(`/api/v1/public/${token}/kb`),
};

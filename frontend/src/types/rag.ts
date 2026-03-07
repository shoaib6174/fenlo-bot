export interface Citation {
  doc_name: string;
  page_number?: number;
  chunk_text: string;
  relevance_score: number;
  document_id: string;
}

export interface RAGMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: string;
  citations?: Citation[];
  feedback?: 'positive' | 'negative' | null;
  sentiment?: 'positive' | 'neutral' | 'negative' | null;
  intent?: string | null;
  quality_score?: number | null;
}

export interface KnowledgeBase {
  id: string;
  name: string;
  description: string | null;
  workspace_id: string;
  created_at: string;
  updated_at: string;
  document_count?: number;
}

export interface Document {
  id: string;
  filename: string;
  file_type: string;
  file_size: number;
  status: 'processing' | 'ready' | 'failed';
  kb_id: string;
  chunk_count: number | null;
  metadata_: Record<string, unknown> | null;
  created_at: string;
  processed_at: string | null;
}

export interface KnowledgeGap {
  id: string;
  query_text: string;
  occurrence_count: number;
  first_asked_at: string;
  last_asked_at: string;
  status: 'active' | 'addressed' | 'dismissed';
  kb_id: string | null;
  workspace_id: string;
}

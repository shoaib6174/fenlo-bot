export interface Message {
  id: string
  conversation_id: string
  role: 'user' | 'assistant'
  content: string
  created_at: string
  metadata?: {
    sentiment?: 'positive' | 'neutral' | 'negative'
    quality_score?: number
    intent?: string
    citations?: Citation[]
    booking_config?: {
      provider: string
      url: string
      prompt: string
    }
  }
  feedback?: 'positive' | 'negative' | null
}

export interface Citation {
  doc_name: string
  page_number?: number
  chunk_text: string
  relevance_score: number
}

export interface Conversation {
  id: string
  title?: string
  lead_score?: number
  started_at: string
  message_count?: number
}

export interface WSMessage {
  type: 'token' | 'typing' | 'done' | 'error' | 'citation' | 'quality_score'
  data?: any
}

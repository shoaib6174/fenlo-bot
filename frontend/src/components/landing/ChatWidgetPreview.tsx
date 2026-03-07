'use client';

import { useState, useEffect, useRef, useCallback, KeyboardEvent } from 'react';
import { MessageSquare, Send, FileText, AlertCircle } from 'lucide-react';

interface Citation {
  doc: string;
  page?: number;
  score?: number;
  source?: string;
  chunk_index?: number;
}

interface DemoMessage {
  role: 'user' | 'assistant';
  content: string;
  citations?: Citation[];
}

const WIDGET_ID = process.env.NEXT_PUBLIC_HOMEPAGE_WIDGET_ID;
const API_URL = process.env.NEXT_PUBLIC_API_URL || '';

// Auto-play demo for when no widget_id is configured (static fallback)
const STATIC_RESPONSES: Record<string, DemoMessage> = {
  default: {
    role: 'assistant',
    content:
      "Great question! I search your uploaded documents and respond with source citations so you can verify every answer. Try asking about returns, shipping, or pricing!",
    citations: [{ doc: 'Knowledge-Base.pdf', page: 1, score: 92 }],
  },
  return: {
    role: 'assistant',
    content:
      'Based on your documentation, customers can return items within 30 days of purchase for a full refund. Items must be in original condition with tags attached.',
    citations: [
      { doc: 'Return-Policy.pdf', page: 3, score: 96 },
      { doc: 'FAQ-Guide.pdf', page: 12, score: 89 },
    ],
  },
  shipping: {
    role: 'assistant',
    content:
      'You ship to 45 countries worldwide. Standard international shipping takes 7\u201314 business days. Express shipping (3\u20135 days) is available for select regions.',
    citations: [{ doc: 'Shipping-Guide.pdf', page: 1, score: 94 }],
  },
  price: {
    role: 'assistant',
    content:
      'Your pricing plans start at $29/month for Starter (up to 1,000 conversations), $79/month for Pro (10,000 conversations), and custom Enterprise pricing for unlimited usage.',
    citations: [
      { doc: 'Pricing-Page.pdf', page: 1, score: 97 },
      { doc: 'Sales-Deck.pdf', page: 8, score: 88 },
    ],
  },
  hello: {
    role: 'assistant',
    content:
      "Hello! I\u2019m your RAG-powered AI assistant. I answer questions using your uploaded documents with full source citations. Try asking about return policies, shipping, or pricing!",
  },
};

const AUTO_DEMO: DemoMessage[] = [
  { role: 'user', content: 'What is your return policy?' },
  STATIC_RESPONSES.return,
  { role: 'user', content: 'Do you offer international shipping?' },
  STATIC_RESPONSES.shipping,
];

function matchStaticResponse(input: string): DemoMessage {
  const lower = input.toLowerCase();
  if (lower.includes('return') || lower.includes('refund')) return STATIC_RESPONSES.return;
  if (lower.includes('ship') || lower.includes('deliver') || lower.includes('international'))
    return STATIC_RESPONSES.shipping;
  if (
    lower.includes('price') ||
    lower.includes('pricing') ||
    lower.includes('cost') ||
    lower.includes('plan')
  )
    return STATIC_RESPONSES.price;
  if (lower.includes('hello') || lower.includes('hi') || lower.includes('hey'))
    return STATIC_RESPONSES.hello;
  return STATIC_RESPONSES.default;
}

/** Parse SSE text into individual events */
function parseSSEEvents(text: string): Array<{ event: string; data: string }> {
  const events: Array<{ event: string; data: string }> = [];
  const blocks = text.split('\n\n');
  for (const block of blocks) {
    if (!block.trim()) continue;
    let event = '';
    let data = '';
    for (const line of block.split('\n')) {
      if (line.startsWith('event: ')) event = line.slice(7);
      else if (line.startsWith('data: ')) data = line.slice(6);
    }
    if (event && data) events.push({ event, data });
  }
  return events;
}

interface ChatWidgetPreviewProps {
  title?: string;
  accentColor?: string;
}

export default function ChatWidgetPreview({ title = 'RAGChat Assistant', accentColor = 'bg-sky-500' }: ChatWidgetPreviewProps) {
  const isLive = !!WIDGET_ID;

  const [messages, setMessages] = useState<DemoMessage[]>([]);
  const [isTyping, setIsTyping] = useState(false);
  const [autoIndex, setAutoIndex] = useState(0);
  const [autoDone, setAutoDone] = useState(isLive); // skip auto-play if live
  const [input, setInput] = useState('');
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [streamingContent, setStreamingContent] = useState('');
  const messagesContainerRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const abortRef = useRef<AbortController | null>(null);

  // Auto-play demo conversation (static mode only)
  useEffect(() => {
    if (isLive) return;
    if (autoDone || autoIndex >= AUTO_DEMO.length) {
      if (!autoDone) setAutoDone(true);
      return;
    }

    const message = AUTO_DEMO[autoIndex];
    const delay = message.role === 'user' ? 1500 : 2000;

    if (message.role === 'assistant') {
      setIsTyping(true);
      const timer = setTimeout(() => {
        setIsTyping(false);
        setMessages((prev) => [...prev, message]);
        setAutoIndex((i) => i + 1);
      }, delay);
      return () => clearTimeout(timer);
    } else {
      const timer = setTimeout(() => {
        setMessages((prev) => [...prev, message]);
        setAutoIndex((i) => i + 1);
      }, delay);
      return () => clearTimeout(timer);
    }
  }, [autoIndex, autoDone, isLive]);

  // Auto-scroll messages container
  useEffect(() => {
    if (messagesContainerRef.current) {
      messagesContainerRef.current.scrollTop = messagesContainerRef.current.scrollHeight;
    }
  }, [messages, isTyping, streamingContent]);

  const sendLiveMessage = useCallback(
    async (text: string) => {
      setError(null);
      setIsTyping(true);
      setStreamingContent('');

      // Abort previous request if any
      if (abortRef.current) abortRef.current.abort();
      const controller = new AbortController();
      abortRef.current = controller;

      try {
        const response = await fetch(`${API_URL}/api/v1/widget/${WIDGET_ID}/chat`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            message: text,
            conversation_id: conversationId,
          }),
          signal: controller.signal,
        });

        if (!response.ok) {
          if (response.status === 429) {
            setError('Rate limit reached. Please try again later.');
          } else {
            setError('Demo temporarily unavailable');
          }
          setIsTyping(false);
          return;
        }

        const reader = response.body?.getReader();
        if (!reader) {
          setError('Demo temporarily unavailable');
          setIsTyping(false);
          return;
        }

        const decoder = new TextDecoder();
        let accumulated = '';
        let fullResponse = '';
        let citations: Citation[] = [];

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          accumulated += decoder.decode(value, { stream: true });
          const events = parseSSEEvents(accumulated);

          // Only keep unparsed remainder
          const lastDoubleNewline = accumulated.lastIndexOf('\n\n');
          if (lastDoubleNewline !== -1) {
            accumulated = accumulated.slice(lastDoubleNewline + 2);
          }

          for (const evt of events) {
            if (evt.event === 'token') {
              const parsed = JSON.parse(evt.data);
              fullResponse += parsed.token;
              setStreamingContent(fullResponse);
            } else if (evt.event === 'done') {
              const parsed = JSON.parse(evt.data);
              if (parsed.conversation_id) {
                setConversationId(parsed.conversation_id);
              }
              if (parsed.citations) {
                citations = parsed.citations;
              }
            } else if (evt.event === 'error') {
              const parsed = JSON.parse(evt.data);
              setError(parsed.message || 'Something went wrong');
            }
          }
        }

        // Finalize: add complete message with citations
        setStreamingContent('');
        if (fullResponse) {
          setMessages((prev) => [
            ...prev,
            {
              role: 'assistant',
              content: fullResponse.trim(),
              citations: citations.length > 0 ? citations : undefined,
            },
          ]);
        }
      } catch (e: unknown) {
        if (e instanceof DOMException && e.name === 'AbortError') return;
        setError('Demo temporarily unavailable');
      } finally {
        setIsTyping(false);
        abortRef.current = null;
      }
    },
    [conversationId],
  );

  const handleSend = () => {
    const text = input.trim();
    if (!text || isTyping) return;
    setInput('');

    // Stop auto-play if still running
    if (!autoDone) setAutoDone(true);

    // Add user message
    setMessages((prev) => [...prev, { role: 'user', content: text }]);

    if (isLive) {
      sendLiveMessage(text);
    } else {
      // Static fallback
      setIsTyping(true);
      setTimeout(() => {
        setIsTyping(false);
        setMessages((prev) => [...prev, matchStaticResponse(text)]);
      }, 1200);
    }
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      handleSend();
    }
  };

  const renderCitations = (citations: Citation[]) => (
    <div className="flex flex-wrap gap-1">
      {citations.map((c, j) => (
        <span
          key={j}
          className="inline-flex items-center gap-1 px-2 py-0.5 bg-sky-50 text-sky-700 rounded text-xs border border-sky-100"
        >
          <FileText className="w-3 h-3" />
          {c.doc || c.source || 'Source'}
          {c.page != null && ` p.${c.page}`}
          {c.score != null && <span className="text-sky-400">{c.score}%</span>}
        </span>
      ))}
    </div>
  );

  return (
    <div className="w-full max-w-sm mx-auto">
      <div className="rounded-2xl shadow-2xl border border-gray-200 overflow-hidden bg-white">
        {/* Header */}
        <div className={`${accentColor} px-4 py-3 flex items-center justify-between`}>
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 bg-white/20 rounded-full flex items-center justify-center">
              <MessageSquare className="w-4 h-4 text-white" />
            </div>
            <div>
              <p className="text-white text-sm font-semibold">{title}</p>
              <div className="flex items-center gap-1">
                <span className="w-2 h-2 bg-green-400 rounded-full" />
                <span className="text-white/80 text-xs">Online</span>
              </div>
            </div>
          </div>
          <span className="text-white/40 text-xs font-medium">{isLive ? 'LIVE' : 'LIVE DEMO'}</span>
        </div>

        {/* Messages */}
        <div ref={messagesContainerRef} className="h-80 overflow-y-auto p-3 space-y-3 bg-gray-50">
          {/* Welcome message */}
          <div className="flex gap-2">
            <div className="w-6 h-6 bg-sky-100 rounded-full flex items-center justify-center flex-shrink-0 mt-1">
              <MessageSquare className="w-3 h-3 text-sky-500" />
            </div>
            <div className="bg-white rounded-lg rounded-tl-none px-3 py-2 shadow-sm max-w-[85%]">
              <p className="text-sm text-gray-700">
                Hi! I&apos;m trained on your documents and answer with source citations. Ask me
                anything!
              </p>
            </div>
          </div>

          {messages.map((msg, i) => (
            <div key={i}>
              {msg.role === 'user' ? (
                <div className="flex justify-end">
                  <div className="bg-sky-500 text-white rounded-lg rounded-tr-none px-3 py-2 max-w-[85%]">
                    <p className="text-sm">{msg.content}</p>
                  </div>
                </div>
              ) : (
                <div className="flex gap-2">
                  <div className="w-6 h-6 bg-sky-100 rounded-full flex items-center justify-center flex-shrink-0 mt-1">
                    <MessageSquare className="w-3 h-3 text-sky-500" />
                  </div>
                  <div className="max-w-[85%] space-y-1.5">
                    <div className="bg-white rounded-lg rounded-tl-none px-3 py-2 shadow-sm">
                      <p className="text-sm text-gray-700">{msg.content}</p>
                    </div>
                    {msg.citations && renderCitations(msg.citations)}
                  </div>
                </div>
              )}
            </div>
          ))}

          {/* Streaming content */}
          {isTyping && streamingContent && (
            <div className="flex gap-2">
              <div className="w-6 h-6 bg-sky-100 rounded-full flex items-center justify-center flex-shrink-0 mt-1">
                <MessageSquare className="w-3 h-3 text-sky-500" />
              </div>
              <div className="max-w-[85%]">
                <div className="bg-white rounded-lg rounded-tl-none px-3 py-2 shadow-sm">
                  <p className="text-sm text-gray-700">{streamingContent}</p>
                </div>
              </div>
            </div>
          )}

          {/* Typing indicator (no content yet) */}
          {isTyping && !streamingContent && (
            <div className="flex gap-2">
              <div className="w-6 h-6 bg-sky-100 rounded-full flex items-center justify-center flex-shrink-0 mt-1">
                <MessageSquare className="w-3 h-3 text-sky-500" />
              </div>
              <div className="bg-white rounded-lg rounded-tl-none px-3 py-2 shadow-sm">
                <div className="flex gap-1">
                  <span
                    className="w-1.5 h-1.5 bg-gray-400 rounded-full animate-bounce"
                    style={{ animationDelay: '0ms' }}
                  />
                  <span
                    className="w-1.5 h-1.5 bg-gray-400 rounded-full animate-bounce"
                    style={{ animationDelay: '150ms' }}
                  />
                  <span
                    className="w-1.5 h-1.5 bg-gray-400 rounded-full animate-bounce"
                    style={{ animationDelay: '300ms' }}
                  />
                </div>
              </div>
            </div>
          )}

          {/* Error message */}
          {error && (
            <div className="flex gap-2">
              <div className="w-6 h-6 bg-red-100 rounded-full flex items-center justify-center flex-shrink-0 mt-1">
                <AlertCircle className="w-3 h-3 text-red-500" />
              </div>
              <div className="bg-red-50 rounded-lg rounded-tl-none px-3 py-2 shadow-sm max-w-[85%]">
                <p className="text-sm text-red-600">{error}</p>
              </div>
            </div>
          )}
        </div>

        {/* Interactive input */}
        <div className="p-3 border-t border-gray-200 bg-white">
          <div className="flex items-center gap-2">
            <input
              ref={inputRef}
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Ask anything about your docs..."
              disabled={isTyping}
              maxLength={500}
              className="flex-1 text-sm px-3 py-2 bg-gray-100 rounded-lg outline-none focus:ring-2 focus:ring-sky-500 text-gray-900 placeholder:text-gray-400 disabled:opacity-50"
            />
            <button
              onClick={handleSend}
              disabled={!input.trim() || isTyping}
              className="w-8 h-8 bg-sky-500 rounded-lg flex items-center justify-center text-white hover:bg-sky-600 transition disabled:bg-gray-300 disabled:cursor-not-allowed"
            >
              <Send className="w-4 h-4" />
            </button>
          </div>
          <p className="text-xs text-gray-400 mt-1.5 text-center">
            {isLive ? 'Answers grounded in your documents' : 'Every answer backed by source citations'}
          </p>
        </div>
      </div>
    </div>
  );
}

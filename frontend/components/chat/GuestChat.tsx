"use client";

import { useEffect, useState, useRef, useCallback } from "react";
import {
  Send,
  Sparkles,
  User,
  FileText,
  MessageSquare,
  ArrowRight,
} from "lucide-react";
import { publicApi } from "@/lib/public-api";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "";

interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  citations?: Array<{ source: string; content: string }>;
}

const SUGGESTED_QUESTIONS = [
  "What is RAG and how does it work?",
  "What are the best use cases for a RAG chatbot?",
  "How does citation-backed answering work?",
  "Can I deploy this on WhatsApp or my website?",
];

export function GuestChat() {
  const demoToken = process.env.NEXT_PUBLIC_DEMO_SHARE_TOKEN;
  const [widgetId, setWidgetId] = useState<string | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [isStreaming, setIsStreaming] = useState(false);
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    if (!demoToken) {
      setError("Chat demo is not configured");
      return;
    }
    publicApi
      .widgetId(demoToken)
      .then((data) => setWidgetId(data.widget_id))
      .catch(() => setError("Chat is not configured for this workspace"));
  }, [demoToken]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const sendMessageText = useCallback(
    async (text: string) => {
      if (!text.trim() || !widgetId || isStreaming) return;

      const userMessage: ChatMessage = {
        id: `user-${Date.now()}`,
        role: "user",
        content: text.trim(),
      };

      setMessages((prev) => [...prev, userMessage]);
      setInput("");
      setIsStreaming(true);
      setError(null);

      const assistantId = `assistant-${Date.now()}`;
      setMessages((prev) => [
        ...prev,
        { id: assistantId, role: "assistant", content: "" },
      ]);

      try {
        const body: Record<string, string> = { message: userMessage.content };
        if (conversationId) body.conversation_id = conversationId;

        const response = await fetch(
          `${API_URL}/api/v1/widget/${widgetId}/chat`,
          {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(body),
          }
        );

        if (!response.ok) throw new Error(`HTTP ${response.status}`);

        const reader = response.body?.getReader();
        if (!reader) throw new Error("No response stream");

        const decoder = new TextDecoder();
        let buffer = "";
        let fullContent = "";
        let currentEvent = "";

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split("\n");
          buffer = lines.pop() || "";

          for (const line of lines) {
            if (line.startsWith("event: ")) {
              currentEvent = line.slice(7).trim();
              continue;
            }
            if (!line.startsWith("data: ")) continue;
            const data = line.slice(6).trim();
            if (!data) continue;

            try {
              const parsed = JSON.parse(data);
              const eventType = currentEvent || parsed.type;

              if (
                eventType === "token" &&
                (parsed.token || parsed.content)
              ) {
                fullContent += parsed.token || parsed.content;
                setMessages((prev) =>
                  prev.map((m) =>
                    m.id === assistantId
                      ? { ...m, content: fullContent }
                      : m
                  )
                );
              } else if (eventType === "done") {
                if (parsed.conversation_id)
                  setConversationId(parsed.conversation_id);
                if (parsed.citations) {
                  const citations = parsed.citations.map(
                    (c: {
                      doc_name?: string;
                      source?: string;
                      chunk_text?: string;
                      content?: string;
                    }) => ({
                      source: c.doc_name || c.source || "Unknown",
                      content: c.chunk_text || c.content || "",
                    })
                  );
                  setMessages((prev) =>
                    prev.map((m) =>
                      m.id === assistantId ? { ...m, citations } : m
                    )
                  );
                }
              } else if (eventType === "error") {
                setError(parsed.message || "An error occurred");
              }
              currentEvent = "";
            } catch {
              // Skip malformed JSON
            }
          }
        }
      } catch (err) {
        setError(
          err instanceof Error ? err.message : "Failed to send message"
        );
        setMessages((prev) => prev.filter((m) => m.id !== assistantId));
      } finally {
        setIsStreaming(false);
      }
    },
    [widgetId, isStreaming, conversationId]
  );

  const sendMessage = useCallback(() => {
    sendMessageText(input);
  }, [input, sendMessageText]);

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  if (error && !widgetId) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="text-center">
          <Sparkles className="w-12 h-12 text-gray-300 mx-auto mb-4" />
          <p className="text-gray-500">{error}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-[calc(100vh-3.5rem)] max-w-3xl mx-auto px-4">
      {/* Messages */}
      <div className="flex-1 overflow-y-auto space-y-4 py-4">
        {messages.length === 0 && (
          <div className="flex flex-col items-center justify-center h-full text-center px-4">
            {/* Icon */}
            <div className="relative mb-6">
              <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-sky-50 to-sky-100 dark:from-sky-900/40 dark:to-sky-800/30 flex items-center justify-center">
                <MessageSquare className="w-7 h-7 text-sky-500" />
              </div>
              <div className="absolute -top-1 -right-1 w-5 h-5 rounded-full bg-green-400 border-2 border-white dark:border-gray-900 flex items-center justify-center">
                <span className="w-2 h-2 rounded-full bg-white" />
              </div>
            </div>

            {/* Heading */}
            <h2 className="text-2xl font-semibold text-gray-900 dark:text-white mb-2">
              Try the live chatbot
            </h2>
            <p className="text-gray-500 dark:text-gray-400 max-w-md mb-8 leading-relaxed">
              This AI is trained on real documents. Ask a question and
              see how it responds with source citations.
            </p>

            {/* Suggested questions */}
            <div className="w-full max-w-lg">
              <p className="text-xs font-medium text-gray-400 dark:text-gray-500 uppercase tracking-wider mb-3">
                Try asking
              </p>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                {SUGGESTED_QUESTIONS.map((q) => (
                  <button
                    key={q}
                    onClick={() => sendMessageText(q)}
                    disabled={isStreaming || !widgetId}
                    className="group flex items-center gap-2 px-4 py-3 text-left text-sm text-gray-700 dark:text-gray-300 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-xl hover:border-sky-300 dark:hover:border-sky-700 hover:bg-sky-50/50 dark:hover:bg-sky-900/20 transition-all disabled:opacity-40 disabled:cursor-not-allowed"
                  >
                    <span className="flex-1">{q}</span>
                    <ArrowRight className="w-3.5 h-3.5 text-gray-300 dark:text-gray-600 group-hover:text-sky-500 transition-colors flex-shrink-0" />
                  </button>
                ))}
              </div>
            </div>
          </div>
        )}

        {messages.map((msg) => (
          <div
            key={msg.id}
            className={`flex gap-3 ${msg.role === "user" ? "justify-end" : ""}`}
          >
            {msg.role === "assistant" && (
              <div className="w-8 h-8 rounded-lg bg-sky-50 dark:bg-sky-900/30 flex items-center justify-center flex-shrink-0 mt-0.5">
                <Sparkles className="w-4 h-4 text-sky-500" />
              </div>
            )}
            <div
              className={`max-w-[80%] rounded-2xl px-4 py-3 ${
                msg.role === "user"
                  ? "bg-sky-500 text-white"
                  : "bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 text-gray-900 dark:text-gray-100"
              }`}
            >
              <p className="whitespace-pre-wrap text-sm leading-relaxed">
                {msg.content || (
                  <span className="inline-flex gap-1">
                    <span className="w-2 h-2 bg-gray-300 rounded-full animate-bounce" />
                    <span className="w-2 h-2 bg-gray-300 rounded-full animate-bounce [animation-delay:150ms]" />
                    <span className="w-2 h-2 bg-gray-300 rounded-full animate-bounce [animation-delay:300ms]" />
                  </span>
                )}
              </p>
              {msg.citations && msg.citations.length > 0 && (
                <div className="mt-3 pt-3 border-t border-gray-100 dark:border-gray-700">
                  <p className="text-xs font-medium text-gray-500 dark:text-gray-400 mb-2">
                    Sources
                  </p>
                  <div className="space-y-1.5">
                    {msg.citations.map((c, i) => (
                      <div
                        key={i}
                        className="flex items-start gap-2 text-xs text-gray-500 dark:text-gray-400"
                      >
                        <FileText className="w-3 h-3 mt-0.5 flex-shrink-0" />
                        <span className="truncate">{c.source}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
            {msg.role === "user" && (
              <div className="w-8 h-8 rounded-lg bg-gray-100 dark:bg-gray-800 flex items-center justify-center flex-shrink-0 mt-0.5">
                <User className="w-4 h-4 text-gray-500" />
              </div>
            )}
          </div>
        ))}
        <div ref={messagesEndRef} />
      </div>

      {/* Error */}
      {error && widgetId && (
        <div className="mx-auto mb-2 px-3 py-1.5 bg-red-50 dark:bg-red-900/20 text-red-600 dark:text-red-400 text-xs rounded-lg">
          {error}
        </div>
      )}

      {/* Input */}
      <div className="pb-4 pt-3">
        <div className="flex items-end gap-2 bg-white dark:bg-gray-800 rounded-2xl border border-gray-300 dark:border-gray-600 px-4 py-2.5 shadow-md focus-within:border-sky-400 dark:focus-within:border-sky-600 focus-within:ring-2 focus-within:ring-sky-100 dark:focus-within:ring-sky-900/30 transition-all">
          <textarea
            ref={inputRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Ask a question about RAG chatbots..."
            rows={1}
            className="flex-1 resize-none bg-transparent text-sm text-gray-900 dark:text-white placeholder-gray-400 focus:outline-none max-h-32 py-1"
            disabled={isStreaming || !widgetId}
          />
          <button
            onClick={sendMessage}
            disabled={!input.trim() || isStreaming || !widgetId}
            className="p-2 rounded-xl bg-sky-500 text-white hover:bg-sky-600 disabled:bg-gray-200 dark:disabled:bg-gray-700 disabled:text-gray-400 disabled:cursor-not-allowed transition-colors flex-shrink-0"
          >
            <Send className="w-4 h-4" />
          </button>
        </div>
      </div>
    </div>
  );
}

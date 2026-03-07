"use client";

import { useAuth } from "@/providers/auth";
import { useEffect, useState } from "react";
import Link from "next/link";
import {
  MessageSquare,
  Upload,
  AlertTriangle,
  FileText,
  TrendingUp,
  Phone,
  Share2,
  BarChart3,
  ArrowRight,
  Map,
  Sparkles,
  Globe,
  Shield,
  Search,
  Zap,
  MessagesSquare,
} from "lucide-react";
import { useOnboardingProgress } from "@/hooks/useOnboarding";
import OnboardingWizard from "@/components/onboarding/OnboardingWizard";
import { useSkin } from "@/providers/skin";
import { publicApi } from "@/lib/public-api";
import { toast } from "sonner";

interface DashboardSummary {
  conversations_count: number;
  messages_count: number;
  documents_count: number;
  knowledge_gaps_count: number;
  avg_quality_score: number | null;
  recent_conversations: Array<{
    id: string;
    first_message: string;
    last_message_at: string;
    message_count: number;
    sentiment: "positive" | "neutral" | "negative" | null;
  }>;
  features: {
    rag_enabled: boolean;
    voice_enabled: boolean;
    channels_enabled: boolean;
    analytics_enabled: boolean;
  };
}

export default function DashboardPage() {
  const { user, isLoading } = useAuth();
  const { isRagchat } = useSkin();
  const [summary, setSummary] = useState<DashboardSummary | null>(null);
  const [summaryLoading, setSummaryLoading] = useState(true);
  const [dismissedOnboarding, setDismissedOnboarding] = useState(false);
  const onboarding = useOnboardingProgress();

  // RAGChat standalone: always show guest/demo view
  const isGuest = isRagchat || (!isLoading && !user);
  const effectiveUser = isRagchat ? null : user;
  const demoToken = process.env.NEXT_PUBLIC_DEMO_SHARE_TOKEN;

  useEffect(() => {
    const fetchSummary = async () => {
      try {
        if (effectiveUser) {
          // Authenticated: use normal API
          const apiUrl = process.env.NEXT_PUBLIC_API_URL || "";
          const response = await fetch(`${apiUrl}/api/v1/dashboard/summary`, {
            credentials: "include",
          });
          if (response.ok) {
            const data = await response.json();
            setSummary(data);
          }
        } else if (demoToken) {
          // Guest mode: use public API
          const data = await publicApi.dashboard(demoToken);
          setSummary({
            conversations_count: data.conversations_count,
            messages_count: data.messages_count,
            documents_count: data.documents_count,
            knowledge_gaps_count: data.knowledge_gaps_count,
            avg_quality_score: data.avg_quality_score,
            recent_conversations: [],
            features: {
              rag_enabled: true,
              voice_enabled: false,
              channels_enabled: false,
              analytics_enabled: true,
            },
          });
        }
      } catch (error) {
        console.error("Failed to fetch dashboard summary:", error);
      } finally {
        setSummaryLoading(false);
      }
    };

    if (!isLoading) {
      fetchSummary();
    }
  }, [isLoading, effectiveUser, demoToken]);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  return (
    <div className="container mx-auto px-6 py-8 max-w-7xl">
      {/* Welcome */}
      <div className="mb-8 flex items-start justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900 dark:text-white mb-2">
            {isGuest
              ? isRagchat ? "RAGChat Dashboard" : "Dashboard"
              : `Welcome${effectiveUser?.name ? `, ${effectiveUser.name}` : ""}`}
          </h1>
          <p className="text-gray-600 dark:text-gray-400">
            {isGuest
              ? "AI-powered chatbot performance at a glance."
              : "Manage your AI chatbot, upload documents, and track conversations."}
          </p>
        </div>
        {effectiveUser && (
          <button
            onClick={() => {
              localStorage.removeItem("botforge_tour_completed");
              localStorage.removeItem("botforge_tour_step");
              window.dispatchEvent(new CustomEvent("botforge:start-tour"));
              window.location.reload();
            }}
            className="flex-shrink-0 inline-flex items-center gap-2 px-4 py-2 text-sm font-medium text-blue-600 bg-blue-50 border border-blue-200 rounded-lg hover:bg-blue-100 transition"
            data-testid="take-tour-button"
          >
            <Map className="w-4 h-4" />
            Take the Tour
          </button>
        )}
        {isGuest && !isRagchat && (
          <Link
            href="/login"
            className="flex-shrink-0 inline-flex items-center gap-2 px-4 py-2 text-sm font-medium text-white bg-sky-500 rounded-lg hover:bg-sky-600 transition"
          >
            Login to Manage
          </Link>
        )}
      </div>

      {/* Onboarding Wizard — shown only for authenticated users */}
      {effectiveUser && !onboarding.isLoading &&
        onboarding.data &&
        !onboarding.data.completed_at &&
        !dismissedOnboarding && (
          <div className="mb-8">
            <OnboardingWizard
              onDismiss={() => setDismissedOnboarding(true)}
            />
          </div>
        )}

      {/* Stats */}
      {!summaryLoading && summary && (
        <div className="mb-8 grid grid-cols-1 md:grid-cols-4 gap-4">
          <div className="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-lg p-5">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-600 dark:text-gray-400 mb-1">Conversations</p>
                <p className="text-2xl font-bold text-gray-900 dark:text-white">
                  {summary.conversations_count}
                </p>
              </div>
              <MessageSquare className="w-8 h-8 text-sky-500 opacity-20" />
            </div>
          </div>
          <div className="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-lg p-5">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-600 dark:text-gray-400 mb-1">Documents</p>
                <p className="text-2xl font-bold text-gray-900 dark:text-white">
                  {summary.documents_count}
                </p>
              </div>
              <FileText className="w-8 h-8 text-sky-500 opacity-20" />
            </div>
          </div>
          <div className="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-lg p-5">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-600 dark:text-gray-400 mb-1">Knowledge Gaps</p>
                <p className="text-2xl font-bold text-gray-900 dark:text-white">
                  {summary.knowledge_gaps_count}
                </p>
              </div>
              <AlertTriangle className="w-8 h-8 text-amber-500 opacity-20" />
            </div>
          </div>
          <div className="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-lg p-5">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-600 dark:text-gray-400 mb-1">Quality Score</p>
                <p className="text-2xl font-bold text-gray-900 dark:text-white">
                  {summary.avg_quality_score !== null
                    ? `${Math.round(summary.avg_quality_score * 100)}%`
                    : "—"}
                </p>
              </div>
              <TrendingUp className="w-8 h-8 text-emerald-500 opacity-20" />
            </div>
          </div>
        </div>
      )}

      {/* Quick Actions — context-aware */}
      {isRagchat && isGuest ? (
        /* RAGChat guest: show capabilities instead of admin actions */
        <div className="mb-8">
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">What This Chatbot Can Do</h2>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {[
              { icon: Sparkles, title: "Citation-Backed Answers", desc: "Every response includes source references from uploaded documents.", color: "text-sky-500", bg: "bg-sky-50" },
              { icon: Search, title: "Knowledge Gap Detection", desc: "AI identifies questions it can't answer so you know what to improve.", color: "text-amber-500", bg: "bg-amber-50" },
              { icon: Globe, title: "Omni-Channel Deploy", desc: "Website widget, WhatsApp, Telegram, API — one knowledge base everywhere.", color: "text-violet-500", bg: "bg-violet-50" },
              { icon: BarChart3, title: "Real-time Analytics", desc: "Sentiment analysis, quality scores, top questions — all tracked live.", color: "text-emerald-500", bg: "bg-emerald-50" },
              { icon: Shield, title: "Production Grade", desc: "Rate limiting, HMAC auth, LLM failover, streaming responses.", color: "text-rose-500", bg: "bg-rose-50" },
              { icon: Zap, title: "Instant Setup", desc: "Upload documents, get a working AI chatbot in under 5 minutes.", color: "text-orange-500", bg: "bg-orange-50" },
            ].map((cap) => {
              const Icon = cap.icon;
              return (
                <div key={cap.title} className="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-xl p-5">
                  <div className={`w-9 h-9 ${cap.bg} dark:bg-opacity-20 rounded-lg flex items-center justify-center mb-3`}>
                    <Icon className={`w-4.5 h-4.5 ${cap.color}`} />
                  </div>
                  <h3 className="text-sm font-semibold text-gray-900 dark:text-white mb-1">{cap.title}</h3>
                  <p className="text-xs text-gray-500 dark:text-gray-400 leading-relaxed">{cap.desc}</p>
                </div>
              );
            })}
          </div>
          {/* Explore sections */}
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white mt-8 mb-4">Explore the Data</h2>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <Link
              href="/conversations"
              className="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-xl p-5 hover:border-sky-300 dark:hover:border-sky-700 hover:shadow-md transition group"
            >
              <MessagesSquare className="w-7 h-7 text-sky-500 mb-3" />
              <h3 className="text-sm font-semibold text-gray-900 dark:text-white mb-1 group-hover:text-sky-600 dark:group-hover:text-sky-400">Conversations</h3>
              <p className="text-xs text-gray-500 dark:text-gray-400 leading-relaxed mb-3">Browse real conversations handled by the AI with sentiment and citations.</p>
              <span className="inline-flex items-center gap-1 text-xs text-sky-600 dark:text-sky-400 font-medium">
                View All <ArrowRight className="w-3 h-3" />
              </span>
            </Link>
            <Link
              href="/kb"
              className="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-xl p-5 hover:border-sky-300 dark:hover:border-sky-700 hover:shadow-md transition group"
            >
              <FileText className="w-7 h-7 text-sky-500 mb-3" />
              <h3 className="text-sm font-semibold text-gray-900 dark:text-white mb-1 group-hover:text-sky-600 dark:group-hover:text-sky-400">Knowledge Base</h3>
              <p className="text-xs text-gray-500 dark:text-gray-400 leading-relaxed mb-3">See the indexed documents powering this chatbot&apos;s answers.</p>
              <span className="inline-flex items-center gap-1 text-xs text-sky-600 dark:text-sky-400 font-medium">
                View Documents <ArrowRight className="w-3 h-3" />
              </span>
            </Link>
            <Link
              href="/kb?tab=gaps"
              className="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-xl p-5 hover:border-amber-300 dark:hover:border-amber-700 hover:shadow-md transition group"
            >
              <AlertTriangle className="w-7 h-7 text-amber-500 mb-3" />
              <h3 className="text-sm font-semibold text-gray-900 dark:text-white mb-1 group-hover:text-amber-600 dark:group-hover:text-amber-400">Knowledge Gaps</h3>
              <p className="text-xs text-gray-500 dark:text-gray-400 leading-relaxed mb-3">Questions the AI couldn&apos;t answer — gaps detected automatically.</p>
              <span className="inline-flex items-center gap-1 text-xs text-amber-600 dark:text-amber-400 font-medium">
                View Gaps <ArrowRight className="w-3 h-3" />
              </span>
            </Link>
          </div>

          {/* Configure section — visible but locked for guests */}
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white mt-8 mb-4">Manage &amp; Configure</h2>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {[
              { icon: Sparkles, title: "Bot Personality", desc: "Customize the AI's tone, name, and system prompt.", href: "/settings?tab=general" },
              { icon: Upload, title: "Upload Documents", desc: "Add PDFs, Word docs, or text to the knowledge base.", href: "/kb" },
              { icon: Globe, title: "Channels", desc: "Deploy to WhatsApp, Telegram, website widget, and more.", href: "/settings?tab=integrations" },
              { icon: Phone, title: "Voice Agent", desc: "Configure AI phone agent with smart escalation rules.", href: "/settings?tab=voice" },
              { icon: Shield, title: "API Keys", desc: "Manage API keys for programmatic access.", href: "/settings?tab=api" },
              { icon: Zap, title: "Webhooks", desc: "Set up event webhooks for real-time integrations.", href: "/settings?tab=webhooks" },
            ].map((item) => {
              const Icon = item.icon;
              return (
                <button
                  key={item.title}
                  onClick={() => toast.info("This requires authentication. Order on Fiverr to get your own fully configurable instance!")}
                  className="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-xl p-5 text-left opacity-75 hover:opacity-100 transition group cursor-not-allowed"
                >
                  <div className="flex items-center gap-3 mb-2">
                    <Icon className="w-5 h-5 text-gray-400 dark:text-gray-500" />
                    <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-300">{item.title}</h3>
                    <span className="ml-auto text-[10px] px-1.5 py-0.5 bg-gray-100 dark:bg-gray-800 text-gray-500 dark:text-gray-400 rounded font-medium">LOCKED</span>
                  </div>
                  <p className="text-xs text-gray-400 dark:text-gray-500 leading-relaxed">{item.desc}</p>
                </button>
              );
            })}
          </div>

          <div className="mt-6 flex flex-col sm:flex-row items-center gap-3">
            <Link
              href="/chat"
              className="inline-flex items-center gap-2 px-5 py-2.5 text-sm font-medium bg-sky-500 text-white rounded-lg hover:bg-sky-600 transition"
            >
              Try the Chat <ArrowRight className="w-4 h-4" />
            </Link>
            <Link
              href="/why-ragchat"
              className="inline-flex items-center gap-2 px-5 py-2.5 text-sm font-medium text-sky-600 bg-sky-50 rounded-lg hover:bg-sky-100 transition"
            >
              Want this for your business? <ArrowRight className="w-4 h-4" />
            </Link>
          </div>
        </div>
      ) : (
        /* Normal quick actions for admin users */
        <>
          <div className="mb-8">
            <h2 className="text-lg font-semibold text-gray-900 mb-4">Get Started</h2>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <Link
                href="/chat"
                className="bg-white border-2 border-blue-100 rounded-lg p-6 hover:border-blue-300 hover:shadow-md transition group"
              >
                <MessageSquare className="w-8 h-8 text-blue-600 mb-3" />
                <h3 className="text-lg font-semibold mb-1 group-hover:text-blue-600">
                  Chat with AI
                </h3>
                <p className="text-sm text-gray-600 mb-3">
                  Ask questions and get answers from your knowledge base with source citations.
                </p>
                <span className="inline-flex items-center gap-1 text-sm text-blue-600 font-medium">
                  Open Chat <ArrowRight className="w-4 h-4" />
                </span>
              </Link>

              <Link
                href="/kb"
                className="bg-white border-2 border-blue-100 rounded-lg p-6 hover:border-blue-300 hover:shadow-md transition group"
              >
                <Upload className="w-8 h-8 text-blue-600 mb-3" />
                <h3 className="text-lg font-semibold mb-1 group-hover:text-blue-600">
                  Upload Documents
                </h3>
                <p className="text-sm text-gray-600 mb-3">
                  Add PDFs, Word docs, or text files. They get parsed and embedded automatically.
                </p>
                <span className="inline-flex items-center gap-1 text-sm text-blue-600 font-medium">
                  Manage KB <ArrowRight className="w-4 h-4" />
                </span>
              </Link>

              <Link
                href="/kb?tab=gaps"
                className="bg-white border-2 border-blue-100 rounded-lg p-6 hover:border-blue-300 hover:shadow-md transition group"
              >
                <AlertTriangle className="w-8 h-8 text-amber-600 mb-3" />
                <h3 className="text-lg font-semibold mb-1 group-hover:text-blue-600">
                  Knowledge Gaps
                </h3>
                <p className="text-sm text-gray-600 mb-3">
                  See questions your bot couldn&apos;t answer and fill content gaps.
                </p>
                <span className="inline-flex items-center gap-1 text-sm text-blue-600 font-medium">
                  View Gaps <ArrowRight className="w-4 h-4" />
                </span>
              </Link>
            </div>
          </div>

          {/* Features — only show for non-ragchat skins */}
          {!isRagchat && (
            <div className="mb-8">
              <h2 className="text-lg font-semibold text-gray-900 mb-4">All Features</h2>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <Link
                  href="/chat"
                  className="bg-white border border-gray-200 rounded-lg p-6 hover:border-blue-300 transition"
                >
                  <div className="flex items-center justify-between mb-2">
                    <div className="flex items-center gap-3">
                      <MessageSquare className="w-5 h-5 text-blue-600" />
                      <h3 className="text-lg font-semibold">RAG Chat</h3>
                    </div>
                    <span className="text-xs bg-green-100 text-green-700 px-2 py-1 rounded-full font-medium">
                      Active
                    </span>
                  </div>
                  <p className="text-gray-600 text-sm">
                    AI-powered chat with document-based answers and source citations
                  </p>
                </Link>

                <Link
                  href="/voice"
                  className="bg-white border border-gray-200 rounded-lg p-6 hover:border-green-300 transition"
                >
                  <div className="flex items-center justify-between mb-2">
                    <div className="flex items-center gap-3">
                      <Phone className="w-5 h-5 text-green-600" />
                      <h3 className="text-lg font-semibold">VoiceBot Pro</h3>
                    </div>
                    <span className="text-xs bg-green-100 text-green-700 px-2 py-1 rounded-full font-medium">
                      {summary?.features.voice_enabled ? "Active" : "Setup Required"}
                    </span>
                  </div>
                  <p className="text-gray-600 text-sm">
                    AI phone agent with voice conversations and smart escalation
                  </p>
                </Link>

                <Link
                  href="/channels"
                  className="bg-white border border-gray-200 rounded-lg p-6 hover:border-gray-300 transition"
                >
                  <div className="flex items-center justify-between mb-2">
                    <div className="flex items-center gap-3">
                      <Share2 className="w-5 h-5 text-purple-600" />
                      <h3 className="text-lg font-semibold">Multi-Channel</h3>
                    </div>
                    <span className="text-xs bg-green-100 text-green-700 px-2 py-1 rounded-full font-medium">
                      Active
                    </span>
                  </div>
                  <p className="text-gray-600 text-sm">
                    Deploy to WhatsApp, Telegram, and your website
                  </p>
                </Link>

                <Link
                  href="/analytics"
                  className="bg-white border border-gray-200 rounded-lg p-6 hover:border-blue-300 transition"
                >
                  <div className="flex items-center justify-between mb-2">
                    <div className="flex items-center gap-3">
                      <BarChart3 className="w-5 h-5 text-blue-600" />
                      <h3 className="text-lg font-semibold">Analytics</h3>
                    </div>
                    <span className="text-xs bg-green-100 text-green-700 px-2 py-1 rounded-full font-medium">
                      Active
                    </span>
                  </div>
                  <p className="text-gray-600 text-sm">
                    Track conversations, quality, and user satisfaction
                  </p>
                </Link>
              </div>
            </div>
          )}
        </>
      )}

      {/* Recent Conversations */}
      {!summaryLoading && summary && summary.recent_conversations.length > 0 && (
        <div className="mb-8">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold text-gray-900">
              Recent Conversations
            </h2>
            <Link
              href="/chat"
              className="text-sm text-blue-600 hover:text-blue-700 font-medium"
            >
              View All
            </Link>
          </div>
          <div className="bg-white border border-gray-200 rounded-lg divide-y divide-gray-200">
            {summary.recent_conversations.map((conv) => (
              <Link
                key={conv.id}
                href={`/chat?conversation=${conv.id}`}
                className="block p-4 hover:bg-gray-50 transition"
              >
                <div className="flex items-start justify-between gap-4">
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-gray-900 truncate mb-1">
                      {conv.first_message}
                    </p>
                    <div className="flex items-center gap-3 text-xs text-gray-500">
                      <span className="flex items-center gap-1">
                        <MessageSquare className="w-3 h-3" />
                        {conv.message_count} messages
                      </span>
                      <span>
                        {new Date(conv.last_message_at).toLocaleDateString("en-US", {
                          month: "short",
                          day: "numeric",
                          hour: "numeric",
                          minute: "2-digit",
                        })}
                      </span>
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    {conv.sentiment && (
                      <span
                        className={`text-xs px-2 py-1 rounded-full font-medium ${
                          conv.sentiment === "positive"
                            ? "bg-green-100 text-green-700"
                            : conv.sentiment === "negative"
                            ? "bg-red-100 text-red-700"
                            : "bg-gray-100 text-gray-700"
                        }`}
                      >
                        {conv.sentiment}
                      </span>
                    )}
                    <Link
                      href={`/debug/${conv.id}`}
                      onClick={(e) => e.stopPropagation()}
                      className="p-1 rounded hover:bg-blue-100 text-gray-400 hover:text-blue-600 transition"
                      title="Debug view"
                    >
                      <BarChart3 className="w-4 h-4" />
                    </Link>
                  </div>
                </div>
              </Link>
            ))}
          </div>
        </div>
      )}

      {/* Account Info */}
      {effectiveUser && (
        <div className="bg-white border border-gray-200 rounded-lg p-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">
            Account
          </h2>
          <dl className="grid grid-cols-1 md:grid-cols-3 gap-4 text-sm">
            <div>
              <dt className="text-gray-500 mb-1">Email</dt>
              <dd className="text-gray-900 font-medium">{effectiveUser.email}</dd>
            </div>
            <div>
              <dt className="text-gray-500 mb-1">Role</dt>
              <dd className="text-gray-900 font-medium capitalize">{effectiveUser.role}</dd>
            </div>
            <div>
              <dt className="text-gray-500 mb-1">Account Type</dt>
              <dd>
                <span className="inline-flex items-center px-2.5 py-0.5 rounded text-xs font-medium bg-green-100 text-green-800">
                  Full Account
                </span>
              </dd>
            </div>
          </dl>
        </div>
      )}
    </div>
  );
}

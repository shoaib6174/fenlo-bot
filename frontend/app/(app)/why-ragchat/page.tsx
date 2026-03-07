"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import {
  ArrowRight,
  CheckCircle2,
  Sparkles,
  MessageSquare,
  FileText,
  Globe,
  Shield,
  Zap,
  Search,
  BarChart3,
  Upload,
  Bot,
  Smartphone,
  Code2,
  TrendingUp,
  Users,
} from "lucide-react";
import { publicApi } from "@/lib/public-api";

interface DemoStats {
  conversations_count: number;
  documents_count: number;
  avg_quality_score: number | null;
}

const FEATURES = [
  {
    icon: MessageSquare,
    title: "Citation-Backed Answers",
    description: "Every response references the exact document and page. Users can verify every claim.",
    color: "text-sky-500",
    bg: "bg-sky-50 dark:bg-sky-950/30",
  },
  {
    icon: Upload,
    title: "Document Intelligence",
    description: "Upload PDFs, Word docs, or text files. Auto-chunking, embedding, and vector indexing.",
    color: "text-violet-500",
    bg: "bg-violet-50 dark:bg-violet-950/30",
  },
  {
    icon: Search,
    title: "Knowledge Gap Detection",
    description: "AI identifies questions it can't answer so you know exactly what content to add next.",
    color: "text-amber-500",
    bg: "bg-amber-50 dark:bg-amber-950/30",
  },
  {
    icon: BarChart3,
    title: "Real-Time Analytics",
    description: "Sentiment analysis, quality scores, top questions, and volume trends — all live.",
    color: "text-emerald-500",
    bg: "bg-emerald-50 dark:bg-emerald-950/30",
  },
  {
    icon: Zap,
    title: "Streaming Responses",
    description: "Token-by-token streaming with sub-second first response. Semantic cache for repeat queries.",
    color: "text-orange-500",
    bg: "bg-orange-50 dark:bg-orange-950/30",
  },
  {
    icon: Shield,
    title: "Production Grade",
    description: "Rate limiting, HMAC auth, LLM circuit breaker with auto-failover, workspace isolation.",
    color: "text-rose-500",
    bg: "bg-rose-50 dark:bg-rose-950/30",
  },
];

const CHANNELS = [
  {
    icon: Globe,
    title: "Website Widget",
    description: "Embed a floating chat bubble on any website. Customize colors, name, and position.",
    tag: "Most Popular",
  },
  {
    icon: Smartphone,
    title: "WhatsApp Business",
    description: "Customers message on WhatsApp and get AI-powered answers from your knowledge base.",
    tag: "Global Reach",
  },
  {
    icon: Bot,
    title: "Telegram Bot",
    description: "Deploy as a Telegram bot. Users chat directly — even in group conversations.",
    tag: "Easy Setup",
  },
  {
    icon: Code2,
    title: "REST API",
    description: "Full API with WebSocket & SSE streaming. Build custom interfaces or integrate into any app.",
    tag: "Developer",
  },
];

const USE_CASES = [
  {
    title: "Customer Support",
    description: "Deflect 60-80% of support tickets. AI answers product questions with citations from your help docs.",
    icon: Users,
    stat: "80%",
    statLabel: "ticket deflection",
  },
  {
    title: "Product Documentation",
    description: "Turn 100+ page manuals into an interactive assistant. Users find answers in seconds, not hours.",
    icon: FileText,
    stat: "10x",
    statLabel: "faster answers",
  },
  {
    title: "Internal Knowledge Base",
    description: "Onboard new employees faster. AI trained on company policies, processes, and institutional knowledge.",
    icon: Search,
    stat: "3x",
    statLabel: "faster onboarding",
  },
  {
    title: "Sales Enablement",
    description: "AI qualifies leads by answering pricing, feature, and comparison questions 24/7.",
    icon: TrendingUp,
    stat: "24/7",
    statLabel: "availability",
  },
];

const TECH_STACK = [
  { label: "FastAPI + Python 3.12", category: "Backend" },
  { label: "Next.js 15 + React 19", category: "Frontend" },
  { label: "PostgreSQL + Redis", category: "Database" },
  { label: "Pinecone Vector DB", category: "Search" },
  { label: "Groq + OpenAI (failover)", category: "LLM" },
  { label: "JWT + RBAC Auth", category: "Security" },
];

export default function WhyRagchatPage() {
  const [stats, setStats] = useState<DemoStats | null>(null);
  const demoToken = process.env.NEXT_PUBLIC_DEMO_SHARE_TOKEN;

  useEffect(() => {
    if (!demoToken) return;
    publicApi
      .dashboard(demoToken)
      .then((data) => {
        setStats({
          conversations_count: data.conversations_count,
          documents_count: data.documents_count,
          avg_quality_score: data.avg_quality_score,
        });
      })
      .catch(() => {});
  }, [demoToken]);

  return (
    <div className="bg-gray-50 dark:bg-gray-950 min-h-screen">
      {/* Hero Section */}
      <section className="relative overflow-hidden">
        <div className="absolute inset-0 bg-gradient-to-b from-sky-50/80 via-transparent to-transparent dark:from-sky-950/30 dark:via-transparent" />
        <div className="relative container mx-auto px-6 pt-12 pb-16 max-w-5xl">
          <div className="text-center">
            <div className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full bg-sky-100 dark:bg-sky-900/40 text-sky-600 dark:text-sky-400 text-sm font-medium mb-6">
              <Sparkles className="w-3.5 h-3.5" />
              Omni-Channel RAG Chatbot Platform
            </div>
            <h1 className="text-4xl sm:text-5xl font-bold text-gray-900 dark:text-white mb-4 leading-tight">
              Turn Your Documents Into an
              <br />
              <span className="text-sky-500">Intelligent AI Assistant</span>
            </h1>
            <p className="text-lg text-gray-500 dark:text-gray-400 max-w-2xl mx-auto leading-relaxed mb-8">
              I build production-ready AI chatbots that answer questions with citations
              from your documents, deploy to any channel, and give you complete analytics.
              Full source code. No vendor lock-in.
            </p>
            <div className="flex flex-col sm:flex-row items-center justify-center gap-3">
              <Link
                href="/chat"
                className="w-full sm:w-auto px-7 py-3.5 text-sm font-semibold bg-sky-500 text-white rounded-xl hover:bg-sky-400 transition-all shadow-lg shadow-sky-500/20 flex items-center justify-center gap-2"
              >
                Try the Live Demo
                <ArrowRight className="w-4 h-4" />
              </Link>
              <Link
                href="/dashboard"
                className="w-full sm:w-auto px-7 py-3.5 text-sm font-medium bg-white dark:bg-gray-800 text-gray-700 dark:text-gray-300 rounded-xl hover:bg-gray-50 dark:hover:bg-gray-700 transition-all border border-gray-200 dark:border-gray-700 shadow-sm"
              >
                View Dashboard
              </Link>
            </div>
          </div>

          {/* Live stats */}
          {stats && (
            <div className="grid grid-cols-3 gap-4 mt-12 max-w-lg mx-auto">
              {[
                { value: `${stats.conversations_count}+`, label: "Conversations" },
                { value: `${stats.documents_count}`, label: "Documents" },
                { value: stats.avg_quality_score ? `${Math.round(stats.avg_quality_score * 100)}%` : "\u2014", label: "Quality Score" },
              ].map((s) => (
                <div key={s.label} className="text-center">
                  <p className="text-2xl sm:text-3xl font-bold text-gray-900 dark:text-white">
                    {s.value}
                  </p>
                  <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">{s.label}</p>
                </div>
              ))}
            </div>
          )}
        </div>
      </section>

      {/* Features Grid */}
      <section className="container mx-auto px-6 py-16 max-w-5xl">
        <div className="text-center mb-10">
          <h2 className="text-2xl sm:text-3xl font-bold text-gray-900 dark:text-white mb-3">
            Everything You Need
          </h2>
          <p className="text-gray-500 dark:text-gray-400 max-w-xl mx-auto">
            A complete RAG chatbot platform — from document ingestion to multi-channel deployment.
          </p>
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5">
          {FEATURES.map((f) => {
            const Icon = f.icon;
            return (
              <div
                key={f.title}
                className="bg-white dark:bg-gray-900 rounded-xl border border-gray-100 dark:border-gray-800 p-6 hover:shadow-md hover:border-gray-200 dark:hover:border-gray-700 transition-all"
              >
                <div className={`w-10 h-10 ${f.bg} rounded-lg flex items-center justify-center mb-4`}>
                  <Icon className={`w-5 h-5 ${f.color}`} />
                </div>
                <h3 className="text-sm font-semibold text-gray-900 dark:text-white mb-2">
                  {f.title}
                </h3>
                <p className="text-xs text-gray-500 dark:text-gray-400 leading-relaxed">
                  {f.description}
                </p>
              </div>
            );
          })}
        </div>
      </section>

      {/* Omni-Channel Section */}
      <section className="bg-white dark:bg-gray-900/50 border-y border-gray-100 dark:border-gray-800">
        <div className="container mx-auto px-6 py-16 max-w-5xl">
          <div className="text-center mb-10">
            <h2 className="text-2xl sm:text-3xl font-bold text-gray-900 dark:text-white mb-3">
              Deploy Anywhere
            </h2>
            <p className="text-gray-500 dark:text-gray-400 max-w-xl mx-auto">
              One knowledge base. Every channel. Update documents once, and every touchpoint is updated.
            </p>
          </div>

          {/* Channel diagram */}
          <div className="bg-gray-50 dark:bg-gray-800/30 rounded-2xl border border-gray-100 dark:border-gray-800 p-6 sm:p-8 mb-8">
            <div className="flex flex-col sm:flex-row items-center gap-6 sm:gap-4 justify-center">
              {/* Channels (left) */}
              <div className="flex flex-col gap-2 text-xs font-medium min-w-[140px]">
                {["Website Widget", "WhatsApp", "Telegram", "REST API"].map((ch) => (
                  <div key={ch} className="px-3 py-2 rounded-lg bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 text-gray-700 dark:text-gray-300 text-center">
                    {ch}
                  </div>
                ))}
              </div>
              {/* Arrow */}
              <div className="text-sky-400 text-xl hidden sm:block">{"\u2192"}</div>
              <div className="text-sky-400 text-xl sm:hidden">{"\u2193"}</div>
              {/* Pipeline (center) */}
              <div className="flex flex-col sm:flex-row items-center gap-3">
                {[
                  { label: "RAG Pipeline", sub: "Retrieval" },
                  { label: "Vector Search", sub: "Similarity" },
                  { label: "LLM", sub: "Generation" },
                ].map((step, i) => (
                  <div key={step.label} className="flex items-center gap-3">
                    <div className="px-4 py-3 rounded-xl bg-sky-500/10 border border-sky-500/20 text-center">
                      <p className="text-sm font-semibold text-sky-600 dark:text-sky-400">{step.label}</p>
                      <p className="text-[10px] text-gray-400 mt-0.5">{step.sub}</p>
                    </div>
                    {i < 2 && <span className="text-sky-400 text-lg hidden sm:inline">{"\u2192"}</span>}
                    {i < 2 && <span className="text-sky-400 text-lg sm:hidden">{"\u2193"}</span>}
                  </div>
                ))}
              </div>
              {/* Arrow */}
              <div className="text-sky-400 text-xl hidden sm:block">{"\u2192"}</div>
              <div className="text-sky-400 text-xl sm:hidden">{"\u2193"}</div>
              {/* Response (right) */}
              <div className="px-4 py-3 rounded-xl bg-emerald-500/10 border border-emerald-500/20 text-center min-w-[100px]">
                <p className="text-sm font-semibold text-emerald-600 dark:text-emerald-400">Response</p>
                <p className="text-[10px] text-gray-400 mt-0.5">With Citations</p>
              </div>
            </div>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            {CHANNELS.map((ch) => {
              const Icon = ch.icon;
              return (
                <div
                  key={ch.title}
                  className="flex items-start gap-4 bg-gray-50 dark:bg-gray-800/30 rounded-xl border border-gray-100 dark:border-gray-800 p-5"
                >
                  <div className="w-10 h-10 bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 flex items-center justify-center flex-shrink-0">
                    <Icon className="w-5 h-5 text-sky-500" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      <h3 className="text-sm font-semibold text-gray-900 dark:text-white">
                        {ch.title}
                      </h3>
                      <span className="text-[10px] font-medium px-2 py-0.5 rounded-full bg-sky-100 dark:bg-sky-900/40 text-sky-600 dark:text-sky-400">
                        {ch.tag}
                      </span>
                    </div>
                    <p className="text-xs text-gray-500 dark:text-gray-400 leading-relaxed">
                      {ch.description}
                    </p>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </section>

      {/* Use Cases */}
      <section className="container mx-auto px-6 py-16 max-w-5xl">
        <div className="text-center mb-10">
          <h2 className="text-2xl sm:text-3xl font-bold text-gray-900 dark:text-white mb-3">
            Built For Real Business Problems
          </h2>
          <p className="text-gray-500 dark:text-gray-400 max-w-xl mx-auto">
            RAG chatbots solve concrete problems across industries and use cases.
          </p>
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-5">
          {USE_CASES.map((uc) => {
            const Icon = uc.icon;
            return (
              <div
                key={uc.title}
                className="bg-white dark:bg-gray-900 rounded-xl border border-gray-100 dark:border-gray-800 p-6"
              >
                <div className="flex items-start justify-between mb-3">
                  <div className="flex items-center gap-3">
                    <Icon className="w-5 h-5 text-sky-500" />
                    <h3 className="text-sm font-semibold text-gray-900 dark:text-white">
                      {uc.title}
                    </h3>
                  </div>
                  <div className="text-right">
                    <p className="text-lg font-bold text-sky-500">{uc.stat}</p>
                    <p className="text-[10px] text-gray-400">{uc.statLabel}</p>
                  </div>
                </div>
                <p className="text-xs text-gray-500 dark:text-gray-400 leading-relaxed">
                  {uc.description}
                </p>
              </div>
            );
          })}
        </div>
      </section>

      {/* How It Works */}
      <section className="bg-white dark:bg-gray-900/50 border-y border-gray-100 dark:border-gray-800">
        <div className="container mx-auto px-6 py-16 max-w-5xl">
          <div className="text-center mb-10">
            <h2 className="text-2xl sm:text-3xl font-bold text-gray-900 dark:text-white mb-3">
              How It Works
            </h2>
            <p className="text-gray-500 dark:text-gray-400 max-w-xl mx-auto">
              You share your content. I build, train, and deploy your AI assistant.
            </p>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-6">
            {[
              {
                step: "01",
                icon: Upload,
                title: "Share Your Content",
                description: "Send your PDFs, docs, help articles, or FAQs. I handle parsing, chunking, and indexing.",
              },
              {
                step: "02",
                icon: MessageSquare,
                title: "I Build & Train",
                description: "Custom-tuned RAG pipeline, quality testing, knowledge gap resolution, and branding.",
              },
              {
                step: "03",
                icon: Globe,
                title: "You Go Live",
                description: "Deployed to your chosen channels — website widget, WhatsApp, Telegram, or API.",
              },
            ].map((s) => {
              const Icon = s.icon;
              return (
                <div key={s.step} className="text-center">
                  <div className="text-4xl font-bold text-gray-100 dark:text-gray-800 mb-3">
                    {s.step}
                  </div>
                  <div className="w-12 h-12 bg-sky-50 dark:bg-sky-950/30 rounded-xl flex items-center justify-center mx-auto mb-4">
                    <Icon className="w-6 h-6 text-sky-500" />
                  </div>
                  <h3 className="text-sm font-semibold text-gray-900 dark:text-white mb-2">
                    {s.title}
                  </h3>
                  <p className="text-xs text-gray-500 dark:text-gray-400 leading-relaxed">
                    {s.description}
                  </p>
                </div>
              );
            })}
          </div>
        </div>
      </section>

      {/* Tech Stack */}
      <section className="container mx-auto px-6 py-16 max-w-5xl">
        <div className="bg-gradient-to-br from-gray-900 to-gray-800 rounded-2xl p-8">
          <h3 className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-6">
            Built With Modern Tech
          </h3>
          <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
            {TECH_STACK.map((tech) => (
              <div
                key={tech.label}
                className="flex flex-col p-3.5 rounded-lg bg-white/5 border border-white/10"
              >
                <span className="text-[10px] text-gray-500 uppercase tracking-wider mb-1">
                  {tech.category}
                </span>
                <span className="text-sm text-gray-200 font-medium">
                  {tech.label}
                </span>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* What You Get (checklist) */}
      <section className="bg-white dark:bg-gray-900/50 border-y border-gray-100 dark:border-gray-800">
        <div className="container mx-auto px-6 py-16 max-w-5xl">
          <div className="text-center mb-8">
            <h2 className="text-2xl sm:text-3xl font-bold text-gray-900 dark:text-white mb-3">
              Full Source Code. No Lock-In.
            </h2>
            <p className="text-gray-500 dark:text-gray-400 max-w-xl mx-auto">
              You own everything. Modify, extend, and deploy however you want.
            </p>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-x-8 gap-y-3 max-w-3xl mx-auto">
            {[
              "Complete source code (frontend + backend)",
              "Admin dashboard with document management",
              "Multi-channel deployment (widget, WhatsApp, Telegram, API)",
              "Real-time analytics and sentiment tracking",
              "Knowledge gap detection and resolution",
              "LLM circuit breaker with auto-failover",
              "Workspace isolation for multi-tenancy",
              "Rate limiting and HMAC authentication",
              "Semantic caching for fast repeat queries",
              "Deployment guide and documentation",
            ].map((item) => (
              <div key={item} className="flex items-start gap-2.5">
                <CheckCircle2 className="w-4 h-4 text-sky-500 flex-shrink-0 mt-0.5" />
                <span className="text-sm text-gray-700 dark:text-gray-300 leading-relaxed">
                  {item}
                </span>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="container mx-auto px-6 py-16 max-w-5xl">
        <div className="bg-gradient-to-br from-sky-500 to-sky-600 rounded-2xl p-10 text-center relative overflow-hidden">
          <div className="absolute inset-0 bg-[url('data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMjAiIGhlaWdodD0iMjAiIHhtbG5zPSJodHRwOi8vd3d3LnczLm9yZy8yMDAwL3N2ZyI+PGNpcmNsZSBjeD0iMSIgY3k9IjEiIHI9IjEiIGZpbGw9InJnYmEoMjU1LDI1NSwyNTUsMC4wNSkiLz48L3N2Zz4=')] opacity-50" />
          <div className="relative">
            <h2 className="text-2xl sm:text-3xl font-bold text-white mb-3">
              Ready to Get Started?
            </h2>
            <p className="text-sky-100 mb-8 max-w-lg mx-auto">
              Choose a package that fits your needs. From a single-channel chatbot to a
              fully managed omni-channel AI assistant with analytics and ongoing support.
            </p>
            <div className="flex flex-col sm:flex-row items-center justify-center gap-3">
              <Link
                href="/chat"
                className="w-full sm:w-auto px-7 py-3.5 text-sm font-semibold bg-white text-sky-600 rounded-xl hover:bg-sky-50 transition-all shadow-lg flex items-center justify-center gap-2"
              >
                Try the Live Demo
                <ArrowRight className="w-4 h-4" />
              </Link>
            </div>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-gray-100 dark:border-gray-800 py-8">
        <div className="container mx-auto px-6 max-w-5xl text-center">
          <p className="text-xs text-gray-400 dark:text-gray-500">
            Built by Fenlo AI &mdash; Custom AI solutions for modern businesses
          </p>
        </div>
      </footer>
    </div>
  );
}

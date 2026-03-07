"use client";

import Link from "next/link";
import { useEffect, useState, useRef, type ReactNode } from "react";
import {
  FileText,
  MessageSquare,
  BarChart3,
  Search,
  Globe,
  Shield,
  Zap,
  ArrowRight,
  CheckCircle2,
  Sparkles,
  BookOpen,
  TrendingUp,
  Code2,
  Users,
  Building2,
  HeadphonesIcon,
  GraduationCap,
  LayoutDashboard,
  LineChart,
} from "lucide-react";
import ChatWidgetPreview from "@/components/landing/ChatWidgetPreview";
import { publicApi } from "@/lib/public-api";

/* ─── Scroll Reveal Hook ─── */
function useReveal(threshold = 0.15) {
  const ref = useRef<HTMLDivElement>(null);
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          setVisible(true);
          observer.unobserve(el);
        }
      },
      { threshold }
    );
    observer.observe(el);
    return () => observer.disconnect();
  }, [threshold]);

  return { ref, visible };
}

function Reveal({
  children,
  delay = 0,
  className = "",
}: {
  children: ReactNode;
  delay?: number;
  className?: string;
}) {
  const { ref, visible } = useReveal();
  return (
    <div
      ref={ref}
      className={`reveal-hidden ${visible ? "reveal-visible" : ""} ${className}`}
      style={{ transitionDelay: `${delay}ms` }}
    >
      {children}
    </div>
  );
}

/* ─── Data ─── */
interface DemoStats {
  conversations_count: number;
  documents_count: number;
  avg_quality_score: number | null;
}

const features = [
  {
    icon: FileText,
    title: "Document Intelligence",
    description:
      "Upload PDFs, DOCX, TXT, CSV. Your AI processes, chunks, and embeds every document automatically.",
    accent: "from-sky-500 to-cyan-400",
    glow: "group-hover:shadow-sky-500/20",
  },
  {
    icon: MessageSquare,
    title: "Citation-Backed Answers",
    description:
      "Every response includes exact source references. Your users always know where information comes from.",
    accent: "from-blue-500 to-indigo-400",
    glow: "group-hover:shadow-blue-500/20",
  },
  {
    icon: Search,
    title: "Knowledge Gap Detection",
    description:
      "AI identifies questions it can\u2019t answer confidently, so you know exactly what content to add next.",
    accent: "from-amber-500 to-orange-400",
    glow: "group-hover:shadow-amber-500/20",
  },
  {
    icon: BarChart3,
    title: "Real-time Analytics",
    description:
      "Sentiment analysis, quality scores, top questions, conversation volume \u2014 all in a live dashboard.",
    accent: "from-emerald-500 to-teal-400",
    glow: "group-hover:shadow-emerald-500/20",
  },
  {
    icon: Globe,
    title: "Omni-Channel Deploy",
    description:
      "Website widget, WhatsApp, Telegram, API. One knowledge base, every channel your customers use.",
    accent: "from-violet-500 to-purple-400",
    glow: "group-hover:shadow-violet-500/20",
  },
  {
    icon: Shield,
    title: "Production Grade",
    description:
      "Rate limiting, HMAC auth, LLM failover, streaming responses, RBAC, and workspace isolation.",
    accent: "from-rose-500 to-pink-400",
    glow: "group-hover:shadow-rose-500/20",
  },
];

const useCases = [
  {
    icon: HeadphonesIcon,
    title: "Customer Support",
    description:
      "Deflect 70% of support tickets. AI answers from your help docs, returns, shipping, and FAQ pages.",
    example: "\u201CWhat\u2019s your return policy on electronics?\u201D",
  },
  {
    icon: BookOpen,
    title: "Product Documentation",
    description:
      "Turn technical docs into an instant Q&A system. Users get answers instead of searching PDFs.",
    example: "\u201CHow do I configure the webhook endpoint?\u201D",
  },
  {
    icon: Building2,
    title: "Internal Knowledge Base",
    description:
      "HR policies, employee handbook, onboarding guides \u2014 your team gets instant answers.",
    example: "\u201CWhat\u2019s our PTO policy for remote employees?\u201D",
  },
  {
    icon: GraduationCap,
    title: "Education & Training",
    description:
      "Course materials, training manuals, compliance docs. Students and trainees get instant help.",
    example: "\u201CExplain the safety protocol for chemical handling.\u201D",
  },
];

const journeySteps = [
  {
    icon: MessageSquare,
    title: "Try the Chat",
    description:
      "Ask the AI anything. See real-time streaming with source citations from uploaded documents.",
    href: "/chat",
    label: "Open Chat",
    num: "01",
  },
  {
    icon: LayoutDashboard,
    title: "Explore the Dashboard",
    description:
      "See how admins manage documents, knowledge gaps, and chatbot settings from one panel.",
    href: "/dashboard",
    label: "View Dashboard",
    num: "02",
  },
  {
    icon: LineChart,
    title: "Check Analytics",
    description:
      "Sentiment trends, quality scores, top questions, and conversation volume \u2014 all live.",
    href: "/analytics",
    label: "See Analytics",
    num: "03",
  },
];

const techStack = [
  { icon: Code2, label: "Next.js 15 + React 19", desc: "Modern Frontend" },
  { icon: Zap, label: "FastAPI + Python", desc: "High-Performance API" },
  {
    icon: BookOpen,
    label: "Pinecone + OpenAI",
    desc: "Vector Search + Embeddings",
  },
  {
    icon: TrendingUp,
    label: "Real-time Analytics",
    desc: "Sentiment & Quality",
  },
  { icon: Shield, label: "JWT + RBAC", desc: "Enterprise Auth" },
  { icon: Globe, label: "Multi-Channel", desc: "Widget, WhatsApp, API" },
];

const deliverables = [
  "Custom-branded AI chatbot trained on YOUR documents",
  "Real-time streaming responses with source citations",
  "Admin dashboard with full control over knowledge base",
  "Analytics: sentiment, quality scores, top questions, volume",
  "Knowledge gap detection \u2014 see what your bot can\u2019t answer",
  "Embeddable widget with your brand colors",
  "Omni-channel: website, WhatsApp, Telegram, API",
  "Rate limiting & HMAC security built-in",
  "LLM failover \u2014 Groq primary + OpenAI backup",
  "Full source code handoff \u2014 you own everything",
];

/* ─── Component ─── */
export default function RagchatLanding() {
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
    <div className="min-h-screen bg-white dark:bg-gray-950">
      {/* ─── Navigation ─── */}
      <nav className="sticky top-0 z-50 bg-white/80 dark:bg-gray-950/80 backdrop-blur-xl border-b border-gray-100 dark:border-gray-800/50">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-3 flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 bg-gradient-to-br from-sky-500 to-cyan-400 rounded-lg flex items-center justify-center shadow-sm shadow-sky-500/20">
              <Sparkles className="w-4 h-4 text-white" />
            </div>
            <span className="text-xl font-bold text-gray-900 dark:text-white tracking-tight">
              RAGChat
            </span>
          </div>
          <div className="flex items-center gap-1 sm:gap-2">
            {[
              { href: "/dashboard", label: "Dashboard" },
              { href: "/analytics", label: "Analytics" },
              { href: "/chat", label: "Try It" },
            ].map((link) => (
              <Link
                key={link.href}
                href={link.href}
                className="hidden sm:inline-block text-sm text-gray-500 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white transition px-2.5 py-1.5 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-800/50"
              >
                {link.label}
              </Link>
            ))}
            <Link
              href="/login"
              className="text-sm font-medium text-sky-600 dark:text-sky-400 hover:text-sky-700 dark:hover:text-sky-300 transition px-3 py-1.5 rounded-lg hover:bg-sky-50 dark:hover:bg-sky-900/20"
            >
              Login
            </Link>
          </div>
        </div>
      </nav>

      {/* ─── Hero ─── */}
      <section className="relative overflow-hidden grain-overlay">
        <div className="absolute inset-0 bg-gradient-to-br from-gray-900 via-gray-800 to-sky-900" />
        {/* Grid pattern */}
        <div
          className="absolute inset-0 opacity-[0.04]"
          style={{
            backgroundImage: `url("data:image/svg+xml,%3Csvg width='60' height='60' viewBox='0 0 60 60' xmlns='http://www.w3.org/2000/svg'%3E%3Cg fill='none' fill-rule='evenodd'%3E%3Cg fill='%23ffffff' fill-opacity='1'%3E%3Cpath d='M36 34v-4h-2v4h-4v2h4v4h2v-4h4v-2h-4zm0-30V0h-2v4h-4v2h4v4h2V6h4V4h-4zM6 34v-4H4v4H0v2h4v4h2v-4h4v-2H6zM6 4V0H4v4H0v2h4v4h2V6h4V4H6z'/%3E%3C/g%3E%3C/g%3E%3C/svg%3E")`,
          }}
        />
        {/* Glow orbs */}
        <div className="absolute top-1/4 left-1/6 w-[400px] h-[400px] bg-sky-500/10 rounded-full blur-[120px]" />
        <div className="absolute bottom-1/4 right-1/4 w-[300px] h-[300px] bg-cyan-500/8 rounded-full blur-[100px]" />

        <div className="relative z-10 max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 pt-16 pb-20 lg:pt-24 lg:pb-32">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-12 lg:gap-16 items-center">
            {/* Left: Copy */}
            <div className="text-center lg:text-left">
              <div
                className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full bg-sky-500/10 border border-sky-500/20 text-sky-300 text-sm font-medium mb-8"
                style={{ animation: "fadeIn 0.8s ease-out both" }}
              >
                <Zap className="w-3.5 h-3.5" />
                Try it live &mdash; ask anything
              </div>
              <h1
                className="font-serif text-4xl sm:text-5xl lg:text-[3.5rem] text-white leading-[1.1] tracking-tight mb-6"
                style={{ animation: "fadeInUp 0.8s ease-out 0.1s both" }}
              >
                Your Documents,{" "}
                <span className="bg-gradient-to-r from-sky-400 to-cyan-300 bg-clip-text text-transparent">
                  Instantly Searchable
                </span>
              </h1>
              <p
                className="text-lg text-gray-300 max-w-lg mb-8 leading-relaxed"
                style={{ animation: "fadeInUp 0.8s ease-out 0.2s both" }}
              >
                Upload your docs. Get an AI chatbot that answers with
                citations. Deploy on your website, WhatsApp, or Telegram.
                Monitor everything.
              </p>

              {/* Live stats — mono numbers */}
              {stats && (
                <div
                  className="flex items-center gap-6 sm:gap-8 mb-8 justify-center lg:justify-start"
                  style={{ animation: "fadeInUp 0.8s ease-out 0.3s both" }}
                >
                  {[
                    {
                      value: `${stats.conversations_count}+`,
                      label: "Conversations",
                    },
                    {
                      value: `${stats.documents_count}`,
                      label: "Documents",
                    },
                    {
                      value: stats.avg_quality_score
                        ? `${Math.round(stats.avg_quality_score * 100)}%`
                        : "\u2014",
                      label: "Quality Score",
                    },
                  ].map((stat, i) => (
                    <div key={stat.label} className="flex items-center gap-6 sm:gap-8">
                      {i > 0 && (
                        <div className="w-px h-8 bg-gray-700" />
                      )}
                      <div>
                        <p className="text-2xl font-bold text-white font-mono tabular-nums">
                          {stat.value}
                        </p>
                        <p className="text-xs text-gray-400 mt-0.5">
                          {stat.label}
                        </p>
                      </div>
                    </div>
                  ))}
                </div>
              )}

              <div
                className="flex flex-col sm:flex-row items-center lg:items-start gap-3"
                style={{ animation: "fadeInUp 0.8s ease-out 0.4s both" }}
              >
                <Link
                  href="/dashboard"
                  className="w-full sm:w-auto px-7 py-3 text-base font-semibold bg-sky-500 text-white rounded-xl hover:bg-sky-400 transition-all shadow-lg shadow-sky-500/25 hover:shadow-sky-500/40 flex items-center justify-center gap-2"
                >
                  Explore Dashboard
                  <ArrowRight className="w-4 h-4" />
                </Link>
                <Link
                  href="/analytics"
                  className="w-full sm:w-auto px-7 py-3 text-base font-medium bg-white/10 text-white rounded-xl hover:bg-white/15 transition-all border border-white/10 hover:border-white/20"
                >
                  View Analytics
                </Link>
              </div>
            </div>

            {/* Right: Live Chat Widget */}
            <div
              className="flex justify-center lg:justify-end"
              style={{ animation: "fadeInUp 1s ease-out 0.3s both" }}
            >
              <div className="w-full max-w-md">
                <ChatWidgetPreview title="RAGChat" accentColor="bg-sky-500" />
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ─── User Journey — "See It In Action" ─── */}
      <section className="py-16 lg:py-20 bg-gray-50 dark:bg-gray-900/30 border-b border-gray-100 dark:border-gray-800/50">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8">
          <Reveal>
            <div className="text-center mb-12">
              <h2 className="font-serif text-3xl sm:text-4xl text-gray-900 dark:text-white mb-3">
                See It In Action
              </h2>
              <p className="text-gray-500 dark:text-gray-400 max-w-xl mx-auto">
                Explore every part of the platform &mdash; live data, no signup
                required.
              </p>
            </div>
          </Reveal>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
            {journeySteps.map((step, i) => {
              const Icon = step.icon;
              return (
                <Reveal key={step.href} delay={i * 100}>
                  <Link
                    href={step.href}
                    className="group relative block bg-white dark:bg-gray-800/50 rounded-2xl border border-gray-100 dark:border-gray-700/50 p-6 hover:border-sky-300 dark:hover:border-sky-600 hover:shadow-xl hover:shadow-sky-500/8 transition-all duration-300 hover:-translate-y-1"
                  >
                    {/* Step number — large, background accent */}
                    <div className="absolute top-4 right-5 text-5xl font-bold font-mono text-sky-500/10 dark:text-sky-400/10 select-none leading-none">
                      {step.num}
                    </div>
                    <div className="relative">
                      <div className="w-11 h-11 rounded-xl bg-sky-50 dark:bg-sky-900/30 flex items-center justify-center mb-4 group-hover:bg-sky-100 dark:group-hover:bg-sky-800/40 transition-colors">
                        <Icon className="w-5 h-5 text-sky-500" />
                      </div>
                      <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-2">
                        {step.title}
                      </h3>
                      <p className="text-sm text-gray-500 dark:text-gray-400 leading-relaxed mb-4">
                        {step.description}
                      </p>
                      <span className="inline-flex items-center gap-1.5 text-sm font-medium text-sky-500 group-hover:text-sky-600 dark:group-hover:text-sky-400 transition-colors">
                        {step.label}
                        <ArrowRight className="w-3.5 h-3.5 group-hover:translate-x-1 transition-transform duration-200" />
                      </span>
                    </div>
                  </Link>
                </Reveal>
              );
            })}
          </div>
        </div>
      </section>

      {/* ─── Features Grid ─── */}
      <section className="py-20 lg:py-28">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8">
          <Reveal>
            <div className="text-center mb-16">
              <h2 className="font-serif text-3xl sm:text-4xl text-gray-900 dark:text-white mb-4">
                Everything Your Chatbot Needs
              </h2>
              <p className="text-lg text-gray-500 dark:text-gray-400 max-w-2xl mx-auto">
                A complete RAG solution &mdash; from document upload to
                omni-channel deployment.
              </p>
            </div>
          </Reveal>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
            {features.map((feature, i) => {
              const Icon = feature.icon;
              return (
                <Reveal key={feature.title} delay={i * 80}>
                  <div
                    className={`group bg-white dark:bg-gray-800/30 rounded-2xl border border-gray-100 dark:border-gray-800 p-6 hover:shadow-xl ${feature.glow} hover:-translate-y-0.5 transition-all duration-300`}
                  >
                    <div
                      className={`w-11 h-11 rounded-xl bg-gradient-to-br ${feature.accent} flex items-center justify-center mb-4 shadow-sm`}
                    >
                      <Icon className="w-5 h-5 text-white" />
                    </div>
                    <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-2">
                      {feature.title}
                    </h3>
                    <p className="text-sm text-gray-500 dark:text-gray-400 leading-relaxed">
                      {feature.description}
                    </p>
                  </div>
                </Reveal>
              );
            })}
          </div>
        </div>
      </section>

      {/* ─── Use Cases ─── */}
      <section className="py-20 lg:py-28 bg-gray-50/80 dark:bg-gray-900/40 border-y border-gray-100 dark:border-gray-800/50">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8">
          <Reveal>
            <div className="text-center mb-16">
              <h2 className="font-serif text-3xl sm:text-4xl text-gray-900 dark:text-white mb-4">
                Built For Every Use Case
              </h2>
              <p className="text-lg text-gray-500 dark:text-gray-400 max-w-2xl mx-auto">
                Any business with documents can have an AI assistant.
              </p>
            </div>
          </Reveal>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
            {useCases.map((uc, i) => {
              const Icon = uc.icon;
              return (
                <Reveal key={uc.title} delay={i * 100}>
                  <div className="bg-white dark:bg-gray-800/30 rounded-2xl p-6 border border-gray-100 dark:border-gray-800 hover:border-sky-200 dark:hover:border-sky-800 transition-colors">
                    <div className="flex items-start gap-4">
                      <div className="w-10 h-10 rounded-xl bg-sky-50 dark:bg-sky-900/30 flex items-center justify-center flex-shrink-0">
                        <Icon className="w-5 h-5 text-sky-500" />
                      </div>
                      <div className="flex-1 min-w-0">
                        <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-2">
                          {uc.title}
                        </h3>
                        <p className="text-sm text-gray-500 dark:text-gray-400 leading-relaxed mb-3">
                          {uc.description}
                        </p>
                        <div className="bg-gray-50 dark:bg-gray-900/50 rounded-lg px-4 py-2.5 border border-gray-200/80 dark:border-gray-700">
                          <p className="text-sm text-gray-600 dark:text-gray-300 font-serif italic">
                            {uc.example}
                          </p>
                        </div>
                      </div>
                    </div>
                  </div>
                </Reveal>
              );
            })}
          </div>
        </div>
      </section>

      {/* ─── What You Get + Tech Stack ─── */}
      <section className="py-20 lg:py-28">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-12 lg:gap-16 items-start">
            {/* Deliverables */}
            <Reveal>
              <div>
                <h2 className="font-serif text-3xl sm:text-4xl text-gray-900 dark:text-white mb-2">
                  What You Get
                </h2>
                <p className="text-gray-500 dark:text-gray-400 mb-8">
                  Full source code. Full ownership. Production-ready.
                </p>
                <div className="space-y-3.5">
                  {deliverables.map((item) => (
                    <div key={item} className="flex items-start gap-3">
                      <CheckCircle2 className="w-5 h-5 text-sky-500 flex-shrink-0 mt-0.5" />
                      <span className="text-gray-700 dark:text-gray-300 text-sm leading-relaxed">
                        {item}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            </Reveal>

            {/* Tech Stack — dark card with grain */}
            <Reveal delay={150}>
              <div className="relative overflow-hidden bg-gradient-to-br from-gray-900 to-gray-800 rounded-2xl p-8 text-white grain-overlay">
                <div className="relative z-10">
                  <h3 className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-6 font-mono">
                    Built With Modern Tech
                  </h3>
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                    {techStack.map((tech) => {
                      const Icon = tech.icon;
                      return (
                        <div
                          key={tech.label}
                          className="flex items-start gap-3 p-3.5 rounded-xl bg-white/5 border border-white/10 hover:bg-white/8 hover:border-white/15 transition-colors"
                        >
                          <Icon className="w-5 h-5 text-sky-400 flex-shrink-0 mt-0.5" />
                          <div>
                            <p className="text-sm font-medium text-white">
                              {tech.label}
                            </p>
                            <p className="text-xs text-gray-400">
                              {tech.desc}
                            </p>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                  <div className="mt-6 pt-6 border-t border-white/10">
                    <div className="flex items-center gap-2 text-sm text-gray-300">
                      <Users className="w-4 h-4 text-sky-400" />
                      <span>
                        Delivered with documentation & deployment guide
                      </span>
                    </div>
                  </div>
                </div>
              </div>
            </Reveal>
          </div>
        </div>
      </section>

      {/* ─── CTA ─── */}
      <section className="relative py-20 lg:py-24 bg-gradient-to-br from-sky-500 to-sky-600 dark:from-sky-600 dark:to-sky-700 overflow-hidden grain-overlay">
        {/* Decorative shapes */}
        <div className="absolute top-0 right-0 w-96 h-96 bg-white/5 rounded-full -translate-y-1/2 translate-x-1/2" />
        <div className="absolute bottom-0 left-0 w-64 h-64 bg-white/5 rounded-full translate-y-1/2 -translate-x-1/2" />

        <Reveal>
          <div className="relative z-10 max-w-3xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
            <h2 className="font-serif text-3xl sm:text-4xl text-white mb-4">
              Want This For Your Business?
            </h2>
            <p className="text-lg text-sky-100 mb-10 max-w-2xl mx-auto leading-relaxed">
              I build custom RAG chatbots. Upload your docs, get an AI that
              knows your business inside out. Let&apos;s talk.
            </p>
            <div className="flex flex-col sm:flex-row items-center justify-center gap-3">
              <Link
                href="/chat"
                className="w-full sm:w-auto px-8 py-3.5 text-base font-semibold bg-white text-sky-600 rounded-xl hover:bg-sky-50 transition-all shadow-lg hover:shadow-xl flex items-center justify-center gap-2"
              >
                Try the Live Demo
                <ArrowRight className="w-4 h-4" />
              </Link>
              <Link
                href="/dashboard"
                className="w-full sm:w-auto px-8 py-3.5 text-base font-semibold bg-sky-700/50 text-white rounded-xl hover:bg-sky-700/70 transition-all border border-sky-400/30 hover:border-sky-400/50 flex items-center justify-center gap-2"
              >
                Explore Dashboard
              </Link>
            </div>
          </div>
        </Reveal>
      </section>

      {/* ─── Footer ─── */}
      <footer className="border-t border-gray-100 dark:border-gray-800/50 py-8 bg-white dark:bg-gray-950">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex flex-col sm:flex-row items-center justify-between gap-4">
            <div className="flex items-center gap-2">
              <div className="w-6 h-6 bg-gradient-to-br from-sky-500 to-cyan-400 rounded-md flex items-center justify-center">
                <Sparkles className="w-3 h-3 text-white" />
              </div>
              <span className="text-sm font-semibold text-gray-900 dark:text-white">
                RAGChat
              </span>
            </div>
            <div className="flex items-center gap-4 text-sm text-gray-400">
              <Link
                href="/dashboard"
                className="hover:text-gray-600 dark:hover:text-gray-300 transition"
              >
                Dashboard
              </Link>
              <Link
                href="/analytics"
                className="hover:text-gray-600 dark:hover:text-gray-300 transition"
              >
                Analytics
              </Link>
              <Link
                href="/chat"
                className="hover:text-gray-600 dark:hover:text-gray-300 transition"
              >
                Chat
              </Link>
            </div>
            <p className="text-sm text-gray-400">
              Built by{" "}
              <span className="text-sky-500">Fenlo AI</span>
            </p>
          </div>
        </div>
      </footer>
    </div>
  );
}

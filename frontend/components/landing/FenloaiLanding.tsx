import Link from 'next/link';
import {
  FileText,
  Phone,
  Globe,
  ArrowRight,
  ArrowUpRight,
  Sparkles,
  BookOpen,
  BarChart3,
  Shield,
  CheckCircle2,
  Layers,
  Zap,
  MessageCircle,
  Play,
  Database,
} from 'lucide-react';
import ChatWidgetPreview from '@/components/landing/ChatWidgetPreview';
import VoiceCallPreview from '@/components/landing/VoiceCallPreview';
import OmniChannelPreview from '@/components/landing/OmniChannelPreview';
import ThemeToggle from '@/components/landing/ThemeToggle';
import ROICalculator from '@/components/landing/ROICalculator';

export default function FenloaiLanding() {
  return (
    <div className="min-h-screen bg-[var(--color-bg-primary)]">
      {/* Navigation */}
      <nav className="border-b border-[var(--color-border)] bg-[var(--color-bg-elevated)]/80 backdrop-blur-sm sticky top-0 z-50">
        <div className="container mx-auto px-6 py-4 flex items-center justify-between">
          <Link href="/" className="flex items-center gap-2">
            <span className="text-2xl font-serif tracking-tight text-[var(--color-text-primary)]">
              Fenlo AI
            </span>
          </Link>
          <div className="hidden md:flex items-center gap-8">
            <a
              href="#solutions"
              className="text-sm text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)] transition"
            >
              Solutions
            </a>
            <a
              href="#demo"
              className="text-sm text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)] transition"
            >
              Demo
            </a>
            <Link
              href="/use-cases"
              className="text-sm text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)] transition"
            >
              Use Cases
            </Link>
            <Link
              href="/architecture"
              className="text-sm text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)] transition"
            >
              Docs
            </Link>
            <Link
              href="/api/docs"
              className="text-sm text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)] transition"
            >
              API
            </Link>
          </div>
          <div className="flex items-center gap-3">
            <ThemeToggle />
            <Link
              href="/login"
              className="text-sm text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)] transition"
            >
              Log in
            </Link>
            <Link
              href="/register"
              className="inline-flex items-center gap-1.5 px-4 py-2 text-sm font-medium bg-[var(--color-terminal-green)] text-white sharp hover:opacity-90 transition"
            >
              Get Started
              <ArrowRight className="w-3.5 h-3.5" />
            </Link>
          </div>
        </div>
      </nav>

      {/* Hero */}
      <section className="relative overflow-hidden">
        <div className="absolute inset-0 grid-pattern opacity-20" />

        <div className="relative container mx-auto px-6 py-28 lg:py-40">
          <div className="max-w-3xl">
            <div className="inline-flex items-center gap-2 px-3 py-1.5 border border-[var(--color-terminal-green)]/30 bg-[var(--color-terminal-green)]/5 mb-8 sharp">
              <Sparkles className="w-3.5 h-3.5 text-[var(--color-terminal-green)]" />
              <span className="text-xs font-medium text-[var(--color-terminal-green)] tracking-wide">
                AI-Powered Business Automation
              </span>
            </div>

            <h1 className="text-5xl lg:text-7xl font-serif leading-[1.08] mb-8 text-[var(--color-text-primary)]">
              Intelligent systems
              <span className="block text-[var(--color-terminal-green)]">
                that work for you
              </span>
            </h1>

            <div className="pl-6 border-l-2 border-[var(--color-cyber-orange)] mb-12">
              <p className="text-lg text-[var(--color-text-secondary)] leading-relaxed max-w-xl">
                Custom AI chatbots, voice agents, and multi-channel automation —
                designed around your workflows, deployed to your infrastructure,
                measurable from day one.
              </p>
            </div>

            <div className="flex flex-wrap gap-4">
              <Link
                href="/register"
                className="inline-flex items-center gap-2 px-7 py-3.5 bg-[var(--color-terminal-green)] text-white font-medium sharp hover:opacity-90 transition"
              >
                Start Building
                <ArrowRight className="w-4 h-4" />
              </Link>
              <a
                href="#solutions"
                className="inline-flex items-center gap-2 px-7 py-3.5 border border-[var(--color-border-strong)] text-[var(--color-text-primary)] font-medium sharp hover:bg-[var(--color-bg-secondary)] transition"
              >
                View Solutions
              </a>
            </div>
          </div>
        </div>
      </section>

      {/* Demo Reel */}
      <section id="demo" className="py-24 border-t border-[var(--color-border)]">
        <div className="container mx-auto px-6">
          <div className="max-w-2xl mb-12">
            <span className="text-xs font-medium text-[var(--color-cyber-orange)] uppercase tracking-widest mb-3 block">
              See It In Action
            </span>
            <h2 className="text-3xl lg:text-4xl font-serif mb-4 text-[var(--color-text-primary)]">
              Platform walkthrough
            </h2>
            <p className="text-[var(--color-text-secondary)] leading-relaxed">
              60-second demo — RAG chat with citations, voice agents, multi-channel inbox, and live analytics.
            </p>
          </div>
          <div className="max-w-4xl border border-[var(--color-border)] sharp overflow-hidden">
            <div className="relative w-full" style={{ paddingBottom: '56.25%' }}>
              <iframe
                className="absolute inset-0 w-full h-full"
                src="https://www.youtube.com/embed/sPG9pD3S_Jw?rel=0&modestbranding=1"
                title="Fenlo AI Platform Demo"
                allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
                allowFullScreen
                loading="lazy"
              />
            </div>
          </div>
        </div>
      </section>

      {/* Solutions — Three Product Cards with LIVE badges */}
      <section id="solutions" className="py-24 border-t border-[var(--color-border)]">
        <div className="container mx-auto px-6">
          <div className="max-w-2xl mb-16">
            <span className="text-xs font-medium text-[var(--color-terminal-green)] uppercase tracking-widest mb-3 block">
              Solutions
            </span>
            <h2 className="text-3xl lg:text-4xl font-serif mb-4 text-[var(--color-text-primary)]">
              Three systems, one platform
            </h2>
            <p className="text-[var(--color-text-secondary)] leading-relaxed">
              Each solution is production-ready, fully customizable, and designed to integrate
              seamlessly with your existing stack.
            </p>
          </div>

          <div className="grid lg:grid-cols-3 gap-6 max-w-6xl">
            {/* RAGChat */}
            <div className="group border border-[var(--color-border)] sharp overflow-hidden bg-[var(--color-bg-elevated)] hover:border-[var(--color-terminal-green)]/50 transition-all duration-300">
              <div className="p-8">
                <div className="flex items-center gap-3 mb-6">
                  <div className="w-12 h-12 bg-[var(--color-terminal-green)]/10 flex items-center justify-center sharp">
                    <FileText className="w-6 h-6 text-[var(--color-terminal-green)]" />
                  </div>
                  <div className="px-2 py-0.5 bg-[var(--color-terminal-green)] text-white text-[10px] font-bold tracking-wider sharp">
                    LIVE
                  </div>
                </div>
                <h3 className="text-xl font-serif mb-2 text-[var(--color-text-primary)]">RAGChat</h3>
                <p className="text-sm text-[var(--color-text-secondary)] mb-6 leading-relaxed">
                  Document-powered AI that answers questions with source citations.
                  Upload your knowledge base, get accurate responses instantly.
                </p>
                <div className="space-y-2.5 mb-8">
                  {[
                    'PDF, DOCX & TXT ingestion',
                    'Source citation extraction',
                    'Knowledge gap detection',
                    'Semantic search & caching',
                  ].map((feature, i) => (
                    <div key={i} className="flex items-center gap-2.5">
                      <CheckCircle2 className="w-4 h-4 text-[var(--color-terminal-green)] flex-shrink-0" />
                      <span className="text-sm text-[var(--color-text-secondary)]">{feature}</span>
                    </div>
                  ))}
                </div>
                <Link
                  href="/register"
                  className="inline-flex items-center gap-1.5 text-sm font-medium text-[var(--color-terminal-green)] hover:gap-2.5 transition-all"
                >
                  Get Started <ArrowRight className="w-4 h-4" />
                </Link>
              </div>
              <div className="border-t border-[var(--color-border)] bg-[var(--color-bg-secondary)] p-6 flex items-center justify-center min-h-[200px]">
                <ChatWidgetPreview />
              </div>
            </div>

            {/* VoiceBot */}
            <div className="group border border-[var(--color-border)] sharp overflow-hidden bg-[var(--color-bg-elevated)] hover:border-[var(--color-cyber-orange)]/50 transition-all duration-300">
              <div className="p-8">
                <div className="flex items-center gap-3 mb-6">
                  <div className="w-12 h-12 bg-[var(--color-cyber-orange)]/10 flex items-center justify-center sharp">
                    <Phone className="w-6 h-6 text-[var(--color-cyber-orange)]" />
                  </div>
                  <div className="px-2 py-0.5 bg-[var(--color-terminal-green)] text-white text-[10px] font-bold tracking-wider sharp">
                    LIVE
                  </div>
                </div>
                <h3 className="text-xl font-serif mb-2 text-[var(--color-text-primary)]">VoiceBot Pro</h3>
                <p className="text-sm text-[var(--color-text-secondary)] mb-6 leading-relaxed">
                  AI phone agents that handle calls naturally. Smart escalation rules
                  route complex issues to your team.
                </p>
                <div className="space-y-2.5 mb-8">
                  {[
                    'Natural voice conversations',
                    'Rule-based escalation',
                    'Real-time transcription',
                    'Sentiment analysis',
                  ].map((feature, i) => (
                    <div key={i} className="flex items-center gap-2.5">
                      <CheckCircle2 className="w-4 h-4 text-[var(--color-cyber-orange)] flex-shrink-0" />
                      <span className="text-sm text-[var(--color-text-secondary)]">{feature}</span>
                    </div>
                  ))}
                </div>
                <Link
                  href="/register"
                  className="inline-flex items-center gap-1.5 text-sm font-medium text-[var(--color-cyber-orange)] hover:gap-2.5 transition-all"
                >
                  Get Started <ArrowRight className="w-4 h-4" />
                </Link>
              </div>
              <div className="border-t border-[var(--color-border)] bg-[var(--color-bg-secondary)] p-6 flex items-center justify-center min-h-[200px]">
                <VoiceCallPreview />
              </div>
            </div>

            {/* OmniBot */}
            <div className="group border border-[var(--color-border)] sharp overflow-hidden bg-[var(--color-bg-elevated)] hover:border-[var(--color-warning-amber)]/50 transition-all duration-300">
              <div className="p-8">
                <div className="flex items-center gap-3 mb-6">
                  <div className="w-12 h-12 bg-[var(--color-warning-amber)]/10 flex items-center justify-center sharp">
                    <Globe className="w-6 h-6 text-[var(--color-warning-amber)]" />
                  </div>
                  <div className="px-2 py-0.5 bg-[var(--color-terminal-green)] text-white text-[10px] font-bold tracking-wider sharp">
                    LIVE
                  </div>
                </div>
                <h3 className="text-xl font-serif mb-2 text-[var(--color-text-primary)]">OmniBot</h3>
                <p className="text-sm text-[var(--color-text-secondary)] mb-6 leading-relaxed">
                  Deploy across every channel your customers use. WhatsApp, web widget,
                  Telegram — one unified inbox.
                </p>
                <div className="space-y-2.5 mb-8">
                  {[
                    'WhatsApp Business API',
                    'Embeddable chat widget',
                    'Webhook integrations',
                    'GDPR compliance toolkit',
                  ].map((feature, i) => (
                    <div key={i} className="flex items-center gap-2.5">
                      <CheckCircle2 className="w-4 h-4 text-[var(--color-warning-amber)] flex-shrink-0" />
                      <span className="text-sm text-[var(--color-text-secondary)]">{feature}</span>
                    </div>
                  ))}
                </div>
                <Link
                  href="/register"
                  className="inline-flex items-center gap-1.5 text-sm font-medium text-[var(--color-warning-amber)] hover:gap-2.5 transition-all"
                >
                  Get Started <ArrowRight className="w-4 h-4" />
                </Link>
              </div>
              <div className="border-t border-[var(--color-border)] bg-[var(--color-bg-secondary)] p-6 flex items-center justify-center min-h-[200px]">
                <OmniChannelPreview />
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ROI Calculator */}
      <ROICalculator />

      {/* How We Work — Process Stepper */}
      <section id="process" className="py-24 border-t border-[var(--color-border)] bg-[var(--color-bg-secondary)]">
        <div className="container mx-auto px-6">
          <div className="max-w-2xl mb-16">
            <span className="text-xs font-medium text-[var(--color-cyber-orange)] uppercase tracking-widest mb-3 block">
              Process
            </span>
            <h2 className="text-3xl lg:text-4xl font-serif mb-4 text-[var(--color-text-primary)]">
              How we work
            </h2>
            <p className="text-[var(--color-text-secondary)] leading-relaxed">
              A structured approach that takes you from requirements to production deployment.
            </p>
          </div>

          <div className="grid md:grid-cols-4 gap-8 max-w-5xl">
            {[
              {
                step: '01',
                title: 'Discovery',
                desc: 'We map your workflows, data sources, and automation goals to define the right solution.',
                icon: BookOpen,
              },
              {
                step: '02',
                title: 'Design',
                desc: 'System architecture, conversation flows, and integration points — all planned before code.',
                icon: Layers,
              },
              {
                step: '03',
                title: 'Build',
                desc: 'Iterative development with weekly demos. RAG pipelines, voice agents, channel integrations.',
                icon: Zap,
              },
              {
                step: '04',
                title: 'Deploy',
                desc: 'Production deployment to your infrastructure. Monitoring, analytics, and ongoing optimization.',
                icon: BarChart3,
              },
            ].map((item) => {
              const Icon = item.icon;
              return (
                <div key={item.step} className="relative">
                  <div className="text-5xl font-serif text-[var(--color-border-strong)] mb-4 leading-none">
                    {item.step}
                  </div>
                  <div className="w-10 h-10 bg-[var(--color-bg-elevated)] border border-[var(--color-border)] flex items-center justify-center sharp mb-4">
                    <Icon className="w-5 h-5 text-[var(--color-terminal-green)]" />
                  </div>
                  <h3 className="text-lg font-serif mb-2 text-[var(--color-text-primary)]">
                    {item.title}
                  </h3>
                  <p className="text-sm text-[var(--color-text-secondary)] leading-relaxed">
                    {item.desc}
                  </p>
                </div>
              );
            })}
          </div>
        </div>
      </section>

      {/* Why Fenlo AI */}
      <section id="why" className="py-24 border-t border-[var(--color-border)]">
        <div className="container mx-auto px-6">
          <div className="max-w-2xl mb-16">
            <span className="text-xs font-medium text-[var(--color-terminal-green)] uppercase tracking-widest mb-3 block">
              Why Fenlo AI
            </span>
            <h2 className="text-3xl lg:text-4xl font-serif mb-4 text-[var(--color-text-primary)]">
              Built different
            </h2>
            <p className="text-[var(--color-text-secondary)] leading-relaxed">
              Not another chatbot builder. Fenlo AI delivers custom-engineered systems
              with production-grade architecture.
            </p>
          </div>

          <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-6 max-w-5xl">
            {[
              {
                icon: Shield,
                title: 'Enterprise Architecture',
                desc: 'Circuit breakers, workspace isolation, RBAC. Patterns that scale.',
              },
              {
                icon: MessageCircle,
                title: 'Citation-Backed Answers',
                desc: 'Every response traceable to source documents. No hallucination guesswork.',
              },
              {
                icon: Zap,
                title: 'Sub-Second Responses',
                desc: 'Semantic caching, streaming pipelines, and optimized embeddings.',
              },
              {
                icon: Layers,
                title: 'Multi-Channel Native',
                desc: 'WhatsApp, web widget, Telegram, webhooks — one codebase, every channel.',
              },
              {
                icon: BarChart3,
                title: 'Built-In Analytics',
                desc: 'Sentiment analysis, intent classification, lead scoring, quality metrics.',
              },
              {
                icon: BookOpen,
                title: 'Your Infrastructure',
                desc: 'Deploy on your AWS, GCP, or on-prem. No vendor lock-in, full data control.',
              },
            ].map((item) => {
              const Icon = item.icon;
              return (
                <div
                  key={item.title}
                  className="p-6 border border-[var(--color-border)] sharp bg-[var(--color-bg-elevated)] hover:border-[var(--color-border-strong)] transition"
                >
                  <Icon className="w-5 h-5 text-[var(--color-terminal-green)] mb-4" />
                  <h3 className="font-serif text-lg mb-2 text-[var(--color-text-primary)]">{item.title}</h3>
                  <p className="text-sm text-[var(--color-text-secondary)] leading-relaxed">{item.desc}</p>
                </div>
              );
            })}
          </div>
        </div>
      </section>

      {/* Technical Stack */}
      <section className="py-24 border-t border-[var(--color-border)] bg-[var(--color-bg-secondary)]">
        <div className="container mx-auto px-6">
          <div className="max-w-2xl mb-16">
            <span className="text-xs font-medium text-[var(--color-terminal-green)] uppercase tracking-widest mb-3 block">
              Under The Hood
            </span>
            <h2 className="text-3xl lg:text-4xl font-serif mb-4 text-[var(--color-text-primary)]">
              Technical stack
            </h2>
            <p className="text-[var(--color-text-secondary)] leading-relaxed">
              Production-grade architecture. Enterprise patterns. Zero vendor lock-in.
            </p>
          </div>

          <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4 max-w-5xl">
            {[
              {
                category: 'Backend',
                stack: ['Python 3.12', 'FastAPI', 'SQLAlchemy', 'Alembic', 'Pydantic', 'ARQ'],
              },
              {
                category: 'Frontend',
                stack: ['Next.js 15', 'React 19', 'TypeScript', 'Tailwind', 'Zustand', 'React Query'],
              },
              {
                category: 'AI / ML',
                stack: ['OpenAI API', 'Groq / Llama', 'Pinecone', 'RAG Pipeline', 'Embeddings'],
              },
              {
                category: 'Infrastructure',
                stack: ['PostgreSQL', 'Redis', 'AWS EC2', 'Docker', 'Nginx', 'GitHub Actions'],
              },
              {
                category: 'Real-time',
                stack: ['WebSocket', 'SSE', 'Streaming', 'Event Bus', 'Redis Pub/Sub'],
              },
              {
                category: 'Voice',
                stack: ['Vapi SDK', 'Twilio', 'STT / TTS', 'WebRTC', 'Audio Streaming'],
              },
            ].map((group) => (
              <div
                key={group.category}
                className="border border-[var(--color-border)] p-5 sharp bg-[var(--color-bg-elevated)]"
              >
                <div className="text-xs font-medium text-[var(--color-text-tertiary)] mb-4 uppercase tracking-widest">
                  {group.category}
                </div>
                <div className="space-y-1.5">
                  {group.stack.map((tech) => (
                    <div key={tech} className="flex items-center gap-2">
                      <div className="w-1 h-1 bg-[var(--color-terminal-green)] sharp flex-shrink-0" />
                      <span className="text-sm text-[var(--color-text-secondary)]">{tech}</span>
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Final CTA */}
      <section className="py-24 border-t border-[var(--color-border)]">
        <div className="container mx-auto px-6 text-center">
          <div className="max-w-2xl mx-auto">
            <h2 className="text-3xl lg:text-5xl font-serif mb-6 text-[var(--color-text-primary)]">
              Ready to automate?
            </h2>
            <p className="text-[var(--color-text-secondary)] mb-10 leading-relaxed text-lg">
              Tell us your requirements. We&apos;ll design, build, and deploy
              an AI system tailored to your business.
            </p>
            <div className="flex flex-wrap justify-center gap-4">
              <Link
                href="/register"
                className="inline-flex items-center gap-2 px-8 py-4 bg-[var(--color-terminal-green)] text-white font-medium sharp hover:opacity-90 transition"
              >
                Start Building
                <ArrowRight className="w-4 h-4" />
              </Link>
              <a
                href="mailto:contact@fenloai.com"
                className="inline-flex items-center gap-2 px-8 py-4 border border-[var(--color-border-strong)] text-[var(--color-text-primary)] font-medium sharp hover:bg-[var(--color-bg-tertiary)] transition"
              >
                Contact Us
                <ArrowUpRight className="w-4 h-4" />
              </a>
            </div>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-[var(--color-border)] py-10">
        <div className="container mx-auto px-6">
          <div className="flex flex-col md:flex-row items-center justify-between gap-6">
            <div>
              <span className="text-xl font-serif text-[var(--color-text-primary)]">Fenlo AI</span>
              <p className="text-sm text-[var(--color-text-tertiary)] mt-1">
                Intelligent automation, delivered.
              </p>
            </div>
            <div className="flex items-center gap-6 text-sm text-[var(--color-text-secondary)]">
              <a href="#solutions" className="hover:text-[var(--color-text-primary)] transition">
                Solutions
              </a>
              <Link href="/use-cases" className="hover:text-[var(--color-text-primary)] transition">
                Use Cases
              </Link>
              <Link href="/architecture" className="hover:text-[var(--color-text-primary)] transition">
                Docs
              </Link>
              <Link href="/api/docs" className="hover:text-[var(--color-text-primary)] transition">
                API
              </Link>
              <a href="mailto:contact@fenloai.com" className="hover:text-[var(--color-text-primary)] transition">
                Contact
              </a>
            </div>
            <div className="text-sm text-[var(--color-text-tertiary)]">
              Built by Mohammad Shoaib &middot; &copy; {new Date().getFullYear()} Fenlo AI
            </div>
          </div>
        </div>
      </footer>
    </div>
  );
}

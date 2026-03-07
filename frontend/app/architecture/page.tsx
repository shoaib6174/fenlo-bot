import Link from 'next/link';
import {
  MessageSquare,
  ArrowRight,
  Database,
  Zap,
  Shield,
  GitBranch,
  Code,
  Globe,
  Phone,
  CheckCircle,
  ExternalLink,
  Layers,
  Lock,
  BarChart3,
  FileText,
  Search,
  Wrench,
  Bot,
  Terminal,
  Cpu,
  Activity,
} from 'lucide-react';
import ThemeToggle from '@/components/landing/ThemeToggle';
import { TechNavBrand, TechFooterBrand } from '@/components/landing/NavBrand';

export default async function ArchitecturePage() {
  return (
    <div className="min-h-screen bg-[var(--color-bg-primary)]">
      {/* Navigation — Terminal Style */}
      <nav className="border-b border-[var(--color-border)] bg-[var(--color-bg-elevated)]/80 backdrop-blur-sm sticky top-0 z-50">
        <div className="container mx-auto px-4 py-3 flex items-center justify-between">
          <TechNavBrand />
          <div className="flex items-center gap-4">
            <Link
              href="/#systems"
              className="text-sm font-mono text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)] transition uppercase tracking-wide"
            >
              Systems
            </Link>
            <Link
              href="/use-cases"
              className="text-sm font-mono text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)] transition uppercase tracking-wide"
            >
              Use Cases
            </Link>
            <Link
              href="/api/docs"
              className="text-sm font-mono text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)] transition uppercase tracking-wide"
            >
              API
            </Link>
            <ThemeToggle />
            <Link
              href="/login"
              className="px-3 py-1.5 text-sm font-mono border border-[var(--color-border)] hover:border-[var(--color-border-strong)] transition sharp uppercase tracking-wide"
            >
              Login
            </Link>
          </div>
        </div>
      </nav>

      {/* Hero — Technical Header */}
      <section className="relative overflow-hidden border-b border-[var(--color-border)]">
        <div className="absolute inset-0 grid-pattern opacity-40" />
        <div className="absolute inset-0 scan-line pointer-events-none" />

        <div className="relative container mx-auto px-4 py-20">
          <div className="max-w-4xl">
            <div className="inline-flex items-center gap-2 px-3 py-1 border border-terminal-green bg-terminal-green/5 mb-8 sharp">
              <div className="w-2 h-2 bg-terminal-green animate-pulse sharp" />
              <span className="text-xs font-mono font-bold text-terminal-green uppercase tracking-wider">
                System Architecture — Technical Documentation
              </span>
            </div>

            <h1 className="text-5xl lg:text-6xl font-mono font-bold leading-[1.1] mb-6 tracking-tight">
              <span className="block">PRODUCTION</span>
              <span className="block text-terminal-green">ARCHITECTURE</span>
            </h1>

            <div className="pl-4 border-l-2 border-cyber-orange mb-8">
              <p className="text-lg text-[var(--color-text-secondary)] leading-relaxed">
                Composable, event-driven system architecture. Pipeline pattern for message processing.
                Circuit breakers for failover. Multi-tenant workspace isolation. Enterprise-grade reliability.
              </p>
            </div>

            {/* System Stats */}
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
              {[
                { label: 'Modules', value: '9', icon: Layers },
                { label: 'Pipeline Steps', value: '12', icon: GitBranch },
                { label: 'API Endpoints', value: '40+', icon: Code },
                { label: 'Integrations', value: '15', icon: Wrench },
              ].map((stat) => (
                <div
                  key={stat.label}
                  className="border border-[var(--color-border)] bg-[var(--color-bg-elevated)] p-4 sharp"
                >
                  <stat.icon className="w-4 h-4 mb-2 text-[var(--color-text-tertiary)]" />
                  <div className="font-mono text-2xl font-bold mb-1 mono-num">
                    {stat.value}
                  </div>
                  <div className="text-xs font-mono text-[var(--color-text-tertiary)] uppercase tracking-wide">
                    {stat.label}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* Message Pipeline — ASCII Flow */}
      <section className="py-20 border-b border-[var(--color-border)]">
        <div className="container mx-auto px-4">
          <div className="max-w-4xl mx-auto">
            <div className="mb-12">
              <div className="flex items-center gap-3 mb-3">
                <div className="w-1 h-8 bg-terminal-green" />
                <h2 className="text-3xl font-mono font-bold uppercase tracking-tight">
                  Message Pipeline
                </h2>
              </div>
              <p className="text-[var(--color-text-secondary)]">
                Composable middleware architecture — each step transforms shared MessageContext
              </p>
            </div>

            {/* Pipeline Flow */}
            <div className="border-2 border-[var(--color-border)] sharp overflow-hidden">
              {[
                {
                  name: 'LoadContextStep',
                  icon: Database,
                  desc: 'Load conversation history, workspace settings, KB metadata',
                  color: 'terminal-green',
                },
                {
                  name: 'PromptGuardStep',
                  icon: Shield,
                  desc: 'Injection detection, content filtering, rate limiting',
                  color: 'cyber-orange',
                },
                {
                  name: 'RAGRetrievalStep',
                  icon: Search,
                  desc: 'Semantic search → vector store → context enrichment',
                  color: 'terminal-green',
                },
                {
                  name: 'LLMStreamStep',
                  icon: Bot,
                  desc: 'Groq (primary) → OpenAI (failover) with circuit breaker',
                  color: 'warning-amber',
                },
                {
                  name: 'SentimentAnalysisStep',
                  icon: BarChart3,
                  desc: 'Keyword-based positive/neutral/negative detection',
                  color: 'terminal-green',
                },
                {
                  name: 'IntentClassifierStep',
                  icon: Layers,
                  desc: 'Pattern matching: FAQ, booking, sales, support, escalation',
                  color: 'cyber-orange',
                },
                {
                  name: 'QualityScorerStep',
                  icon: CheckCircle,
                  desc: 'Heuristic: length, citations, relevance signals → 0.0-1.0',
                  color: 'terminal-green',
                },
                {
                  name: 'LeadScoringStep',
                  icon: Zap,
                  desc: 'Pricing/timeline/contact signals → cumulative score',
                  color: 'warning-amber',
                },
                {
                  name: 'PersistenceStep',
                  icon: FileText,
                  desc: 'Save message, update conversation state, emit events',
                  color: 'terminal-green',
                },
              ].map((step, idx, arr) => (
                <div key={step.name}>
                  <div className="p-6 border-b border-[var(--color-border)] last:border-b-0 group hover:bg-[var(--color-bg-secondary)] transition-colors">
                    <div className="flex items-start gap-4">
                      <div className="flex-shrink-0 w-10 h-10 bg-[var(--color-bg-elevated)] border border-[var(--color-border)] sharp flex items-center justify-center">
                        <step.icon className="w-5 h-5 text-[var(--color-text-tertiary)]" />
                      </div>
                      <div className="flex-1">
                        <div className="flex items-center gap-2 mb-2">
                          <h3 className="font-mono text-sm font-bold uppercase tracking-wide">
                            {step.name}
                          </h3>
                          <div className={`w-1 h-1 bg-${step.color} sharp`} />
                        </div>
                        <p className="text-sm text-[var(--color-text-secondary)] leading-relaxed">
                          {step.desc}
                        </p>
                      </div>
                      <div className="flex-shrink-0 px-2 py-1 bg-[var(--color-bg-elevated)] border border-[var(--color-border)] sharp">
                        <span className="text-xs font-mono font-bold mono-num text-[var(--color-text-tertiary)]">
                          {String(idx + 1).padStart(2, '0')}
                        </span>
                      </div>
                    </div>
                  </div>
                  {idx < arr.length - 1 && (
                    <div className="flex justify-center py-2 bg-[var(--color-bg-secondary)]">
                      <div className="font-mono text-xs text-[var(--color-text-tertiary)]">
                        ▼
                      </div>
                    </div>
                  )}
                </div>
              ))}
            </div>

            {/* Composability Callout */}
            <div className="mt-6 p-4 border border-terminal-green bg-terminal-green/5 sharp">
              <div className="flex items-start gap-3">
                <GitBranch className="w-5 h-5 text-terminal-green mt-0.5" />
                <div>
                  <h4 className="font-mono text-sm font-bold text-terminal-green mb-1 uppercase">
                    Composable Design Pattern
                  </h4>
                  <p className="text-sm text-[var(--color-text-secondary)]">
                    Add/remove pipeline steps without touching core engine. Steps share{' '}
                    <code className="px-1.5 py-0.5 bg-[var(--color-bg-elevated)] border border-[var(--color-border)] sharp text-xs font-mono">
                      MessageContext
                    </code>{' '}
                    — modify in-place, return control to pipeline.
                  </p>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Tech Stack Grid */}
      <section className="py-20 border-b border-[var(--color-border)]">
        <div className="container mx-auto px-4">
          <div className="max-w-6xl mx-auto">
            <div className="mb-12">
              <div className="flex items-center gap-3 mb-3">
                <div className="w-1 h-8 bg-cyber-orange" />
                <h2 className="text-3xl font-mono font-bold uppercase tracking-tight">
                  Technology Stack
                </h2>
              </div>
              <p className="text-[var(--color-text-secondary)]">
                Production-grade components. Battle-tested reliability. Zero vendor lock-in.
              </p>
            </div>

            <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-6">
              {/* Backend */}
              <div className="border-2 border-[var(--color-border)] sharp">
                <div className="p-4 border-b-2 border-[var(--color-border)] bg-[var(--color-bg-secondary)]">
                  <div className="flex items-center gap-2">
                    <Database className="w-4 h-4 text-terminal-green" />
                    <h3 className="font-mono text-sm font-bold uppercase tracking-wider">
                      Backend
                    </h3>
                  </div>
                </div>
                <div className="p-4 space-y-3">
                  {[
                    { name: 'FastAPI', ver: '0.115' },
                    { name: 'SQLAlchemy', ver: '2.0' },
                    { name: 'PostgreSQL', ver: '17' },
                    { name: 'Redis', ver: '7.4' },
                    { name: 'Pinecone', ver: 'v2' },
                    { name: 'ARQ', ver: '0.26' },
                  ].map((tech) => (
                    <div
                      key={tech.name}
                      className="flex items-center justify-between text-sm"
                    >
                      <span className="font-mono">{tech.name}</span>
                      <span className="font-mono text-[var(--color-text-tertiary)] text-xs">
                        {tech.ver}
                      </span>
                    </div>
                  ))}
                </div>
              </div>

              {/* Frontend */}
              <div className="border-2 border-[var(--color-border)] sharp">
                <div className="p-4 border-b-2 border-[var(--color-border)] bg-[var(--color-bg-secondary)]">
                  <div className="flex items-center gap-2">
                    <Globe className="w-4 h-4 text-terminal-green" />
                    <h3 className="font-mono text-sm font-bold uppercase tracking-wider">
                      Frontend
                    </h3>
                  </div>
                </div>
                <div className="p-4 space-y-3">
                  {[
                    { name: 'Next.js', ver: '15.1' },
                    { name: 'React', ver: '19' },
                    { name: 'TypeScript', ver: '5.x' },
                    { name: 'Tailwind', ver: '3.4' },
                    { name: 'Zustand', ver: '5.x' },
                    { name: 'React Query', ver: '5.x' },
                  ].map((tech) => (
                    <div
                      key={tech.name}
                      className="flex items-center justify-between text-sm"
                    >
                      <span className="font-mono">{tech.name}</span>
                      <span className="font-mono text-[var(--color-text-tertiary)] text-xs">
                        {tech.ver}
                      </span>
                    </div>
                  ))}
                </div>
              </div>

              {/* AI/ML */}
              <div className="border-2 border-[var(--color-border)] sharp">
                <div className="p-4 border-b-2 border-[var(--color-border)] bg-[var(--color-bg-secondary)]">
                  <div className="flex items-center gap-2">
                    <Bot className="w-4 h-4 text-terminal-green" />
                    <h3 className="font-mono text-sm font-bold uppercase tracking-wider">
                      AI/ML
                    </h3>
                  </div>
                </div>
                <div className="p-4 space-y-3">
                  {[
                    { name: 'Groq', ver: 'llama-3.3' },
                    { name: 'OpenAI', ver: 'gpt-4o' },
                    { name: 'Transformers', ver: 'local' },
                    { name: 'Vapi', ver: 'v1' },
                  ].map((tech) => (
                    <div
                      key={tech.name}
                      className="flex items-center justify-between text-sm"
                    >
                      <span className="font-mono">{tech.name}</span>
                      <span className="font-mono text-[var(--color-text-tertiary)] text-xs">
                        {tech.ver}
                      </span>
                    </div>
                  ))}
                </div>
              </div>

              {/* Infrastructure */}
              <div className="border-2 border-[var(--color-border)] sharp">
                <div className="p-4 border-b-2 border-[var(--color-border)] bg-[var(--color-bg-secondary)]">
                  <div className="flex items-center gap-2">
                    <Wrench className="w-4 h-4 text-terminal-green" />
                    <h3 className="font-mono text-sm font-bold uppercase tracking-wider">
                      Infra
                    </h3>
                  </div>
                </div>
                <div className="p-4 space-y-3">
                  {[
                    { name: 'AWS EC2', ver: 'm7i-flex' },
                    { name: 'RDS PG', ver: '17' },
                    { name: 'Nginx', ver: '1.18' },
                    { name: 'Actions', ver: 'CI/CD' },
                  ].map((tech) => (
                    <div
                      key={tech.name}
                      className="flex items-center justify-between text-sm"
                    >
                      <span className="font-mono">{tech.name}</span>
                      <span className="font-mono text-[var(--color-text-tertiary)] text-xs">
                        {tech.ver}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Architectural Patterns */}
      <section className="py-20 border-b border-[var(--color-border)]">
        <div className="container mx-auto px-4">
          <div className="max-w-6xl mx-auto">
            <div className="mb-12">
              <div className="flex items-center gap-3 mb-3">
                <div className="w-1 h-8 bg-[var(--color-text-tertiary)]" />
                <h2 className="text-3xl font-mono font-bold uppercase tracking-tight">
                  Design Patterns
                </h2>
              </div>
              <p className="text-[var(--color-text-secondary)]">
                Enterprise-grade architectural patterns for reliability and maintainability
              </p>
            </div>

            <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
              {[
                {
                  icon: Layers,
                  title: 'Pipeline',
                  desc: 'Composable middleware for message processing. Isolated, testable, swappable steps.',
                },
                {
                  icon: Zap,
                  title: 'Circuit Breaker',
                  desc: 'LLM router tracks failures, auto-failover from Groq to OpenAI after threshold.',
                },
                {
                  icon: Lock,
                  title: 'Workspace Isolation',
                  desc: 'Every DB query scoped to workspace_id. JWT tokens carry workspace context.',
                },
                {
                  icon: GitBranch,
                  title: 'Event Bus',
                  desc: 'In-process pub/sub for cross-module communication. Decouples analytics, channels.',
                },
                {
                  icon: Shield,
                  title: 'Repository',
                  desc: 'Database access abstracted. Simplifies testing and data layer migration.',
                },
                {
                  icon: Database,
                  title: 'Graceful Degradation',
                  desc: 'Redis failure doesn&apos;t break app. Cache, rate limiting degrade gracefully.',
                },
              ].map((pattern) => (
                <div
                  key={pattern.title}
                  className="border border-[var(--color-border)] p-6 sharp hover:border-terminal-green transition-colors duration-200"
                >
                  <div className="flex items-center gap-3 mb-3">
                    <pattern.icon className="w-5 h-5 text-[var(--color-text-tertiary)]" />
                    <h3 className="font-mono text-sm font-bold uppercase tracking-wider">
                      {pattern.title}
                    </h3>
                  </div>
                  <p className="text-sm text-[var(--color-text-secondary)] leading-relaxed">
                    {pattern.desc}
                  </p>
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* API Documentation CTA */}
      <section className="py-20 border-t-2 border-[var(--color-border)]">
        <div className="container mx-auto px-4 text-center">
          <div className="max-w-2xl mx-auto">
            <div className="inline-flex items-center gap-2 px-3 py-1 border border-cyber-orange bg-cyber-orange/5 mb-6 sharp">
              <Code className="w-3 h-3 text-cyber-orange" />
              <span className="text-xs font-mono font-bold text-cyber-orange uppercase tracking-wider">
                Interactive Documentation
              </span>
            </div>
            <h2 className="text-3xl lg:text-4xl font-mono font-bold mb-4 uppercase tracking-tight">
              Explore the API
            </h2>
            <p className="text-[var(--color-text-secondary)] mb-10 leading-relaxed">
              Live endpoint testing. Complete schema definitions. Request/response examples.
            </p>
            <div className="flex flex-wrap justify-center gap-4">
              <Link
                href="/api/docs"
                className="inline-flex items-center gap-2 px-8 py-4 bg-black dark:bg-white text-white dark:text-black font-mono font-bold sharp hover:opacity-90 transition uppercase tracking-wide"
              >
                <Code className="w-4 h-4" />
                Swagger UI
                <ExternalLink className="w-3 h-3" />
              </Link>
              <Link
                href="/api/redoc"
                className="inline-flex items-center gap-2 px-8 py-4 border-2 border-[var(--color-border)] font-mono font-bold sharp hover:border-[var(--color-border-strong)] transition uppercase tracking-wide"
              >
                <FileText className="w-4 h-4" />
                ReDoc
                <ExternalLink className="w-3 h-3" />
              </Link>
            </div>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-[var(--color-border)] py-8">
        <div className="container mx-auto px-4">
          <div className="flex flex-col md:flex-row items-center justify-between gap-4">
            <TechFooterBrand />
            <div className="flex items-center gap-4 font-mono text-sm">
              <Link href="/" className="hover:text-terminal-green transition">
                /home
              </Link>
              <Link href="/use-cases" className="hover:text-terminal-green transition">
                /use-cases
              </Link>
              <Link href="/#systems" className="hover:text-terminal-green transition">
                /systems
              </Link>
              <Link href="/status" className="hover:text-terminal-green transition">
                /status
              </Link>
              <Link href="/api/docs" className="hover:text-terminal-green transition">
                /api
              </Link>
            </div>
            <div className="text-sm text-[var(--color-text-tertiary)] font-mono">
              Technical Documentation
            </div>
          </div>
        </div>
      </footer>
    </div>
  );
}

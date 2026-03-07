import Link from 'next/link';
import { notFound } from 'next/navigation';
import {
  Terminal,
  ArrowLeft,
  ArrowRight,
  ExternalLink,
  AlertTriangle,
  CheckCircle,
  Cpu,
  FileText,
  Zap,
} from 'lucide-react';
import ThemeToggle from '@/components/landing/ThemeToggle';
import { TechNavBrand, TechFooterBrand } from '@/components/landing/NavBrand';
import SystemBadge from '@/components/use-cases/SystemBadge';
import JourneyFlow from '@/components/use-cases/JourneyFlow';
import ArchitectureFlow from '@/components/use-cases/ArchitectureFlow';
import UseCasePrevNext from '@/components/use-cases/UseCasePrevNext';
import {
  useCases,
  getUseCaseBySlug,
  getAdjacentUseCases,
} from '@/lib/use-cases-data';
import type { Metadata } from 'next';

interface PageProps {
  params: Promise<{ slug: string }>;
}

export async function generateStaticParams() {
  return useCases.map((uc) => ({ slug: uc.slug }));
}

export async function generateMetadata({ params }: PageProps): Promise<Metadata> {
  const { slug } = await params;
  const useCase = getUseCaseBySlug(slug);
  const brand = 'Fenlo AI';
  if (!useCase) return { title: `Not Found — ${brand}` };
  return {
    title: `${useCase.title} — ${brand} Use Cases`,
    description: useCase.subtitle,
  };
}

const accentBorderLeft: Record<string, string> = {
  'terminal-green': 'border-terminal-green',
  'cyber-orange': 'border-cyber-orange',
  'warning-amber': 'border-warning-amber',
};

const accentBg: Record<string, string> = {
  'terminal-green': 'bg-terminal-green',
  'cyber-orange': 'bg-cyber-orange',
  'warning-amber': 'bg-warning-amber',
};

const accentBgFaint: Record<string, string> = {
  'terminal-green': 'bg-terminal-green/5',
  'cyber-orange': 'bg-cyber-orange/5',
  'warning-amber': 'bg-warning-amber/5',
};

const accentText: Record<string, string> = {
  'terminal-green': 'text-terminal-green',
  'cyber-orange': 'text-cyber-orange',
  'warning-amber': 'text-warning-amber',
};

export default async function UseCaseDetailPage({ params }: PageProps) {
  const { slug } = await params;
  const useCase = getUseCaseBySlug(slug);
  if (!useCase) notFound();

  const { prev, next } = getAdjacentUseCases(slug);
  const Icon = useCase.icon;
  const caseIndex = useCases.findIndex((uc) => uc.slug === slug);
  const caseNum = String(caseIndex + 1).padStart(2, '0');

  return (
    <div className="min-h-screen bg-[var(--color-bg-primary)]">
      {/* Navigation */}
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
              className="text-sm font-mono text-[var(--color-text-primary)] transition uppercase tracking-wide"
            >
              Use Cases
            </Link>
            <Link
              href="/architecture"
              className="text-sm font-mono text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)] transition uppercase tracking-wide"
            >
              Docs
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

      {/* Hero */}
      <section className="relative overflow-hidden border-b border-[var(--color-border)]">
        <div className="absolute inset-0 grid-pattern opacity-40" />
        <div className="absolute inset-0 scan-line pointer-events-none" />

        {/* Large watermark number */}
        <div className={`absolute right-8 lg:right-16 top-1/2 -translate-y-1/2 text-[12rem] lg:text-[16rem] font-mono font-bold leading-none ${accentText[useCase.accentColor]} opacity-[0.03] select-none pointer-events-none`}>
          {caseNum}
        </div>

        <div className="relative container mx-auto px-4 py-16 lg:py-24">
          <div className="max-w-4xl">
            {/* Back link + counter */}
            <div className="flex items-center justify-between mb-8">
              <Link
                href="/use-cases"
                className="inline-flex items-center gap-2 text-sm font-mono text-[var(--color-text-tertiary)] hover:text-[var(--color-text-primary)] transition"
              >
                <ArrowLeft className="w-3 h-3" />
                All Use Cases
              </Link>
              <div className="text-sm font-mono text-[var(--color-text-tertiary)]">
                <span className={`font-bold ${accentText[useCase.accentColor]}`}>{caseNum}</span>
                <span className="mx-1">/</span>
                <span>{String(useCases.length).padStart(2, '0')}</span>
              </div>
            </div>

            {/* Status badge */}
            <div className={`inline-flex items-center gap-2 px-3 py-1 border ${accentBorderLeft[useCase.accentColor]} ${accentBgFaint[useCase.accentColor]} mb-6 sharp`}>
              <div className={`w-2 h-2 ${accentBg[useCase.accentColor]} animate-pulse sharp`} />
              <span className={`text-xs font-mono font-bold ${accentText[useCase.accentColor]} uppercase tracking-wider`}>
                Case {caseNum} — {useCase.systems.join(' + ')}
              </span>
            </div>

            {/* Title */}
            <h1 className="text-5xl lg:text-6xl font-mono font-bold leading-[1.1] mb-6 tracking-tight">
              <span className="block">{useCase.title.split(' ')[0]}</span>
              <span className={`block ${accentText[useCase.accentColor]}`}>
                {useCase.title.split(' ').slice(1).join(' ') || useCase.title}
              </span>
            </h1>

            {/* Subtitle */}
            <div className={`pl-4 border-l-2 ${accentBorderLeft[useCase.accentColor]} mb-8`}>
              <p className="text-lg text-[var(--color-text-secondary)] leading-relaxed max-w-2xl">
                {useCase.subtitle}
              </p>
            </div>

            {/* System badges — larger */}
            <div className="flex flex-wrap gap-2">
              {useCase.systems.map((sys) => (
                <SystemBadge key={sys} system={sys} size="md" />
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* Quick Spec Bar */}
      <section className="py-4 border-b border-[var(--color-border)] bg-[var(--color-bg-secondary)]">
        <div className="container mx-auto px-4">
          <div className="flex items-center gap-6 overflow-x-auto text-xs font-mono text-[var(--color-text-tertiary)]">
            <div className="flex items-center gap-2 whitespace-nowrap">
              <Zap className="w-3 h-3" />
              <span className="uppercase tracking-wider">Systems:</span>
              <span className="text-[var(--color-text-primary)] font-bold">{useCase.systems.length}</span>
            </div>
            <div className="w-px h-4 bg-[var(--color-border)]" />
            <div className="flex items-center gap-2 whitespace-nowrap">
              <FileText className="w-3 h-3" />
              <span className="uppercase tracking-wider">Journey Steps:</span>
              <span className="text-[var(--color-text-primary)] font-bold">{useCase.journeySteps.length}</span>
            </div>
            <div className="w-px h-4 bg-[var(--color-border)]" />
            <div className="flex items-center gap-2 whitespace-nowrap">
              <Cpu className="w-3 h-3" />
              <span className="uppercase tracking-wider">Tech Components:</span>
              <span className="text-[var(--color-text-primary)] font-bold">{useCase.techStack.length}</span>
            </div>
          </div>
        </div>
      </section>

      {/* The Problem */}
      <section className="py-20 border-b border-[var(--color-border)]">
        <div className="container mx-auto px-4">
          <div className="max-w-4xl mx-auto">
            <div className="mb-10">
              <div className="flex items-center gap-3 mb-3">
                <div className="w-1 h-8 bg-cyber-orange" />
                <h2 className="text-3xl font-mono font-bold uppercase tracking-tight">
                  The Problem
                </h2>
              </div>
              <p className="text-[var(--color-text-secondary)] font-medium">
                {useCase.problem.headline}
              </p>
            </div>

            <div className="grid sm:grid-cols-2 gap-4">
              {useCase.problem.points.map((point, i) => (
                <div
                  key={i}
                  className="relative p-5 border border-[var(--color-border)] border-l-2 border-l-cyber-orange sharp group hover:bg-[var(--color-bg-secondary)] transition-colors"
                >
                  {/* Number watermark */}
                  <div className="absolute top-3 right-4 text-3xl font-mono font-bold text-cyber-orange opacity-[0.07] select-none">
                    {String(i + 1).padStart(2, '0')}
                  </div>
                  <div className="flex items-start gap-3">
                    <AlertTriangle className="w-4 h-4 text-cyber-orange flex-shrink-0 mt-1" />
                    <p className="text-sm text-[var(--color-text-secondary)] leading-relaxed">
                      {point}
                    </p>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* The Solution */}
      <section className="py-20 border-b border-[var(--color-border)]">
        <div className="container mx-auto px-4">
          <div className="max-w-4xl mx-auto">
            <div className="mb-10">
              <div className="flex items-center gap-3 mb-3">
                <div className="w-1 h-8 bg-terminal-green" />
                <h2 className="text-3xl font-mono font-bold uppercase tracking-tight">
                  The Solution
                </h2>
              </div>
              <p className="text-[var(--color-text-secondary)] font-medium">
                {useCase.solution.headline}
              </p>
            </div>

            <p className="text-[var(--color-text-secondary)] leading-relaxed mb-8 max-w-3xl">
              {useCase.solution.description}
            </p>

            {/* Capabilities — "System Spec" readout */}
            <div className="border-2 border-terminal-green sharp overflow-hidden">
              <div className="flex items-center gap-2 px-5 py-3 bg-terminal-green/10 border-b border-terminal-green">
                <CheckCircle className="w-4 h-4 text-terminal-green" />
                <h3 className="font-mono text-sm font-bold text-terminal-green uppercase tracking-wider">
                  System Capabilities
                </h3>
              </div>
              <div className="p-5">
                <div className="grid sm:grid-cols-2 gap-3">
                  {useCase.solution.capabilities.map((cap, i) => (
                    <div key={i} className="flex items-start gap-3 group">
                      <span className="text-[10px] font-mono font-bold text-terminal-green mt-0.5 mono-num flex-shrink-0">
                        [{String(i + 1).padStart(2, '0')}]
                      </span>
                      <span className="text-sm text-[var(--color-text-secondary)] group-hover:text-[var(--color-text-primary)] transition-colors">
                        {cap}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* User Journey */}
      <section className="py-20 border-b border-[var(--color-border)]">
        <div className="container mx-auto px-4">
          <div className="max-w-4xl mx-auto">
            <div className="mb-10">
              <div className="flex items-center gap-3 mb-3">
                <div className={`w-1 h-8 ${accentBg[useCase.accentColor]}`} />
                <h2 className="text-3xl font-mono font-bold uppercase tracking-tight">
                  User Journey
                </h2>
              </div>
              <p className="text-[var(--color-text-secondary)]">
                Step-by-step flow from initial contact to resolution
              </p>
            </div>

            <JourneyFlow
              steps={useCase.journeySteps}
              accentColor={useCase.accentColor}
            />
          </div>
        </div>
      </section>

      {/* System Architecture */}
      <section className="py-20 border-b border-[var(--color-border)]">
        <div className="container mx-auto px-4">
          <div className="max-w-4xl mx-auto">
            <div className="mb-10">
              <div className="flex items-center gap-3 mb-3">
                <div className="w-1 h-8 bg-[var(--color-text-tertiary)]" />
                <h2 className="text-3xl font-mono font-bold uppercase tracking-tight">
                  System Architecture
                </h2>
              </div>
              <p className="text-[var(--color-text-secondary)]">
                How data flows through the system for this use case
              </p>
            </div>

            <ArchitectureFlow
              nodes={useCase.architecture.nodes}
              description={useCase.architecture.description}
            />
          </div>
        </div>
      </section>

      {/* Tech Stack */}
      <section className="py-20 border-b border-[var(--color-border)]">
        <div className="container mx-auto px-4">
          <div className="max-w-4xl mx-auto">
            <div className="mb-10">
              <div className="flex items-center gap-3 mb-3">
                <div className="w-1 h-8 bg-terminal-green" />
                <h2 className="text-3xl font-mono font-bold uppercase tracking-tight">
                  Tech Stack
                </h2>
              </div>
              <p className="text-[var(--color-text-secondary)]">
                Technologies powering this solution
              </p>
            </div>

            <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-3">
              {useCase.techStack.map((tech, i) => (
                <div
                  key={tech}
                  className="group flex items-center gap-3 px-4 py-3 border border-[var(--color-border)] sharp hover:border-terminal-green transition-colors bg-[var(--color-bg-primary)]"
                >
                  <span className="text-[10px] font-mono font-bold text-[var(--color-text-tertiary)] mono-num">
                    {String(i + 1).padStart(2, '0')}
                  </span>
                  <span className="text-sm font-mono group-hover:text-terminal-green transition-colors">
                    {tech}
                  </span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* CTA + Prev/Next */}
      <section className="py-20">
        <div className="container mx-auto px-4">
          <div className="max-w-4xl mx-auto">
            {/* CTA */}
            <div className="text-center mb-16">
              <div className="inline-flex items-center gap-2 px-3 py-1 border border-terminal-green bg-terminal-green/5 mb-6 sharp">
                <Terminal className="w-3 h-3 text-terminal-green" />
                <span className="text-xs font-mono font-bold text-terminal-green uppercase tracking-wider">
                  Ready to Deploy
                </span>
              </div>
              <h2 className="text-3xl font-mono font-bold mb-4 uppercase tracking-tight">
                Deploy This Solution
              </h2>
              <p className="text-[var(--color-text-secondary)] mb-8">
                Custom-built for your specific documents, workflows, and channels.
              </p>
              <div className="flex flex-wrap justify-center gap-4">
                <a
                  href="https://www.upwork.com/freelancers/~01616659fe49b6d49c"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-2 px-8 py-4 bg-black dark:bg-white text-white dark:text-black font-mono font-bold sharp hover:opacity-90 transition uppercase tracking-wide"
                >
                  Hire on Upwork
                  <ExternalLink className="w-4 h-4" />
                </a>
                <Link
                  href="/register"
                  className="inline-flex items-center gap-2 px-8 py-4 border-2 border-[var(--color-border)] font-mono font-bold sharp hover:border-[var(--color-border-strong)] transition uppercase tracking-wide"
                >
                  Try Live Demo
                  <ArrowRight className="w-4 h-4" />
                </Link>
              </div>
            </div>

            {/* Prev/Next */}
            <UseCasePrevNext prev={prev} next={next} />
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
              <Link href="/architecture" className="hover:text-terminal-green transition">
                /architecture
              </Link>
              <Link href="/api/docs" className="hover:text-terminal-green transition">
                /api
              </Link>
            </div>
            <div className="text-sm text-[var(--color-text-tertiary)] font-mono">
              Built by{' '}
              <a
                href="https://www.upwork.com/freelancers/~01616659fe49b6d49c"
                target="_blank"
                rel="noopener noreferrer"
                className="text-terminal-green hover:underline"
              >
                Mohammad Shoaib
              </a>
            </div>
          </div>
        </div>
      </footer>
    </div>
  );
}

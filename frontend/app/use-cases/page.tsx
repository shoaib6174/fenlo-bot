import Link from 'next/link';
import {
  Terminal,
  ArrowRight,
  ExternalLink,
  Crosshair,
  Layers,
} from 'lucide-react';
import ThemeToggle from '@/components/landing/ThemeToggle';
import { TechNavBrand, TechFooterBrand } from '@/components/landing/NavBrand';
import UseCaseCard from '@/components/use-cases/UseCaseCard';
import { useCases } from '@/lib/use-cases-data';
import type { Metadata } from 'next';

export const metadata: Metadata = {
  title: 'Use Cases — Fenlo AI',
  description:
    'Industry-specific AI chatbot and voice agent solutions. E-commerce, SaaS, real estate, healthcare, legal, restaurant, education, and HR use cases.',
};

export default async function UseCasesIndexPage() {
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

        <div className="relative container mx-auto px-4 py-20 lg:py-28">
          <div className="max-w-4xl">
            <div className="inline-flex items-center gap-2 px-3 py-1 border border-cyber-orange bg-cyber-orange/5 mb-8 sharp">
              <Crosshair className="w-3 h-3 text-cyber-orange" />
              <span className="text-xs font-mono font-bold text-cyber-orange uppercase tracking-wider">
                Industry Solutions — 8 Dossiers
              </span>
            </div>

            <h1 className="text-5xl lg:text-7xl font-mono font-bold leading-[1.05] mb-6 tracking-tight">
              <span className="block">USE CASES</span>
              <span className="block text-cyber-orange">BY INDUSTRY</span>
            </h1>

            <div className="pl-4 border-l-2 border-cyber-orange mb-10">
              <p className="text-lg text-[var(--color-text-secondary)] leading-relaxed max-w-2xl">
                Real-world deployment scenarios for AI chatbots and voice agents.
                Each dossier details the problem, solution architecture, user journey,
                and technology stack — using only real Fenlo AI system capabilities.
              </p>
            </div>

            {/* Quick stats */}
            <div className="flex flex-wrap gap-4">
              {[
                { label: 'Industries', value: '8' },
                { label: 'Systems', value: '4' },
                { label: 'Channels', value: '5+' },
              ].map((stat) => (
                <div
                  key={stat.label}
                  className="border border-[var(--color-border)] bg-[var(--color-bg-elevated)] px-4 py-2.5 sharp"
                >
                  <span className="font-mono text-lg font-bold mono-num mr-2">
                    {stat.value}
                  </span>
                  <span className="text-xs font-mono text-[var(--color-text-tertiary)] uppercase tracking-wider">
                    {stat.label}
                  </span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* Table of Contents */}
      <section className="py-8 border-b border-[var(--color-border)] bg-[var(--color-bg-secondary)]">
        <div className="container mx-auto px-4">
          <div className="flex items-center gap-3 overflow-x-auto pb-1">
            <Layers className="w-4 h-4 text-[var(--color-text-tertiary)] flex-shrink-0" />
            {useCases.map((uc, i) => (
              <Link
                key={uc.slug}
                href={`/use-cases/${uc.slug}`}
                className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-mono text-[var(--color-text-tertiary)] hover:text-[var(--color-text-primary)] transition whitespace-nowrap"
              >
                <span className="text-[var(--color-text-tertiary)] mono-num">
                  {String(i + 1).padStart(2, '0')}
                </span>
                <span className="uppercase tracking-wide">{uc.title}</span>
              </Link>
            ))}
          </div>
        </div>
      </section>

      {/* Use Case Grid */}
      <section className="py-20 border-b border-[var(--color-border)]">
        <div className="container mx-auto px-4">
          <div className="mb-12">
            <div className="flex items-center gap-3 mb-3">
              <div className="w-1 h-8 bg-terminal-green" />
              <h2 className="text-3xl font-mono font-bold uppercase tracking-tight">
                Solution Dossiers
              </h2>
            </div>
            <p className="text-[var(--color-text-secondary)]">
              Each card opens a full technical breakdown — problem analysis, user journey,
              system architecture, and deployment stack.
            </p>
          </div>

          <div className="grid md:grid-cols-2 gap-5 max-w-5xl">
            {useCases.map((uc, i) => (
              <UseCaseCard key={uc.slug} useCase={uc} index={i} />
            ))}
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="py-20 border-b border-[var(--color-border)]">
        <div className="container mx-auto px-4 text-center">
          <div className="max-w-2xl mx-auto">
            <div className="inline-flex items-center gap-2 px-3 py-1 border border-terminal-green bg-terminal-green/5 mb-6 sharp">
              <Terminal className="w-3 h-3 text-terminal-green" />
              <span className="text-xs font-mono font-bold text-terminal-green uppercase tracking-wider">
                Custom Solutions
              </span>
            </div>
            <h2 className="text-3xl lg:text-4xl font-mono font-bold mb-4 uppercase tracking-tight">
              Need a Different Use Case?
            </h2>
            <p className="text-[var(--color-text-secondary)] mb-10 leading-relaxed">
              These are starting points. Every deployment is customized to your
              specific requirements, documents, and workflows.
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

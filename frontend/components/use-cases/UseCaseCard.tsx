import Link from 'next/link';
import { ArrowRight } from 'lucide-react';
import type { UseCase } from '@/lib/use-cases-data';
import SystemBadge from './SystemBadge';

const accentBorderHover: Record<string, string> = {
  'terminal-green': 'hover:border-terminal-green',
  'cyber-orange': 'hover:border-cyber-orange',
  'warning-amber': 'hover:border-warning-amber',
};

const accentBg: Record<string, string> = {
  'terminal-green': 'bg-terminal-green',
  'cyber-orange': 'bg-cyber-orange',
  'warning-amber': 'bg-warning-amber',
};

const accentText: Record<string, string> = {
  'terminal-green': 'text-terminal-green',
  'cyber-orange': 'text-cyber-orange',
  'warning-amber': 'text-warning-amber',
};

export default function UseCaseCard({
  useCase,
  index,
}: {
  useCase: UseCase;
  index: number;
}) {
  const Icon = useCase.icon;
  const num = String(index + 1).padStart(2, '0');

  return (
    <Link
      href={`/use-cases/${useCase.slug}`}
      className={`group relative block border-2 border-[var(--color-border)] sharp overflow-hidden transition-all duration-300 ${accentBorderHover[useCase.accentColor]} hover:shadow-[4px_4px_0px_0px_var(--color-border)]`}
    >
      {/* Grid pattern overlay on hover */}
      <div className="absolute inset-0 grid-pattern opacity-0 group-hover:opacity-30 transition-opacity duration-300 pointer-events-none" />

      {/* Accent top bar */}
      <div className={`h-1 ${accentBg[useCase.accentColor]}`} />

      <div className="relative p-6 lg:p-8">
        {/* Top row: Number + Icon */}
        <div className="flex items-start justify-between mb-5">
          <div className="flex items-center gap-4">
            <div className={`w-12 h-12 ${accentBg[useCase.accentColor]} flex items-center justify-center sharp`}>
              <Icon className="w-6 h-6 text-black" />
            </div>
            <div>
              <div className="text-[10px] font-mono font-bold text-[var(--color-text-tertiary)] uppercase tracking-widest mb-1">
                Case {num}
              </div>
              <h3 className="text-lg font-mono font-bold uppercase tracking-tight leading-tight">
                {useCase.title}
              </h3>
            </div>
          </div>
          {/* Large background number */}
          <div className={`text-6xl font-mono font-bold leading-none ${accentText[useCase.accentColor]} opacity-[0.07] select-none`}>
            {num}
          </div>
        </div>

        {/* Brief */}
        <p className="text-sm text-[var(--color-text-secondary)] mb-5 leading-relaxed">
          {useCase.subtitle}
        </p>

        {/* Systems */}
        <div className="flex flex-wrap gap-1.5 mb-6">
          {useCase.systems.map((sys) => (
            <SystemBadge key={sys} system={sys} />
          ))}
        </div>

        {/* Divider */}
        <div className="border-t border-[var(--color-border)] pt-4">
          <div className={`flex items-center justify-between text-sm font-mono font-bold uppercase tracking-wide ${accentText[useCase.accentColor]}`}>
            <span>View Dossier</span>
            <ArrowRight className="w-4 h-4 group-hover:translate-x-2 transition-transform duration-300" />
          </div>
        </div>
      </div>
    </Link>
  );
}

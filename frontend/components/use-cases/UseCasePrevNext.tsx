import Link from 'next/link';
import { ArrowLeft, ArrowRight } from 'lucide-react';
import { useCases, type UseCase } from '@/lib/use-cases-data';

const accentBorderTop: Record<string, string> = {
  'terminal-green': 'border-t-terminal-green',
  'cyber-orange': 'border-t-cyber-orange',
  'warning-amber': 'border-t-warning-amber',
};

const accentText: Record<string, string> = {
  'terminal-green': 'text-terminal-green',
  'cyber-orange': 'text-cyber-orange',
  'warning-amber': 'text-warning-amber',
};

function getIndex(uc: UseCase): string {
  const idx = useCases.findIndex((u) => u.slug === uc.slug);
  return String(idx + 1).padStart(2, '0');
}

export default function UseCasePrevNext({
  prev,
  next,
}: {
  prev: UseCase | null;
  next: UseCase | null;
}) {
  return (
    <div className="grid grid-cols-2 gap-4">
      {prev ? (
        <Link
          href={`/use-cases/${prev.slug}`}
          className={`group border-2 border-[var(--color-border)] border-t-2 ${accentBorderTop[prev.accentColor]} sharp p-5 hover:bg-[var(--color-bg-secondary)] transition-colors`}
        >
          <div className="flex items-center gap-2 text-xs font-mono text-[var(--color-text-tertiary)] uppercase tracking-wider mb-3">
            <ArrowLeft className="w-3 h-3 group-hover:-translate-x-1 transition-transform" />
            Previous — Case {getIndex(prev)}
          </div>
          <div className="font-mono text-sm font-bold uppercase tracking-tight">
            {prev.title}
          </div>
          <div className="flex flex-wrap gap-1 mt-2">
            {prev.systems.map((s) => (
              <span key={s} className={`text-[9px] font-mono font-bold uppercase tracking-wider ${accentText[prev.accentColor]}`}>
                {s}
              </span>
            ))}
          </div>
        </Link>
      ) : (
        <div />
      )}

      {next ? (
        <Link
          href={`/use-cases/${next.slug}`}
          className={`group border-2 border-[var(--color-border)] border-t-2 ${accentBorderTop[next.accentColor]} sharp p-5 hover:bg-[var(--color-bg-secondary)] transition-colors text-right`}
        >
          <div className="flex items-center justify-end gap-2 text-xs font-mono text-[var(--color-text-tertiary)] uppercase tracking-wider mb-3">
            Case {getIndex(next)} — Next
            <ArrowRight className="w-3 h-3 group-hover:translate-x-1 transition-transform" />
          </div>
          <div className="font-mono text-sm font-bold uppercase tracking-tight">
            {next.title}
          </div>
          <div className="flex flex-wrap justify-end gap-1 mt-2">
            {next.systems.map((s) => (
              <span key={s} className={`text-[9px] font-mono font-bold uppercase tracking-wider ${accentText[next.accentColor]}`}>
                {s}
              </span>
            ))}
          </div>
        </Link>
      ) : (
        <div />
      )}
    </div>
  );
}

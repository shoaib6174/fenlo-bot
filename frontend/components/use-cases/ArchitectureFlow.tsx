import { ArrowRight, Monitor } from 'lucide-react';
import type { ArchitectureNode } from '@/lib/use-cases-data';

export default function ArchitectureFlow({
  nodes,
  description,
}: {
  nodes: ArchitectureNode[];
  description: string;
}) {
  return (
    <div>
      {/* Terminal window chrome */}
      <div className="border-2 border-[var(--color-border)] sharp overflow-hidden">
        {/* Title bar */}
        <div className="flex items-center gap-3 px-4 py-2.5 bg-[var(--color-bg-secondary)] border-b-2 border-[var(--color-border)]">
          <div className="flex items-center gap-1.5">
            <div className="w-2.5 h-2.5 bg-error-red sharp" />
            <div className="w-2.5 h-2.5 bg-warning-amber sharp" />
            <div className="w-2.5 h-2.5 bg-terminal-green sharp" />
          </div>
          <div className="flex items-center gap-2">
            <Monitor className="w-3.5 h-3.5 text-[var(--color-text-tertiary)]" />
            <span className="text-xs font-mono font-bold text-[var(--color-text-tertiary)] uppercase tracking-wider">
              system-architecture.flow
            </span>
          </div>
        </div>

        {/* Flow diagram */}
        <div className="p-6 bg-[var(--color-bg-primary)]">
          {/* Horizontal flow — scrollable on mobile */}
          <div className="overflow-x-auto pb-2">
            <div className="flex items-stretch gap-0 min-w-max">
              {nodes.map((node, idx) => (
                <div key={idx} className="flex items-stretch">
                  <div className="relative group">
                    {/* Top accent line */}
                    <div className={`h-0.5 ${
                      idx === 0 ? 'bg-terminal-green' :
                      idx === nodes.length - 1 ? 'bg-cyber-orange' :
                      'bg-[var(--color-text-tertiary)]'
                    }`} />

                    <div className="border border-[var(--color-border)] border-t-0 sharp p-4 w-44 flex flex-col group-hover:bg-[var(--color-bg-secondary)] transition-colors duration-200">
                      <div className="flex items-center gap-2 mb-2">
                        <span className="text-[10px] font-mono font-bold text-[var(--color-text-tertiary)] uppercase tracking-widest mono-num">
                          N{String(idx + 1).padStart(2, '0')}
                        </span>
                      </div>
                      <h4 className="font-mono text-sm font-bold mb-2 uppercase tracking-wide leading-tight">
                        {node.label}
                      </h4>
                      <p className="text-xs text-[var(--color-text-secondary)] leading-relaxed mt-auto">
                        {node.description}
                      </p>
                    </div>
                  </div>

                  {idx < nodes.length - 1 && (
                    <div className="flex items-center px-1.5 self-center">
                      <div className="flex items-center gap-0.5">
                        <div className="w-3 h-px bg-[var(--color-text-tertiary)]" />
                        <ArrowRight className="w-3.5 h-3.5 text-[var(--color-text-tertiary)]" />
                        <div className="w-3 h-px bg-[var(--color-text-tertiary)]" />
                      </div>
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* Description callout */}
      <div className="mt-4 p-4 border border-[var(--color-border)] bg-[var(--color-bg-secondary)] sharp">
        <div className="flex items-start gap-3">
          <span className="text-xs font-mono font-bold text-[var(--color-text-tertiary)] uppercase tracking-wider mt-0.5 flex-shrink-0">
            {'//'}
          </span>
          <p className="text-sm text-[var(--color-text-secondary)] leading-relaxed">
            {description}
          </p>
        </div>
      </div>
    </div>
  );
}

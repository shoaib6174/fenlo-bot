import type { SystemName } from '@/lib/use-cases-data';

const systemConfig: Record<SystemName, { bg: string; text: string; dot: string }> = {
  RAGChat: { bg: 'bg-terminal-green/10 border-terminal-green', text: 'text-terminal-green', dot: 'bg-terminal-green' },
  'VoiceBot Pro': { bg: 'bg-cyber-orange/10 border-cyber-orange', text: 'text-cyber-orange', dot: 'bg-cyber-orange' },
  OmniBot: { bg: 'bg-warning-amber/10 border-warning-amber', text: 'text-warning-amber', dot: 'bg-warning-amber' },
  'Human Handoff': { bg: 'bg-[var(--color-bg-elevated)] border-[var(--color-border-strong)]', text: 'text-[var(--color-text-primary)]', dot: 'bg-[var(--color-text-tertiary)]' },
};

export default function SystemBadge({ system, size = 'sm' }: { system: SystemName; size?: 'sm' | 'md' }) {
  const config = systemConfig[system];
  const isMd = size === 'md';
  return (
    <span
      className={`inline-flex items-center gap-1.5 border sharp font-mono font-bold uppercase tracking-wider ${config.bg} ${config.text} ${
        isMd ? 'px-3 py-1 text-xs' : 'px-2 py-0.5 text-[10px]'
      }`}
    >
      <span className={`${isMd ? 'w-1.5 h-1.5' : 'w-1 h-1'} ${config.dot} sharp`} />
      {system}
    </span>
  );
}

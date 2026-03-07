import type { JourneyStep, AccentColor } from '@/lib/use-cases-data';
import SystemBadge from './SystemBadge';

const accentBg: Record<AccentColor, string> = {
  'terminal-green': 'bg-terminal-green',
  'cyber-orange': 'bg-cyber-orange',
  'warning-amber': 'bg-warning-amber',
};

const accentBorder: Record<AccentColor, string> = {
  'terminal-green': 'border-terminal-green',
  'cyber-orange': 'border-cyber-orange',
  'warning-amber': 'border-warning-amber',
};

const accentText: Record<AccentColor, string> = {
  'terminal-green': 'text-terminal-green',
  'cyber-orange': 'text-cyber-orange',
  'warning-amber': 'text-warning-amber',
};

export default function JourneyFlow({
  steps,
  accentColor,
}: {
  steps: JourneyStep[];
  accentColor: AccentColor;
}) {
  return (
    <div className="relative">
      {/* Vertical track line */}
      <div
        className={`absolute left-[23px] top-0 bottom-0 w-px ${accentBg[accentColor]} opacity-20`}
      />

      <div className="space-y-0">
        {steps.map((step, idx) => (
          <div key={idx} className="relative group">
            <div className="flex items-start gap-5 py-5 pl-0 pr-4">
              {/* Node indicator */}
              <div className="relative flex-shrink-0 z-10">
                {/* Pulse ring */}
                <div className={`absolute inset-0 ${accentBg[accentColor]} opacity-0 group-hover:opacity-20 sharp scale-150 transition-opacity duration-300`} />
                {/* Node box */}
                <div className={`w-12 h-12 border-2 ${accentBorder[accentColor]} bg-[var(--color-bg-primary)] sharp flex items-center justify-center transition-colors duration-200 group-hover:${accentBg[accentColor]}`}>
                  <span className={`text-sm font-mono font-bold mono-num ${accentText[accentColor]} group-hover:text-black transition-colors duration-200`}>
                    {String(idx + 1).padStart(2, '0')}
                  </span>
                </div>
              </div>

              {/* Content */}
              <div className="flex-1 min-w-0 pt-1">
                <div className="flex items-center gap-3 mb-2 flex-wrap">
                  <h3 className="font-mono text-sm font-bold uppercase tracking-wide">
                    {step.name}
                  </h3>
                  {step.systemTag && <SystemBadge system={step.systemTag} />}
                </div>
                <p className="text-sm text-[var(--color-text-secondary)] leading-relaxed">
                  {step.description}
                </p>
              </div>
            </div>

            {/* Connector */}
            {idx < steps.length - 1 && (
              <div className="flex items-center gap-0 ml-[14px] py-0">
                <div className={`w-[3px] h-4 ${accentBg[accentColor]} opacity-30`} />
              </div>
            )}
          </div>
        ))}
      </div>

      {/* Terminal footer */}
      <div className={`mt-4 p-3 border ${accentBorder[accentColor]} bg-[var(--color-bg-secondary)] sharp`}>
        <div className="flex items-center gap-2">
          <div className={`w-2 h-2 ${accentBg[accentColor]} animate-pulse sharp`} />
          <span className={`text-xs font-mono font-bold ${accentText[accentColor]} uppercase tracking-wider`}>
            Pipeline Complete — {steps.length} Steps
          </span>
        </div>
      </div>
    </div>
  );
}

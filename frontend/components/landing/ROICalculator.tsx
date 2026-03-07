/**
 * ROI Calculator — Technical Brutalism Edition
 * Precision engineering metrics with terminal aesthetics
 */

"use client";

import { useState, useEffect, useRef } from "react";
import { Calculator, DollarSign, Clock, TrendingUp, Terminal } from "lucide-react";

const AUTOMATION_RATE = 0.6;
const MONTHS_PER_YEAR = 12;

function useAnimatedNumber(target: number, duration: number = 400) {
  const [value, setValue] = useState(0);
  const rafRef = useRef<number | undefined>(undefined);
  const startRef = useRef<number | undefined>(undefined);
  const fromRef = useRef<number>(0);

  useEffect(() => {
    fromRef.current = value;
    startRef.current = undefined;

    const animate = (timestamp: number) => {
      if (!startRef.current) startRef.current = timestamp;
      const elapsed = timestamp - startRef.current;
      const progress = Math.min(elapsed / duration, 1);
      // Linear easing for precision feel
      const current = fromRef.current + (target - fromRef.current) * progress;
      setValue(Math.round(current));

      if (progress < 1) {
        rafRef.current = requestAnimationFrame(animate);
      }
    };

    rafRef.current = requestAnimationFrame(animate);
    return () => {
      if (rafRef.current) cancelAnimationFrame(rafRef.current);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [target, duration]);

  return value;
}

export default function ROICalculator() {
  const [tickets, setTickets] = useState(500);
  const [handleTime, setHandleTime] = useState(8); // minutes
  const [hourlyCost, setHourlyCost] = useState(25); // dollars

  // Calculations
  const handleTimeHours = handleTime / 60;
  const monthlySavings = Math.round(
    tickets * AUTOMATION_RATE * handleTimeHours * hourlyCost
  );
  const yearlySavings = monthlySavings * MONTHS_PER_YEAR;
  const hoursFreed = Math.round(tickets * AUTOMATION_RATE * handleTimeHours);

  // Animated values
  const animatedMonthlySavings = useAnimatedNumber(monthlySavings);
  const animatedYearlySavings = useAnimatedNumber(yearlySavings);
  const animatedHoursFreed = useAnimatedNumber(hoursFreed);

  return (
    <section className="py-20 border-b border-[var(--color-border)]">
      <div className="container mx-auto px-4">
        <div className="mb-12">
          <div className="flex items-center gap-3 mb-3">
            <div className="w-1 h-8 bg-terminal-green" />
            <h2 className="text-3xl font-mono font-bold uppercase tracking-tight">
              ROI Calculator
            </h2>
          </div>
          <p className="text-[var(--color-text-secondary)] max-w-2xl">
            Quantify automation savings. Real-time computational metrics.
          </p>
        </div>

        <div className="max-w-6xl mx-auto">
          <div className="grid lg:grid-cols-2 gap-6">
            {/* Input Panel */}
            <div className="border-2 border-[var(--color-border)] p-8 sharp">
              <div className="flex items-center gap-2 mb-6">
                <Terminal className="w-4 h-4 text-terminal-green" />
                <h3 className="text-sm font-mono font-bold uppercase tracking-wider">
                  Input Parameters
                </h3>
              </div>

              <div className="space-y-8">
                {/* Tickets slider */}
                <div>
                  <div className="flex items-center justify-between mb-3">
                    <label className="text-xs font-mono text-[var(--color-text-tertiary)] uppercase tracking-wider">
                      Monthly Ticket Volume
                    </label>
                    <div className="px-2 py-1 bg-[var(--color-bg-elevated)] border border-[var(--color-border)] sharp">
                      <span className="text-sm font-mono font-bold mono-num">
                        {tickets.toLocaleString()}
                      </span>
                    </div>
                  </div>
                  <input
                    type="range"
                    min="50"
                    max="5000"
                    step="50"
                    value={tickets}
                    onChange={(e) => setTickets(Number(e.target.value))}
                    className="w-full h-1 bg-[var(--color-border)] appearance-none cursor-pointer sharp
                      [&::-webkit-slider-thumb]:appearance-none
                      [&::-webkit-slider-thumb]:w-4
                      [&::-webkit-slider-thumb]:h-4
                      [&::-webkit-slider-thumb]:bg-terminal-green
                      [&::-webkit-slider-thumb]:sharp
                      [&::-webkit-slider-thumb]:cursor-pointer
                      [&::-moz-range-thumb]:w-4
                      [&::-moz-range-thumb]:h-4
                      [&::-moz-range-thumb]:bg-terminal-green
                      [&::-moz-range-thumb]:border-0
                      [&::-moz-range-thumb]:sharp
                      [&::-moz-range-thumb]:cursor-pointer"
                    aria-label="Support tickets per month"
                  />
                  <div className="flex justify-between text-[10px] font-mono text-[var(--color-text-tertiary)] mt-1">
                    <span>50</span>
                    <span>5,000</span>
                  </div>
                </div>

                {/* Handle time slider */}
                <div>
                  <div className="flex items-center justify-between mb-3">
                    <label className="text-xs font-mono text-[var(--color-text-tertiary)] uppercase tracking-wider">
                      Avg Handle Time (min)
                    </label>
                    <div className="px-2 py-1 bg-[var(--color-bg-elevated)] border border-[var(--color-border)] sharp">
                      <span className="text-sm font-mono font-bold mono-num">
                        {handleTime}
                      </span>
                    </div>
                  </div>
                  <input
                    type="range"
                    min="2"
                    max="30"
                    step="1"
                    value={handleTime}
                    onChange={(e) => setHandleTime(Number(e.target.value))}
                    className="w-full h-1 bg-[var(--color-border)] appearance-none cursor-pointer sharp
                      [&::-webkit-slider-thumb]:appearance-none
                      [&::-webkit-slider-thumb]:w-4
                      [&::-webkit-slider-thumb]:h-4
                      [&::-webkit-slider-thumb]:bg-terminal-green
                      [&::-webkit-slider-thumb]:sharp
                      [&::-webkit-slider-thumb]:cursor-pointer
                      [&::-moz-range-thumb]:w-4
                      [&::-moz-range-thumb]:h-4
                      [&::-moz-range-thumb]:bg-terminal-green
                      [&::-moz-range-thumb]:border-0
                      [&::-moz-range-thumb]:sharp
                      [&::-moz-range-thumb]:cursor-pointer"
                    aria-label="Average handle time in minutes"
                  />
                  <div className="flex justify-between text-[10px] font-mono text-[var(--color-text-tertiary)] mt-1">
                    <span>2</span>
                    <span>30</span>
                  </div>
                </div>

                {/* Hourly cost slider */}
                <div>
                  <div className="flex items-center justify-between mb-3">
                    <label className="text-xs font-mono text-[var(--color-text-tertiary)] uppercase tracking-wider">
                      Agent Hourly Cost (USD)
                    </label>
                    <div className="px-2 py-1 bg-[var(--color-bg-elevated)] border border-[var(--color-border)] sharp">
                      <span className="text-sm font-mono font-bold mono-num">
                        ${hourlyCost}
                      </span>
                    </div>
                  </div>
                  <input
                    type="range"
                    min="10"
                    max="80"
                    step="5"
                    value={hourlyCost}
                    onChange={(e) => setHourlyCost(Number(e.target.value))}
                    className="w-full h-1 bg-[var(--color-border)] appearance-none cursor-pointer sharp
                      [&::-webkit-slider-thumb]:appearance-none
                      [&::-webkit-slider-thumb]:w-4
                      [&::-webkit-slider-thumb]:h-4
                      [&::-webkit-slider-thumb]:bg-terminal-green
                      [&::-webkit-slider-thumb]:sharp
                      [&::-webkit-slider-thumb]:cursor-pointer
                      [&::-moz-range-thumb]:w-4
                      [&::-moz-range-thumb]:h-4
                      [&::-moz-range-thumb]:bg-terminal-green
                      [&::-moz-range-thumb]:border-0
                      [&::-moz-range-thumb]:sharp
                      [&::-moz-range-thumb]:cursor-pointer"
                    aria-label="Agent hourly cost in dollars"
                  />
                  <div className="flex justify-between text-[10px] font-mono text-[var(--color-text-tertiary)] mt-1">
                    <span>$10</span>
                    <span>$80</span>
                  </div>
                </div>
              </div>

              <div className="mt-8 p-3 border border-terminal-green bg-terminal-green/5 sharp">
                <p className="text-xs font-mono text-terminal-green leading-relaxed">
                  ALGO: tickets × 0.60 × (time_min/60) × cost_usd<br/>
                  Rate: 60% automation (L1 support baseline)
                </p>
              </div>
            </div>

            {/* Output Panel */}
            <div className="space-y-4">
              {/* Primary Metric */}
              <div className="border-2 border-terminal-green bg-terminal-green/5 p-8 sharp">
                <div className="flex items-center gap-2 mb-4">
                  <DollarSign className="w-5 h-5 text-terminal-green" />
                  <span className="text-xs font-mono text-terminal-green uppercase tracking-wider">
                    Monthly Savings
                  </span>
                </div>
                <div
                  className="text-5xl font-mono font-bold text-terminal-green mono-num"
                  data-testid="monthly-savings"
                >
                  ${animatedMonthlySavings.toLocaleString()}
                </div>
              </div>

              {/* Secondary Metrics Grid */}
              <div className="grid grid-cols-2 gap-4">
                <div className="border border-[var(--color-border)] p-6 sharp">
                  <div className="flex items-center gap-2 mb-3">
                    <TrendingUp className="w-4 h-4 text-cyber-orange" />
                    <span className="text-[10px] font-mono text-[var(--color-text-tertiary)] uppercase tracking-wider">
                      Annual
                    </span>
                  </div>
                  <div
                    className="text-2xl font-mono font-bold mono-num"
                    data-testid="yearly-savings"
                  >
                    ${animatedYearlySavings.toLocaleString()}
                  </div>
                </div>

                <div className="border border-[var(--color-border)] p-6 sharp">
                  <div className="flex items-center gap-2 mb-3">
                    <Clock className="w-4 h-4 text-cyber-orange" />
                    <span className="text-[10px] font-mono text-[var(--color-text-tertiary)] uppercase tracking-wider">
                      Hours/Mo
                    </span>
                  </div>
                  <div
                    className="text-2xl font-mono font-bold mono-num"
                    data-testid="hours-freed"
                  >
                    {animatedHoursFreed.toLocaleString()}
                  </div>
                </div>
              </div>

              {/* FTE Equivalent */}
              <div className="border border-[var(--color-border)] p-6 sharp">
                <div className="text-xs font-mono text-[var(--color-text-tertiary)] mb-2 uppercase tracking-wider">
                  Equivalent Capacity
                </div>
                <div className="text-2xl font-mono font-bold mono-num mb-1">
                  {Math.max(1, Math.round(hoursFreed / 160))} FTE
                </div>
                <div className="text-[10px] font-mono text-[var(--color-text-tertiary)]">
                  Full-time agents @ 160 hrs/month
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}

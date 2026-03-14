import { ReactNode } from 'react';

interface Stat {
  label: string;
  value: string | number;
  accent: string;
  icon: ReactNode;
}

interface Props {
  stats: Stat[];
}

const ACCENT: Record<string, { dot: string; text: string; bg: string; bar: string }> = {
  green:  { dot: 'bg-green-500',   text: 'text-green-600',   bg: 'bg-green-50',        bar: 'from-green-400/40 to-transparent' },
  gray:   { dot: 'bg-gray-400',    text: 'text-gray-900',    bg: 'bg-gray-50',          bar: 'from-gray-300/30 to-transparent' },
  cyan:   { dot: 'bg-[#7DF9FF]',   text: 'text-[#0097A7]',   bg: 'bg-[#7DF9FF]/10',    bar: 'from-[#7DF9FF]/50 to-transparent' },
  purple: { dot: 'bg-purple-500',  text: 'text-purple-600',  bg: 'bg-purple-50',        bar: 'from-purple-400/40 to-transparent' },
};

export function StatsBar({ stats }: Props) {
  return (
    <>
      {stats.map((stat, i) => {
        const a = ACCENT[stat.accent] || ACCENT.gray;
        return (
          <div
            key={i}
            className="bg-white rounded-2xl px-4 flex items-center gap-3 relative overflow-hidden transition-shadow hover:shadow-md cursor-default"
            style={{ boxShadow: '0 1px 3px rgba(0,0,0,0.04), 0 6px 16px rgba(0,0,0,0.04)' }}
          >
            {/* Bottom accent bar */}
            <div className={`absolute bottom-0 left-0 right-0 h-[2px] bg-gradient-to-r ${a.bar}`} />

            <div className={`w-9 h-9 rounded-xl ${a.bg} flex items-center justify-center shrink-0`}>
              {stat.icon}
            </div>
            <div>
              <div className={`text-xl font-bold tabular-nums leading-none mb-0.5 ${a.text}`}>
                {stat.value}
              </div>
              <div className="text-[10px] text-gray-400 font-medium uppercase tracking-wider leading-tight">
                {stat.label}
              </div>
            </div>
          </div>
        );
      })}
    </>
  );
}

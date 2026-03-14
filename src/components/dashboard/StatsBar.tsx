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

const ACCENT: Record<string, { gradient: string; text: string; iconBg: string; iconText: string; border: string }> = {
  green:  { gradient: 'from-emerald-50 to-white', text: 'text-emerald-600', iconBg: 'bg-emerald-500', iconText: 'text-white', border: 'border-emerald-200/60' },
  gray:   { gradient: 'from-slate-50 to-white',   text: 'text-slate-800',   iconBg: 'bg-slate-700',   iconText: 'text-white', border: 'border-slate-200/60' },
  cyan:   { gradient: 'from-[#E0FCFF] to-white',  text: 'text-[#006B7A]',   iconBg: 'bg-[#7DF9FF]',   iconText: 'text-[#006B7A]', border: 'border-[#7DF9FF]/30' },
  purple: { gradient: 'from-purple-50 to-white',   text: 'text-purple-700',  iconBg: 'bg-purple-500',  iconText: 'text-white', border: 'border-purple-200/60' },
};

export function StatsBar({ stats }: Props) {
  return (
    <>
      {stats.map((stat, i) => {
        const a = ACCENT[stat.accent] || ACCENT.gray;
        return (
          <div
            key={i}
            className={`bg-gradient-to-br ${a.gradient} rounded-2xl px-4 flex items-center gap-3.5 border ${a.border} relative overflow-hidden group transition-all hover:scale-[1.02] cursor-default`}
            style={{ boxShadow: '0 1px 3px rgba(0,0,0,0.03), 0 4px 12px rgba(0,0,0,0.04)' }}
          >
            <div className={`w-10 h-10 rounded-xl ${a.iconBg} ${a.iconText} flex items-center justify-center shrink-0 shadow-sm`}>
              {stat.icon}
            </div>
            <div>
              <div className={`text-[22px] font-bold tabular-nums leading-none mb-0.5 font-mono ${a.text}`}>
                {stat.value}
              </div>
              <div className="text-[10px] text-slate-400 font-semibold uppercase tracking-[0.1em] leading-tight">
                {stat.label}
              </div>
            </div>
          </div>
        );
      })}
    </>
  );
}

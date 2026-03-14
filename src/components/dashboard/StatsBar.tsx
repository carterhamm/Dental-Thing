interface Stat {
  label: string;
  value: string | number;
  accent: string;
}

interface Props {
  stats: Stat[];
}

const ACCENT: Record<string, { dot: string; text: string; bg: string }> = {
  green:  { dot: 'bg-green-500',   text: 'text-green-600',   bg: 'bg-green-50' },
  gray:   { dot: 'bg-gray-400',    text: 'text-gray-900',    bg: 'bg-gray-50' },
  cyan:   { dot: 'bg-[#7DF9FF]',   text: 'text-[#0097A7]',   bg: 'bg-[#7DF9FF]/10' },
  purple: { dot: 'bg-purple-500',  text: 'text-purple-600',  bg: 'bg-purple-50' },
};

export function StatsBar({ stats }: Props) {
  return (
    <div className="grid grid-cols-4 gap-4 h-full">
      {stats.map((stat, i) => {
        const a = ACCENT[stat.accent] || ACCENT.gray;
        return (
          <div key={i} className="bg-white rounded-2xl shadow-sm px-5 flex items-center gap-3">
            <div className={`w-8 h-8 rounded-lg ${a.bg} flex items-center justify-center shrink-0`}>
              <div className={`w-2.5 h-2.5 rounded-full ${a.dot}`} />
            </div>
            <div>
              <div className={`text-xl font-bold tabular-nums ${a.text}`}>
                {stat.value}
              </div>
              <div className="text-[10px] text-gray-400 font-medium uppercase tracking-wide leading-tight">
                {stat.label}
              </div>
            </div>
          </div>
        );
      })}
    </div>
  );
}

export interface LogEntry {
  time: string;
  icon: string;
  message: string;
  type: 'call' | 'sms' | 'system' | 'success' | 'warning';
}

interface Props {
  entries: LogEntry[];
}

const TYPE_CONFIG: Record<LogEntry['type'], { text: string; border: string }> = {
  call:    { text: 'text-[#0097A7]',  border: 'border-l-[#7DF9FF]' },
  sms:     { text: 'text-purple-600', border: 'border-l-purple-400' },
  system:  { text: 'text-gray-500',   border: 'border-l-gray-300' },
  success: { text: 'text-green-600',  border: 'border-l-green-400' },
  warning: { text: 'text-amber-600',  border: 'border-l-amber-400' },
};

export function ActivityLog({ entries }: Props) {
  return (
    <div
      className="bg-white rounded-2xl p-5 flex flex-col h-full"
      style={{ boxShadow: '0 1px 3px rgba(0,0,0,0.04), 0 6px 16px rgba(0,0,0,0.04)' }}
    >
      <div className="flex items-center justify-between mb-3 px-1">
        <span className="text-[11px] font-semibold tracking-[0.08em] text-gray-400 uppercase">
          Activity
        </span>
        <span className="text-[11px] text-gray-300 tabular-nums">
          {entries.length} events
        </span>
      </div>

      <div className="flex-1 overflow-y-auto space-y-1">
        {entries.length === 0 && (
          <div className="flex flex-col items-center justify-center h-full text-center py-8">
            <div className="w-10 h-10 rounded-full bg-gray-100 flex items-center justify-center mb-3">
              <svg width="20" height="20" viewBox="0 0 20 20" fill="none"><path d="M4 6h12M4 10h8M4 14h10" stroke="#d1d5db" strokeWidth="1.5" strokeLinecap="round"/></svg>
            </div>
            <span className="text-[13px] font-medium text-gray-400">No activity yet</span>
            <span className="text-[11px] text-gray-300 mt-1">Events will stream here in real time</span>
          </div>
        )}
        {entries.map((entry, i) => {
          const cfg = TYPE_CONFIG[entry.type];
          return (
            <div
              key={i}
              className={`flex items-start gap-3 pl-3 pr-3 py-2.5 rounded-r-xl border-l-2 transition-all duration-300 ${cfg.border} ${
                i === 0 ? 'bg-gray-50/80' : 'hover:bg-gray-50/50'
              }`}
            >
              <span className="text-[11px] text-gray-300 mt-0.5 shrink-0 w-[50px] tabular-nums font-medium">
                {entry.time}
              </span>
              <span className="text-[13px] shrink-0">{entry.icon}</span>
              <span className={`text-[12.5px] leading-snug ${cfg.text}`}>
                {entry.message}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}

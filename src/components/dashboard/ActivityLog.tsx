export interface LogEntry {
  time: string;
  icon: string;
  message: string;
  type: 'call' | 'sms' | 'system' | 'success' | 'warning';
}

interface Props {
  entries: LogEntry[];
}

const TYPE_COLOR: Record<LogEntry['type'], string> = {
  call: 'text-[#0097A7]',
  sms: 'text-purple-600',
  system: 'text-gray-500',
  success: 'text-green-600',
  warning: 'text-amber-600',
};

export function ActivityLog({ entries }: Props) {
  return (
    <div className="bg-white rounded-2xl shadow-sm p-6 flex flex-col h-full">
      <div className="flex items-center justify-between mb-3">
        <span className="text-[11px] font-semibold tracking-[0.08em] text-gray-400 uppercase">
          Activity
        </span>
        <span className="text-[11px] text-gray-300 tabular-nums">
          {entries.length} events
        </span>
      </div>

      <div className="flex-1 overflow-y-auto space-y-0.5">
        {entries.map((entry, i) => (
          <div
            key={i}
            className={`flex items-start gap-3 px-3 py-2.5 rounded-xl transition-colors ${
              i === 0 ? 'bg-gray-50' : ''
            }`}
          >
            <span className="text-[11px] text-gray-300 mt-0.5 shrink-0 w-[52px] tabular-nums">
              {entry.time}
            </span>
            <span className="text-sm shrink-0">{entry.icon}</span>
            <span className={`text-[13px] leading-snug ${TYPE_COLOR[entry.type]}`}>
              {entry.message}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}

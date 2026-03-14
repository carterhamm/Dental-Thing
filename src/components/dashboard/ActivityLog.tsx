import { IconActivity } from '../Icons';

export interface LogEntry {
  time: string;
  icon: string;
  message: string;
  type: 'call' | 'sms' | 'system' | 'success' | 'warning';
}

interface Props {
  entries: LogEntry[];
}

const TYPE_CFG: Record<LogEntry['type'], { text: string; dot: string; line: string }> = {
  call:    { text: 'text-[#006B7A]',    dot: 'bg-[#7DF9FF]',     line: 'bg-[#7DF9FF]/30' },
  sms:     { text: 'text-purple-700',   dot: 'bg-purple-400',    line: 'bg-purple-200' },
  system:  { text: 'text-slate-500',    dot: 'bg-slate-300',     line: 'bg-slate-200' },
  success: { text: 'text-emerald-700',  dot: 'bg-emerald-400',   line: 'bg-emerald-200' },
  warning: { text: 'text-amber-700',    dot: 'bg-amber-400',     line: 'bg-amber-200' },
};

export function ActivityLog({ entries }: Props) {
  return (
    <div className="bg-white rounded-2xl p-5 flex flex-col h-full border border-slate-100"
      style={{ boxShadow: '0 1px 3px rgba(0,0,0,0.03), 0 6px 16px rgba(0,0,0,0.04)' }}>
      <div className="flex items-center justify-between mb-3 px-1">
        <div className="flex items-center gap-2">
          <div className="w-7 h-7 rounded-lg bg-[#E0FCFF] text-[#0097A7] flex items-center justify-center">
            <IconActivity />
          </div>
          <span className="text-[12px] font-semibold text-slate-500 uppercase tracking-[0.06em]">Activity</span>
        </div>
        <span className="text-[11px] text-slate-300 font-mono tabular-nums">{entries.length} events</span>
      </div>

      <div className="flex-1 overflow-y-auto">
        {entries.length === 0 && (
          <div className="flex flex-col items-center justify-center h-full text-center py-8">
            <div className="w-14 h-14 rounded-2xl bg-slate-50 flex items-center justify-center mb-4 text-slate-300">
              <IconActivity />
            </div>
            <span className="text-[14px] font-semibold text-slate-400">No activity yet</span>
            <span className="text-[12px] text-slate-300 mt-1">Events will stream here in real time</span>
          </div>
        )}

        {/* Timeline */}
        <div className="relative">
          {entries.map((entry, i) => {
            const cfg = TYPE_CFG[entry.type];
            const isLast = i === entries.length - 1;
            return (
              <div key={i} className="flex gap-3 relative">
                {/* Timeline spine */}
                <div className="flex flex-col items-center shrink-0 w-5">
                  <div className={`w-2.5 h-2.5 rounded-full ${cfg.dot} mt-1.5 shrink-0 z-10 ${i === 0 ? 'ring-4 ring-offset-1 ring-white' : ''}`}
                    style={i === 0 ? { boxShadow: `0 0 0 3px ${cfg.dot === 'bg-[#7DF9FF]' ? 'rgba(125,249,255,0.2)' : 'rgba(0,0,0,0.04)'}` } : undefined} />
                  {!isLast && <div className={`w-[1.5px] flex-1 ${cfg.line} min-h-[16px]`} />}
                </div>

                {/* Content */}
                <div className={`flex-1 pb-3 ${i === 0 ? 'pt-0' : ''}`}>
                  <div className="flex items-start gap-2">
                    <span className="text-[10px] text-slate-300 mt-0.5 shrink-0 w-[46px] font-mono tabular-nums font-medium">{entry.time}</span>
                    <span className="text-[13px] shrink-0">{entry.icon}</span>
                    <span className={`text-[12px] leading-relaxed ${cfg.text}`}>{entry.message}</span>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}

import { IconClock } from '../Icons';

export interface ScheduleSlot {
  id: string;
  time: string;
  treatment: string;
  status: 'booked' | 'cancelled' | 'filled';
  patient_name: string | null;
  value: number;
}

interface Props {
  slots: ScheduleSlot[];
}

const STATUS_STYLE: Record<ScheduleSlot['status'], { dot: string; text: string; bg: string }> = {
  booked:    { dot: 'bg-emerald-400', text: 'text-slate-700', bg: 'bg-white' },
  cancelled: { dot: 'bg-red-400 animate-pulse', text: 'text-red-600', bg: 'bg-red-50/50' },
  filled:    { dot: 'bg-[#7DF9FF]', text: 'text-[#006B7A]', bg: 'bg-[#E0FCFF]/30' },
};

export function DailySchedule({ slots }: Props) {
  return (
    <div className="bg-white rounded-2xl p-5 flex flex-col h-full border border-slate-100"
      style={{ boxShadow: '0 1px 3px rgba(0,0,0,0.03), 0 6px 16px rgba(0,0,0,0.04)' }}>
      <div className="flex items-center justify-between mb-3 px-1">
        <div className="flex items-center gap-2">
          <div className="w-7 h-7 rounded-lg bg-[#E0FCFF] text-[#0097A7] flex items-center justify-center">
            <IconClock />
          </div>
          <span className="text-[12px] font-semibold text-slate-500 uppercase tracking-[0.06em]">Today's Schedule</span>
        </div>
        <span className="text-[11px] text-slate-300 font-mono tabular-nums">
          {slots.length} slots
        </span>
      </div>

      <div className="flex-1 overflow-y-auto space-y-1">
        {slots.length === 0 && (
          <div className="flex flex-col items-center justify-center h-full text-center py-8">
            <div className="w-14 h-14 rounded-2xl bg-slate-50 flex items-center justify-center mb-4 text-slate-300">
              <IconClock />
            </div>
            <span className="text-[14px] font-semibold text-slate-400">No schedule loaded</span>
            <span className="text-[12px] text-slate-300 mt-1">Reset to load today's appointments</span>
          </div>
        )}
        {slots.map((slot) => {
          const s = STATUS_STYLE[slot.status];
          return (
            <div key={slot.id} className={`flex items-center gap-3 px-3 py-2.5 rounded-xl transition-all ${s.bg}`}>
              {/* Time */}
              <div className="w-16 shrink-0">
                <span className="text-[13px] font-semibold text-slate-800 tabular-nums">{slot.time}</span>
              </div>

              {/* Status dot */}
              <div className={`w-2 h-2 rounded-full shrink-0 ${s.dot}`} />

              {/* Treatment + Patient */}
              <div className="flex-1 min-w-0">
                <div className={`text-[12px] font-medium truncate ${s.text}`}>
                  {slot.treatment}
                </div>
                <div className="text-[11px] text-slate-400 truncate">
                  {slot.patient_name || (slot.status === 'cancelled' ? 'Open slot' : '—')}
                </div>
              </div>

              {/* Value */}
              <div className="text-[11px] text-slate-400 font-mono tabular-nums shrink-0">
                ${slot.value}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

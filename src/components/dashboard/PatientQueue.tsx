export interface Patient {
  name: string;
  age?: number;
  phone: string;
  lastCleaning: string;
  status: 'calling' | 'no_answer' | 'sms_sent' | 'confirmed' | 'queued' | 'skipped';
}

interface Props {
  patients: Patient[];
}

const STATUS_STYLE: Record<Patient['status'], { label: string; cls: string }> = {
  calling:    { label: 'CALLING',    cls: 'bg-[#7DF9FF]/15 text-[#0097A7] border border-[#7DF9FF]/20' },
  no_answer:  { label: 'NO ANSWER',  cls: 'bg-amber-50 text-amber-600 border border-amber-100' },
  sms_sent:   { label: 'SMS SENT',   cls: 'bg-purple-50 text-purple-600 border border-purple-100' },
  confirmed:  { label: 'CONFIRMED',  cls: 'bg-green-50 text-green-600 border border-green-100' },
  queued:     { label: 'QUEUED',      cls: 'bg-gray-50 text-gray-400 border border-gray-100' },
  skipped:    { label: 'SKIPPED',     cls: 'bg-gray-50 text-gray-300 border border-gray-50' },
};

export function PatientQueue({ patients }: Props) {
  return (
    <div
      className="bg-white rounded-2xl p-5 flex flex-col h-full"
      style={{ boxShadow: '0 1px 3px rgba(0,0,0,0.04), 0 6px 16px rgba(0,0,0,0.04)' }}
    >
      <div className="flex items-center justify-between mb-3 px-1">
        <span className="text-[11px] font-semibold tracking-[0.08em] text-gray-400 uppercase">
          Outreach Queue
        </span>
        <span className="text-[11px] text-gray-300 tabular-nums">
          {patients.filter(p => p.status === 'queued').length} remaining
        </span>
      </div>

      <div className="flex-1 overflow-y-auto space-y-0.5">
        {patients.map((p, i) => {
          const s = STATUS_STYLE[p.status];
          return (
            <div
              key={i}
              className={`flex items-center justify-between px-3 py-2.5 rounded-xl transition-all duration-300 ${
                p.status === 'calling' ? 'bg-[#7DF9FF]/[0.06]' : 'hover:bg-gray-50'
              }`}
            >
              <div className="flex items-center gap-3 min-w-0">
                <div className="relative shrink-0">
                  <div className={`w-2 h-2 rounded-full ${
                    p.status === 'calling' ? 'bg-[#7DF9FF]' :
                    p.status === 'confirmed' ? 'bg-green-500' :
                    p.status === 'no_answer' ? 'bg-amber-400' :
                    p.status === 'sms_sent' ? 'bg-purple-400' :
                    'bg-gray-200'
                  }`} />
                  {p.status === 'calling' && (
                    <div className="absolute inset-0 rounded-full bg-[#7DF9FF] animate-ping opacity-60" />
                  )}
                </div>
                <div className="min-w-0">
                  <div className="text-[13px] text-gray-800 font-medium truncate">
                    {p.name}
                    {p.age && <span className="text-gray-400 font-normal ml-1">({p.age})</span>}
                  </div>
                  <div className="text-[11px] text-gray-400 truncate">
                    {p.phone} &middot; {p.lastCleaning}
                  </div>
                </div>
              </div>
              <span className={`text-[9px] font-bold px-2 py-0.5 rounded-full shrink-0 ml-2 ${s.cls}`}>
                {s.label}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}

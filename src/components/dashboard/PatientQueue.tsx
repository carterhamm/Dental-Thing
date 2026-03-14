export interface Patient {
  name: string;
  lastCleaning: string;
  phone: string;
  status: 'calling' | 'no_answer' | 'sms_sent' | 'confirmed' | 'queued' | 'skipped';
}

interface Props {
  patients: Patient[];
}

const STATUS_STYLE: Record<Patient['status'], { label: string; cls: string }> = {
  calling:    { label: 'CALLING',    cls: 'bg-[#7DF9FF]/15 text-[#0097A7]' },
  no_answer:  { label: 'NO ANSWER',  cls: 'bg-amber-50 text-amber-600' },
  sms_sent:   { label: 'SMS SENT',   cls: 'bg-purple-50 text-purple-600' },
  confirmed:  { label: 'CONFIRMED',  cls: 'bg-green-50 text-green-600' },
  queued:     { label: 'QUEUED',      cls: 'bg-gray-100 text-gray-400' },
  skipped:    { label: 'SKIPPED',     cls: 'bg-gray-50 text-gray-300' },
};

export function PatientQueue({ patients }: Props) {
  return (
    <div className="bg-white rounded-2xl shadow-sm p-6 flex flex-col h-full">
      <div className="flex items-center justify-between mb-3">
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
              className={`flex items-center justify-between px-3 py-2.5 rounded-xl transition-colors ${
                p.status === 'calling' ? 'bg-[#7DF9FF]/8' : 'hover:bg-gray-50'
              }`}
            >
              <div className="flex items-center gap-3">
                <div className={`w-1.5 h-1.5 rounded-full shrink-0 ${
                  p.status === 'calling' ? 'bg-[#7DF9FF] animate-pulse' :
                  p.status === 'confirmed' ? 'bg-green-500' :
                  'bg-gray-200'
                }`} />
                <div>
                  <div className="text-[13px] text-gray-800 font-medium">{p.name}</div>
                  <div className="text-[11px] text-gray-400">{p.lastCleaning}</div>
                </div>
              </div>
              <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full ${s.cls}`}>
                {s.label}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}

import { IconUsers } from '../Icons';

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

const STATUS_STYLE: Record<Patient['status'], { label: string; cls: string; ringCls: string }> = {
  calling:    { label: 'CALLING',    cls: 'bg-[#E0FCFF] text-[#006B7A] border border-[#7DF9FF]/30', ringCls: 'bg-[#7DF9FF] text-[#006B7A]' },
  no_answer:  { label: 'MISSED',     cls: 'bg-amber-50 text-amber-700 border border-amber-200/50', ringCls: 'bg-amber-100 text-amber-600' },
  sms_sent:   { label: 'TEXTED',     cls: 'bg-purple-50 text-purple-700 border border-purple-200/50', ringCls: 'bg-purple-100 text-purple-600' },
  confirmed:  { label: 'CONFIRMED',  cls: 'bg-emerald-50 text-emerald-700 border border-emerald-200/50', ringCls: 'bg-emerald-100 text-emerald-600' },
  queued:     { label: 'QUEUED',      cls: 'bg-slate-50 text-slate-400 border border-slate-100', ringCls: 'bg-slate-100 text-slate-400' },
  skipped:    { label: 'SKIPPED',     cls: 'bg-slate-50 text-slate-300 border border-slate-50', ringCls: 'bg-slate-50 text-slate-300' },
};

function getInitials(name: string) {
  return name.split(' ').map(n => n[0]).join('').slice(0, 2).toUpperCase();
}

export function PatientQueue({ patients }: Props) {
  return (
    <div className="bg-white rounded-2xl p-5 flex flex-col h-full border border-slate-100"
      style={{ boxShadow: '0 1px 3px rgba(0,0,0,0.03), 0 6px 16px rgba(0,0,0,0.04)' }}>
      <div className="flex items-center justify-between mb-3 px-1">
        <div className="flex items-center gap-2">
          <div className="w-7 h-7 rounded-lg bg-[#E0FCFF] text-[#0097A7] flex items-center justify-center">
            <IconUsers />
          </div>
          <span className="text-[12px] font-semibold text-slate-500 uppercase tracking-[0.06em]">Queue</span>
        </div>
        <span className="text-[11px] text-slate-300 font-mono tabular-nums">
          {patients.filter(p => p.status === 'queued').length} remaining
        </span>
      </div>

      <div className="flex-1 overflow-y-auto space-y-1">
        {patients.length === 0 && (
          <div className="flex flex-col items-center justify-center h-full text-center py-8">
            <div className="w-14 h-14 rounded-2xl bg-slate-50 flex items-center justify-center mb-4 text-slate-300">
              <IconUsers />
            </div>
            <span className="text-[14px] font-semibold text-slate-400">No patients queued</span>
            <span className="text-[12px] text-slate-300 mt-1">Candidates appear when the agent starts</span>
          </div>
        )}
        {patients.map((p, i) => {
          const s = STATUS_STYLE[p.status];
          return (
            <div key={i} className={`flex items-center justify-between px-3 py-3 rounded-xl transition-all duration-200 ${
              p.status === 'calling' ? 'bg-[#7DF9FF]/[0.06] border border-[#7DF9FF]/10' : 'hover:bg-slate-50'
            }`}>
              <div className="flex items-center gap-3 min-w-0">
                <div className={`w-9 h-9 rounded-full ${s.ringCls} flex items-center justify-center shrink-0 text-[11px] font-bold relative`}>
                  {getInitials(p.name)}
                  {p.status === 'calling' && (
                    <span className="absolute -top-0.5 -right-0.5 w-3 h-3 rounded-full bg-[#7DF9FF] border-2 border-white animate-pulse" />
                  )}
                </div>
                <div className="min-w-0">
                  <div className="text-[13px] text-slate-800 font-semibold truncate">
                    {p.name}
                    {p.age && <span className="text-slate-400 font-normal ml-1 text-[11px]">({p.age})</span>}
                  </div>
                  <div className="text-[11px] text-slate-400 truncate font-mono">
                    {p.phone} &middot; {p.lastCleaning}
                  </div>
                </div>
              </div>
              <span className={`text-[9px] font-bold px-2.5 py-1 rounded-full shrink-0 ml-2 ${s.cls}`}>
                {s.label}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}

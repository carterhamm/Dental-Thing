import { IconBot } from '../Icons';

export type AgentPhase = 'idle' | 'calling' | 'no_answer' | 'sms_sent' | 'sms_reply' | 'booking' | 'filled';

interface Props {
  phase: AgentPhase;
  currentPatient: string;
  attempt: number;
  totalPatients: number;
}

const PHASE_CFG: Record<AgentPhase, { label: string; color: string; dotColor: string; desc: string; borderColor: string }> = {
  idle:       { label: 'STANDBY',     color: 'text-slate-400',   dotColor: 'bg-slate-300', desc: 'Waiting for cancellation...', borderColor: 'border-slate-200' },
  calling:    { label: 'CALLING',     color: 'text-[#006B7A]',   dotColor: 'bg-[#7DF9FF]', desc: 'Calling via Twilio', borderColor: 'border-[#7DF9FF]/40' },
  no_answer:  { label: 'NO ANSWER',   color: 'text-amber-600',   dotColor: 'bg-amber-400', desc: 'No answer — switching to SMS', borderColor: 'border-amber-200' },
  sms_sent:   { label: 'TEXTING',     color: 'text-purple-600',  dotColor: 'bg-purple-400', desc: 'Waiting for text reply', borderColor: 'border-purple-200' },
  sms_reply:  { label: 'CONFIRMED',   color: 'text-[#006B7A]',   dotColor: 'bg-[#7DF9FF]', desc: 'Patient confirmed!', borderColor: 'border-[#7DF9FF]/40' },
  booking:    { label: 'BOOKING',     color: 'text-amber-600',   dotColor: 'bg-amber-400', desc: 'Confirming appointment', borderColor: 'border-amber-200' },
  filled:     { label: 'COMPLETE',    color: 'text-emerald-600', dotColor: 'bg-emerald-400', desc: 'Appointment booked successfully', borderColor: 'border-emerald-200' },
};

export function AgentStatus({ phase, currentPatient, attempt, totalPatients }: Props) {
  const cfg = PHASE_CFG[phase];
  const isActive = phase !== 'idle' && phase !== 'filled';
  const pct = totalPatients > 0 ? (attempt / totalPatients) * 100 : 0;

  if (phase === 'idle' && totalPatients === 0) {
    return (
      <div className="bg-white rounded-2xl p-6 flex flex-col items-center justify-center h-full border border-dashed border-slate-200"
        style={{ boxShadow: '0 1px 3px rgba(0,0,0,0.03)' }}>
        <div className="w-14 h-14 rounded-2xl bg-[#E0FCFF] flex items-center justify-center mb-4 text-[#0097A7]">
          <IconBot />
        </div>
        <span className="text-[14px] font-semibold text-slate-400">Agent standing by</span>
        <span className="text-[12px] text-slate-300 mt-1 text-center">Trigger a cancellation to<br/>start outreach</span>
      </div>
    );
  }

  return (
    <div className={`rounded-2xl p-6 flex flex-col justify-between h-full border ${cfg.borderColor} relative overflow-hidden transition-all duration-500 bg-gradient-to-br from-white via-white to-[#E0FCFF]/10`}
      style={{ boxShadow: '0 1px 3px rgba(0,0,0,0.04), 0 8px 20px rgba(0,0,0,0.04)' }}>

      {/* Corner glow when active */}
      {isActive && <div className="absolute -top-8 -right-8 w-28 h-28 rounded-full bg-[#7DF9FF] blur-3xl opacity-20" />}

      <div className="relative">
        <div className="flex items-center justify-between mb-5">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-lg bg-[#E0FCFF] text-[#0097A7] flex items-center justify-center">
              <IconBot />
            </div>
            <span className="text-[12px] font-semibold text-slate-500 uppercase tracking-[0.06em]">Agent Status</span>
          </div>
          <div className="flex items-center gap-2">
            <span className={`w-2 h-2 rounded-full ${cfg.dotColor} ${isActive ? 'animate-pulse' : ''}`} />
            <span className={`text-[11px] font-bold ${cfg.color}`}>{cfg.label}</span>
          </div>
        </div>

        {phase !== 'idle' ? (
          <>
            <div className="text-slate-900 text-[18px] font-bold mb-1">{currentPatient}</div>
            <div className="text-slate-400 text-[13px] font-medium">{cfg.desc}</div>
            {phase === 'calling' && (
              <div className="flex items-center gap-1.5 mt-4">
                {[0, 1, 2, 3, 4].map(i => (
                  <div key={i} className="w-1.5 rounded-full bg-[#7DF9FF]"
                    style={{
                      height: `${10 + Math.sin(i * 1.3) * 8}px`,
                      animation: `shimmer ${0.5 + i * 0.12}s ease-in-out infinite`,
                      animationDelay: `${i * 0.08}s`,
                    }} />
                ))}
                <span className="text-[11px] text-[#0097A7] ml-2 font-semibold">Ringing...</span>
              </div>
            )}
          </>
        ) : (
          <div className="text-slate-300 text-[13px] font-medium">{cfg.desc}</div>
        )}
      </div>

      <div className="relative mt-5 pt-4 border-t border-slate-100">
        <div className="flex items-center justify-between text-[11px] text-slate-400 mb-2.5 font-semibold">
          <span>Outreach progress</span>
          <span className="font-mono tabular-nums">{attempt} / {totalPatients}</span>
        </div>
        <div className="w-full h-2.5 rounded-full bg-slate-100 overflow-hidden">
          <div className="h-full rounded-full transition-all duration-700 relative"
            style={{
              width: `${pct}%`,
              background: 'linear-gradient(90deg, #7DF9FF, #00D4E0)',
              boxShadow: pct > 0 ? '0 0 12px rgba(125,249,255,0.5), 0 0 4px rgba(125,249,255,0.3)' : 'none',
            }} />
        </div>
      </div>
    </div>
  );
}
